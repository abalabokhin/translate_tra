# Full Codex translation comparison

Status: finished

Two models × two methods × eight datasets × three repeats = 96 planned dialogue pairs.
Initial pilot is separate. No rejected reply was retried. Invalid/missing passes fail all expected checks.
Targeted checks are diagnostics, not translation-quality percentages. Human review is pending.

| Model | Method | Pairs completed / attempted | Rejected | All checks | Accepted pairs only | CLI calls | Total seconds |
|---|---|---:|---:|---:|---:|---:|---:|
| gpt-6-luna | both | 22/24 | 2 | 876/1020 | 876/900 | 24 | 160.2 |
| gpt-6-luna | two-pass | 24/24 | 0 | 986/1020 | 986/1020 | 48 | 232.2 |
| gpt-6.1-sol | both | 24/24 | 0 | 1014/1020 | 1014/1020 | 24 | 283.2 |
| gpt-6.1-sol | two-pass | 24/24 | 0 | 1002/1020 | 1002/1020 | 48 | 360.2 |

## Rejections

- inkgallery / gpt-6-luna / both / repeat 2: line 1: changed number of quotation marks
- inkgallery_beholder / gpt-6-luna / both / repeat 2: line 1: changed number of quotation marks

## Dataset checks

| Dataset | Model | Method | Completed / attempted | Checks |
|---|---|---|---:|---:|
| inkgallery | gpt-6-luna | both | 2/3 | 175/270 |
| inkgallery | gpt-6-luna | two-pass | 3/3 | 265/270 |
| inkgallery | gpt-6.1-sol | both | 3/3 | 270/270 |
| inkgallery | gpt-6.1-sol | two-pass | 3/3 | 270/270 |
| ambiguous_addressees | gpt-6-luna | both | 3/3 | 84/90 |
| ambiguous_addressees | gpt-6-luna | two-pass | 3/3 | 84/90 |
| ambiguous_addressees | gpt-6.1-sol | both | 3/3 | 90/90 |
| ambiguous_addressees | gpt-6.1-sol | two-pass | 3/3 | 90/90 |
| multiple_npcs | gpt-6-luna | both | 3/3 | 149/150 |
| multiple_npcs | gpt-6-luna | two-pass | 3/3 | 142/150 |
| multiple_npcs | gpt-6.1-sol | both | 3/3 | 148/150 |
| multiple_npcs | gpt-6.1-sol | two-pass | 3/3 | 144/150 |
| original_female_variants | gpt-6-luna | both | 3/3 | 103/105 |
| original_female_variants | gpt-6-luna | two-pass | 3/3 | 104/105 |
| original_female_variants | gpt-6.1-sol | both | 3/3 | 105/105 |
| original_female_variants | gpt-6.1-sol | two-pass | 3/3 | 99/105 |
| reused_strings | gpt-6-luna | both | 3/3 | 98/102 |
| reused_strings | gpt-6-luna | two-pass | 3/3 | 96/102 |
| reused_strings | gpt-6.1-sol | both | 3/3 | 102/102 |
| reused_strings | gpt-6.1-sol | two-pass | 3/3 | 102/102 |
| inkgallery_beholder | gpt-6-luna | both | 2/3 | 58/90 |
| inkgallery_beholder | gpt-6-luna | two-pass | 3/3 | 85/90 |
| inkgallery_beholder | gpt-6.1-sol | both | 3/3 | 86/90 |
| inkgallery_beholder | gpt-6.1-sol | two-pass | 3/3 | 84/90 |
| inkgallery_moon_sisters | gpt-6-luna | both | 3/3 | 114/114 |
| inkgallery_moon_sisters | gpt-6-luna | two-pass | 3/3 | 114/114 |
| inkgallery_moon_sisters | gpt-6.1-sol | both | 3/3 | 114/114 |
| inkgallery_moon_sisters | gpt-6.1-sol | two-pass | 3/3 | 114/114 |
| inkgallery_sewers | gpt-6-luna | both | 3/3 | 95/99 |
| inkgallery_sewers | gpt-6-luna | two-pass | 3/3 | 96/99 |
| inkgallery_sewers | gpt-6.1-sol | both | 3/3 | 99/99 |
| inkgallery_sewers | gpt-6.1-sol | two-pass | 3/3 | 99/99 |

## Interpretation

Compare both completion/validation reliability and accepted-pair checks. Entire rejected replies
can dominate all-attempted scores even when their raw Russian has useful content; see the review export.
Token counts include Codex scaffolding and are not directly comparable with Ollama prompt counts.
The CLI uses model-default reasoning effort; this is not an isolated architecture or reasoning-effort benchmark.
A simultaneous pair makes one CLI request; two-pass makes up to two. Compare complete-pair cost/time.
See REVIEW_UNIQUE.csv and ASSISTANT_REVIEW.csv for raw texts and separate editorial annotations.
Raw replies, reference translations, prompts and production code were not edited.
