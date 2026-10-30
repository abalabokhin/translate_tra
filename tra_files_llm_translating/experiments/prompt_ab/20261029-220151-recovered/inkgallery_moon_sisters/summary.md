# Diagnostic results

Evaluation versions: inkgallery_moon_sisters-v1

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/prompt_ab/20261029-220151-recovered/inkgallery_moon_sisters/runs.jsonl` (12 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 112/114 (98%) | 0 | 111.8 | 382 |
| mistral-small3.2:24b | production-nouns | full | default | default | 3 | 112/114 (98%) | 0 | 1619.8 | 382 |

## Failed checks by configuration

### mistral-small3.2:24b / production / full / default / default

- 000_BLOCK_4_ELEMENT_0_REPLY_6 female: no masculine real self — failed 2/3

### mistral-small3.2:24b / production-nouns / full / default / default

- 000_BLOCK_4_ELEMENT_0_REPLY_6 female: no masculine real self — failed 2/3

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 42 | 0 | 0 | 0 |
| mistral-small3.2:24b | production-nouns | full | default | default | 39 | 3 | 0 | 0 |
