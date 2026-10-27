# Local LLM dialogue translation: workflow and experiment record

For a new session, read [SESSION_HANDOFF.md](SESSION_HANDOFF.md) first for the latest
state, user constraints and pending decisions.

This is the current reference for these scripts. It also records failed and
partially successful approaches so they are not accidentally reintroduced.

## Decisions and scope

- Keep the original **male translation, then female edit** approach.
- Send the **complete connected dialogue graph** in each request. Never silently
  partition it into a fixed number of rows or discard context lines.
- Ask for JSON containing translated text only. Python owns CSV metadata, escaping
  and TRA references. Do not ask the model to regenerate CSV.
- Use the selected model's native context by default. `--num-ctx` is an explicit
  user override, not an automatically selected smaller budget.
- `num_predict=-1`: no fixed generation-token cap. No client timeout is imposed.
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
`antlr4-python3-runtime==4.9.3` in the Python environment actually running the
command. The repository's `venv` did not contain ANTLR during the trials; the
system Python did. No package installation is performed by these scripts.

From the repository root:

```bash
python3 tra_files_llm_translating/parse_d_grammar.py \
  /path/to/dialogue /path/to/languages/english /path/to/english_csv

python3 tra_files_llm_translating/translate_dialogs.py /path/to/english_csv \
  --target /path/to/russian_csv --model qwen3.5:9b \
  --actors /path/to/actors.csv --dictionary /path/to/dict.csv

# After reviewing the translations, export to a separate directory:
python3 tra_files_llm_translating/update_tra_from_csv.py \
  /path/to/languages/english /path/to/russian_csv --output /path/to/translated_tra

python3 -m unittest discover -s tra_files_llm_translating/tests -v
```

Ollama must already be running and the model installed. Nothing downloads models
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

The same string in two *different* CSV files: when a file is saved, rows whose TRA
string already has a translation in another dialogue CSV in the target folder take
that existing translation (the first file by name wins), and the console names the
files it came from. So the earlier export, including one from a previous run, decides
the wording. To re-translate a shared string, remove or edit the older export first.
Reuse requires identical male and female English source text, and both reused
translations must pass structural validation against that source. A mismatch fails
the current file without replacing its previous export.

## Two requests, one CSV

1. Male pass: translate the complete English graph with Player1 male, fixed NPC
   genders, existing role facts and the relevant glossary.
2. Female pass: receive the same complete graph, original English and validated
   male Russian text. Edit only what depends on Player1 becoming female. Copy
   unaffected words and punctuation exactly. Return complete lines, not fragments.

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
`Russian_Male,Russian_Female`. Both responses must validate before export. Commas,
quotes, pipes and multiline strings are handled by Python's CSV writer.

The entire `_unused_tra_lines.csv` also uses two requests and JSON, with no batching
or positional fallback. Output is:

```text
Reference,English_Text,Source_Female_Text,Source_Has_Female,Russian_Male,Russian_Female
```

“Unused” means not referenced by the selected D files. These strings are not
necessarily context-free: they may include dialogue from other files, journals,
item descriptions or interface text.

A failed request/validation stops processing that file and produces a failing
exit status. A reply that fails validation is kept as
`<name>.male.rejected.txt` / `<name>.female.rejected.txt` in the target folder for
diagnosis; the TRA updater ignores these files. Processing a file again first removes
its old rejected replies. If a rejected reply cannot be written, the error message
still gives the validation failure. There is no automatic retry or split. Previously exported CSVs remain
unchanged, so review failures before importing an existing output directory. Use
fresh directories for separate experiments. `--test` copies English without any
Ollama calls; it checks plumbing, not translation quality.

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

- D-to-TRA mapping assumes matching basenames, case-insensitively; it does not
  evaluate TP2 `LOAD_TRA`/`AUTO_TRA` overrides or conditional compilation.
- EXTERN links across separate D-file parse walks are not resolved globally.
- Graph extraction does not prove who a line addresses. Do not infer gender from
  the speaker label alone.
- Some direct CHAIN epilog EXTERN links are not joined by the current flow builder;
  the full L#IGSTA file was split into nine extracted groups. Do not call these
  group boundaries a complete model of every game dialogue transition.
- Direct strings embedded in D files are translated for review but are not written
  back by the TRA updater.
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
