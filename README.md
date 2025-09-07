# translate_tra

Collection of Python scripts for working with TRA files (localization files for Infinity Engine games like Baldur's Gate, Icewind Dale, etc.). Includes translation, text processing, and dialogue parsing tools.

## Main Scripts

### Translation: `translate_tra.py`
Translates TRA files using various translation engines:
```bash
python3 translate_tra.py infile.tra [--engine=googletrans|deepl|googlecloud] [--lang=ru]
```

### D File Dialogue Parsing

#### `parse_d_grammar.py` ⭐ **RECOMMENDED**
Advanced grammar-based parser using complete ANTLR4 grammar:
- **100% TRA reference capture** - All @NUMBER dialogue references
- **State-level dialogue grouping** - Proper dialogue flow connections  
- **Multi-speaker support** - Handles CHAIN dialogues with speaker changes
- **Complete grammar coverage** - Supports all WeiDU D file constructs

```bash
python3 parse_d_grammar.py <d_folder> <tra_folder> <output_folder>
```

#### `parse_d_complete.py`
Regex-based D file parser for comparison/fallback:
```bash
python3 parse_d_complete.py <d_folder> <tra_folder> <output_folder>
```

## Installation

Install required Python packages:
```bash
pip install googletrans==4.0.0rc1 textblob pycld2 google-cloud-translate
pip install deepl colorama click chardet levenshtein nltk antlr4-python3-runtime
```

## Translation Engines
* **googletrans** - Free, unlimited requests, basic quality
* **deepl** - High quality, requires API key  
* **googlecloud** - Best quality, requires authentication and billing

## D File Grammar Parsing
The grammar-based parser uses ANTLR4 with complete WeiDU D file grammar for robust parsing. ANTLR4 files are included - no need to regenerate unless modifying the grammar.
