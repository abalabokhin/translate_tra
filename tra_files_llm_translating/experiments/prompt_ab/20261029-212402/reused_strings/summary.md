# Diagnostic results

Evaluation versions: reused_strings-v2

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/prompt_ab/20261029-212402/reused_strings/runs.jsonl` (12 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 96/102 (94%) | 0 | 16.8 | 75 |
| mistral-small3.2:24b | production-nouns | full | default | default | 3 | 96/102 (94%) | 0 | 18.5 | 74 |

## Failed checks by configuration

### mistral-small3.2:24b / production / full / default / default

- 301_a male: no form incompatible with male Player1 and female Selene — failed 3/3
- 301_b male: no form incompatible with male Player1 and female Selene — failed 3/3

### mistral-small3.2:24b / production-nouns / full / default / default

- 301_a male: no form incompatible with male Player1 and female Selene — failed 3/3
- 301_b male: no form incompatible with male Player1 and female Selene — failed 3/3

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 12 | 6 | 0 | 0 |
| mistral-small3.2:24b | production-nouns | full | default | default | 12 | 6 | 0 | 0 |
