# Real dialogue candidates — 2026-10-29

**Superseded:** the user selected fresh InkGallery text instead. These AloraEE
preparation artifacts are retained for provenance and excluded from inference.

Four complete connected graphs extracted with the repository ANTLR parser from a
local AloraEE v1.9 checkout, commit `6e324a40a0dc804e94aa0dbdaa4f431102ca4735`.
Inputs and actor facts are ready for user inspection; Russian reference columns
are deliberately empty. Each candidate also has `existing_russian_for_review.csv`
with the matching existing Russian locale text as a review starting point; its
authorship/quality has not been verified. No human review has occurred. These are not gold data.

| Candidate | Lines | Coverage |
|---|---:|---|
| alora_jaheira | 13 | Fixed female/female/male NPCs; discussed third persons |
| alora_rescue_imoen | 12 | Female NPC and Player1; Imoen and a male mage discussed; tokens |
| alora_mage | 15 | Female NPC and Player1; a different male mage discussed |
| alora_missing_boo | 18 | Multiple fixed male/female NPCs; Boo discussed |

These candidates do not cover shared mixed-gender strings or explicit female
source variants; the existing synthetic fixtures cover those cases.

Each fixture contains input.csv, actors.csv, checks.json (only no-Latin checks)
and a reference.csv skeleton. Source paths and hashes are in source_sha256.json;
parser diagnostics are in parser.log. The selected parser CSVs are in parsed/.

Review actors, graph and context, fill/correct both Russian references, add focused
checks, and record reviewer/date before moving approved fixtures to real_set/.
They remain outside real_set/ so the authorized five-dataset runs do not silently
change inputs mid-run. No independent-real-set result is claimed.

The user subsequently chose InkGallery and authorized assistant reference review,
with user review of translations later. See ../../real_set/ for the active fixtures.
No commit is authorized until user review and an explicit request.
