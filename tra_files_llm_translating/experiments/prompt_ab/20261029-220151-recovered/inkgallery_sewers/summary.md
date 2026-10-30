# Diagnostic results

Evaluation versions: inkgallery_sewers-v1

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/prompt_ab/20261029-220151-recovered/inkgallery_sewers/runs.jsonl` (7 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 16/99 (16%) | 3 | 7427.8 | 124 |
| mistral-small3.2:24b | production-nouns | full | default | default | 3 | 0/99 (0%) | 3 | 0.0 | 0 |

## Failed checks by configuration

### mistral-small3.2:24b / production / full / default / default

- 100_BLOCK_0_ELEMENT_0_SAY_1 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_0_ELEMENT_0_SAY_1 female: Jans cousin stays female — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 female: no masculine original leader agreement — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_4 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_5 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_6 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_7 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_8 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_9 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 female: both prices retained — failed 3/3
- 100_INITIAL_0_SAY_0 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_INITIAL_0_SAY_0 female: narrated adventurer stays male — failed 3/3
- 100_INITIAL_0_SAY_0 female: worms remain creatures — failed 3/3
- 101_INITIAL_0_SAY_10 female: no untranslated Latin text outside engine tokens — failed 3/3
- 101_INITIAL_0_SAY_10 female: female player choice — failed 3/3
- 100_BLOCK_0_ELEMENT_0_SAY_1 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_0_ELEMENT_0_SAY_1 male: Jans cousin stays female — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 male: male original leader — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_4 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_5 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_6 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_7 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_8 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_REPLY_9 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 male: both prices retained — failed 2/3
- 100_INITIAL_0_SAY_0 male: no untranslated Latin text outside engine tokens — failed 2/3
- 100_INITIAL_0_SAY_0 male: narrated adventurer stays male — failed 2/3
- 100_INITIAL_0_SAY_0 male: worms remain creatures — failed 2/3
- 101_INITIAL_0_SAY_10 male: no untranslated Latin text outside engine tokens — failed 2/3
- request error (repeat 1, female): Remote end closed connection without response
- request error (repeat 2, male): <urlopen error [Errno 111] Connection refused>
- request error (repeat 2, female): skipped: male pass failed
- request error (repeat 3, male): <urlopen error [Errno 111] Connection refused>
- request error (repeat 3, female): skipped: male pass failed

### mistral-small3.2:24b / production-nouns / full / default / default

- 100_BLOCK_0_ELEMENT_0_SAY_1 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_0_ELEMENT_0_SAY_1 male: Jans cousin stays female — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 male: male original leader — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_4 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_5 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_6 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_7 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_8 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_9 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 male: both prices retained — failed 3/3
- 100_INITIAL_0_SAY_0 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_INITIAL_0_SAY_0 male: narrated adventurer stays male — failed 3/3
- 100_INITIAL_0_SAY_0 male: worms remain creatures — failed 3/3
- 101_INITIAL_0_SAY_10 male: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_0_ELEMENT_0_SAY_1 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_0_ELEMENT_0_SAY_1 female: Jans cousin stays female — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_3 female: no masculine original leader agreement — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_4 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_5 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_6 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_7 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_8 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_REPLY_9 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_BLOCK_1_ELEMENT_0_SAY_2 female: both prices retained — failed 3/3
- 100_INITIAL_0_SAY_0 female: no untranslated Latin text outside engine tokens — failed 3/3
- 100_INITIAL_0_SAY_0 female: narrated adventurer stays male — failed 3/3
- 100_INITIAL_0_SAY_0 female: worms remain creatures — failed 3/3
- 101_INITIAL_0_SAY_10 female: no untranslated Latin text outside engine tokens — failed 3/3
- 101_INITIAL_0_SAY_10 female: female player choice — failed 3/3
- request error (repeat 1, male): <urlopen error [Errno 111] Connection refused>
- request error (repeat 1, female): skipped: male pass failed
- request error (repeat 2, male): <urlopen error [Errno 111] Connection refused>
- request error (repeat 2, female): skipped: male pass failed
- request error (repeat 3, male): <urlopen error [Errno 111] Connection refused>
- request error (repeat 3, female): skipped: male pass failed

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 0 | 0 | 33 | 0 |
| mistral-small3.2:24b | production-nouns | full | default | default | 0 | 0 | 33 | 0 |
