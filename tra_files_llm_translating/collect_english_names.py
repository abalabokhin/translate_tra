import re
import csv
import argparse
import os
import glob
from wordfreq import zipf_frequency
from collections import OrderedDict

ZIPF_THRESH = 3.5  # threshold for common English words
TOKEN_OK_RE = re.compile(r"^[A-Z][A-Za-z''-]*$")


def is_common_word(word):
    return zipf_frequency(word.lower(), "en") >= ZIPF_THRESH

def extract_text_from_tra_line(line):
    match = re.search(r'~(.*?)~', line)
    return match.group(1) if match else None

def collect_fantasy_names_from_text(text, min_words=1):
    """Extract consecutive capitalized words and filter common words."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    expressions = []

    for sent in sentences:
        tokens = sent.split()
        if not tokens:
            continue

        current = []
        for i, tok in enumerate(tokens):
            if i == 0:
                continue  # skip first word of sentence

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

    def keep(expr):
        words = expr.split()
        if len(words) < min_words:
            return False
        # Check that each individual word is uncommon (not a common English word)
        return all(not is_common_word(w) for w in words)

    return [e for e in expressions if keep(e)]

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
                bl.add(line)
    return bl

def save_to_dictionary(dictionary_csv, new_words):
    """Add new words to dictionary file in alphabetical order."""
    if not dictionary_csv or not new_words:
        return

    # Load existing rows (preserving translations if they exist)
    existing_rows = {}
    try:
        with open(dictionary_csv, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():  # Skip empty rows
                    existing_rows[row[0]] = row
    except FileNotFoundError:
        # Dictionary file doesn't exist yet
        pass

    # Add new words (without translations initially)
    for word in new_words:
        if word not in existing_rows:
            existing_rows[word] = [word]

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

def collect_fantasy_names_from_tra_files(tra_path, dictionary_csv=None, blacklist_file=None):
    existing = load_dictionary(dictionary_csv) if dictionary_csv else set()
    blacklist = load_blacklist(blacklist_file) if blacklist_file else set()

    # Get list of TRA files to process
    tra_files = get_tra_files(tra_path)
    print(f"Processing {len(tra_files)} TRA file(s)...")

    all_expressions = []
    for tra_file in tra_files:
        print(f"Processing: {os.path.basename(tra_file)}")
        with open(tra_file, encoding="utf-8") as f:
            for line in f:
                text = extract_text_from_tra_line(line)
                if text:
                    names = collect_fantasy_names_from_text(text)
                    for name in names:
                        if name not in existing and name not in blacklist:
                            all_expressions.append(name)

    # remove duplicates
    seen = OrderedDict()
    for e in all_expressions:
        if e not in seen:
            seen[e] = None

    unique_expressions = list(seen.keys())

    # Split multiword expressions if their parts exist as standalone expressions
    # Also check against dictionary during splitting
    final_expressions = []
    single_words = {expr for expr in unique_expressions if len(expr.split()) == 1}

    for expr in unique_expressions:
        words = expr.split()
        if len(words) > 1:
            # Check if this multiword expression is already in dictionary
            if expr in existing:
                continue  # Skip if already in dictionary

            # Check if any word in this multiword expression exists as a standalone
            if any(word in single_words for word in words):
                # Split into individual words, but only add those not in dictionary
                for word in words:
                    if word not in existing:
                        final_expressions.append(word)
            else:
                # Keep the multiword expression if not in dictionary
                final_expressions.append(expr)
        else:
            # Single word, add if not in dictionary
            if expr not in existing:
                final_expressions.append(expr)

    # Remove duplicates again after splitting
    final_seen = OrderedDict()
    for e in final_expressions:
        if e not in final_seen:
            final_seen[e] = None

    new_words = list(final_seen.keys())

    # Save new words to dictionary file
    if dictionary_csv and new_words:
        save_to_dictionary(dictionary_csv, new_words)

    return new_words

# ---------------- CLI ----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract fantasy names from .tra files or folders (text inside ~…~)"
    )
    parser.add_argument("tra_path", help="Path to .tra file or folder containing .tra files")
    parser.add_argument("-d", "--dictionary", help="Optional CSV dictionary file (first column = names)")
    parser.add_argument("-b", "--blacklist", help="Optional blacklist file (one word/expression per line)")

    args = parser.parse_args()

    try:
        new_names = collect_fantasy_names_from_tra_files(
            args.tra_path,
            dictionary_csv=args.dictionary,
            blacklist_file=args.blacklist
        )

        print("\nNew names found:")
        print("\n".join(new_names))
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
