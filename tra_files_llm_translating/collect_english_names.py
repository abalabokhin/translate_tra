import re
import csv
import argparse
from wordfreq import zipf_frequency
from collections import OrderedDict

ZIPF_THRESH = 4.0  # threshold for common English words
TOKEN_OK_RE = re.compile(r"^[A-Z][A-Za-z'’-]*$")

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

def collect_fantasy_names_from_tra_file(tra_file, dictionary_csv=None, blacklist_file=None):
    existing = load_dictionary(dictionary_csv) if dictionary_csv else set()
    blacklist = load_blacklist(blacklist_file) if blacklist_file else set()

    all_expressions = []
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
    return list(seen.keys())

# ---------------- CLI ----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract fantasy names from .tra files (text inside ~…~)"
    )
    parser.add_argument("tra_file", help="Path to .tra file to process")
    parser.add_argument("-d", "--dictionary", help="Optional CSV dictionary file (first column = names)")
    parser.add_argument("-b", "--blacklist", help="Optional blacklist file (one word/expression per line)")

    args = parser.parse_args()

    new_names = collect_fantasy_names_from_tra_file(
        args.tra_file,
        dictionary_csv=args.dictionary,
        blacklist_file=args.blacklist
    )

    print("\n".join(new_names))
