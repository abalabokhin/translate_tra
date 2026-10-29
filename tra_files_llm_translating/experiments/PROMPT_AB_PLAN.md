# Prompt A/B: female-pass noun rule — plan (2026-10-29)

**Status: not run yet.** Its actual results must be committed to the repository under
`experiments/prompt_ab/<UTC timestamp>/`. That folder is not Git-ignored.

## Question

The most common gender error left after the 2026-10-28 runs is a masculine noun
for a female Player1 (`путник`, `странник`, `приключенец`, `искатель приключений`),
while the verbs are usually correct. Does saying explicitly that nouns, adjectives
and participles change too fix that, without causing unrelated rewrites?

## Change tested

Variant `production-nouns` in `diagnose_translation.py` is the production prompt with
one sentence added to the female-pass instruction (`FEMALE_NOUN_RULE`):

> This includes every noun, adjective and participle that refers to Player1, not only
> verbs, e.g. гость → гостья, герой → героиня, чужак → чужачка, уставший → уставшая.

The examples deliberately avoid the words the checks look for, so the rule cannot pass a
check by copying an example. The male pass is identical in both variants.

**Production is unchanged** until this is measured. The verifier experiment uses the
unchanged production prompt, so the two effects are not mixed.

## Design

`run_prompt_ab.py`: one model (default `mistral-small3.2:24b`, thinking off/model
default, context 8192), both prompts, all datasets including `real_set/`, full
dialogues, three repeats, model-default sampling. With five datasets that is up to 60
requests. It is scored with evaluation v3.

`REPORT.md` shows checks, rejected requests and wording flags per prompt and dataset,
and lists every check whose failure count differs between the prompts.

## Deciding

Adopt the rule into production (`translate_dialogs.py` female instruction) only if:

1. Address-noun checks improve across repeats, not in a single run.
2. Wording flags (`pair_reviews.csv`: differences outside listed gender edits) and
   rejected requests do not rise. A rule that makes the female pass rewrite more is
   worse.
3. A manual read of both prompts' female `outputs.csv` rows confirms the change. In
   particular, NPC genders and narrated third persons must not start flipping.

Five small datasets and three repeats cannot prove a general improvement. A clear,
consistent difference is enough to adopt; a mixed one is not.

## Running

```bash
cd tra_files_llm_translating/experiments
python3 run_prompt_ab.py --dry-run
python3 -u run_prompt_ab.py                 # or --model gemma4:12b
```

Afterwards, fill in the "Manual review" section of `REPORT.md`, commit the whole
output folder, and write `PROMPT_AB_RESULTS_<date>.md` with the decision.
