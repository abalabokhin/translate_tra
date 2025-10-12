# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a collection of Python scripts for working with TRA files (localization files for Infinity Engine games like Baldur's Gate, Icewind Dale, etc.). The main functionality includes translation, text processing, and file management for game modding.

## Key Scripts and Usage

### Primary Translation Script
- `translate_tra.py` - Main translation script for TRA files
  ```bash
  python3 translate_tra.py infile.tra [--engine=googletrans|deepl|googlecloud] [--lang=ru] [--out=output.tra]
  ```
  - Supports multiple translation engines: googletrans (free), deepl (API key required), googlecloud (authentication required)
  - Default engine is deepl, default language is Russian (ru)
  - Automatically detects file encoding using chardet

### Russian Text Processing
- `yo_making.py` - Converts Russian е to ё based on dictionary
  ```bash
  python3 yo_making.py infile.tra [--out=output.tra] [--always-no]
  ```
  - Uses `russian_yo_words.txt` and `russian_yo_words_both.txt` dictionaries
  - Interactive mode for ambiguous cases unless `--always-no` specified

### Dialogue Processing (D Files)
- `parse_d_grammar.py` - **Primary dialogue parser** using ANTLR4 grammar
  ```bash
  python3 parse_d_grammar.py d_folder tra_folder output_folder
  ```
  - Parses D dialogue files using proper ANTLR4 grammar (robust, handles all constructs)
  - Extracts SAY lines (NPC dialogue) and REPLY lines (player responses)
  - Resolves @number references from TRA files
  - Creates one CSV per connected dialogue with proper flow tracking
  - Generates `_unused_tra_lines.csv` containing lines not used in dialogues (setup, journal entries, etc.)
  - Uses `DParser.g4` and `DLexer.g4` grammar files

- `translate_dialogs.py` - Translates dialogue CSV files using local LLM (Ollama)
  ```bash
  python3 translate_dialogs.py [source_folder] [--target target_folder] [--model model_name]
  ```
  - Translates CSV dialog files from English to Russian using Ollama
  - Supports gender-specific translations for Player1
  - Handles `_unused_tra_lines.csv` with batch translation (10 lines per request)
  - Uses `actors.csv` for character information
  - Uses `dict.csv` for translation dictionary with context
  - Dictionary features: word boundaries, prioritizes longer phrases, supports multiple translations with context

- `update_tra_from_csv.py` - Updates TRA files with translations from CSV files
  ```bash
  python3 update_tra_from_csv.py tra_folder csv_folder [--output output_folder]
  ```
  - Reads translated dialogue CSVs (male/female variants) and unused lines CSV
  - Updates original TRA files with Russian translations
  - Preserves original formatting, comments, and sound references
  - Gender handling: same translation → single line, different → `~male~ ~female~` format
  - Only updates lines with TRA references (ignores D file direct text)
  - Output encoding: UTF-8

### File Management and Processing
- `generate_global_renaming_table.py` - Creates renaming tables for game files with prefixes
- `find_closest_lines_in_tra.py` - Finds similar lines between TRA files using Levenshtein distance
- `update_tra.py` - Updates TRA files based on mapping tables
- `extract_lines_tra.py` - Extracts specific lines from TRA files
- `extract_actors_using_grammar.py` - Extracts actor names from D files using grammar parser

## Dependencies

Install required Python packages:
```bash
pip install googletrans==4.0.0rc1
pip install textblob
pip install pycld2
pip install google-cloud-translate
pip install deepl
pip install colorama
pip install click
pip install chardet
pip install levenshtein
pip install nltk
pip install antlr4-python3-runtime  # For D file grammar parsing
```

## TRA File Format

TRA files contain localization strings in this format:
```
@1 = ~English text here~
@2 = "Another format with quotes"
```

Scripts automatically detect delimiters (~~ or "") and preserve formatting.

## Virtual Environment

A virtual environment exists in `venv/` directory. Activate with:
```bash
source venv/bin/activate
```

## File Encoding

Scripts automatically detect file encoding using chardet and preserve original encoding when saving files. Common encodings handled include UTF-8, CP1251, CP1252, and others.

## Shell Scripts

Various utility scripts for encoding conversion and batch processing:
- `utf8_2_cp1251.sh`, `cp1251_2_utf8.sh` - Encoding conversion utilities
- `folder_processing.sh` - Batch processing for folders
- `traify.sh` - Quick TRA file processing

## Architecture Notes

- All main scripts follow similar pattern: file reading with encoding detection, text processing, and safe file writing
- TRA file parsing uses regex patterns to identify structure (@number = ~text~ or @number = "text")
- **D file parsing uses ANTLR4 grammar** (`DParser.g4`, `DLexer.g4`) for robust parsing of all dialogue constructs (IF-THEN, CHAIN, APPEND, etc.)
- Translation engines are abstracted to allow switching between different providers
- Dictionary-based text processing for Russian language improvements with:
  - Word boundary matching to avoid partial matches
  - Prioritization of longer phrases over shorter ones
  - Support for multiple context-dependent translations
- File collision handling in renaming operations with automatic suffix generation

## D File Dialogue Format

D files contain dialogue scripts for Infinity Engine games. Key constructs:
- `APPEND ~NPC~ ... END` - Append dialogue to existing NPC
- `IF ~condition~ THEN BEGIN state_id ... END` - Dialogue state with condition
- `SAY @number` - NPC dialogue line (references TRA file)
- `++ @number GOTO target` - Player reply option
- `CHAIN ... EXIT` - Sequential dialogue chain
- `EXTERN ~NPC~ state` - Jump to another NPC's dialogue

The grammar-based parser (`parse_d_grammar.py`) handles all these constructs correctly.