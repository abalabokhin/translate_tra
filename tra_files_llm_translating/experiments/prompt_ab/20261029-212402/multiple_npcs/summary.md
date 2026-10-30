# Diagnostic results

Evaluation versions: multiple_npcs-v2

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/prompt_ab/20261029-212402/multiple_npcs/runs.jsonl` (12 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 147/150 (98%) | 0 | 31.2 | 141 |
| mistral-small3.2:24b | production-nouns | full | default | default | 3 | 147/150 (98%) | 0 | 52.1 | 144 |

## Failed checks by configuration

### mistral-small3.2:24b / production / full / default / default

- 105 female: masculine address noun for female Player1 — failed 3/3

### mistral-small3.2:24b / production-nouns / full / default / default

- 105 female: masculine address noun for female Player1 — failed 3/3

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 18 | 0 | 0 | 0 |
| mistral-small3.2:24b | production-nouns | full | default | default | 18 | 0 | 0 | 0 |
