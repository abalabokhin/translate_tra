import re
import csv
import argparse
import os
import glob
from wordfreq import zipf_frequency
from collections import OrderedDict

ZIPF_THRESH = 2.5  # threshold for common English words
TOKEN_OK_RE = re.compile(r"^[A-Z][A-Za-z''-]*$")


def is_common_word(word):
    # For words with hyphens or apostrophes, check each part separately
    if '-' in word or "'" in word:
        # Split on hyphens and apostrophes, filter empty parts
        parts = re.split(r"[-']", word)
        parts = [part for part in parts if part and len(part) > 1]  # Skip single letters

        # If any part is a common word, consider the whole thing common
        for part in parts:
            if zipf_frequency(part.lower(), "en") >= ZIPF_THRESH:
                return True
        return False
    else:
        return zipf_frequency(word.lower(), "en") >= ZIPF_THRESH

def is_valid_fantasy_name(word):
    """Check if a word is a valid fantasy name (not onomatopoeia, repetitive patterns, etc.)"""
    # Skip words that are all caps common English words
    if word.isupper() and is_common_word(word):
        return False

    word_upper = word.upper()
    # Skip words with excessive repetition of letter pairs or 3+ consecutive letters
    if re.match(r'^(.)\1{3,}', word_upper) or re.match(r'^(.{2})\1{2,}', word_upper):
        return False

    # Skip words with 3 or more consecutive identical letters anywhere in the word
    if re.search(r'(.)\1{2,}', word_upper):
        return False

    return True

def extract_text_from_tra_line(line):
    match = re.search(r'~(.*?)~', line)
    return match.group(1) if match else None

def collect_fantasy_names_from_text(text, min_words=1, location_info=None):
    """Extract consecutive capitalized words and filter common words."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    expressions = []

    for sent in sentences:
        tokens = sent.split()
        if not tokens:
            continue

        current = []
        for tok in tokens:
            clean = tok.strip("()\"'"".,;:!?")
            clean = clean.replace("'", "'").replace("'", "'").replace("–", "-").replace("—", "-")

            # Remove possessive forms - any apostrophe-like character followed by 's or alone
            # Include regular apostrophe ('), right single quotation (\u2019), and backtick (`)
            if clean.endswith("'s") or clean.endswith("\u2019s") or clean.endswith("`s"):
                clean = clean[:-2]
            elif clean.endswith("'") or clean.endswith("\u2019") or clean.endswith("`"):
                clean = clean[:-1]

            if TOKEN_OK_RE.match(clean) and clean:
                current.append(clean)
            else:
                if current:
                    expressions.append(" ".join(current))
                    current = []
        if current:
            expressions.append(" ".join(current))

    def normalize_capitalization(word):
        """Convert all-caps words to proper case (first letter capitalized)"""
        if word.isupper() and len(word) > 1:
            return word.capitalize()
        return word

    def process_word(word):
        """Process a word - if it's compound, extract valid parts, otherwise return as-is"""
        if '-' in word or "'" in word:
            # Split compound words and check each part
            parts = re.split(r"[-']", word)
            parts = [part for part in parts if part and len(part) > 1]  # Skip single letters

            valid_parts = []
            for part in parts:
                # Skip parts that don't start with capital letter (after normalization)
                normalized_part = normalize_capitalization(part)
                if not normalized_part[0].isupper():
                    continue

                # Keep parts that are uncommon and valid fantasy names
                if not is_common_word(part) and is_valid_fantasy_name(part):
                    valid_parts.append(normalized_part)

            return valid_parts
        else:
            # Single word - check if it's valid
            if not is_common_word(word) and is_valid_fantasy_name(word):
                normalized_word = normalize_capitalization(word)
                # Skip words that don't start with capital letter (after normalization)
                if not normalized_word[0].isupper():
                    return []
                return [normalized_word]
            else:
                return []

    def keep_and_expand(expr):
        words = expr.split()
        if len(words) < min_words:
            return []

        all_valid_words = []
        for word in words:
            valid_parts = process_word(word)
            all_valid_words.extend(valid_parts)

        return all_valid_words

    # Process all expressions and collect valid words/parts
    final_words = []
    for expr in expressions:
        valid_words = keep_and_expand(expr)
        final_words.extend(valid_words)

    # If location_info provided, return tuples of (word, location), otherwise just words
    if location_info:
        return [(word, location_info) for word in final_words]
    else:
        return final_words

def load_dictionary(csv_file):
    existing = set()
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                existing.add(row[0])
    return existing

def load_blacklist(file_path):
    bl = set()
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                bl.add(line.upper())
    return bl

def save_to_dictionary(dictionary_csv, new_word_locations, comment=""):
    """Add new words with locations to dictionary file in alphabetical order."""
    if not dictionary_csv or not new_word_locations:
        return

    # Load existing rows (preserving translations if they exist)
    existing_rows = {}
    try:
        with open(dictionary_csv, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():  # Skip empty rows
                    # Extend row to 4 columns if needed
                    while len(row) < 4:
                        row.append("")
                    existing_rows[row[0]] = row
    except FileNotFoundError:
        # Dictionary file doesn't exist yet
        pass

    # Process new word locations
    for word, location in new_word_locations:
        if word in existing_rows:
            # Word exists - check if translation exists (column 1 not empty)
            if existing_rows[word][1].strip():
                # Translation exists, don't add location
                continue
            else:
                # No translation, add/update location info
                if len(existing_rows[word]) < 3:
                    existing_rows[word].extend(["", location, comment])
                elif len(existing_rows[word]) < 4:
                    # Append to existing locations
                    if existing_rows[word][2].strip():
                        existing_rows[word][2] += "; " + location
                    else:
                        existing_rows[word][2] = location
                    existing_rows[word].append(comment)
                else:
                    # Append to existing locations
                    if existing_rows[word][2].strip():
                        existing_rows[word][2] += "; " + location
                    else:
                        existing_rows[word][2] = location
                    # Update comment if provided
                    if comment:
                        existing_rows[word][3] = comment
        else:
            # New word - add with empty translation, location, and comment
            existing_rows[word] = [word, "", location, comment]

    # Write back in alphabetical order
    with open(dictionary_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for word in sorted(existing_rows.keys()):
            writer.writerow(existing_rows[word])

def get_tra_files(path):
    """Get list of TRA files from a file or folder path."""
    if os.path.isfile(path):
        if path.lower().endswith('.tra'):
            return [path]
        else:
            raise ValueError(f"File {path} is not a .tra file")
    elif os.path.isdir(path):
        # Find all .tra files in the directory
        tra_files = glob.glob(os.path.join(path, "*.tra"))
        if not tra_files:
            raise ValueError(f"No .tra files found in directory {path}")
        return sorted(tra_files)  # Sort for consistent processing order
    else:
        raise ValueError(f"Path {path} does not exist")

def collect_fantasy_names_from_tra_files(tra_path, dictionary_csv=None, blacklist_file=None, comment=""):
    existing = load_dictionary(dictionary_csv) if dictionary_csv else set()
    blacklist = load_blacklist(blacklist_file) if blacklist_file else set()

    # Get list of TRA files to process
    tra_files = get_tra_files(tra_path)
    print(f"Processing {len(tra_files)} TRA file(s)...")

    all_word_locations = []
    for tra_file in tra_files:
        print(f"Processing: {os.path.basename(tra_file)}")
        abs_path = os.path.abspath(tra_file)
        with open(tra_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Look for @number pattern to get the TRA line identifier
                tra_match = re.match(r'^@(\d+)', line.strip())
                if tra_match:
                    tra_number = tra_match.group(1)
                    text = extract_text_from_tra_line(line)
                    if text:
                        location = f"{abs_path}@{tra_number}"
                        word_location_pairs = collect_fantasy_names_from_text(text, location_info=location)
                        for word, loc in word_location_pairs:
                            if word.upper() not in blacklist:
                                all_word_locations.append((word, loc))

    # Group locations by word and handle case normalization
    word_locations_map = {}
    for word, location in all_word_locations:
        # Normalize case (prefer proper case over all caps)
        key = word.upper()
        if key not in word_locations_map:
            word_locations_map[key] = {'word': word, 'locations': [location]}
        else:
            # Update word if this version is better (not all caps)
            existing_word = word_locations_map[key]['word']
            if existing_word.isupper() and not word.isupper():
                word_locations_map[key]['word'] = word

            # Add location if not already present
            if location not in word_locations_map[key]['locations']:
                word_locations_map[key]['locations'].append(location)

    # Convert to final format
    final_word_locations = []
    for entry in word_locations_map.values():
        word = entry['word']
        locations = "; ".join(entry['locations'])
        final_word_locations.append((word, locations))

    # Save new words to dictionary file
    if dictionary_csv and final_word_locations:
        save_to_dictionary(dictionary_csv, final_word_locations, comment)

    return [word for word, _ in final_word_locations]

# ---------------- CLI ----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract fantasy names from .tra files or folders (text inside ~…~)"
    )
    parser.add_argument("tra_path", help="Path to .tra file or folder containing .tra files")
    parser.add_argument("-d", "--dictionary", help="Optional CSV dictionary file (first column = names)")
    parser.add_argument("-b", "--blacklist", help="Optional blacklist file (one word/expression per line)")
    parser.add_argument("-c", "--comment", default="", help="Optional comment to add to the 4th column of CSV")

    args = parser.parse_args()

    try:
        new_names = collect_fantasy_names_from_tra_files(
            args.tra_path,
            dictionary_csv=args.dictionary,
            blacklist_file=args.blacklist,
            comment=args.comment
        )

        print("\nNew names found:")
        print("\n".join(new_names))
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
