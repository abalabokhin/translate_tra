# Diagnostic results

Evaluation versions: inkgallery_beholder-v1

Source: `/home/paladin/source/translate_tra/tra_files_llm_translating/experiments/translate_verify/20261031-021108-continuation/remaining-translations/translate-verify/inkgallery_beholder/translation/runs.jsonl` (6 requests). Checks = expected-form tests from the checks JSON, summed over repeats. Failed outputs and skipped female passes fail all expected checks. Time and tokens are per actual request.

| model | prompt | scope | think | temp | runs | checks ok | failed requests | avg s | avg tokens |
|---|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 3 | 90/90 (100%) | 0 | 98.7 | 404 |

## Failed checks by configuration

None.

## Male/female wording review

Diagnostic flags only; excluded from check scores and automatic selection. A pass does not establish correct gender or faithful meaning.

| model | prompt | scope | think | temp | pass | review | missing | different source |
|---|---|---|---|---|---|---|---|---|
| mistral-small3.2:24b | production | full | default | default | 32 | 1 | 0 | 0 |
