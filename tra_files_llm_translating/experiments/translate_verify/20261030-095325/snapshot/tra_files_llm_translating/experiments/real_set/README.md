# Real-mod evaluation set

**Status: three fresh InkGallery v1.5 encounters are ready.** The user authorized
assistant reference review and offered to review translations later. References and
checks were written/reviewed by the assistant before inference; human review is
pending. They are new authentic mod text, not independent human gold data.

| Fixture | Rows | Coverage |
|---|---:|---|
| [inkgallery_sewers](inkgallery_sewers/README.md) | 11 | Narrated male adventurer, Jan's female cousin, female proprietor, Player1 leader, prices/tokens |
| [inkgallery_beholder](inkgallery_beholder/README.md) | 11 | Narrated monster, male NPC, female proprietor, Player1 leader, dead magic, prices/tokens |
| [inkgallery_moon_sisters](inkgallery_moon_sisters/README.md) | 14 | Three fixed female NPCs, Player1 arrival/identity, plural address, marked path |

The running five-dataset A/B batch keeps its frozen input list. A separate real-set
A/B extension will use these three fixtures. Translate + verify will include all
eight datasets, with clean-reference verifier cases for these three fixtures.

Earlier [Alora candidates](../real_set_candidates/20261029/README.md) were superseded
by the user's request to use the same mod as the initial InkGallery tests; they
are retained as preparation artifacts and excluded from inference.

The synthetic fixtures were written and checked by the same assistant that designed the
prompts, and the InkGallery lines have already been used for tuning. This set supplies new real mod dialogues. Under the latest user instruction, the
assistant may review references; the user can review the resulting translations.
Independent human review remains pending and must not be claimed.

## Choosing dialogues

Pick 3–5 connected dialogues from real mods, roughly 10–40 lines each. Together they
should cover:

- an NPC addressing Player1 with gendered forms (вернулся/вернулась, nouns of address);
- Player1 talking to a female NPC, and to a male NPC;
- a man or woman being talked about (third person);
- a string reused by speakers of different genders, if the mod has one;
- an original female variant (`~male~ ~female~` in the TRA), including an empty one if
  available;
- glossary terms, names, engine tokens (`<CHARNAME>`, `%var%`), stage directions.

## Adding one

```bash
# 1. Parse the mod's D and TRA files (produces one CSV per connected dialogue):
python3 parse_d_grammar.py path/to/d path/to/tra parsed/
# 2. Create the fixture skeleton from one of those CSVs:
python3 experiments/make_real_fixture.py parsed/SOMEDIALOG.csv actors.csv mymod_somedialog \
    --source "MyMod v1.2, SOMEDIALOG.d / somedialog.tra"
```

This creates `real_set/mymod_somedialog/` with:

- `input.csv`, a copy of the parsed dialogue, and `actors.csv`. Check the genders.
- `reference.csv`: English plus empty `Russian_Male`, `Russian_Female` and `Review_Notes`.
  **Fill these yourself**, or start from a model draft and correct it line by line.
  An empty female source (`English_Female` empty with `Source_Has_Female=1` in
  input.csv) stays empty.
- `checks.json`: every line is a scored target with only the global no-Latin check.
  Add line checks for the specific risks you see, e.g.
  `"@12": {"female": [{"name": "feminine address", "forbid": "\bпутник\b"}]}`.
  Keep them about errors, not about one preferred wording.
- `README.md`: fill in reviewer, date and context notes.

## How it is used

- `run_translate_verify.py` and `run_prompt_ab.py` include every `real_set/*/checks.json`.
- The planted stage uses a fixture's reference only once it is complete. With no
  planted cases, it then measures verifier false alarms on human-approved text.
- Do not change a reviewed reference to match a model's output. If the model's wording
  is also correct, note it in `Review_Notes` instead.
- Commit the fixtures. They are the evaluation data.
