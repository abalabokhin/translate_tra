#!/usr/bin/env python3
"""
Dialog Translation Script for Game Dialogs
Translates CSV dialog files from English to Russian using local LLM (Ollama)
"""

import csv
import os
import sys
import json
import time
from pathlib import Path
import urllib.request
import urllib.parse
from typing import Dict, List, Tuple, Optional


class DialogTranslator:
    def __init__(self, source_folder: str = "english", target_folder: str = "russian",
                 actors_file: str = "actors.csv", dict_file: str = "dict.csv",
                 model: str = "qwen2.5:72b-instruct", test_mode: bool = False,
                 ollama_url: str = None):
        self.source_folder = Path(source_folder)
        self.target_folder = Path(target_folder)
        self.actors_file = Path(actors_file)
        self.dict_file = Path(dict_file)
        self.model = model
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.test_mode = test_mode
        
        # Load actors and dictionary data
        self.actors = self._load_actors()
        self.dictionary = self._load_dictionary()
        
        # Create target folder if it doesn't exist
        self.target_folder.mkdir(exist_ok=True)
    
    def _load_actors(self) -> Dict[str, str]:
        """Load actor information from actors.csv"""
        actors = {}
        if self.actors_file.exists():
            with open(self.actors_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        actors[row[0].strip()] = row[1].strip().lower()
        return actors
    
    def _load_dictionary(self) -> Dict[str, List[Tuple[str, str]]]:
        """Load translation dictionary from dict.csv
        Returns dict mapping English -> list of (Russian translation, Russian comment) tuples
        Supports multiple translations for the same word with different contexts
        """
        dictionary = {}
        if self.dict_file.exists():
            with open(self.dict_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        english = row[0].strip()
                        russian = row[1].strip()
                        comment = row[2].strip() if len(row) >= 3 and row[2].strip() else ""

                        # Add to list of translations for this word
                        if english not in dictionary:
                            dictionary[english] = []
                        dictionary[english].append((russian, comment))
        return dictionary
    
    def _get_actors_in_dialog(self, csv_file: Path) -> List[str]:
        """Get list of unique actors in the dialog file"""
        actors = set()
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 1 and row[0].strip():
                    actors.add(row[0].strip())
        return list(actors)
    
    def _build_actor_info(self, actors_in_dialog: List[str]) -> str:
        """Build actor information string for the prompt"""
        actor_info = []
        for actor in actors_in_dialog:
            if actor in self.actors:
                actor_info.append(f'"{actor}" is a {self.actors[actor]}')
        return ". ".join(actor_info) + "." if actor_info else ""
    
    def _build_dictionary_context(self, dialog_text: str) -> str:
        """Build dictionary context for words that appear in the dialog"""
        import re

        relevant_translations = []
        matched_positions = set()  # Track which positions have been matched

        # Sort dictionary entries by length (descending) to match longer phrases first
        sorted_dict_items = sorted(self.dictionary.items(), key=lambda x: len(x[0]), reverse=True)

        for english_word, translations_list in sorted_dict_items:
            # Create a regex pattern with word boundaries
            # Use \b for word boundaries to match whole words/phrases only
            pattern = r'\b' + re.escape(english_word) + r'\b'

            # Find all matches in the dialog text (case-insensitive)
            for match in re.finditer(pattern, dialog_text, re.IGNORECASE):
                start, end = match.span()

                # Check if this position range overlaps with already matched positions
                if not any(pos in matched_positions for pos in range(start, end)):
                    # Mark these positions as matched
                    matched_positions.update(range(start, end))

                    # Build translation rule based on number of translations
                    if len(translations_list) == 1:
                        # Single translation
                        russian_word, comment = translations_list[0]
                        if comment:
                            translation_rule = f'"{english_word}" should be translated as "{russian_word}" ({comment})'
                        else:
                            translation_rule = f'"{english_word}" should be translated as "{russian_word}"'
                    else:
                        # Multiple translations - list all options
                        options = []
                        for russian_word, comment in translations_list:
                            if comment:
                                options.append(f'"{russian_word}" ({comment})')
                            else:
                                options.append(f'"{russian_word}"')
                        translation_rule = f'"{english_word}" should be translated as {" or ".join(options)} depending on context'

                    if translation_rule not in relevant_translations:
                        relevant_translations.append(translation_rule)
                    break  # Found at least one match for this dictionary entry

        return " ".join(relevant_translations) + "." if relevant_translations else ""
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API to get translation"""
        if self.test_mode:
            # Return different mock translations based on context
            if "Translate independent game text lines" in prompt:
                # Unused lines translation - extract references and mock translate
                lines = prompt.split("Lines to translate:")[1].split("Return ONLY")[0].strip().split('\n')
                result = []
                for line in lines:
                    if '|' in line:
                        ref, text = line.split('|', 1)
                        result.append(f"{ref}|[ТЕСТ ПЕРЕВОД] {text[:30]}...")
                return '\n'.join(result)
            elif "Previously translated CSV for male Player1:" in prompt:
                # Female version referencing male translation
                return '''ACTOR,UNIQUE LINE NUMBER,PREVIOUS LINE NUMBER(S),LINE
Cassia,"1",,~(Кассия глубоко дышит, когда её взгляд опускается на землю, и что-то шепчет себе, прежде чем снова поднять глаза и дать тебе резкий кивок.)~
Cassia,"2","1",~Просто сохраняй спокойствие и сосредоточься на поставленной задаче. Я постараюсь помнить твои слова.~
Cassia,"3","2",~И... спасибо тебе за терпение со мной. Я стараюсь держать свои эмоции под контролем, как только могу, но боюсь, что стресс от ситуации добрался до меня.~
Player1,"4","3",~Это понятно, я думаю. У меня тоже много мыслей в голове с момента лавины.~
Player1,"5","3",~Подавлять свои эмоции не очень полезно, знаешь. Не бойся высказывать своё мнение, если что-то тебя беспокоит.~'''
            else:
                # Male version or neutral
                return '''ACTOR,UNIQUE LINE NUMBER,PREVIOUS LINE NUMBER(S),LINE
Cassia,"1",,~(Кассия глубоко дышит, когда её взгляд опускается на землю, и что-то шепчет себе, прежде чем снова поднять глаза и дать тебе резкий кивок.)~
Cassia,"2","1",~Просто сохраняй спокойствие и сосредоточься на поставленной задаче. Я постараюсь помнить твои слова.~
Cassia,"3","2",~И... спасибо тебе за терпение со мной. Я стараюсь держать свои эмоции под контролем, как только могу, но боюсь, что стресс от ситуации добрался до меня.~
Player1,"4","3",~Это понятно, я полагаю. У меня тоже много мыслей в голове с момента лавины.~
Player1,"5","3",~Подавлять свои эмоции не очень полезно, знаешь. Не бойся высказывать своё мнение, если что-то тебя беспокоит.~'''
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.ollama_url, data=data,
                                       headers={'Content-Type': 'application/json'})

            with urllib.request.urlopen(req, timeout=3600) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("response", "").strip()
        except urllib.error.URLError as e:
            if "Connection refused" in str(e):
                print(f"Error: Cannot connect to Ollama at {self.ollama_url}")
                print("Make sure Ollama is running: ollama serve")
                print("Or set OLLAMA_URL environment variable to the correct address")
            else:
                print(f"Error calling Ollama: {e}")
            return ""
        except TimeoutError:
            print(f"Error: Request to Ollama timed out (3600 seconds)")
            print("The model might be too large or your system too slow")
            print("Try using a smaller model like: ollama pull qwen2.5:7b-instruct")
            return ""
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            print("Make sure Ollama is running: ollama serve")
            print(f"And the model is available: ollama pull {self.model}")
            return ""
    
    def _read_csv_content(self, csv_file: Path) -> List[List[str]]:
        """Read CSV file and return all rows"""
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)
        return rows
    
    def _write_csv_content(self, csv_file: Path, rows: List[List[str]]):
        """Write rows to CSV file"""
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    
    def _create_translation_prompt(self, csv_content: str, player1_gender: str, 
                                   actor_info: str, dict_context: str, 
                                   previous_translation: str = None) -> str:
        """Create the translation prompt"""
        if previous_translation is None:
            # First translation (male version)
            base_prompt = f"""Translate the dialog tree in Russian. The dialog tree is defined in CSV format, every new dialog line is defined by a new row. The meaning of the columns in CSV is the next:
1. First column is the actor: the one who says every dialog line.
2. The second column is every dialog line unique number.
3. The third column is the number(s) of the line followed by the current line. If it is empty, that means that this line is the first in the dialog, if it has more than one number (semicolon separated), this line should be translated to be a good following line after the lines with all of these numbers.
4. The fourth column is the dialog line itself to translate.

Additional information how to translate properly:
1. People in the dialog should address each other using T distinction, not V distinction. Eg they should use "ты", "тебе", "твоё" instead of "вы", "вам", "ваше" if they address one person.
2. "<PLAYER1>" is the name of "Player1", leave this without translation, but put it in the proper place, so the addressing of Player1 by his/her name is suitable.
3. The result should be the same CSV, with the fourth column translated in Russian."""
        else:
            # Second translation (female version) - reference the male translation
            base_prompt = f"""Now translate the same CSV in Russian with the same requirements but Player1 is female now. Use the Russian lines from already translated CSV if they are appropriate for both Player1's genders.

The dialog tree is defined in CSV format, every new dialog line is defined by a new row. The meaning of the columns in CSV is the next:
1. First column is the actor: the one who says every dialog line.
2. The second column is every dialog line unique number.
3. The third column is the number(s) of the line followed by the current line. If it is empty, that means that this line is the first in the dialog, if it has more than one number (semicolon separated), this line should be translated to be a good following line after the lines with all of these numbers.
4. The fourth column is the dialog line itself to translate.

Additional information how to translate properly:
1. People in the dialog should address each other using T distinction, not V distinction. Eg they should use "ты", "тебе", "твоё" instead of "вы", "вам", "ваше" if they address one person.
2. "<PLAYER1>" is the name of "Player1", leave this without translation, but put it in the proper place, so the addressing of Player1 by his/her name is suitable.
3. The result should be the same CSV, with the fourth column translated in Russian.

Previously translated CSV for male Player1:
{previous_translation}"""
        
        if actor_info:
            base_prompt += f"\n\nThe information about actors: {actor_info}"
        else:
            base_prompt += f"\n\nPlayer1 is {player1_gender}."
        
        if dict_context:
            base_prompt += f"\n\nAdditional translation requirements: {dict_context}"
        
        base_prompt += f"\n\nThe CSV to translate is:\n{csv_content}"
        
        return base_prompt
    
    def _needs_gender_variants(self, csv_file: Path) -> bool:
        """Check if dialog contains Player1 and needs gender variants"""
        actors_in_dialog = self._get_actors_in_dialog(csv_file)
        return "Player1" in actors_in_dialog
    
    def translate_dialog_file(self, csv_file: Path):
        """Translate a single dialog CSV file"""
        print(f"Processing {csv_file.name}...")
        
        # Read the original CSV
        rows = self._read_csv_content(csv_file)
        if not rows:
            print(f"Warning: {csv_file.name} is empty")
            return
        
        # Convert to string for the prompt
        csv_content = ""
        for row in rows:
            csv_content += ','.join(f'"{cell}"' if ',' in cell or '"' in cell else cell for cell in row) + '\n'
        
        # Get actors in this dialog
        actors_in_dialog = self._get_actors_in_dialog(csv_file)
        actor_info = self._build_actor_info(actors_in_dialog)
        dict_context = self._build_dictionary_context(csv_content)
        
        # Check if we need gender variants
        needs_gender_variants = self._needs_gender_variants(csv_file)
        
        if needs_gender_variants:
            # Translate for male Player1 first
            print(f"  Translating {csv_file.name} for male Player1...")
            male_start_time = time.time()
            male_prompt = self._create_translation_prompt(csv_content, "male", actor_info, dict_context)
            male_translation = self._call_ollama(male_prompt)
            male_end_time = time.time()
            male_duration = male_end_time - male_start_time
            
            if male_translation:
                male_output = self.target_folder / f"{csv_file.stem}_male.csv"
                self._save_translation_result(male_translation, male_output)
                print(f"  Saved: {male_output} (took {male_duration:.2f} seconds)")
                
                # Now translate for female Player1 using male translation as context
                print(f"  Translating {csv_file.name} for female Player1 (using male translation as reference)...")
                female_start_time = time.time()
                female_prompt = self._create_translation_prompt(csv_content, "female", actor_info, dict_context, male_translation)
                female_translation = self._call_ollama(female_prompt)
                female_end_time = time.time()
                female_duration = female_end_time - female_start_time
                
                if female_translation:
                    female_output = self.target_folder / f"{csv_file.stem}_female.csv"
                    self._save_translation_result(female_translation, female_output)
                    print(f"  Saved: {female_output} (took {female_duration:.2f} seconds)")
            else:
                print(f"  Error: Failed to translate male version, skipping female version")
        else:
            # Single translation (no Player1 or gender doesn't matter)
            print(f"  Translating {csv_file.name}...")
            start_time = time.time()
            prompt = self._create_translation_prompt(csv_content, "neutral", actor_info, dict_context)
            translation = self._call_ollama(prompt)
            end_time = time.time()
            duration = end_time - start_time
            
            if translation:
                output = self.target_folder / csv_file.name
                self._save_translation_result(translation, output)
                print(f"  Saved: {output} (took {duration:.2f} seconds)")
    
    def _save_translation_result(self, translation_text: str, output_file: Path):
        """Save the translation result to a CSV file"""
        # Try to extract CSV content from the response
        lines = translation_text.strip().split('\n')
        csv_lines = []
        
        # Look for CSV content in the response
        in_csv = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this looks like a CSV line
            if '"' in line or ',' in line:
                in_csv = True
                csv_lines.append(line)
            elif in_csv and not line.startswith('"') and ',' not in line:
                # Probably not CSV anymore
                break
        
        if csv_lines:
            # Write the CSV content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(csv_lines))
        else:
            # Fallback: write the entire response
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(translation_text)
    
    def translate_unused_lines_file(self, csv_file: Path):
        """Translate the special _unused_tra_lines.csv file with independent lines"""
        print(f"Processing unused TRA lines from {csv_file.name}...")

        # Read the CSV file
        rows = self._read_csv_content(csv_file)
        if not rows or len(rows) < 2:  # Need at least header + 1 line
            print(f"Warning: {csv_file.name} is empty or has only header")
            return

        header = rows[0]
        if len(header) < 2 or header[0] != "Reference" or header[1] != "Text":
            print(f"Warning: {csv_file.name} has unexpected format")
            return

        # Prepare output with additional column for translation
        output_rows = [["Reference", "English_Text", "Russian_Text"]]

        # Process lines in batches for efficiency (10 lines per request)
        batch_size = 10
        total_lines = len(rows) - 1  # Exclude header
        processed = 0

        for batch_start in range(1, len(rows), batch_size):
            batch_end = min(batch_start + batch_size, len(rows))
            batch_rows = rows[batch_start:batch_end]

            print(f"  Translating lines {batch_start} to {batch_end-1} of {total_lines}...")

            # Build batch content and collect dictionary context
            batch_content = ""
            all_text = ""
            for row in batch_rows:
                if len(row) >= 2:
                    reference = row[0]
                    text = row[1]
                    all_text += text + " "
                    batch_content += f"{reference}|{text}\n"

            # Get dictionary context for all text in this batch
            dict_context = self._build_dictionary_context(all_text)

            # Create simplified prompt for independent lines
            prompt = self._create_unused_lines_prompt(batch_content.strip(), dict_context)

            # Call LLM
            start_time = time.time()
            translation = self._call_ollama(prompt)
            end_time = time.time()
            duration = end_time - start_time

            if translation:
                # Parse the translation result
                translated_lines = self._parse_unused_lines_result(translation)

                # Match translations with original lines
                for i, row in enumerate(batch_rows):
                    if len(row) >= 2:
                        reference = row[0]
                        english_text = row[1]

                        # Find corresponding translation
                        russian_text = translated_lines.get(reference, "")
                        if not russian_text:
                            # Fallback: use by index if reference lookup fails
                            if i < len(translated_lines):
                                russian_text = list(translated_lines.values())[i]

                        output_rows.append([reference, english_text, russian_text])

                processed += len(batch_rows)
                print(f"  Processed {processed}/{total_lines} lines (took {duration:.2f} seconds)")
            else:
                print(f"  Error: Failed to translate batch starting at line {batch_start}")
                # Add lines without translation
                for row in batch_rows:
                    if len(row) >= 2:
                        output_rows.append([row[0], row[1], ""])

        # Save the result
        output_file = self.target_folder / csv_file.name
        self._write_csv_content(output_file, output_rows)
        print(f"Saved: {output_file}")

    def _create_unused_lines_prompt(self, batch_content: str, dict_context: str) -> str:
        """Create translation prompt for unused lines (independent lines)"""
        prompt = """Translate independent game text lines from English to Russian. These are NOT part of dialogues - they are standalone lines like item descriptions, journal entries, system messages, etc.

Input format: Each line is "Reference|English text"
Output format: Return each line as "Reference|Russian translation"

Translation requirements:
1. Use informal address (T-distinction): "ты", "тебе", "твоё" instead of "вы", "вам", "ваше" when addressing one person
2. Keep any special markup like <PLAYER1>, ~, *, [], etc. unchanged in their proper positions
3. Each line is independent - translate based on its own context"""

        if dict_context:
            prompt += f"\n\nAdditional translation requirements: {dict_context}"

        prompt += f"\n\nLines to translate:\n{batch_content}"
        prompt += "\n\nReturn ONLY the translated lines in the same format (Reference|Russian translation), nothing else:"

        return prompt

    def _parse_unused_lines_result(self, translation_text: str) -> Dict[str, str]:
        """Parse the translation result for unused lines"""
        translations = {}

        lines = translation_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to parse "Reference|Translation" format
            if '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2:
                    reference = parts[0].strip()
                    translation = parts[1].strip()
                    translations[reference] = translation

        return translations

    def translate_all_dialogs(self):
        """Translate all CSV files in the source folder"""
        if not self.source_folder.exists():
            print(f"Error: Source folder '{self.source_folder}' does not exist")
            return

        csv_files = list(self.source_folder.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in '{self.source_folder}'")
            return

        print(f"Found {len(csv_files)} CSV file(s) to translate")
        print(f"Actors loaded: {self.actors}")
        print(f"Dictionary entries: {len(self.dictionary)}")
        print()

        for csv_file in csv_files:
            try:
                # Check if this is the special unused lines file
                if csv_file.name == "_unused_tra_lines.csv":
                    self.translate_unused_lines_file(csv_file)
                else:
                    self.translate_dialog_file(csv_file)
            except Exception as e:
                print(f"Error processing {csv_file.name}: {e}")

        print("\nTranslation completed!")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Translate dialog CSV files using Ollama')
    parser.add_argument('source_folder', nargs='?', default='english',
                       help='Source folder containing CSV files (default: english)')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode with mock translations')
    parser.add_argument('--model', default='qwen2.5:72b-instruct',
                       help='Ollama model to use (default: qwen2.5:72b-instruct)')
    parser.add_argument('--url',
                       help='Ollama API URL (default: http://localhost:11434/api/generate)')
    parser.add_argument('--target', default='russian',
                       help='Target folder for translated files (default: russian)')

    args = parser.parse_args()

    translator = DialogTranslator(
        source_folder=args.source_folder,
        target_folder=args.target,
        model=args.model,
        test_mode=args.test,
        ollama_url=args.url
    )
    translator.translate_all_dialogs()


if __name__ == "__main__":
    main()
