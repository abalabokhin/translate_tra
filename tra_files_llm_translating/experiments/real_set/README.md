# Real-mod evaluation set

**Status: empty. Needs dialogues and references from a person.**

The synthetic fixtures were written and checked by the same assistant that designed the
prompts, and the InkGallery lines have already been used for tuning. This set is the
independent check: real mod dialogues, with Russian references written or reviewed by
a person who knows the game and Russian.

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
