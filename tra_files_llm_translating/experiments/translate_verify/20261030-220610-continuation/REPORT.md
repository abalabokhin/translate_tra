# Translate + verify experiment

Status: running. Started 2026-10-30T22:06:11.041331+00:00, finished -.
Translator `mistral-small3.2:24b` (think default, ctx native); verifier `gemma4:12b` (think on, ctx native, num_predict -1); 3 repeats.

Checks are the frozen targeted assertions, not overall quality. Complete corrected lines are applied after structural validation; grammar and meaning still need review. Read before_after.csv and verifier.jsonl is required before drawing conclusions.

## Stage 1: translate, then verify

| Dataset | Verified repeats | Checks before | Checks after | Fixed | Broken | Issues | Applied | Lines changed | Verifier s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ambiguous_addressees | 3/3 | 90/90 | 90/90 | 0 | 0 | 2 | 2 | 2 | 137.4 |
| multiple_npcs | 3/3 | 147/150 | 149/150 | 2 | 0 | 2 | 2 | 2 | 149.3 |
| original_female_variants | 3/3 | 105/105 | 105/105 | 0 | 0 | 0 | 0 | 0 | 67.7 |
| reused_strings | 3/3 | 96/102 | 96/102 | 0 | 0 | 12 | 12 | 12 | 405.2 |

## Manual review

Pending.
