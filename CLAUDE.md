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

### File Management and Processing
- `generate_global_renaming_table.py` - Creates renaming tables for game files with prefixes
- `find_closest_lines_in_tra.py` - Finds similar lines between TRA files using Levenshtein distance
- `update_tra.py` - Updates TRA files based on mapping tables
- `extract_lines_tra.py` - Extracts specific lines from TRA files

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

- All main scripts follow similar pattern: file reading with encoding detection, regex-based text processing, and safe file writing
- Text processing uses regex patterns to identify TRA file structure (@number = ~text~ or @number = "text")
- Translation engines are abstracted to allow switching between different providers
- Dictionary-based text processing for Russian language improvements
- File collision handling in renaming operations with automatic suffix generation