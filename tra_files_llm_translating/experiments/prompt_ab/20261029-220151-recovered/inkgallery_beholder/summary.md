# Diagnostic results

Evaluation versions: inkgallery_beholder-v1

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/prompt_ab/20261029-220151-recovered/inkgallery_beholder/runs.jsonl` (12 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 90/90 (100%) | 0 | 103.0 | 408 |
| mistral-small3.2:24b | production-nouns | full | default | default | 3 | 88/90 (98%) | 0 | 92.4 | 406 |

## Failed checks by configuration

### mistral-small3.2:24b / production-nouns / full / default / default

- 100_INITIAL_0_SAY_0 male: dead magic preserved — failed 1/3
- 100_INITIAL_0_SAY_0 female: dead magic preserved — failed 1/3

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 32 | 1 | 0 | 0 |
| mistral-small3.2:24b | production-nouns | full | default | default | 28 | 5 | 0 | 0 |
