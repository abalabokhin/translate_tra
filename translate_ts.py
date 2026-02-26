#!/usr/bin/env python3

import os
import xml.etree.ElementTree as ET
import re
import argparse
import deepl
from pathlib import Path

class TSTranslator:
    def __init__(self, target_lang='RU', force_update=False, remove_unfinished=False, test_mode=False):
        self.translation_dict = {}
        self.deepl_translator = None
        self.target_lang = target_lang.upper()
        self.force_update = force_update
        self.remove_unfinished = remove_unfinished
        self.test_mode = test_mode
        self.test_count = 0
        self._load_deepl_api()
    
    def _load_deepl_api(self):
        """Load DeepL API key from file"""
        try:
            with open('DEEPL_API_KEY', 'r') as file:
                deepl_key = file.read().strip()
                self.deepl_translator = deepl.Translator(deepl_key)
        except FileNotFoundError:
            print("Warning: DEEPL_API_KEY file not found. DeepL translation will not be available.")
        except Exception as e:
            print(f"Error loading DeepL API key: {e}")
    
    def build_translation_dictionary(self, ts_files):
        """Build dictionary from all existing translations in .ts files.

        Each entry is {'text': str, 'finished': bool}.
        Finished entries always take priority over unfinished ones.
        Unfinished non-empty entries are included only when not in --force-update mode.
        """
        print("Building translation dictionary from existing translations...")

        for ts_file in ts_files:
            print(f"Processing {ts_file}...")
            try:
                tree = ET.parse(ts_file)
                root = tree.getroot()

                for message in root.findall('.//message'):
                    source_elem = message.find('source')
                    translation_elem = message.find('translation')

                    if source_elem is not None and translation_elem is not None:
                        source_text = source_elem.text or ""
                        translation_text = translation_elem.text or ""
                        is_unfinished = translation_elem.get('type') == 'unfinished'

                        if not translation_text.strip():
                            continue

                        if not is_unfinished:
                            # Finished entries always win
                            self.translation_dict[source_text] = {'text': translation_text, 'finished': True}
                        elif not self.force_update and source_text not in self.translation_dict:
                            # Unfinished entries only in default mode, and only if no entry yet
                            self.translation_dict[source_text] = {'text': translation_text, 'finished': False}

            except Exception as e:
                print(f"Error processing {ts_file}: {e}")

        finished_count = sum(1 for e in self.translation_dict.values() if e['finished'])
        unfinished_count = len(self.translation_dict) - finished_count
        print(f"Built dictionary with {finished_count} finished and {unfinished_count} unfinished translations")
    
    def translate_text(self, text):
        """Translate text using DeepL API"""
        try:
            result = self.deepl_translator.translate_text(text, target_lang=self.target_lang)
            return str(result)
        except deepl.exceptions.QuotaExceededException:
            print(f"DeepL quota exceeded while translating: '{text}'")
            print("Stopping execution due to quota limit.")
            raise
        except Exception as e:
            print(f"Error translating '{text}': {e}")
            return None
    
    def process_ts_file(self, ts_file):
        """Process a single .ts file, translating unfinished entries"""
        print(f"Processing {ts_file}...")
        
        try:
            # Read the original file content
            with open(ts_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ET.parse(ts_file)
            root = tree.getroot()
            
            translations_updated = 0
            modified_content = content
            
            for message in root.findall('.//message'):
                source_elem = message.find('source')
                translation_elem = message.find('translation')
                
                if (source_elem is not None and
                    translation_elem is not None and
                    translation_elem.get('type') == 'unfinished'):

                    source_text = source_elem.text or ""
                    existing_translation = translation_elem.text or ""

                    if not source_text.strip():
                        continue

                    new_translation = None
                    should_remove_tag = self.remove_unfinished  # default, may be overridden below

                    dict_entry = self.translation_dict.get(source_text)

                    if dict_entry and dict_entry['finished']:
                        # Finished translation in dict: always use it and always remove tag
                        new_translation = dict_entry['text']
                        should_remove_tag = True
                        print(f"  Using finished translation: '{source_text}' -> '{new_translation}'")

                    elif not self.force_update and existing_translation.strip():
                        # Default mode: don't touch non-empty unfinished lines (may be human-edited)
                        print(f"  Skipping non-empty unfinished: '{source_text}'")
                        continue

                    elif dict_entry:
                        # Unfinished entry in dict: reuse to avoid a duplicate DeepL call
                        new_translation = dict_entry['text']
                        print(f"  Reusing unfinished translation: '{source_text}' -> '{new_translation}'")

                    else:
                        # Not in dict: call DeepL
                        new_translation = self.translate_text(source_text)
                        if new_translation and new_translation != source_text:
                            print(f"  DeepL translation: '{source_text}' -> '{new_translation}'")
                            # Add to dict so the same source isn't translated twice in this run
                            self.translation_dict[source_text] = {'text': new_translation, 'finished': False}
                            if self.test_mode:
                                self.test_count += 1

                    if new_translation:
                        source_pattern = re.escape(source_text).replace(r'\ ', r'\s*')
                        # Use (?:(?!</message>)[\s\S])*? to prevent matching across message boundaries
                        no_msg_end = r'(?:(?!</message>)[\s\S])*?'
                        message_pattern = (r'(<message\b' + no_msg_end + r'<source[^>]*>)' +
                                         source_pattern +
                                         r'(</source>' + no_msg_end + r'<translation[^>]*type=(["\'])unfinished\3[^>]*>)([^<]*)(</translation>' + no_msg_end + r'</message>)')

                        match = re.search(message_pattern, modified_content)
                        if match:
                            replacement = (match.group(1) + source_text + match.group(2) +
                                         new_translation + match.group(5))
                            if should_remove_tag:
                                replacement = re.sub(r'\s*type=(["\'])unfinished\1', '', replacement)
                            modified_content = modified_content.replace(match.group(0), replacement)
                            translations_updated += 1
                            if self.test_mode and self.test_count >= 3:
                                break
            
            if translations_updated > 0:
                # Write the modified content back to the file
                with open(ts_file, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                print(f"  Updated {translations_updated} translations in {ts_file}")
            else:
                print(f"  No translations updated in {ts_file}")
                # File remains unchanged - original formatting preserved
                
        except deepl.exceptions.QuotaExceededException:
            # Re-raise quota exceeded to stop all processing
            raise
        except Exception as e:
            print(f"Error processing {ts_file}: {e}")
    
    def translate_all_ts_files(self, folders=None):
        """Main method to translate all matching .ts files in the given folders"""
        if folders is None:
            folders = ['.']

        lang_suffix = f"_{self.target_lang.lower()}"
        ts_files = []
        for folder in folders:
            folder_path = Path(folder)
            if not folder_path.is_dir():
                print(f"Warning: '{folder}' is not a directory, skipping")
                continue
            matched = [f for f in sorted(folder_path.rglob('*.ts'))
                       if f.stem.lower().endswith(lang_suffix)]
            ts_files.extend(matched)

        if not ts_files:
            print(f"No *{lang_suffix}.ts files found in: {folders}")
            return

        print(f"Found {len(ts_files)} .ts files: {[str(f) for f in ts_files]}")
        
        # Step 1: Build translation dictionary
        self.build_translation_dictionary(ts_files)
        
        if self.test_mode:
            print("Test mode: will make up to 3 DeepL calls then stop")

        # Step 2: Process each file for unfinished translations
        try:
            for ts_file in ts_files:
                self.process_ts_file(str(ts_file))
                if self.test_mode and self.test_count >= 3:
                    print(f"Test mode: reached 3 DeepL calls, stopping")
                    return
            print("Translation process completed!")
        except deepl.exceptions.QuotaExceededException:
            print("Translation stopped due to DeepL quota exceeded.")
            print("Partial translations have been saved.")
            return

def main():
    parser = argparse.ArgumentParser(description='Translate .ts files using DeepL')
    parser.add_argument('folders', nargs='*', default=['.'],
                        help='Folders to search recursively for .ts files (default: current directory)')
    parser.add_argument('--lang', default='RU', help='Target language code (default: RU)')
    parser.add_argument('--force-update', action='store_true',
                        help='Retranslate all unfinished lines, even non-empty ones')
    parser.add_argument('--remove-unfinished', action='store_true',
                        help='Remove type="unfinished" attribute after translating')
    parser.add_argument('--test', action='store_true',
                        help='Translate only the first 10 untranslated lines then save and exit')
    args = parser.parse_args()

    translator = TSTranslator(
        target_lang=args.lang,
        force_update=args.force_update,
        remove_unfinished=args.remove_unfinished,
        test_mode=args.test,
    )
    translator.translate_all_ts_files(args.folders)

if __name__ == '__main__':
    main()
