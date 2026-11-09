# Dialogue translation with Codex or Ollama: workflow and experiment record

For a new session, read [SESSION_HANDOFF.md](SESSION_HANDOFF.md) first for the latest
state, user constraints and pending decisions.

This is the current reference for these scripts. It also records failed and
partially successful approaches so they are not accidentally reintroduced.

## Current choice — 2026-11-07

Use **Codex CLI, `gpt-6.1-sol`, explicit `low` effort, both genders in one request**
for the full-mod trial. The user authorized making this approach selectable in
the production translator. The [explicit-low reproduction](experiments/codex_translation/20261107-sol-low-one-repeat/SUMMARY.md)
completed all eight dialogues with both methods, one repeat, 24 requests.
Simultaneous output passed 338/340 targeted checks, the same rate as historical
1014/1020. Its two failures were valid neutral wording; assistant review found no
definite gender/meaning error in this sample. Two-pass scored 333/340 and had
four definite erroneous female lines. See the
[review](experiments/codex_translation/20261107-sol-low-one-repeat/MANUAL_REVIEW.md).

This supports the next complete-mod translation cycle with editorial review.
It does not establish unattended translation quality, full parser coverage or
five-hour subscription capacity. Historical resolved effort was not recorded;
the CLI version also changed, so the comparison does not isolate effort effects.
InkGallery's full translation cycle has not started. CHAIN-final EXTERN
continuations are linked by the current parser; broader graph boundaries are
listed below.

## Preparation: Python environment and tools

Use Python 3.10+ and the repository's virtual environment for every step. From
the repository root, create it if needed, activate it, and install all direct
Python dependencies of the seven-step workflow:

```bash
python3 -m venv venv
source venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install chardet antlr4-python3-runtime==4.9.2 wordfreq
python -m pip check
```

If `venv` is already healthy, start with activation. `ensurepip` repairs an
environment missing pip; it is harmless when pip is already available. Use this
environment rather than installing into an externally managed system Python.
After activation, the `python3` commands below use the virtual environment too.
Without activation, invoke `venv/bin/python` explicitly.

Verified in the project `venv` on 2026-11-07: `wordfreq 3.1.1`, `chardet 7.7.0`
and `antlr4-python3-runtime 4.9.2`. Package consistency, imports, a common-word
lookup and the collector's CLI startup pass; all 71 then-existing offline tests
passed in this environment. Dependency setup is complete. The collector now uses
the shared TRA parser and preserves existing dictionary context rows.

| Python package | Used by |
| --- | --- |
| `chardet` | TRA encoding detection, dialogue parsing, CRE/actor extraction. |
| `antlr4-python3-runtime==4.9.2` | Generated D grammar parser and actor extraction. Keep this version aligned with the checked-in generated parser. |
| `wordfreq` | Common-word filtering when collecting new English names. |

Pip installs these packages' transitive dependencies automatically. The remaining
workflow imports, including CSV/JSON, HTTP, subprocesses, binary reading and
`unittest`/mocking, are Python standard-library modules. There is no additional
Python OpenAI SDK or Ollama SDK requirement: Codex uses its executable and the
Ollama helpers use standard-library HTTP calls. The dependencies above cover the
name collector, dictionary finder, actor extractor, CSV extraction/translation,
TRA export and their offline tests; older unrelated utilities have separate
optional dependencies listed in the root README.

Verify the environment before modifying the dictionary or translating:

```bash
python -c "import chardet, antlr4, wordfreq; print('Workflow imports OK')"
python tra_files_llm_translating/collect_english_names.py --help
python -m unittest discover -s tra_files_llm_translating/tests -q
```

Non-Python tools: install/authenticate the Codex CLI for the chosen translation
backend (`codex login status` checks the existing login). For a local backend or
the current legacy dictionary translation finder, have Ollama running with the
chosen model installed. The final installation/review step needs WeiDU and a
supported game installation. Generated ANTLR Python files are already checked in;
the workflow does not need to regenerate the grammar to run.

## Complete mod routine and readiness audit — 2026-11-07

The agreed order is: collect new names → review/translate dictionary entries →
associate CRE genders with dialogue actors → build source CSVs → translate CSVs
with Codex → rebuild Russian TRA files → install and review in game.

**Step 1 is ready under the skip-existing policy below; later steps still have
gaps.** The commands below document the existing scripts; blocked steps must be
fixed before running the entire sequence on the real dictionary/mod. No dictionary
entries were added, no live translation was requested, and no mod source was
modified during this audit. Tests write only to temporary directories.

| Step | Existing script | Audit result |
| --- | --- | --- |
| 1. Collect new names | `collect_english_names.py` | Ready: complete TRA reading, skip-existing dictionary entries, deduplicated new locations and reporting only actual additions. |
| 2. Review/translate dictionary | Manual editing; `find_translations_with_llm.py` | Manual route available. Automatic finder is legacy Ollama-only, requires existing parallel Russian TRA files and still uses a narrow line parser. |
| 3. Associate CRE genders | `extract_actors_using_grammar.py` | With mod CREs and the BG2EE reference CREs/dialogue tables: all 42 speaking actors resolve (28 MALE, 10 FEMALE, 4 NEITHER). Empty declarations are excluded; NEITHER still needs translation context. |
| 4. Build source CSVs | `parse_d_grammar.py` | With TP2 analysis: 417 unique references across 56 dialogue CSVs; the other 178 entries are split into contextual BAF, journal and resource CSVs. Three installer-only entries deliberately stay English. Cross-file D targets are linked after parsing all sources; arbitrary runtime-generated resource transformations remain a boundary. |
| 5. Translate CSVs | `translate_dialogs.py` | Codex backend works in offline tests and shares the live-tested transport. Use explicit Codex options below; bare CLI still defaults to Ollama, so changing the global default is outstanding. |
| 6. Rebuild Russian TRA | `update_tra_from_csv.py` | Synthetic tests and an InkGallery mock round trip pass: all 598 entries/original variants preserved in 26 output TRA files. Does not register a new WeiDU language. |
| 7. Install/review | Game/WeiDU plus human review | Not performed; Russian language registration, unresolved strings, terminology and in-game review remain. |

The offline regression suite passes, including shared TRA parsing, name
collection and dictionary saving. This does not validate the legacy dictionary
translation finder or guarantee correct CRE classification, graph completeness
or Russian translation quality. The initial audit used system Python and found
`wordfreq` missing. Dependency installation is an environment preparation step,
not a script defect. The project `venv` is now the environment for the routine;
follow the preparation instructions above. The generated ANTLR parser identifies
itself as 4.9.2, which is why that runtime is pinned.

### Example paths

Run from the repository root. Use fresh work directories for separate trials;
keep actor CSVs outside the source/translated CSV directories, because those
folders are interpreted as translation inputs by their respective scripts.

```bash
mod_dir=work/InkGallery/InkGallery-v1.5/InkGallery
work_dir=work/InkGallery
glossary=tra_files_llm_translating/dict.csv
mkdir -p "$work_dir"
```

### 1. Collect new English names into the versioned dictionary

Collect new entries and review the dictionary diff:

```bash
python3 tra_files_llm_translating/collect_english_names.py \
  "$mod_dir/languages/english" \
  --dictionary "$glossary" \
  --blacklist tra_files_llm_translating/blacklist.txt \
  --comment InkGallery

git diff -- "$glossary"
```

`tra_path` accepts one TRA file or a flat directory. `--dictionary` selects the
file to update; `--blacklist` excludes listed candidates; `--comment` puts the mod
name in column four. The collector finds uncommon capitalized words/name parts,
not every English word. It preserves all existing dictionary rows and translations;
new rows contain `English,empty translation,source locations,mod comment`.

The collector reads complete literals with the shared TRA parser and encoding
reader, including multiline, quoted, percent-delimited, five-tilde, bare and
concatenated strings. It does not extract text from comments or sound references.

See [TRA format, grammar sources and test coverage](TRA_FORMAT.md) and the local
[TRA EBNF](TRA.ebnf). Tests cover comments between tokens, nested comments,
optional sounds after either gender, concatenation, all delimiters, empty values,
LF/CRLF/CR endings, encodings and format-preserving replacements. An in-memory
parse/replace/reparse audit of all 104 InkGallery TRA files preserved 2,392 entries,
including all 89 gender pairs and their sound metadata.

Dictionary collection needs words, not dialogue roles or grammatical gender.
Both male and female source literals are scanned, including multiline text in
either variant. Empty variants contribute no names. Identical names across the
variants are deduplicated, and their shared file/@ID source location is recorded
once. Names appearing in different entries retain each distinct source location.
Single-string gender tokens such as `<PRO_SIRMAAM>` are allowed and are not names.
Paired source strings are valid input here; the earlier rejection policy has
been removed. All files are parsed before names are saved, so malformed TRA input
still fails without a partial dictionary update.

For dictionary collection, duplicate TRA IDs use the last definition, matching
WeiDU's documented lookup rule. This is separate from duplicate rows in the
dictionary itself. Reference-only values (`#123`, `@123`, `(AT "variable")`)
contain no literal names and are skipped; embedded literal text after a forced
reference is scanned without executing it. Default parsing for TRA export still
rejects duplicate IDs and reference-dependent values. See the format document
for the supported static syntax and explicit runtime/undelimited-string limits.

All 104 InkGallery TRA files were checked: English, Spanish and Chinese each have
26 files / 598 entries with no explicit pairs. Polish has 89 paired entries.
The collector accepts paired literals too; their rarity in English does not
require a special restriction during name collection.

**Current dictionary policy (user decision): if an English entry already exists,
skip it.** Matching is case-insensitive and ignores surrounding key whitespace.
This applies whether or not the existing row has a translation. Existing
translations, context, source locations and mod comments are not changed; no new
sense is inferred or added for a known name. This is a pragmatic collection
policy, not a declaration that every English key can only ever have one meaning.
Revisit it if an existing dictionary translation produces a wrong result.

Existing duplicate rows, if present, are retained without interpretation. The
dictionary before InkGallery collection had 5,210 rows and no exact duplicate English keys. The
old lossy key-to-row merge has been removed. Newly added rows keep the collected
locations deduplicated across source variants/entries. The existing singular-form
suppression remains: a candidate plural is skipped when a corresponding singular
key is already known. When adding rows, the output remains alphabetically sorted
and is written atomically. If nothing is added, the file is not rewritten.

`New names found` reports only entries actually added when `--dictionary` is
supplied. Without a dictionary, it reports all extracted candidates. A second run
on the same input therefore reports no additions and leaves the dictionary
unchanged; it does not append duplicate locations or replace an old mod comment.
Untranslated existing entries remain for the separate review/translation step.
The `wordfreq` dependency is provided by the preparation step above.

### 2. Translate new dictionary entries or remove unsuitable candidates

Review the dictionary diff before translating the mod. Fill the Russian column,
add an English context comment for every new translated entry (a short comment
such as `Personal name` or `Nickname` is sufficient when unambiguous), and remove
false positives. Replace collected source locations in the context column with
these comments. Keep comments concise and useful to translators and LLMs:
explain the meaning or identity, and mention an existing translation when relevant.
Avoid file paths, string IDs and review history. Preserve
existing meanings/translations. Use the blacklist for recurring false positives.
The dialogue translator ignores dictionary rows whose Russian column is empty,
so leaving them unresolved does not supply terminology to the model.

#### Required context review of new candidates

This review is always required after automatic collection, whether performed by
a person or with LLM assistance. Limit edits to the new candidates; preserve
previous dictionary entries under the skip-existing policy.

1. Read each new candidate's referenced TRA text and search the entire English
   text for its other uses, case-insensitively. Include complete multiline strings
   and both source variants. A candidate's first capitalized occurrence alone is
   not enough to determine its meaning or whether it is part of a larger name.
2. Judge whether an entry helps preserve a specific name or a consistent translation.
   Remove ordinary English vocabulary that needs no glossary guidance. Keep names,
   invented-language terms, setting-specific terms and nicknames that require a
   stable rendering, even when made from ordinary words. Capitalization alone is
   insufficient: inspect the actual use in the source text.
3. Check fixed expressions and multiword/hyphenated names. Keep or add a complete
   name when it helps preserve a consistent translation, including full book,
   item and spell names made from ordinary words. If components occur only inside
   the complete expression, remove unnecessary fragment entries. Retain reusable
   components such as a surname shared by different characters. Ordinary
   descriptive titles are assessed separately. Exclude mechanical suffixes such
   as an item's `+3` enchantment bonus from the dictionary name.
4. Check suspicious spellings against their context, other occurrences, existing
   glossary entries and references where needed. Report confirmed typos with the
   source filename/@ID and suggested spelling. Distinguish suspected typos from
   attested variants or unusual invented names. Do not silently change English
   mod sources or invent a corrected dictionary key.
5. Check the final diff: retained terms have real source uses, removed terms are
   explained, old rows are unchanged and remaining translations are reviewed
   separately. The user verifies the edited dictionary before translation proceeds.

The collector only knows the current dictionary and blacklist; rerunning it after
manual deletions can reintroduce those candidates. Treat this as a separate review
stage. Store per-mod review results separately under `reviews/`; this README
records the procedure. Do not globally blacklist a valid name component just because it is part
of a fixed expression in one mod. Blacklist changes should be explicit.

Translation-time case matching is conditional: it is case-sensitive only when
every Russian translation for the key starts with an uppercase letter. Otherwise
it is case-insensitive. For example, `Licker → Лизун` does not match lowercase
`licker`, while `Licker → лизун` does. Empty translations are not loaded. This is
a heuristic, not an explicit proper-name flag. It controls glossary hints supplied
to the LLM, not a guaranteed distinction in generated translations. Dictionary
collection's skip-existing comparison is separately case-insensitive.

Manual editing is supported. For LLM help, the existing legacy command is:

```bash
python3 tra_files_llm_translating/find_translations_with_llm.py \
  --dictionary "$glossary" --model qwen2.5:72b-instruct \
  --url http://localhost:11434/api/generate

git diff -- "$glossary"
```

This finder identifies a term's translation in **already translated** parallel
English/Russian TRA lines. It replaces `english` with `russian` in recorded paths
and pairs entries by TRA ID; it does not translate novel names from English alone.
An exact whole-line term match is copied without inference; other matches use
Ollama. It processes all untranslated rows with recorded locations, not just the
latest mod's additions. It clears the locations column when filling a translation.
For InkGallery there is currently no Russian source folder, so this automatic
backfill route cannot supply its new translations before the first mod translation.
Codex support, reliable full-TRA parsing and a new-entry selection mechanism are
outstanding for this utility. Do not run it expecting the main translator's
`--backend`, `--effort` or `--method` parameters to work here.

### 3. Extract CRE genders and associate them with dialogue actors

```bash
python3 tra_files_llm_translating/extract_actors_using_grammar.py \
  "$mod_dir/dialogue" \
  --cre-folder "$mod_dir" \
  --cre-folder tra_files_llm_translating/reference/bg2ee_cre \
  --pdialog-file tra_files_llm_translating/reference/bg2ee_cre/PDIALOG.2DA \
  --interdia-file tra_files_llm_translating/reference/bg2ee_cre/INTERDIA.2DA \
  --tp2-file "$mod_dir/InkGallery.tp2" \
  --csv-output "$work_dir/actors.csv" \
  --output "$work_dir/actor_mapping.txt"
```

The D-folder argument supplies actors with actual NPC text (SAY, CHAIN/CHAIN2,
interjection speaker blocks and replacement text). Empty dialogue declarations,
external references alone, player replies and trigger/action changes alone do not
require a speaker gender and are excluded from D-derived actors. An explicit
empty SAY still counts as a text entry. Dialogue tables provide mappings only;
they do not add unrelated speakers to the output.

Repeat `--cre-folder` to search any number of mod/game folders, including external
absolute paths. Folders are recursive; the first occurrence of a CRE resource
name wins, case-insensitively, so put the mod before base-game resources. The
script reads short CRE headers to find dialogue/death-variable identities, then
retains gender data only for resources matching the selected speaking actors or
their mapped death variables. It does not load entire CRE files or export the
game's whole actor inventory.

`reference/bg2ee_cre/` contains the user-provided BG2EE CRE reference files and dialogue
tables copied from the user's existing `~/source/temp` exports. Game dialogue
tables are needed because a companion CRE may reference `AERIE`, whereas the
mod adds text to `AERIEJ`. `--pdialog-file` and `--interdia-file` read the real
2DA mappings to associate those dialogue names with CRE death variables. Both
options can be repeated; later table rows override earlier rows for the same
character. PDIALOG dream/override script columns are excluded. For a different
game or installation, supply matching exported resources via these parameters.
`--tp2-file` additionally recognizes the mod's PDIALOG/INTERDIA APPEND mappings,
which override supplied table rows for the same character.
`--csv-output` produces headerless
`actor,gender/description` rows accepted by the translator; `--output` saves the
mapping details. `--verbose` adds per-file diagnostics. Existing actor CSVs are
appended to and existing identifiers are skipped, so rerunning does not refresh
previously unknown or wrong genders; generate a fresh file when reassessing them.

On InkGallery, mod CREs alone resolve 29 actors (19 MALE, 6 FEMALE, 4 NEITHER),
leaving 13 base-game companions unresolved. With the reference game CREs and
dialogue tables, all 42 speakers resolve: 28 MALE, 10 FEMALE, 4 NEITHER. Of 4,780
CRE headers inspected, only 104 resources match the speakers or mapped death
variables; multiple level variants of a companion are checked for consistency.
L#IGCS1–L#IGCS5 declare empty dialogues and are excluded; their gender is not
needed for dialogue translation. Regenerate an existing actor CSV to remove rows
produced by the older declaration-based extraction.
Review the mapping against available game/mod resources. Keep NEITHER as NEITHER;
every actor does not need a manually assigned male/female gender. The translation
prompt treats NEITHER/OTHER/unknown as unspecified, rather than Russian neuter.
For unspecified gender it requires natural wording that works for both male and
female speakers/addressees, unless the source clearly establishes gender. It
preserves plural self-reference ("we" needs plural agreement, not an inferred sex)
and keeps source-supported choices consistent across both Player1 versions. Consistency across separate LLM requests still needs translation review.
MIXED indicates resources with differing labels and remains a separate review case.
The scanner validates V1.0 CRE signatures/header lengths,
rejects unsupported or truncated files and supports only limited TP2 patterns;
it does not interpret arbitrary
WeiDU transformations/includes. A complete association for every mod is not proven.
Pass the reviewed file with `translate_dialogs.py --actors "$work_dir/actors.csv"`;
the translator joins it to CSV Actor identifiers when building prompts. The
categorized extractor also records known source genders in `Speaker_Gender`;
party slots 2–6 remain unspecified.

### 4. Build CSVs from the mod's text

```bash
python3 tra_files_llm_translating/parse_d_grammar.py \
  "$mod_dir/dialogue" "$mod_dir/languages/english" "$work_dir/english_csv" \
  --tp2-file "$mod_dir/InkGallery.tp2" \
  --source-language english \
  --actors-file "$work_dir/actors.csv" \
  --unused-layout categorized --category-batch-size 40 \
  --usage-report "$work_dir/tra_usage.json"
```

The three positional arguments are a D directory (searched recursively), a flat source-language
TRA directory and an output directory. The script creates connected-dialogue
CSVs plus categorized script, journal and resource CSVs when `--tp2-file` is
supplied. Without TP2 analysis the default remains `_unused_tra_lines.csv`.
Hardcoded D dialogue can supply read-only context; editable CSV rows retain
their physical TRA filename/ID and original female source.
**Agreed routing policy:** resolve `@number` in the source file's corresponding
TRA file first (the same basename as the D or BAF file, with case-insensitive
filename comparison). If the entry is absent there, resolve it in the fallback
files declared by the selected TP2 `LANGUAGE`, rather than assuming the filename
is `setup.tra`. Multiple fallback files follow load order (later definitions win).
`LOAD_TRA`, scoped `WITH_TRA`, charset-helper reload arrays, and
`COMPILE`/`EXTEND_* ... USING` additions are associated with the compilation site. Paths are matched case-insensitively, including Windows path
separators. WeiDU references use the active declared fallback files.
If neither file defines the entry, report the source file/reference and stop;
do not search arbitrary TRA files or guess a translation source. This policy
deliberately assumes the common mod layout rather than interpreting arbitrary
`AUTO_TRA` routing. Revisit it when a mod contradicts the assumption. Supply
`--tp2-file` to enable TP2 analysis. `--source-language` matches a LANGUAGE name
or directory and defaults to the TRA-folder basename. Without a TP2, the legacy
matching-file then `setup.tra` lookup remains available, without usage exclusions.
The source language folder is currently flat: dialogue references to TRA files
outside it are reported rather than written with misleading source metadata.

**Translation scope:** translate the physical English literals in the mod's TRA
files, except entries proven to be used only by the installer. Installer prompts,
component labels, errors and debug messages stay English when identified as
installer-only. Hardcoded text in D, BAF, TP2, TPA or TPH is intentionally outside
this scope: leave it unchanged, do not write translated text back into those
sources, and do not stop because a mod was not fully TRAified. Such text may be
retained as read-only context around TRA-backed lines. Improving a mod's
TRAification is not a prerequisite or a planned part of this translation cycle.

`weidu_usage.py` tokenizes nested comments and strings before scanning commands.
It follows reachable INCLUDE/REINCLUDE/PATCH_INCLUDE/PATCH_REINCLUDE/LOAD files,
selected LANGUAGE fallbacks and literal compilation inputs. Only TRA entries
whose observed uses are exclusively recognized installer uses are excluded from
translation inputs. Shared game references, unreferenced entries and uncertain
uses remain included. D and BAF references protect shared entries. The contextual
extractor below builds BAF response CSVs and groups resource fields; it does not
execute arbitrary item-patching code.

The scanner follows called functions/macros with their static arguments, inline
files, copied source aliases and charset-conversion paths. It evaluates known
path/parameter tests and finite string-list helpers; unknown game conditions
retain both possible branches. Action and patch functions have separate
namespaces. Function variables follow WeiDU scope and escape only through
explicit returns; macros share the caller scope.
Missing optional TRA overrides are skipped, matching WeiDU; a game reference
still must resolve in another loaded file. Uncalled helper definitions are not
executed. Reference-valued TRA entries (`@alias` or native TLK `#number`) are
preserved: aliases route to their literal target; native TLK text is omitted from
translation CSVs because its English text is not in the mod.

Unknown include/compile paths and unresolved game references disable installer
exclusions for that analysis, retaining text rather than dropping it. Opaque
external asset generators also retain all entries. Conditional loads protect
all possible bindings; the dialogue builder rejects conflicting text instead of
choosing a source. This is static analysis; it does not execute installers or
reproduce arbitrary WeiDU patch operations.
The optional usage report lists excluded entries with their reasons/locations and
any limitations. Excluded entries remain English in the rebuilt Russian TRA files.
Always use a fresh CSV output folder after changing filtering: stale old CSVs
are not removed automatically.

Audit every TP2 under a source tree without running any installer:

```bash
python3 tra_files_llm_translating/weidu_usage.py \
  --audit-root ~/source --source-language english \
  --report "$work_dir/weidu_audit.json"
```

The JSON report includes every TP2, including those with no selected language,
missing source-language files and unresolved runtime inputs. `skip_reason` and
`source_data_issues` distinguish nonlocalized helpers, absent English resources,
and malformed language declarations. Warnings identify the actual source paths;
these cases are not reported as successful full coverage.

#### Categorized CSVs and context

`text_categories.py` extends the existing builder. `--unused-layout auto` (the
default) chooses categorized extraction when `--tp2-file` is present. Explicit
`--unused-layout legacy` keeps the old single `_unused_tra_lines.csv`. Use a fresh
output directory for categorized extraction; the CLI refuses existing CSVs so
old catch-all files cannot duplicate the new categories.

All new files use the same dialogue CSV columns accepted by the translator and
TRA updater. Additional metadata includes `Text_Type`, `Speaker_Gender`,
`Display_Target`, `Resource`, `Field`, `Source_Context`, and `Usage_Context`.
The model receives this context, while the exporter keeps physical TRA filenames
and IDs as the authoritative write-back keys.

| CSV group | Grouping and translation context |
| --- | --- |
| `baf__…` | One IF block's RESPONSE branch per file; all `DisplayString` / `DisplayStringHead` actions remain in order, including cutscenes. Alternative responses are separate files with no invented links. D `DO` action strings are also inspected for these actions. |
| `journal__…` | Journal entries from BAF actions, D journal clauses/DO strings and installer `ADD_JOURNAL`; grouped by source TRA and explicit journal title when present. Player1 supplies the male/female narrator agreement. |
| `item__…`, `spell__…` | Each resource's names and descriptions together. Shared names appear with each applicable resource and keep one physical TRA translation. |
| `character_sound__…` | One actor's soundset together, with known gender and sound-slot metadata. |
| Creature/name/store/biography groups | Split by type, source TRA and known gender/actor where applicable. |
| Map/area labels | Native `AddMapNote` text and recognized area-structure string fields, kept separate from speech. |
| Other game text / `unclassified__…` | Remaining physical TRA literals, grouped by type/source file; no unknown or unreferenced text is discarded. |

`--category-batch-size` limits standalone groups (default 40). BAF response
branches, individual item/spell resource groups and actor soundsets stay intact.
It controls grouping, not model generation limits. `--cre-folder` can be repeated
to supply additional game CRE folders; mod resources take precedence.
`--actors-file` supplies reviewed actor genders. CRE V1.0 script slots and ARE
V1.0 area/region scripts identify BAF owners; unsupported/ambiguous owners remain
unknown. `ActionOverride` and `CutSceneId` are tracked, including nested overrides.
A D DO action's `Myself` stays unknown when its executing actor is not proven.

CRE sound text assigned by TP2/include `SAY` statements is associated with the
copied CRE resource, including assignments inside supported patch helpers.
Named slots such as `BATTLE_CRY1`, `DAMAGE`, `DYING` and `SELECT_COMMON1`, and
numeric CRE V1 sound offsets, become `character_sound` rows. The translation
prompt receives the CRE actor's gender, resource filename and sound slot, so
short cries follow the NPC's agreement in both protagonist versions. A shared
TRA entry retains all its associated speakers/genders and one physical
translation; differing or unspecified genders require wording suitable for all
of them. Use the CRE-folder and reviewed-actor options above for gender context
when the resource is outside the mod. These hints come from source CRE headers
and reviewed actor data; arbitrary installer changes to CRE gender are not
executed or inferred.

A display target is distinct from the speaker. Parenthesized display narration
is exported with `NARRATOR` and `Text_Type=notification`, retaining its original
target separately. Other display text retains the target/owner and available
gender context; the prompt preserves impersonal descriptions rather than
inventing character speech. Player2–Player6 stay unspecified even if another
column or actor table claims a fixed gender.

Every copy of a shared TRA entry receives its observed usage contexts, including
D dialogue uses. The translator reuses established translations consistently;
if every string in a later file is already translated, it makes no model call.
Source mismatches and invalid cached formatting still stop export.

`_extraction_manifest.json` lists generated files, category counts, unclassified
references, reused native TLK references and coverage against the full source TRA
inventory. Row counts can exceed distinct-entry counts because one string can
have several uses. Native TLK text has no mod English literal to translate.
Hardcoded DisplayString text remains unchanged and can supply read-only context.
Dynamic resource paths/offsets that cannot be classified retain their text and
source usage metadata; they do not receive a guessed item or actor identity.

The same translation/export commands work for both layouts:

```bash
python3 tra_files_llm_translating/translate_dialogs.py "$work_dir/english_csv" \
  --target "$work_dir/russian_csv" --backend codex --model gpt-6.1-sol \
  --effort low --method both --actors "$work_dir/actors.csv" \
  --dictionary tra_files_llm_translating/dict.csv

python3 tra_files_llm_translating/update_tra_from_csv.py \
  "$mod_dir/languages/english" "$work_dir/russian_csv" \
  --output "$mod_dir/languages/russian"
```

All D sources are parsed before building the combined graph. Direct CHAIN endings
(`EXTERN dialogue label` and `END dialogue label`), ordinary EXTERN/GOTO transitions
and EXTEND additions can connect across files. State identities include source file
and dialogue actor, so reused labels do not merge unrelated scenes. Local definitions
take precedence; TP2 compilation groups disambiguate targets when available.
Ambiguous definitions stop extraction rather than selecting an arbitrary file.
Numeric destinations across separate compilation actions are linked only when a
complete BEGIN resource establishes their state indices; APPEND-only resources
have an unknown base-game state count.

This produces 56 InkGallery dialogue CSVs; L#IGCS6 contains three connected scenes
instead of nine fragments. Player replies retain their own destinations, so EXIT
alternatives do not acquire continuation edges. Targets outside the available D
sources remain external boundaries and do not merge separate scenes that happen
to reference the same base-game state. `_dialogue_graph.json` records these targets
and the number of cross-file line edges. Hardcoded nodes can connect TRA-backed
lines and supply read-only context, but do not become editable CSV rows.

### 5. Translate CSVs with Codex as the chosen workflow default

```bash
python3 tra_files_llm_translating/translate_dialogs.py "$work_dir/english_csv" \
  --target "$work_dir/russian_csv" \
  --backend codex --model gpt-6.1-sol --effort low --method both \
  --actors "$work_dir/actors.csv" --dictionary "$glossary"
```

Codex/Sol/low/both is the agreed workflow choice. The current program's bare
`--backend` default is still Ollama for compatibility, so the explicit flags above
are required until the user-requested Codex default is implemented. `--model`,
`--effort`, `--method`, `--codex-bin` and `--requests-dir` remain configurable.
The installed Codex CLI must already be logged in. `--backend ollama` selects the
local alternative; its `--url`, `--num-ctx` and `--think` options apply only there.
Both backends generate JSON text and Python writes CSV metadata/escaping.

`--test` copies English for a no-inference plumbing run; it is never a Russian
translation. It can check the CSV/TRA path without spending subscription allowance.
Review actual Russian output for omissions, speaker/addressee agreement, glossary
consistency, repeated strings and natural language. Keep request evidence; measure
subscription allowance before/after the future real-mod batch rather than
inferring it from speed or token counts.

#### Item statistics templates

Any source description with a `STATISTICS:` heading (case-insensitive, on its own
line) receives item-specific prompt instructions, regardless of its CSV category.
This applies to categorized CSVs and the legacy unused-lines CSV, with either
translation backend and either gender method. The ordinary glossary still applies.

`find_closest_item.py` selects a paired BG1EE English/Russian **statistics section**.
The references are `reference/bg1-english.tra` and `reference/bgee.tra`, relative
to this README. Statistics labels supply a vocabulary of short matching concepts,
including `THAC0`, `Damage`, `Speed Factor`, requirements and ability fields.
These concepts are then recognized throughout the statistics section, including
ability sentences without colon-labelled fields. Rare concepts carry more weight
than common ones such as `Weight`.
For matching, `Target receives Acid/Cold/Electrical/Fire Resistance` is normalized
to the corresponding `Acid/Cold/Electrical/Fire Resistance` label. The recipient
wording remains unchanged in the reference example; it is not a separate statistic.
`Chance to score a critical hit` supplies the independent concepts `Chance` and
`Critical Hit`; `Damage done to user` supplies `Damage`. The globe-of-antimagic
sentence supplies `Anti-magic`. Specific `Save vs. …` labels and `Saving Throws`
remain distinct; `Save` matches generic mentions. Matching uses word boundaries and longer phrases first:
the words in `Magic Resistance` do not also count as a generic `Resistance` match.
Each concept contributes once per description, regardless of repeated occurrences;
separate non-overlapping statistics may still supply distinct concepts.
Weighted coverage favors matching the target's fields, penalizes unrelated
sections, and prefers compatible weapon/armor structures. Ties prefer shorter
examples and then the lower TRA number. Narrative prose and numeric values do
not influence matching. Unmatched target fields are reported and must still be
translated; the vocabulary is collected from the references, not a fixed list
of allowed item properties.

Only the example's statistics are sent to the model. Its Russian headings,
terminology, section order, indentation and quotation style serve as a template.
Its abilities, numbers and item identity must never be copied to the target.
The target's narrative follows the ordinary faithful-translation rules. Each
description gets its own example, including a separate example for a differing
original female description when necessary. Selection loads once per translator
and reuses cached matches; it requires no extra LLM request.

Inspect a match for an actual InkGallery item CSV:

```bash
python3 tra_files_llm_translating/find_closest_item.py \
  "$work_dir/english_csv/item__l#ig12r1.csv"

# Also accepts a text description or a TRA file (optionally one entry):
python3 tra_files_llm_translating/find_closest_item.py \
  tra_files_llm_translating/reference/bg1-english.tra --tra-ref 6653

# Regenerate the reviewable English/Russian keyword inventory:
python3 tra_files_llm_translating/find_closest_item.py --list-keywords \
  --output tra_files_llm_translating/reference/item_statistics_keywords.json
```

The checked-in inventory contains 61 English matching concepts and 65 Russian labels from 615
paired descriptions, with item counts for each label. Matching derives its data
from the paired TRA files; regenerate the
inventory after updating those references. Pairing uses the same TRA number,
so custom references must be corresponding English/Russian exports. Entries
without a paired `ПАРАМЕТРЫ:` section are skipped and listed in the inventory;
an entirely unusable reference set fails clearly. Reference narrative differences
do not matter because narrative is excluded from examples.

Templates are enabled by default. Override their sources with
`translate_dialogs.py --item-reference-english PATH --item-reference-russian PATH`,
or disable retrieval with `--no-item-templates`. The standalone selector uses
`--reference-english PATH --reference-russian PATH`; `--output PATH` saves its JSON
report. Reference files load only when a statistics description needs a template.
Missing files fail that translation rather than silently dropping its template.

Translation and TRA export validate the statistics' numeric inventory, including
signs, percentages and dice expressions. Requirements may reorder (`5 Strength`
→ `Сила 5`) and decimal commas are accepted. Statistics may adopt reference
spacing/quotes, while narrative formatting and engine-token checks remain in
force. This does not verify which property each number belongs to, units or
semantic correctness; those still need review. `--test` remains an English-copy
plumbing check and is not evidence of Russian item quality.

### 6. Convert reviewed CSVs into the Russian TRA folder

```bash
python3 tra_files_llm_translating/update_tra_from_csv.py \
  "$mod_dir/languages/english" "$work_dir/russian_csv" \
  --output "$mod_dir/languages/russian"
```

The updater reads combined dialogue and catch-all translations, validates source
references/formatting and rejects conflicting translations for one TRA entry.
It writes UTF-8 TRA files, preserving comments, placeholders, sound references
and original formatting. Equal male/female text can use a single literal;
different translations use the TRA male/female pair. It creates the output folder.
Always supply `--output`: omitting it updates the input TRA folder in place.
Untranslated entries remain English, so creating a Russian directory alone is
not proof of complete translation. It only applies rows with TRA references;
it does not rewrite inline D/BAF/WeiDU literals or alter the installer.

### 7. Profit: install, check coverage and review in game

Register the Russian language in the mod's TP2 and review its encoding/loading
requirements, then install and inspect dialogue, item descriptions, journal
entries and both protagonist genders. No existing script performs the entire
registration/install/review step. InkGallery currently declares English, Spanish,
Chinese and Polish; writing `languages/russian` does not make it selectable.
Do not label the result complete while source strings, unresolved actors or
untranslated entries remain. General CLAUDE.md routing is still deferred until
this complete translation cycle has actually been exercised.

### Earlier local-model evaluation (historical)

2026-10-29: [v3 rescoring](experiments/RESCORED_V3_RESULTS_2026-10-29.md)
and the original five-dataset [prompt A/B](experiments/PROMPT_AB_RESULTS_2026-10-29.md)
are complete. Production scored 703/717; the noun rule 704/717, with no improvement
on either target address noun. Do not adopt the rule on this evidence. The fresh
InkGallery extension completed Beholder and Moon Sisters; Sewers was interrupted
by a serving failure, with unsubmitted cases queued after the active translate +
verify run. The [finished-dialogue review](experiments/review/20261029/FINISHED_DIALOGUE_REVIEW_2026-10-30.md)
and annotated full-line proposals are ready. Verifier/control results remain pending. See the
[review index](experiments/REVIEW_2026-10-29.md). No commit until the user reviews
and explicitly asks.

The [native-context thinking comparison](experiments/THINKING_NATIVE_RESULTS_2026-10-28.md)
remains the earlier model comparison. Scores there use the old checks; use the v3
rescoring CSVs for comparisons under the revised checks. No model is approved for
unattended export.

Empty female lines and mixed-gender shared strings are handled in code (below).
The new A/B run confirms the empty-source fix, while the mixed-speaker note alone
still fails to produce neutral readiness wording. Experiments use native contexts,
uncapped generation and complete-line verifier corrections.

## Decisions and scope

- `--backend codex`: default to Sol, explicit low effort, simultaneous male/female
  output. `--backend ollama`: retain Qwen3.5 and male-then-female editing defaults.
  Select a different model or method explicitly with `--model` / `--method`.
- Send the **complete connected dialogue graph** in each request. Never silently
  partition it into a fixed number of rows or discard context lines.
- Ask for JSON containing translated text only. Python owns CSV metadata, escaping
  and TRA references. Do not ask the model to regenerate CSV.
- Ollama uses model-native context by default. `--num-ctx` is an explicit
  Ollama override. Codex uses its client/model context configuration.
- Ollama uses `num_predict=-1`; neither backend adds a fixed generation-token cap
  or an inference timeout.
  Model context capacity and hardware remain finite.
- No automatic splitting, retries, repair pass, Python-inferred addressees, checkpoint
  cache or fallback to positional matching. These experimental mechanisms have
  been removed from the production translator.
- **Get the user's agreement before adding new approaches, limits, guardrails or
  fallback mechanisms.** Explain the benefit, tradeoffs and exact behavior first.
- No commits without instructions. Keep code changes tied to identified defects;
  do not move or rename functions just to reorganize the code.

The results justify a draft workflow with human review, **not unattended approval
of translations**. JSON validation does not prove Russian agreement or fidelity.

## Scripts and commands

Python 3.10+ is required. The grammar parser uses `chardet` and
`antlr4-python3-runtime==4.9.2` in the Python environment actually running the
command. The repository's `venv` did not contain ANTLR during the trials; the
system Python did. No package installation is performed by these scripts.

From the repository root:

```bash
python3 tra_files_llm_translating/parse_d_grammar.py \
  /path/to/dialogue /path/to/languages/english /path/to/english_csv

python3 tra_files_llm_translating/translate_dialogs.py /path/to/english_csv \
  --target /path/to/russian_csv --backend codex \
  --model gpt-6.1-sol --effort low --method both \
  --actors /path/to/actors.csv --dictionary /path/to/dict.csv

# Local alternative:
python3 tra_files_llm_translating/translate_dialogs.py /path/to/english_csv \
  --target /path/to/local_russian_csv --backend ollama \
  --model qwen3.5:9b --method two-pass

# After reviewing the translations, export to a separate directory:
python3 tra_files_llm_translating/update_tra_from_csv.py \
  /path/to/languages/english /path/to/russian_csv --output /path/to/translated_tra

python3 -m unittest discover -s tra_files_llm_translating/tests -v
```

### Backend parameters

| Parameter | Behavior |
| --- | --- |
| `--backend ollama\|codex` | Default `ollama` preserves existing invocations; select `codex` for the recommended trial. |
| `--model ID` | Provider-specific default: `qwen3.5:9b` / `gpt-6.1-sol`. |
| `--method both\|two-pass` | Available for either backend; default `two-pass` for Ollama, `both` for Codex. |
| `--effort LEVEL` | Codex only; defaults to explicit `low`. Accepts low, medium, high, xhigh, max, ultra; model/client must support the selection. |
| `--codex-bin PATH` | Codex executable; default `codex` on PATH. |
| `--requests-dir PATH` | Codex evidence root; default `TARGET/_requests`. Each invocation creates a fresh run folder. |
| `--url`, `--num-ctx`, `--think` / `--no-think` | Ollama only; rejected with Codex rather than ignored. |
| `--test` | Copy English through the selected output method; no model request or subscription usage. |

Codex must already be installed and authenticated (`codex login status`). It uses
the existing login; Python does not extract credentials or implement an API-key
client. User config is ignored, while selected model and effort are passed
explicitly. Unsupported settings fail without substituting a model or backend.
The CLI runs in a fresh temporary directory with a read-only sandbox and the
tested instruction to use no tools. Non-message/tool activity rejects the reply.

Each Codex request saves its prompt, schema, response, JSONL events, stderr and
`call.json` containing the command, selected effort, timing, reported token usage
and failure status. `run.json` records backend/model/method/effort and source/target
paths. These files are evidence, not a retry/resume cache. Token usage does not
measure remaining subscription allowance; that needs a separate before/after
measurement for the full-mod trial.

For Ollama, the server must already be running and the model installed. Nothing downloads models
or changes the Ollama service configuration. `--url` accepts a server base URL or
a full `/api/chat` or `/api/generate` endpoint; `OLLAMA_URL` is also supported.
The default is the chat API. Thinking follows the model's default (enabled for
this Qwen3.5 model); `--think` and `--no-think` are explicit user overrides.
Generation uses the model's own sampling defaults, rather than silently
overriding them.

Default `actors.csv` and `dict.csv` paths are relative to the script, independent
of the shell's current directory. An actor row is `identifier,gender/description`;
a glossary row is `English,Russian,optional context,optional source mod`. Multiple
senses are supported; longer phrases take priority. Proper nouns (entries
whose Russian side is capitalised) match case-sensitively, so `Bane` does not match "the bane of"; an English
plural also matches (`Cowled Wizards`, `fairies`, `dwarves`/`dwarfs`, `watchmen`/`humans`,
but `Rob` no longer matches "Robes"). Glossary words may be
inflected but their spelling/stems should be preserved. The existing dictionary
contains `Cormyr,Кормир`; the direct-CSV diagnostic did **not** supply this glossary
and produced `Кормирра`.

`extract_actors_using_grammar.py` can produce character data from D/CRE/TP2 input.
Review its `actor_description.csv` before supplying it as `--actors`.

## Data and roles

Parser output keeps these columns in this order:

```text
Actor,Line_ID,Predecessors,Dialogue_Text,TRA_Reference,Additional_Info
```

Extra columns preserve the original female source where present:
`Source_Female_Text` and `Source_Has_Female`. The latter distinguishes a genuinely
empty female string from a missing female variant. Existing extra columns are
preserved in the final CSV.

`PLAYER` and `Player1` both mean the protagonist. The male/female setting is always
explicit, including when NPC information exists and when Player1 has no reply.
NPC-only dialogue can still require variants because an NPC addresses Player1.

`Player2`–`Player6` are current party slots, not fixed companion identities. Their
gender remains unspecified in both protagonist versions, even if an actor CSV
contains a fixed gender for that slot. Use wording suitable for either gender
unless the source clearly establishes otherwise. Named NPC identities still use
their known CRE genders.

A display target is not necessarily a speaker. Impersonal narration, area/object
descriptions and reward/status messages remain gender-neutral in both versions:
"Gained +5% Fire Resistance" → "Получено +5% сопротивления огню", rather than
"получил/получила". A known display-target gender does not turn narration into
that character's speech.

Journal entries are an exception: their first-person narrator is the protagonist,
so they follow the same male/female agreement rules as Player1 dialogue replies.
For example, "I spoke to a strange vampire today" becomes "Я сегодня поговорил со
странным вампиром" / "Я сегодня поговорила со странным вампиром". Preserve plural
"we", the original viewpoint, tense, and other characters' own genders; do not
invent first-person narration where the source has none.

With `--tp2-file`, extraction identifies journal references consumed by BAF
`AddJournalEntry`/`EraseJournalEntry`, D `JOURNAL`/`SOLVED_JOURNAL`/`UNSOLVED_JOURNAL`,
and TP2 `ADD_JOURNAL`, including journal actions in D `DO` strings. Journal rows
carry `Text_Type=journal`; the translator routes those rows to Player1 and
preserves the role in its CSV export. Other
standalone rows retain unspecified speaker gender. Regenerate older CSVs with
TP2 analysis to obtain this metadata; the translator does not guess a journal
role from an arbitrary first-person sentence.

**Speaker is not addressee or grammatical subject.** The graph describes incoming
paths, not who every pronoun refers to. There is no `Addressee` field: the parser
cannot fill it reliably, and in the 12-line test supplying it explicitly did not
prevent the @18 error. The prompt gives speakers, their genders and predecessor
links, and asks the model to infer who each line addresses; where that is genuinely
unclear it should prefer wording that does not mark the addressee's gender.
An `Addressee` column in an input CSV is ignored (preserved in the export only).
The archived examples predate this and still contain addressee facts.

Example: Player1 asks female Velcealle, “You said you came from Cormyr?” Both
player versions should address her with feminine agreement: `Ты говорила, что
пришла…`. In contrast, Velcealle saying “You returned!” to Player1 needs
`Ты вернулся!` / `Ты вернулась!`.

The source `Line_ID`s and predecessor links stay unchanged in exports. The model
uses short numeric request IDs; Python maps them back to the original rows.

A TRA string used by several states (e.g. a "Farewell." reply offered in many places)
appears in several CSV rows. It is sent to the model **once**, with the speakers and
predecessors of all its uses, and every row gets that one translation. If its uses have
different speakers (e.g. an NPC line that is also a PLAYER reply), `speaker` and
`speaker_gender` become lists and the prompt says the one translation must agree with
every listed speaker. Without this the model could word the copies differently and the
TRA updater would reject the conflicting translations.

**Speakers of different genders (since 2026-10-29).** A TRA string has one male-Player1
and one female-Player1 variant. When it is spoken by, say, a female NPC and the
player, the male-Player1 variant must suit both a woman and a man. "I am ready" cannot
be `Я готов` or `Я готова`; it needs neutral wording such as `Можно начинать`. Every
model tested failed this case. Now, for each pass in which a shared string's speakers
differ in gender, or a speaker's gender is unknown, that line carries a `note` asking
for wording with no gendered form. After a successful export, such strings are listed in
`<name>.shared_strings_review.txt` in the target folder, with both translations, for a
person to check. If no neutral wording works, the mod's D file needs separate strings.
The TRA updater ignores this file, and processing the dialogue again removes an old one.
NPC gender comes from `actors.csv`: a description containing the word `female` or `male`.

The same string in two *different* CSV files: when a file is saved, rows whose TRA
string already has a translation in another dialogue CSV in the target folder take
that existing translation (the first file by name wins), and the console names the
files it came from. So the earlier export, including one from a previous run, decides
the wording. To re-translate a shared string, remove or edit the older export first.
Reuse requires identical male and female English source text, and both reused
translations must pass structural validation against that source. A mismatch fails
the current file without replacing its previous export.

## Gender methods and CSV output

`--method both` (recommended with Codex) translates the entire graph in one
request with both original English variants. It returns complete strings:

```json
{"translations":{"1":{"male":"Я понял.","female":"Я поняла."}}}
```

Original female meaning and explicit empty female strings are included in the
prompt and validated separately. NPC genders stay fixed. The same shared-string,
placeholder and metadata checks apply to both methods.

`--method two-pass` uses the earlier sequence:

1. Male pass: translate the complete English graph with Player1 male, fixed NPC
   genders, existing role facts and the relevant glossary.
2. Female pass: receive the same complete graph, original English and validated
   male Russian text. Edit only what depends on Player1 becoming female. Copy
   unaffected words and punctuation exactly. Return complete lines, not fragments.
   A line whose original female text is explicitly empty (`Source_Has_Female=1`,
   empty `Source_Female_Text`) is not sent; Python exports it empty. Before
   2026-10-29 it was sent with its male translation, and every model copied that text
   into it, so the reply was rejected. If all female texts are empty, no female request
   is made.

Each response has the same simple shape:

```json
{
  "translations": {
    "1": "Ты вернулся, <PLAYER1>!",
    "2": "Мне бы хотелось купить сувенир."
  }
}
```

The female response might change only value `1` to `Ты вернулась, <PLAYER1>!`.
Value `2` should remain identical. The male prompt intentionally asks for natural
common wording, but not at the expense of meaning or character voice. This is an
instruction to the model, not an automatic guarantee.

Python requires exact ID coverage, string values, no duplicate JSON keys, preserved
placeholders/counts, line breaks, quotation marks, asterisks and brackets. It then
writes one CSV per original file, retaining English/metadata and appending
`Russian_Male,Russian_Female`. Both gender versions must validate before export. Commas,
quotes, pipes and multiline strings are handled by Python's CSV writer.

The entire `_unused_tra_lines.csv` uses the selected backend and method: one
request for `both`, up to two for `two-pass`, with no batching or positional
fallback. Output is:

```text
Reference,English_Text,Source_Female_Text,Source_Has_Female,Russian_Male,Russian_Female
```

“Unused” means not referenced by the selected D files. These strings are not
necessarily context-free: they may include dialogue from other files, journals,
item descriptions or interface text.

A failed request/validation stops processing that file and produces a failing
exit status. A reply that fails validation is kept as
`<name>.both.rejected.txt`, `<name>.male.rejected.txt` or
`<name>.female.rejected.txt` in the target folder for
diagnosis; the TRA updater ignores these files. Processing a file again first removes
its old rejected replies. If a rejected reply cannot be written, the error message
still gives the validation failure. There is no automatic retry or split. Previously exported CSVs remain
unchanged, so review failures before importing an existing output directory. Use
fresh directories for separate experiments. `--test` copies English without any
model calls; it checks plumbing, not translation quality.

## TRA export and parser boundaries

The updater accepts the combined CSVs and legacy `_male.csv` / `_female.csv` pairs,
neutral dialogue CSVs, and standalone `Russian_Text` CSVs. Legacy pairs must have
matching IDs and metadata. Conflicting translations for the same TRA reference
fail explicitly. Empty failed legacy standalone translations retain the source;
no `[NO TRANSLATION]` marker is inserted.

Shared TRA parsing tracks literal spans rather than matching fake entries inside
comments. It preserves existing male/female literals and both sound references,
comments, whitespace and newlines. New gender pairs copy the existing sound.
Equal translations use a single literal for an originally single entry; existing
pairs remain pairs to retain their sounds/comments. Delimiters change safely when
needed. Tilde, quote, percent, five-tilde literals and concatenation are supported.
Unsupported syntax fails instead of silently producing a partial parse.

All referenced files/entries and structural checks are validated before writing.
Output is UTF-8 and includes untouched TRA files. Omitting `--output` updates the
original TRA directory in place. Test eventual installation with the mod's WeiDU
encoding setup; these scripts do not compile or install the mod.

Known extraction boundaries:

- D-to-TRA mapping uses matching basenames, case-insensitively, plus the selected
  TP2 fallback context when `--tp2-file` is supplied. Arbitrary runtime-generated
  routing is not interpreted; conflicting possible sources stop extraction.
- Targets in unavailable base-game DLG resources remain external graph boundaries;
  arbitrary runtime changes to compiled state indices are not reconstructed.
- Graph extraction does not prove who a line addresses. Do not infer gender from
  the speaker label alone.
- Hardcoded strings outside TRA files remain unchanged; extraction and write-back
  target TRA-backed text only.
- Subdirectories are not traversed by the translator/updater; supply the actual
  directory containing CSV/TRA files.

## Experiments: observed results, not assumptions

Tests used local `qwen3.5:9b` Q4_K_M on an RX 6900 XT-class 16 GiB GPU,
Ollama 0.40.11. Model digest:
`56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90`.
Original mod: `/home/paladin/source/InkGallery-v1.5/InkGallery/`. It was not changed.

| Approach | Evidence | Decision |
| --- | --- | --- |
| Original male-then-female CSV workflow | Reasonable sequence, but prompts could omit male gender when actors existed; four-column instructions described six-column input; CSV quoting was unsafe. | Keep the sequence; fix prompt and transport. |
| One request, required male/female JSON values | On L#IGB3, the model changed a narrated male necromancer into a woman and varied unrelated wording. | Rejected as the default. |
| One request, shared-or-male/female JSON | Three short diagnostic lines succeeded, but larger samples labelled masculine-only forms as shared. | Tiny success does not establish larger-dialogue reliability. |
| Fixed 4K/8K generation allowances with temperature zero | Thinking reached the allowance before finishing. | Not evidence of insufficient VRAM, nor proof that thinking cannot work. |
| Model-card sampling plus 32K context/16K generation | Plain diagnostic: 57.03 s, 3,227 tokens; gender plain: 119.84 s, 7,219; gender JSON: 115.15 s, 6,919. All stopped normally. | Thinking plus JSON can work. Sampling and budget changed together; cause was not isolated. |
| 34-line graph with 12-row batches, retries and splitting | Duplicate IDs were caught; “unexpected or duplicate” feedback made the model exclude valid targets and repeatedly recheck IDs. Later, a 12-row request spent 16,384 tokens reasoning without an answer. | Removed. Mechanisms were not approved and obscured the intended whole-graph test. |
| Compact request IDs and clearer top-level format | Short IDs fixed the observed ID-copying problem. Aligning examples with the `translations` wrapper removed a prompt contradiction. Language errors still remained. | Keep simple ID mapping and one unambiguous format; do not claim these solve gender. |
| Direct CSV, male then female edit, 12 lines | Gender improved: six lines differed and six stayed identical; female NPC agreement stayed feminine. Female @16 dropped its second sentence. Raw CSV had five rows with unquoted commas. | Supports two passes as a draft workflow; raw CSV output remains unsuitable for automatic import. |
| Two-pass JSON client, live 12-line trial | Both responses and Python CSV passed structural checks. @16 kept both sentences, Cormyr used Кормира, and seen remained видел/видела. The male @18 still incorrectly addressed female Velcealle with masculine verbs despite correct role data; @48 had an idiom error. | Cleaner transport did not establish reliable language quality. Draft not approved. |

The 34-line connected questions/menu trial came from `L#IGSTA.d`. Only 12 lines
completed; it was stopped because gender accuracy failed. **There is no approved
34-line translation.** Earlier `L#IGB3.d` trials did complete all 16 strings, but
contained language errors and were not approved for installation.

## Reproducible two-pass example

The direct-CSV experiment is preserved in
[examples/inkgallery-two-pass](examples/inkgallery-two-pass/).
[Read the Russian-first review](examples/inkgallery-two-pass/RUSSIAN_REVIEW.md).
Archived files:

- `input.csv`: the exact 12 English rows, speaker/addressee facts and incoming links.
- `male-request.json`, `female-request.json`: complete API payloads, including the
  exact prompts, sampling settings and context. The female input includes the male
  result but not its reasoning trace.
- `male-response.csv`, `female-response.csv`: **raw model responses**, including
  their CSV mistakes. Do not import them as approved translations.
- `comparison.json`: parsed texts, previous one-request baseline and CSV issues.
  For human comparison only, unquoted text fragments after the four metadata
  fields were rejoined. That repair is NOT part of the production parser.
- `metrics.json`: exact final events and model allocation.

Both requests used `num_ctx=262144`, `num_predict=-1`, thinking enabled and the
model-card general-task sampling settings: temperature 1, top_p .95, top_k 20,
min_p 0, presence_penalty 1.5, repeat_penalty 1, seed 42.

Measured allocation was **14,326,295,428 bytes, all on GPU**, at the model's native
262,144-token context. Thus the smaller context settings were not imposed by this
GPU. The male pass took **164.75 s / 9,778 generated tokens**; the female edit took
**248.96 s / 14,550 tokens**. Neither was split or retried, and neither had a fixed
generation-token cap. Generated counts include reasoning.

The direct test also used a shorter prompt and explicit addressees. It is not a
controlled demonstration that splitting by gender alone caused the improvement.

Specific observations to preserve:

- `@18`: “You said you came from Cormyr?” must address female Velcealle with
  feminine agreement in both player versions. This worked in the direct two-pass
  test; the combined-gender larger test had confused the genders.
- `@17`, `@24`: Player1's `понял/поняла` was correct; unaffected wording stayed the
  same in the direct female edit.
- `@48`: Player1's `заглянул/заглянула` was correct.
- `@21`: `Хотел бы / Хотела бы` was grammatically correct, but a common phrase such
  as `Мне бы хотелось…` was still possible. A prompt request to prefer common
  wording is not a guarantee that the model finds it.
- `@16`: the female edit returned only “Приветствую тебя вновь, путница.”, omitting
  the Gallery welcome sentence. Stronger completeness instructions are now in
  the prompt; this omission is NOT structurally detectable in the general case.
- `@18`: `Кормирра` was a spelling error; use the existing glossary stem `Кормир`.
- `@100`: the model changed “seen” to “read” (`прочёл/прочела`); grammar correctness
  does not imply meaning correctness.

Extended temporary traces and Russian-first review files remain under
`/tmp/translate-tra-inkgallery/`, especially `two-pass-comparison/RUSSIAN_REVIEW.md`
and `diagnostic-comparison/REVIEW.md`. `/tmp` is not permanent storage; the compact
example above is the durable record. Full reasoning dumps are intentionally not
copied into the repository.

Official references used for the experiments:

- [Qwen3.5 9B model card and sampling guidance](https://huggingface.co/Qwen/Qwen3.5-9B#best-practices)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama thinking output](https://docs.ollama.com/capabilities/thinking)
- [Ollama parameter definitions](https://docs.ollama.com/modelfile)

## Changes that need separate agreement

These are ideas, not implemented behavior:

- The user rejected mechanical word replacement: the LLM must handle full
  grammatical agreement in complete lines. Do not introduce a word/span patch
  workflow unless the user explicitly reopens and agrees to that approach.
- Add sentence-count/length heuristics, an automated linguistic reviewer, or a
  third model pass. None reliably proves completeness without further evaluation.
- Infer addressees in Python/the parser or rewrite the grammar/flow
  architecture. More context is not a substitute for accurate role facts.
- Introduce token/time caps, batching, retries, splitting, checkpoint/resume
  policies, CPU offload policies or automatic context reduction.
- Change models, sampling settings or use context extension beyond the model's
  native context as a new experiment.

Do not silently turn these proposals into production features. Discuss them first.

## Final code review checklist

Review against the last commit, not against an intermediate experiment. The main
translator keeps the original class and function sequence: load actors/dictionary,
build prompts, call Ollama, translate dialogue, save CSV, translate standalone
lines, run the CLI. Replaced code is concentrated in unsafe parsing/generation,
not cosmetic movement. Removed experimental APIs/tests are not current features.

Every remaining code change should map to one of these identified defects:
missing gender instructions; wrong speaker/addressee agreement; unsafe model CSV;
missing/duplicate IDs or damaged tokens; wrong standalone reference fallback;
filename case mismatches; fake/comment TRA entries; stale original female literals;
lost sounds/comments; empty failed translations overwriting source; conflicting
translations silently winning; or incomplete/error runs reported as success.

Passing tests cover data integrity and workflow, not literary quality, absence of
omissions, complete grammar coverage or correct Russian agreement in every line.


### Review completed for this revision

The review was performed against repository HEAD after the two-pass fixes:

- Restored the translator's original function sequence and the importer's original
  loading/update methods and nested male/female storage. Removed the experimental
  diagnostic executable, batching, splitting, retry feedback, caches and trace APIs
  instead of leaving abandoned runtime paths in the production code.
- Kept shared TRA scanning because the old regex/parser plus string replacement
  could not preserve existing female literals, comments and both sound variants.
  This extraction is a functional fix used by both reader and updater, not a
  cosmetic reorganization. The former literal-building method is replaced by
  span-based updates for that reason.
- Fixed missing actor/glossary paths failing silently, malformed model metadata
  producing an unhelpful error, empty standalone files making unnecessary calls,
  and the client forcing a thinking option onto models that might not support it.
- Confirmed exact original CSV metadata and multiline text round trips, both passes
  receiving the full graph, fixed NPC gender across passes, no automatic
  retry after failure, no fixed generation/time allowance, and no export when the
  female response fails validation.
- Retained structural rejection of corrupt IDs, tokens and conflicting TRA entries.
  No new linguistic filter, omission heuristic, patch protocol or reviewer model
  was added. Known source-flow limitations remain documented rather than silently
  expanded into a parser rewrite.

Validation: 21 focused unit/integration tests pass; Python compilation and
`git diff --check` pass. The updated production **JSON two-pass** client has now had a live trial, recorded
below, but its output is not human-approved. The earlier direct-CSV trial still
has the explicitly recorded omission and format errors. No commits were made by
the assistant as part of these tests.


## Production JSON client: Qwen3.5 live test

[Russian-first review](examples/inkgallery-json-two-pass/RUSSIAN_REVIEW.md) and
[Python-written CSV](examples/inkgallery-json-two-pass/translated.csv).

The same 12 English rows were supplied as the production dialogue CSV, with
explicit Speaker/Addressee facts. A temporary observation wrapper saved the exact
requests, reasoning and replies without altering the production payloads. No
production code, prompts or model settings were changed during or after the test.

- Native context: 262,144; generation allowance: `num_predict=-1`; model-default
  thinking and sampling. No custom time cap, automatic retry or splitting.
- `ollama ps`: 100% GPU, native context 262144, about 14 GB allocated.
- Male pass: 156.02 s, 9,085 generated tokens, normal stop.
- Female edit: 175.82 s, 10,405 generated tokens, normal stop.
- All 12 rows, exact source metadata, IDs and protected tokens passed structural
  validation. Six male/female strings were identical and six differed.
- The omitted welcome sentence in female @16 did not recur in this run. This does
  not prove omissions cannot recur. Female @16 still retained masculine путник.
- @18 used the existing glossary's spelling Кормира. But the male pass said
  `Ты говорил ... пришёл ... приехал` to female Velcealle. The request explicitly
  supplied `addressee=Velcealle` and a female gender description in BOTH passes.
  This is not an absent-metadata explanation; the model contradicted the facts.
- @100 retained seen as видел/видела rather than changing it to read.
- @48 correctly changed заглянул/заглянула but rendered “how I'm doing” as the
  unidiomatic `как я делаю`. Thus some earlier errors disappeared while another
  translation error appeared.
- @21 still chose хотел/хотела rather than a possible common phrase.

The durable folder contains the input CSV, actor facts, exact JSON requests and
raw replies, final CSV, metrics and annotated review. No handwritten corrections
were applied to model translations. The output is a review draft, not an approved
translation. No extra generation was run to improve or cherry-pick this result.

The glossary, prompt, transport and sampling differed from earlier experimental
runs, so this is not a controlled causal comparison of JSON versus CSV or of two
requests versus one. The defensible conclusion is limited: transport integrity
works in this run; gender and semantic accuracy remain unreliable.


## Installed Qwen2.5 14B comparison

[Russian-first side-by-side review](examples/inkgallery-qwen25-json-two-pass/RUSSIAN_REVIEW.md)
and [Python-written CSV](examples/inkgallery-qwen25-json-two-pass/translated.csv).

The same 12-line production JSON test was run with installed `qwen2.5:14b`
(digest `7cdf5a0187d5`). The male request's system and user prompts were identical
to the Qwen3.5 request. The female system prompt, instructions, English, graph,
roles and glossary were also identical; its male Russian draft naturally came
from Qwen2.5 instead. No prompt, code or production-default model was changed.

- Model-native context: 32,768, as reported by this installed model's metadata.
  This was not a smaller client-selected token budget. `num_predict=-1` remained
  unchanged; there was no fixed generation cap, retry or splitting.
- `ollama ps`: 100% GPU, approximately 15 GB, context 32768.
- Male: 21.58 s / 374 tokens, including roughly 11.2 s model load time.
- Female edit: 10.86 s / 375 tokens. Both stopped normally and passed structural
  validation. Total wall time approximately 32 s versus 332 s for Qwen3.5.
- Qwen2.5 produced 749 tokens; Qwen3.5 produced 19,490 including reasoning. Their
  model-default sampling/thinking behavior differs, so the observed runtime is
  not a direct comparison of decoding speed or an isolated architecture test.
- All 12 metadata rows were preserved. Eight Russian lines were identical across
  genders and four differed. Do not mistake the larger identical count for better
  common wording: formal plural agreement hid several gender distinctions.
- Qwen2.5 retained both @16 sentences and changed путешественник/путешественница.
  It correctly changed понял/поняла and хотел/хотела, and used the idiom
  как у меня дела rather than Qwen3.5's как я делаю.
- It repeatedly used вы/вас/вы сказали/вы пришли for a single addressee, violating
  the explicit ты instruction. In @18 this form also hides whether it understood
  Velcealle's female gender; it is not evidence that this role issue is solved.
- Колпаковые Маги for Cowled Wizards needs terminology review. Natural common
  wording for I would like to buy was still not selected.

Conclusion: substantially faster in this configuration and promising for review,
but not a clear overall quality winner under all the requested constraints.
The output remains unapproved. Both models' prompts, raw responses and metrics
are preserved; no extra request was made to improve or cherry-pick Qwen2.5's result.


## Expanded diagnostic evaluation (2026-10-27)

The baseline pilot, improved InkGallery checks, separate male/female wording
review and four new synthetic dialogue fixtures are documented in
[experiments/EVALUATION.md](experiments/EVALUATION.md). These are diagnostic tools,
not production repair passes or evidence that automatic translation is solved.
The first live comparison of both installed models is documented in
[experiments/MODEL_COMPARISON_2026-10-27.md](experiments/MODEL_COMPARISON_2026-10-27.md).

The uncapped Qwen3.5 thinking-on baseline is documented in
[experiments/THINKING_BASELINE_2026-10-27.md](experiments/THINKING_BASELINE_2026-10-27.md).
It completed one of fifteen dialogue pairs at the matched 8192-token context.

Seven-model non-thinking batch completed: [results, manual review and limitations](experiments/NON_THINKING_RESULTS_2026-10-28.md).
