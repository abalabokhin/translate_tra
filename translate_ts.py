#!/usr/bin/env python3

import os
import xml.etree.ElementTree as ET
import re
import deepl
from pathlib import Path

class TSTranslator:
    def __init__(self):
        self.translation_dict = {}
        self.deepl_translator = None
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
        """Build dictionary from all existing translations in .ts files"""
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
                        
                        # Only add non-empty translations that are not marked as unfinished
                        if (translation_text and 
                            translation_text.strip() and 
                            translation_elem.get('type') != 'unfinished'):
                            self.translation_dict[source_text] = translation_text
                            
            except Exception as e:
                print(f"Error processing {ts_file}: {e}")
        
        print(f"Built dictionary with {len(self.translation_dict)} translations")
    
    def translate_text(self, text):
        """Translate text using DeepL API"""
        try:
            result = self.deepl_translator.translate_text(text, target_lang='RU')
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
                    
                    if source_text.strip():
                        new_translation = None
                        
                        # First, check if translation exists in dictionary
                        if source_text in self.translation_dict:
                            new_translation = self.translation_dict[source_text]
                            print(f"  Found existing translation: '{source_text}' -> '{new_translation}'")
                        
                        # If not found in dictionary, use DeepL
                        else:
                            new_translation = self.translate_text(source_text)
                            if new_translation and new_translation != source_text:
                                print(f"  DeepL translation: '{source_text}' -> '{new_translation}'")
                                # Add the new translation to dictionary for future reuse
                                self.translation_dict[source_text] = new_translation
                        
                        # Update the translation if we found one
                        if new_translation:
                            # Find the translation tag in the original content and replace it
                            # Look for the pattern: <translation type="unfinished"></translation>
                            # or <translation type="unfinished"/>
                            escaped_source = re.escape(source_text)
                            
                            # Pattern to match the translation element with unfinished type
                            pattern = (r'(<translation[^>]*type=(["\'])unfinished\2[^>]*>)([^<]*)(</translation>)')
                            
                            # Find all matches and replace the appropriate one
                            matches = list(re.finditer(pattern, modified_content))
                            
                            # We need to find the right translation element that corresponds to our source
                            # This is complex, so let's use a simpler approach: find the message block
                            source_pattern = re.escape(source_text).replace(r'\ ', r'\s*')
                            message_pattern = (r'(<message[^>]*>.*?<source[^>]*>)' + 
                                             source_pattern + 
                                             r'(</source>.*?<translation[^>]*type=(["\'])unfinished\3[^>]*>)([^<]*)(</translation>.*?</message>)')
                            
                            match = re.search(message_pattern, modified_content, re.DOTALL)
                            if match:
                                # Replace with the new translation and remove type="unfinished"
                                replacement = (match.group(1) + source_text + match.group(2) + 
                                             new_translation + match.group(5))
                                # Remove type="unfinished" from the replacement
                                replacement = re.sub(r'\s*type=(["\'])unfinished\1', '', replacement)
                                modified_content = modified_content.replace(match.group(0), replacement)
                                translations_updated += 1
            
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
    
    def translate_all_ts_files(self):
        """Main method to translate all .ts files"""
        # Find all .ts files in current directory
        ts_files = list(Path('.').glob('*.ts'))
        
        if not ts_files:
            print("No .ts files found in current directory")
            return
        
        print(f"Found {len(ts_files)} .ts files: {[str(f) for f in ts_files]}")
        
        # Step 1: Build translation dictionary
        self.build_translation_dictionary(ts_files)
        
        # Step 2: Process each file for unfinished translations
        try:
            for ts_file in ts_files:
                self.process_ts_file(str(ts_file))
            print("Translation process completed!")
        except deepl.exceptions.QuotaExceededException:
            print("Translation stopped due to DeepL quota exceeded.")
            print("Partial translations have been saved.")
            return

def main():
    translator = TSTranslator()
    translator.translate_all_ts_files()

if __name__ == '__main__':
    main()
