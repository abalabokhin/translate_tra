# Translation diagnostic experiment

Answers one question: **why does the local LLM get the Russian wrong?** Is it the
model's ability, the instruction framing, request size, thinking, or sampling noise?

`diagnose_translation.py` runs the same 12 archived InkGallery lines through a grid
of settings and automatically scores each Russian output against expected forms
(`inkgallery_checks.json`). It is standalone: it reuses the production prompt
builder, glossary and validation, but does not change the production translator.
It makes no retries; a failed request is recorded as a failure.

## Requirements

- Ollama running, with the models you want to test already pulled.
- Python 3.10+. No extra packages (does not need `chardet` or ANTLR).
- Run from the repository root or anywhere; paths resolve relative to the script.

## One-command run (recommended)

`run_all.py` does everything: pulls the candidate models, runs the three stages
below, and writes one `REPORT.md`.

```bash
python3 tra_files_llm_translating/experiments/run_all.py --dry-run   # plan and request counts
python3 tra_files_llm_translating/experiments/run_all.py             # pull, test, report
```

What it does:

1. **Pull.** Downloads each model in its list that isn't installed yet. The list holds
   the Ollama library models plus two Russian fine-tunes from Hugging Face. A model
   that fails to pull (wrong tag, no network) is reported and skipped. Downloads total
   roughly 60–70 GB. `--skip-pull` uses only installed models. `--remove-pulled`
   deletes the models this run downloaded once it finishes; pre-installed ones are kept.
2. **Stage 1** on the baseline (`qwen3.5:9b`): all prompts, `full`/`pair`, temperature
   `default`/`0.2`, thinking off. It picks the best prompt (any variant except `reframed-addressee`)
   and temperature together from the full-dialogue results for the later stages.
   On a tie, it prefers production, then model-default temperature.
3. **Stage 2:** thinking on vs. off for every model that Ollama reports as
   thinking-capable.
4. **Stage 3:** every model, `production` vs. the best prompt, whole dialogue, thinking
   off (non-thinking models keep their default).
5. **Report:** `experiments/results/full-<timestamp>/REPORT.md` lists model status,
   GPU share and tables by prompt, scope, temperature, thinking and model, and links
   each stage's `summary.md` and `outputs.csv`.

Useful options: `--models a,b,c` (replace the list), `--baseline TAG`,
`--stages 1` or `--stages 2,3`, `--repeats N`, `--num-ctx 8192` (default; prompts are
about 2k tokens). Model tags are in `DEFAULT_MODELS` at the top of `run_all.py`.
Expect several hours with thinking stages included. Stages 2 and 3 with no thinking
models are much faster. Ctrl+C keeps finished requests, but rerun with `--out` to
the same folder and fewer `--stages` to continue; no automatic resume.

The sections below describe the underlying single-grid script, `diagnose_translation.py`,
for running individual experiments by hand.

## What it varies

| Option | Values | Tests the hypothesis |
|---|---|---|
| `--models` | any Ollama tags | the model's ability |
| `--prompts` | `production`, `reframed`, `reframed-addressee`, `examples`, `markup` | instruction framing, worked examples, one request vs. two |
| `--scopes` | `full`, `pair` | request size: whole dialogue vs. one line plus its predecessors |
| `--think` | `default`, `on`, `off` | whether thinking helps or hurts |
| `--temperatures` | `default` or numbers, e.g. `default,0.2` | sampling noise |
| `--repeats` | integer (default 3) | noise vs. a consistent fault |

Prompt variants:

- `production`: exactly what `translate_dialogs.py` sends today (male pass, then female edit).
- `reframed`: short numbered rules, no "this pass is male" framing, and a per-line
  grammar note, e.g. `я: masculine (Player1)`. No listener information.
- `examples`: as `reframed`, plus six worked examples (English → male/female Russian),
  each showing one case: Player1 speaking to a female NPC, an NPC speaking to Player1, a
  noun of address, a narrated man staying male, a line that doesn't depend on gender.
  They use other characters and wording than the scored lines, so they teach the pattern,
  not the answers. Edit them in `EXAMPLES` in `diagnose_translation.py`.
- `markup`: one request instead of two. The model writes each line once and marks
  every word that depends on Player1's gender as `{masculine|feminine}`, e.g.
  `Ты {вернулся|вернулась}!`. Python splits it into the male and female versions, so
  unrelated wording cannot differ between them. Uses the same worked examples, in markup
  form. Malformed markup (stray braces or `|`) counts as a failed request. In
  `runs.jsonl` the female record is marked `derived` and has no time/tokens of its own.
- `reframed-addressee`: as `reframed`, plus `ты: feminine (Velcealle)` from the
  input's hand-labelled `Addressee` column. This is an **upper bound**: production has
  no addressee field. If it beats `reframed` by a lot, structural addressees
  (reply → dialogue owner) may be worth revisiting.

All variants except `markup` keep the two-pass male → female-edit structure.

Defaults: `qwen3.5:9b`, all three prompts, both scopes, thinking off, temperatures
`default,0.2`, 3 repeats, `--num-ctx 16384`. Production uses the model-native context;
pass `--num-ctx native` to match it. That is slow to load and can push bigger models
off the GPU. The script warns if a model is not 100% on the GPU (`/api/ps`).

## Recommended stages

Always check the size first with `--dry-run`.

**Stage 1: framing, size and noise (thinking off, about 30 minutes):**

```bash
python3 tra_files_llm_translating/experiments/diagnose_translation.py --dry-run
python3 tra_files_llm_translating/experiments/diagnose_translation.py
```

**Stage 2: thinking.** Use the best prompt from stage 1. Thinking requests take
minutes each.

```bash
python3 tra_files_llm_translating/experiments/diagnose_translation.py \
  --prompts reframed --scopes full --think on,off --temperatures 0.2 --repeats 3
```

(`default` thinking = the model's own setting, which is on for Qwen3.5.)

**Stage 3: models.** Same settings, several models that fit the GPU.

```bash
python3 tra_files_llm_translating/experiments/diagnose_translation.py \
  --models qwen3.5:9b,gemma3:12b,qwen3:14b,mistral-small3.2:24b \
  --prompts production,reframed --scopes full --think off --temperatures 0.2 --repeats 3
```

Model tags are examples; use whatever `ollama list` shows. For thinking models,
optionally repeat with `--think on`.

Ctrl+C is safe: finished requests are kept, and the summary is written for them.

## Results

Each run writes to `experiments/results/<timestamp>/` (or `--out DIR`):

- `summary.md`: one row per configuration with checks passed, failed requests,
  average seconds and tokens per request, then each failed check with its count
  (e.g. `@18 male: Velcealle addressed as masculine — failed 3/3`).
- `outputs.csv`: every scored Russian line with its failed checks, for reading the
  actual translations (opens in Excel/LibreOffice as UTF-8).
- `runs.jsonl`: everything: the exact request, raw reply, **thinking trace**, token
  counts, timings and GPU share. Use it to read why the model chose a wrong form.

Both scopes score only the lines named in the checks file; `full` still supplies
the entire dialogue as context. Failed requests fail every expected check. When
the male pass fails, the skipped female pass also fails its expected checks and is
logged with `skipped: true`, without adding a request or time to the averages.
Markup variants likewise count as one request while scoring both genders.
Rankings therefore account for missing output as well as incorrect translations.
Use a fresh results directory after this scoring change: old logs lack these
failure checks and skipped-pass records, and rebuilding their summaries does not
rescore them.

To rebuild the summary from `runs.jsonl` (e.g. after editing the checks):

```bash
python3 tra_files_llm_translating/experiments/diagnose_translation.py --summarize experiments/results/<timestamp>
```

Scores are stored per request, so changing the checks requires a rerun to rescore.
Rebuilding only regenerates the tables.

## Reading the results

| Observation | Meaning |
|---|---|
| The same check fails in some repeats, not others | sampling noise: lower temperature, or a bigger model |
| A check fails in every repeat | consistent fault: framing or the model's ability |
| `pair` scores no better than `full` | request size is not the problem; don't split dialogues |
| `reframed` beats `production` | the instructions are at fault; port the framing to production |
| `reframed-addressee` beats `reframed` a lot | listener facts matter; revisit structural addressees |
| `examples` beats `reframed` | worked examples help; add them to production |
| `markup` matches or beats `examples` | one request with markup can replace the two-pass flow (half the requests) |
| A bigger model fixes the idiom/meaning checks (@48, @100) | the model's ability |
| `think on` doesn't beat `off` | thinking costs time without benefit for this task |

The checks are deliberately narrow: they catch the errors seen so far (gender
agreement, вы, the @48 idiom, seen vs. read, the dropped @16 sentence, Кормир).
Passing them does not mean the translation is good. Read `outputs.csv` for the
best configurations before changing production.

## Checks file

`inkgallery_checks.json` names the input CSV and actors file, then lists
case-insensitive regexes per `Line_ID`, under `both`, `male` or `female` (Player1's
gender in that pass). `require` must match; `forbid` must not. `all` applies to
every line. Write `\b` as `\\b` in JSON. To test another dialogue, copy the file,
point `input` and `actors` at your CSVs, write checks, and pass `--checks`.
