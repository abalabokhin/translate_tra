# Translate + verify experiment — plan (2026-10-29)

**Status: not run yet.** The runner and its offline tests are in place. The actual
results of this experiment must be committed to the repository. Earlier experiments kept
their raw outputs only in the Git-ignored `experiments/results/` folder on the machine
that ran them, so the translations could not be reviewed from another checkout. Do not
repeat that.

## Decisions confirmed 2026-10-29

- Use each model's native context discovered from Ollama; impose no smaller context
  limit for now. This applies to both translator and verifier.
- The verifier returns complete corrected lines, with error categories and
  explanations. Python validates and applies complete lines rather than replacing
  fragments. This keeps responsibility for all Russian agreement with the LLM.

**Implemented before inference:** both contexts default to `native`; the verifier
returns whole lines, one issue per line/column. Generation defaults to uncapped
(`num_predict=-1`) under the standing instruction in
[SESSION_HANDOFF.md](../SESSION_HANDOFF.md). No retries, splitting or client timeouts.
The user authorized the run and saving results, but explicitly requires review and
a later explicit request before any commit.

## Question

Does translating without thinking (fast) and then checking the result with a thinking
model give better Russian than translation alone, without the checker breaking
correct text?

Earlier results motivating this:

- Thinking during translation added at most a small gain on the frozen checks
  (Gemma4 564 → 592/660) at 10–48× the request time.
- The remaining errors are mostly detectable but persistent: masculine nouns of address
  for a female Player1 (путник, искатель приключений), narrated men turned female in
  the female pass (его → её), meaning changes (ferryman → проводник, "seen" → "read"),
  formal вы, and shared strings with speakers of both genders.

## Fix made before this experiment

Lines whose original female text is explicitly empty are no longer sent to the female
pass; production code leaves them empty itself. Previously every model, with or without
thinking, copied the male translation into them and all three such requests were rejected.
Earlier scores on `original_female_variants` (45/90 for every model) are therefore not
comparable with new runs. The frozen-hash check in `run_non_thinking.py` will refuse to
rerun the old batch against the changed production code. That is intended.

## Other changes since this plan was written (same day)

- **Evaluation v3** (see [EVALUATION.md](EVALUATION.md)): checks now catch the masculine
  nouns, narrated-pronoun flips, ferryman errors and condition changes found in manual
  reviews, and accept valid wording that was rejected. This experiment is scored with v3.
- **Mixed-gender shared strings** are now handled in production: the prompt asks for
  neutral wording and a review file lists them. See the [README](../README.md).
- **Real-mod set** `real_set/` is included automatically once dialogues are added.
- **Prompt A/B** for a female-pass noun rule is a separate experiment
  ([PROMPT_AB_PLAN.md](PROMPT_AB_PLAN.md)). This experiment keeps the production prompt.

Suggested order on the experiment machine:

1. `rescore.py` on the old result folders, to get v3 baselines.
2. Add real-mod dialogues to `real_set/` if available.
3. `run_prompt_ab.py`.
4. `run_translate_verify.py`.

## Design

Runner: [run_translate_verify.py](run_translate_verify.py). Agreed design below;
implemented before this run.

| Setting | Default | Parameter |
|---|---|---|
| Translator | `mistral-small3.2:24b`, thinking off (model has none) | `--translator`, `--translator-think` |
| Translator context | model native; no imposed smaller limit | `--translator-num-ctx` |
| Verifier | `gemma4:12b`, thinking on | `--verifier`, `--verifier-think` |
| Verifier context | model native | `--verifier-num-ctx` |
| Verifier generation cap | uncapped (`-1`) | `--verifier-num-predict` |
| Repeats | 3 | `--repeats` |

The original 32768-token cap was removed to follow the standing uncapped-generation
instruction. The earlier 1h47m loop remains documented in the previous results; no
automatic intervention is added here.

**Stage 1, translate-verify (eight datasets, up to 72 requests: 45 original + 27 fresh InkGallery).** The production
two-pass translation is scored as before. The verifier then receives each dialogue with
English, original female English where it differs, speakers and their genders,
predecessors, glossary, and both Russian columns. It returns a list of issues, each with
a line, a column (male or female), a category, an explanation and the complete
corrected line. The LLM must correct all related agreement within that line while
preserving unaffected wording. Code applies the complete line only for a valid
line/column whose source is not empty, after structural validation (tokens,
newlines, markers, quotes). It does not perform fragment substitution. Structural
validation does not prove grammatical or semantic correctness. Every decision is
logged. The frozen checks are scored before and after, and manual review checks
for missed agreement and unwanted rewrites.

**Stage 2, planted errors (four synthetic fixtures plus three clean real fixtures, up to 54 requests).** The verifier
reviews the hand-written reference translations: once unchanged, which counts false
alarms and damaging edits, and once per case in
[verify_mutations.json](verify_mutations.json). Its 11 cases plant 17 known errors:
masculine noun or verb for a female player, narrated man made female, NPC gender, female
source ignored, meaning changes, formal address, a gendered shared string, and grammar.
This measures the verifier independently of translator noise. A complete reference in
`real_set/` adds a clean-only case: false alarms on text approved by a person.

## Metrics

- Stage 1: checks before/after, checks fixed and broken, issues proposed and applied,
  lines changed, verifier time and tokens, verifier failures.
- Stage 2: planted errors flagged (right line and column), restored exactly, wrong text
  removed; issues and changes on the clean reference (false alarms); collateral changes
  in planted cases; per-category recall.

**What matters most:** false alarms and broken checks. A verifier that catches 70% and
never damages a correct line is useful; one that catches 90% and damages 10% is not.

Known limits: the frozen checks miss some nouns and narrated pronouns and reject some
valid alternatives (see [NON_THINKING_RESULTS](NON_THINKING_RESULTS_2026-10-28.md)).
The fixtures are synthetic and small. Manual review of the before/after table is
required. The checks alone do not establish quality.

## Running

```bash
cd tra_files_llm_translating/experiments
python3 run_translate_verify.py --dry-run
python3 -u run_translate_verify.py
# e.g. a different pair:
python3 -u run_translate_verify.py --translator gemma4:12b --verifier qwen3.5:9b
```

Both models must already be installed (`ollama pull mistral-small3.2:24b gemma4:12b`).

## Results go into the repository

The runner writes to `experiments/translate_verify/<UTC timestamp>/`, which is **not**
Git-ignored. After a run:

1. Read `REPORT.md`, `translate-verify/*/before_after.csv` and the `verifier.jsonl`
   files. Fill in the report's "Manual review" section: real errors caught, wrong
   "fixes", and errors missed.
2. Save the whole folder for user review, including translations, verifier issues,
   thinking text and manifest (model digests, settings, file hashes). Commit only
   after the user reviews everything and explicitly asks.
3. Write a dated summary `TRANSLATE_VERIFY_RESULTS_<date>.md` next to this plan, and link
   it from the experiments README and `SESSION_HANDOFF.md`.
