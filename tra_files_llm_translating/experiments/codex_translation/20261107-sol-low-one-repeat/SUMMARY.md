# Sol explicit-low reproduction

Run status: finished

Eight datasets, both methods, one repeat. Historical Sol used three repeats with unspecified default effort.
Inputs/glossary/prompt builders/scoring match the frozen historical hashes. Only the runner adds effort selection and recording.
CLI changed from 0.166.0 to codex-cli 0.167.0. Backend changes and normal sampling variation are uncontrolled.
This is a reproduction comparison, not an isolated test of reasoning effort. Checks are diagnostics, not quality percentages.

| Method / run | Valid pairs | Checks | Calls | Seconds per pair | Input tokens per pair | Output tokens per pair | Reasoning tokens per pair |
|---|---:|---:|---:|---:|---:|---:|---:|
| both / historical | 24/24 | 1014/1020 | 24 | 11.80 | 16277.0 | 529.6 | 55.8 |
| both / explicit low | 8/8 | 338/340 | 8 | 15.10 | 16643.6 | 569.0 | 56.5 |
| two-pass / historical | 24/24 | 1002/1020 | 48 | 15.01 | 31807.0 | 488.2 | 30.5 |
| two-pass / explicit low | 8/8 | 333/340 | 16 | 17.90 | 32360.8 | 490.9 | 30.5 |

## Per-dataset checks

| Dataset | Method | New low | Previous repeat 1 | Previous repeat 2 | Previous repeat 3 |
|---|---|---:|---:|---:|---:|
| inkgallery | both | 90/90 | 90/90 | 90/90 | 90/90 |
| inkgallery | two-pass | 90/90 | 90/90 | 90/90 | 90/90 |
| ambiguous_addressees | both | 30/30 | 30/30 | 30/30 | 30/30 |
| ambiguous_addressees | two-pass | 30/30 | 30/30 | 30/30 | 30/30 |
| multiple_npcs | both | 48/50 | 50/50 | 50/50 | 48/50 |
| multiple_npcs | two-pass | 48/50 | 48/50 | 48/50 | 48/50 |
| original_female_variants | both | 35/35 | 35/35 | 35/35 | 35/35 |
| original_female_variants | two-pass | 32/35 | 32/35 | 35/35 | 32/35 |
| reused_strings | both | 34/34 | 34/34 | 34/34 | 34/34 |
| reused_strings | two-pass | 34/34 | 34/34 | 34/34 | 34/34 |
| inkgallery_beholder | both | 30/30 | 28/30 | 28/30 | 30/30 |
| inkgallery_beholder | two-pass | 28/30 | 28/30 | 28/30 | 28/30 |
| inkgallery_moon_sisters | both | 38/38 | 38/38 | 38/38 | 38/38 |
| inkgallery_moon_sisters | two-pass | 38/38 | 38/38 | 38/38 | 38/38 |
| inkgallery_sewers | both | 33/33 | 33/33 | 33/33 | 33/33 |
| inkgallery_sewers | two-pass | 33/33 | 33/33 | 33/33 | 33/33 |

## Failed checks

- multiple_npcs / both: {"line": "104", "gender": "male", "check": "Orin injured masculine", "ok": false}
- multiple_npcs / both: {"line": "104", "gender": "female", "check": "Orin injured masculine", "ok": false}
- multiple_npcs / two-pass: {"line": "102", "gender": "female", "check": "narrated man stays male", "ok": false}
- multiple_npcs / two-pass: {"line": "102", "gender": "female", "check": "narrated man not made female", "ok": false}
- original_female_variants / two-pass: {"line": "401", "gender": "female", "check": "female form", "ok": false}
- original_female_variants / two-pass: {"line": "402", "gender": "female", "check": "female form", "ok": false}
- original_female_variants / two-pass: {"line": "403", "gender": "female", "check": "female form", "ok": false}
- inkgallery_beholder / two-pass: {"line": "100_INITIAL_0_SAY_0", "gender": "male", "check": "dead magic preserved", "ok": false}
- inkgallery_beholder / two-pass: {"line": "100_INITIAL_0_SAY_0", "gender": "female", "check": "dead magic preserved", "ok": false}

## Text comparison

106/140 source-row pairs exactly match at least one historical repeat of the same method.
105 distinct new source-row/translation pairs are exported for review.
SIDE_BY_SIDE.csv includes all three historical translations beside the new result. Linguistic assessment is recorded separately in MANUAL_REVIEW.md.
