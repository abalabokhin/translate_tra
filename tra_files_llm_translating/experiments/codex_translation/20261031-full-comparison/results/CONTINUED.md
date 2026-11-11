# Original launcher stopped; comparison continues

The second Luna simultaneous reply added quotation marks and failed unchanged
structural validation. Both attempted pairs and all raw artifacts are retained.
`../continue_unattempted.py` continues only the unattempted combinations, without
retries, under the frozen original runtime and inputs. Canonical full-grid state:
`../COMPARISON.json`, progress/results: `../REPORT.md`. This original manifest
and report describe the stopped initial launcher, not the whole comparison.
Invalid replies are recorded as rejections and remaining independent cases run;
CLI/infrastructure errors still stop the coordinator. Missing/invalid passes fail
all expected checks, and valid male passes are retained if a female pass fails.
