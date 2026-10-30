# Diagnostic results

Evaluation versions: ambiguous_addressees-v2

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/prompt_ab/20261029-212402/ambiguous_addressees/runs.jsonl` (12 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 90/90 (100%) | 0 | 29.5 | 98 |
| mistral-small3.2:24b | production-nouns | full | default | default | 3 | 90/90 (100%) | 0 | 26.2 | 100 |

## Failed checks by configuration

None.

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 15 | 0 | 0 | 0 |
| mistral-small3.2:24b | production-nouns | full | default | default | 15 | 0 | 0 | 0 |
