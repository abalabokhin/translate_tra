# translate_tra

Collection of Python scripts for working with TRA files (localization files for Infinity Engine games like Baldur's Gate, Icewind Dale, etc.). Includes translation, text processing, and dialogue parsing tools.

## Complete mod translation routine

See the [seven-step workflow, commands and script-readiness audit](tra_files_llm_translating/README.md#complete-mod-routine-and-readiness-audit--2026-11-07):
collect new dictionary names, review/translate them, associate CRE genders with
dialogue actors, extract CSVs, translate with Codex, rebuild Russian TRA files,
then install and review. The audit found blocking gaps in dictionary handling
and all-source extraction, so the full InkGallery translation is stopped before
step 1. Codex/Sol/low/simultaneous output is the chosen workflow; commands specify
it explicitly because the current bare CLI still defaults to Ollama.

## Main Scripts

### Translation: `translate_tra.py`
Translates TRA files using various translation engines:
```bash
python3 translate_tra.py infile.tra [--engine=googletrans|deepl|googlecloud] [--lang=ru]
```

### D File Dialogue Parsing

#### `parse_d_grammar.py` ⭐ **RECOMMENDED**
Advanced grammar-based parser using complete ANTLR4 grammar:
- Extracts @NUMBER dialogue references and inventories remaining TRA entries
- **State-level dialogue grouping** - Proper dialogue flow connections  
- **Multi-speaker support** - Handles CHAIN dialogues with speaker changes
- Uses an ANTLR grammar; known CHAIN/EXTERN flow limitations are documented in the workflow

```bash
python3 tra_files_llm_translating/parse_d_grammar.py <d_folder> <tra_folder> <output_folder>
```

#### `parse_d_complete.py`
Regex-based D file parser for comparison/fallback:
```bash
python3 parse_d_complete.py <d_folder> <tra_folder> <output_folder>
```

## Installation

For the complete mod workflow, follow the
[preparation instructions and complete workflow dependency list](tra_files_llm_translating/README.md#preparation-python-environment-and-tools).
Use Python 3.10+ and the repository virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
python -m ensurepip --upgrade
python -m pip install chardet antlr4-python3-runtime==4.9.2 wordfreq
python -m pip check
```

Additional optional packages for older translation/text-processing utilities
outside that workflow:
```bash
pip install googletrans==4.0.0rc1 textblob pycld2 google-cloud-translate
pip install deepl colorama click levenshtein nltk
```

## Translation Engines
* **googletrans** - Free, unlimited requests, basic quality
* **deepl** - High quality, requires API key  
* **googlecloud** - Best quality, requires authentication and billing

## D File Grammar Parsing
The grammar-based parser uses ANTLR4 with complete WeiDU D file grammar for robust parsing. ANTLR4 files are included - no need to regenerate unless modifying the grammar.
