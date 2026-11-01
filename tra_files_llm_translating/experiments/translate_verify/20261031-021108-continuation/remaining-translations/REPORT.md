# Translate + verify experiment

Status: running. Started 2026-10-31T02:11:08.254834+00:00, finished -.
Translator `mistral-small3.2:24b` (think default, ctx native); verifier `gemma4:12b` (think on, ctx native, num_predict -1); 3 repeats.

Checks are the frozen targeted assertions, not overall quality. Complete corrected lines are applied after structural validation; grammar and meaning still need review. Read before_after.csv and verifier.jsonl is required before drawing conclusions.

## Stage 1: translate, then verify

| Dataset | Verified repeats | Checks before | Checks after | Fixed | Broken | Issues | Applied | Lines changed | Verifier s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| inkgallery_beholder | 3/3 | 90/90 | 90/90 | 0 | 0 | 8 | 5 | 5 | 295.6 |

## Manual review

Pending.
