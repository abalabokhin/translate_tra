# Diagnostic results

Evaluation versions: inkgallery-v3

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/prompt_ab/20261029-212402/inkgallery/runs.jsonl` (12 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 265/270 (98%) | 0 | 88.1 | 340 |
| mistral-small3.2:24b | production-nouns | full | default | default | 3 | 266/270 (99%) | 0 | 77.6 | 342 |

## Failed checks by configuration

### mistral-small3.2:24b / production / full / default / default

- @16 female: masculine address noun for female Player1 — failed 3/3
- @48 female: masculine verb for female Player1 — failed 2/3

### mistral-small3.2:24b / production-nouns / full / default / default

- @16 female: masculine address noun for female Player1 — failed 3/3
- @48 female: masculine verb for female Player1 — failed 1/3

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 36 | 0 | 0 | 0 |
| mistral-small3.2:24b | production-nouns | full | default | default | 36 | 0 | 0 | 0 |
