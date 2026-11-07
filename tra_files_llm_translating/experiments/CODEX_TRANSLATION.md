# Codex CLI translation experiment

For measured token usage and the limits of five-hour capacity estimates, see
[subscription capacity](CODEX_SUBSCRIPTION_CAPACITY.md). No quota-calibrated
words-per-window estimate has been measured yet.

`run_codex_translation.py` evaluates the existing dialogue fixtures using Codex
CLI instead of Ollama. Saved references remain unchanged. This guide records the
diagnostic runner; arbitrary parser CSVs now use the production translator below.

## Production backend — 2026-11-07

The user accepted **Sol / explicit low / simultaneous male and female output**
for the next full-mod trial and authorized adding selectable backend support.
The one-repeat reproduction passed 338/340 simultaneous checks; its two failed
checks are false alarms. Two-pass had four definitely erroneous female lines.
See [review and comparison](codex_translation/20261107-sol-low-one-repeat/MANUAL_REVIEW.md).

```bash
python3 tra_files_llm_translating/translate_dialogs.py /path/to/english_csv \
  --target /path/to/russian_csv --backend codex \
  --model gpt-6.1-sol --effort low --method both \
  --actors /path/to/actors.csv --dictionary /path/to/dict.csv
```

Backend/model/method/effort are configurable. `--codex-bin` selects the executable;
`--requests-dir` selects the evidence root (default `TARGET/_requests`). Existing
invocations still default to Ollama; `--backend codex` supplies Sol/low/both
defaults. Both methods support dialogue and unused-TRA CSVs and produce the
existing combined CSV format for `update_tra_from_csv.py`. Export still requires
editorial review. No full-mod translation or quota measurement has been run.

Production and experiments now share `codex_backend.py` and the simultaneous
prompt/parser in `translate_dialogs.py`. Offline tests verify prompt/schema
equivalence against the saved explicit-low run. Transport behavior remains the
tested no-tool CLI workflow. Read the [main workflow](../README.md) for parameter
defaults, authentication, evidence files and error behavior. Historical
"no production switch" statements below describe the earlier experiment stage.

The installed CLI smoke test succeeded with `gpt-6-luna` through the existing
ChatGPT login (`CODEX_CLI_OK`, process exit 0). The first user-launched translation
completed in [20261031-124541-618623](codex_translation/20261031-124541-618623/MANUAL_REVIEW.md):
Luna / InkGallery / both, 6.334 s, 88/90 targeted checks. Assistant review completed;
human approval pending. Subscription limits and model availability apply.

## First run

From the repository root, prepare the prompt and schema without sending anything:

```bash
python3 tra_files_llm_translating/experiments/run_codex_translation.py --dry-run
```

Then run one full InkGallery dialogue, one request, both genders together:

```bash
python3 tra_files_llm_translating/experiments/run_codex_translation.py
```

Defaults: `gpt-6-luna`, `--modes both`, `--datasets inkgallery`, one repeat.
No installation or API key is needed when `codex login status` confirms ChatGPT
authentication. The runner invokes the CLI with the existing authentication;
it does not implement OAuth or extract credentials. No Ollama request is made.

## Compare methods and models

```bash
python3 tra_files_llm_translating/experiments/run_codex_translation.py \
  --models gpt-6-luna gpt-6.1-sol \
  --modes both two-pass \
  --datasets inkgallery,original_female_variants,reused_strings \
  --repeats 3
```

This example makes up to 54 CLI invocations, sequentially. Start with the single
default request before expanding. `--datasets all` selects the original dialogue,
four synthetic fixtures and three real encounters. `--out /path/to/new-folder`
selects a fresh output directory; existing directories are rejected. Model IDs
are explicit and recorded; unsupported models fail rather than being substituted.
Reasoning effort and context use the chosen CLI model's defaults. No generation
cap, inference timeout, automatic retry/resume, splitting or corrective pass is
added. The CLI itself may perform transport recovery; its event stream is saved.

Use `--effort low` (or another supported effort) to explicitly set
`model_reasoning_effort` for every request. The manifest, per-call metadata and
saved CLI commands record this setting. Omitting the option retains historical
model-default behavior. The historical comparison did not record the resolved
default effort. The explicit-low reproduction uses Sol, both methods, all eight
datasets and one repeat; see
[20261107-sol-low-one-repeat](codex_translation/20261107-sol-low-one-repeat/SUMMARY.md).

`both` asks for two complete strings per unique TRA entry:

```json
{"translations":{"1":{"male":"Я понял.","female":"Я поняла."}}}
```

`two-pass` reuses the production male prompt followed by the female-edit prompt.
Only a structurally validated male response is supplied to the female pass. An
entirely empty female source set needs no female request. In a dry run only the
male prompt can be prepared for this mode: the female prompt requires its actual
male translation. The both-mode prompt carries original female English variants
explicitly, and requests an empty string for explicitly empty female originals.
Player1's gender varies; NPC genders remain fixed. Shared TRA entries are sent
once and expanded back into every source row after validation. Full lines are
generated by the model; Python never patches Russian words or gender endings.

## Evidence and evaluation

Each run writes under `experiments/codex_translation/<UTC timestamp>/`:

- `manifest.json`: selected models/modes, input/runtime hashes, CLI version,
  request timings, token usage when reported, validation/scoring and pair reviews.
- `REPORT.md`: run status and targeted check totals. Manual review remains pending.
- `outputs.csv`: original source and validated complete male/female translations
  for every row, including repeated strings. No production TRA files are updated.
- Per request: `prompt.txt`, `schema.json`, raw `response.txt`, `events.jsonl`,
  `stderr.txt`, and `call.json` (exit status, usage, timing and error).
- `validated.json` per completed dialogue/method/repeat, keyed by source Line_ID.

The full dialogue, actor facts and relevant glossary are supplied, using existing
production builders. Checks, reference translations and past model replies are
not supplied to the translator. The CLI runs from a fresh temporary directory
outside the repository, ignores user config, and is instructed to use no tools.
The read-only sandbox is not a filesystem secrecy boundary. Any observed tool or
other non-message activity makes the response fail the experiment; the event log
preserves evidence. Global CLI instructions/agent scaffolding may still contribute
to the request, so this is a CLI workflow comparison, not identical API prompts.

`--output-schema` constrains final JSON shape. Local validation also rejects
missing/extra/duplicate IDs, malformed gender pairs, nonempty explicitly empty
female lines, lost engine placeholders, and changed formatting markers. CLI exit
0 alone is insufficient: the runner also requires a successful turn event and a
saved response. A failed CLI call or structural check stops the run, retaining
raw evidence, with a nonzero exit status. Targeted linguistic check failures are
reported without automatic correction and do not make the process fail.

The existing regex checks and wording flags are diagnostics, not proof of overall
quality or correct gender. Assess omissions, meaning, glossary, speaker/addressee
agreement and natural Russian manually before selecting a model or method.

The user subsequently authorized the complete comparison. All 96 pairs / 144
requests are finished under [20261031-full-comparison](codex_translation/20261031-full-comparison/SUMMARY.md).
Sol simultaneous scored 1014/1020; its six failed checks were assistant-adjudicated
false alarms. [Full assistant assessment](codex_translation/20261031-full-comparison/MANUAL_REVIEW.md)
covers all 371 distinct raw line pairs; human approval is pending. Two Luna
simultaneous replies failed quote validation. An archived one-off coordinator
continued only unattempted cases after the initial launcher stopped, without
retrying either reply. Canonical full-grid state is COMPARISON.json; the original
results/manifest.json records the stopped initial launcher. No production
switch or evaluator change was made. The user subsequently requested documenting
and committing the complete workspace snapshot. This authorizes preserving the
runner/results, not promoting a production change.

Official references checked during preparation:
[authentication](https://learn.chatgpt.com/docs/auth),
[non-interactive execution and schemas](https://learn.chatgpt.com/docs/non-interactive-mode),
[models](https://learn.chatgpt.com/docs/models).
