# TRA parser: format, scope and regression coverage

The shared parser is `tra_format.py`. Dictionary collection, dialogue extraction
and CSV-to-TRA export use it instead of separate line-based TRA regular expressions.
The name collector scans only parsed literal text from both gender variants.
Comments, sound names, entry IDs and runtime reference names are not candidates.

## Sources and grammar

Checked against primary WeiDU sources on 2026-11-07:

- [WeiDU documentation: strings/text, comments and TRA translation files](https://weidu.org/WeiDU/README-WeiDU.html).
- [WeiDU's actual D/TRA parser grammar](https://github.com/WeiDUorg/weidu/blob/devel/src/dparser.mly): `tra_file`, `lse`, `lse_string`, `sound_opt`.
- [WeiDU's lexer template](https://github.com/WeiDUorg/weidu/blob/devel/src/tlexer.in): literal delimiters, signed numeric references, sounds and nested comments.

WeiDU has an upstream grammar, but there is no dedicated generated TRA grammar
in this repository. `DParser.g4` / `DLexer.g4` describe D dialogue scripts. The
new [TRA.ebnf](TRA.ebnf) records our supported static syntax. The Python reader
implements it directly and retains exact literal spans for format-preserving
updates; running it requires no new grammar generator or runtime dependency.
It is not a complete WeiDU interpreter.

## Literal text and metadata

An entry has an `@number`, an equals sign and a value. Normal values have one
text variant or a male/female pair. Each variant may have its own sound:

```text
// Comments and sound names are metadata, not dictionary words.
@1 /* header comment */ = ~Zyxxara returned.
She met Qyzzorin.~ [VOICE_M]
/* between variants */ "Vraxxala returned.
She met Qyzzorin." [VOICE_F]
```

Supported features and regression checks:

| Feature | Behavior / coverage |
| --- | --- |
| Delimiters | Tilde, double quote, percent and five tildes; multiline and empty literals. |
| Gender pairs | Both variants; identical or empty variants; sounds on either, both or neither. |
| Sounds | Optional bracketed tokens, including empty sounds; preserved verbatim, outside text. |
| Concatenation | `^` joins literal parts without inserting spaces; each gender can concatenate independently. |
| Comments | Line and nested block comments between tokens, including before `=`, between parts/variants and before sounds. Fake entries inside comments are ignored. |
| Literal punctuation | Comment syntax, `@N`, brackets, engine tags and other delimiters inside a string remain literal content. Backslashes are not C-style escapes. |
| Layout | LF, CRLF and CR line endings; adjacent entries; EOF comments; initial Unicode BOM. |
| IDs | Signed decimal IDs and leading zeros; values normalize to Python integers. |
| Duplicate IDs | Strict updater mode rejects them; dictionary inspection explicitly selects the last definition. |
| Encoding | UTF-8/BOM, UTF-16/BOM, UTF-32/BOM and CP1251 regression cases through the encoding reader. Other legacy encodings use chardet and depend on detection. |
| Updates | Male/female sounds, intervening comments, concatenation trivia, unrelated entries and line endings survive literal replacement. A safe alternate delimiter is chosen if needed. |
| Errors | Truncated literals/comments/sounds, missing `=`, bad concatenations, excess variants/sounds and trailing unsupported syntax fail explicitly. |

Tests: `tests/test_tra_format.py` contains parser and replacement tests, including
48 delimiter/line-ending/gender-sound combinations and additional single-string
sound cases. `tests/test_collect_english_names.py` checks the actual collector
and CLI output, candidate/location deduplication, filters, comment/sound exclusion,
reference-only values and malformed input leaving the dictionary unchanged.
The existing translation pipeline tests additionally exercise TRA export.

```bash
source venv/bin/activate
python -m unittest discover -s tra_files_llm_translating/tests -p test_tra_format.py -v
python -m unittest discover -s tra_files_llm_translating/tests -p test_collect_english_names.py -v
python -m unittest discover -s tra_files_llm_translating/tests -q
```

## Inspection versus runtime-dependent references

Default `parse_tra(content)` accepts literal values and rejects duplicate IDs or
values needing reference semantics, preserving existing export behavior.
Dictionary collection uses:

```python
entries = parse_tra(content, allow_references=True, duplicate_policy='last')
for entry in entries.values():
    for variant in entry.variants:
        # Only variant.text is sent to the candidate-name heuristic.
        pass
```

Inspection recognizes `#123`, `@123` and `(AT "variable")` values as reference
metadata with no literal variants. It does not read TLK files, resolve aliases,
look up variables or invent text for them. A forced-reference prefix such as
`!123 ~Actual text~` retains the number as metadata and exposes the embedded
literal text without performing any engine write. The updater refuses to rewrite
these reference-bearing entries even when supplied through inspection mode.
Literal names reached only through an external TLK/reference are outside the
collector's physical input-text scope; dictionary collection does not need to
execute WeiDU to discover them.

The upstream lexer also allows some bare identifier-like strings. This reader
requires delimited literals; it rejects bare strings and arbitrary expressions.
Other pipeline stages may impose narrower constraints on IDs/routing than the
shared syntax reader. These are documented boundaries, not a claim that every
valid WeiDU program can be evaluated by this parser.

Dictionary collection follows the user's skip-existing policy: known English
keys are not added or modified, including untranslated entries. Existing rows
are retained, including any duplicates. Only genuinely new entries are saved and
reported; repeated runs do not append duplicate source locations. Tests cover
this separately from TRA parsing. The real dictionary was not modified by this
implementation or its tests.
