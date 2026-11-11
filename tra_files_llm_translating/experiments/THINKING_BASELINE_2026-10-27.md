# Uncapped thinking baseline — Qwen3.5:9b, 2026-10-27

Thinking on was impractical at the context setting used by our comparison. It
spent 37 minutes on the suite and completed one of fifteen dialogue pairs.
Thinking off took about 91 seconds and completed eleven pairs. Fourteen
thinking-on requests exhausted the context without returning any answer.

This is a matched **8192-context** experiment, not a test of Qwen3.5 at its full
262144-token native context. It does not show that thinking cannot improve
translation when given more context. It does establish the failure mode, latency
and usable-output rate of unrestricted thinking at our current test setting.

## Request and frozen settings

The user explicitly requested thinking on without a thinking limit, as a baseline.
No short-reasoning instruction, thinking budget, output-token cap, client timeout,
retry, repair, split or backend change was introduced.

- Installed `qwen3.5:9b`, Q4_K_M, Ollama 0.40.11.
- Production prompt, full dialogue, model-default sampling, no fixed seed,
  three repeats per dataset, male pass followed by female edit.
- InkGallery v2 and the same four synthetic fixtures used by the
  [thinking-off model comparison](MODEL_COMPARISON_2026-10-27.md).
- Exact runtime options: `{"num_ctx":8192,"num_predict":-1}`; `think:true`.
  This toggles thinking on while preserving the previous context and other
  request settings. Native context was not selected or silently substituted.
- Runtime code, checks, glossary, actors and input CSV hashes were checked against
  the thinking-off manifest before the run and again after it. The request
  payloads were verified afterward. Documentation updates do not alter the run.
- All five dataset GPU checks reported 100% placement, approximately 5.86 GB
  resident. No CPU offload was observed. First-load/cache conditions and timing
  order are not randomized, and sampling is nondeterministic.
- Run: 2026-10-27 22:31:58–23:09:16 UTC. All scheduled repeats finished.
  Nineteen actual requests were made; eleven female passes were skipped after
  failed male replies. Those skipped passes count as failed expected checks.

## Results

| Metric | Thinking off | Thinking on |
|---|---:|---:|
| Expected-form checks passed | 523/660 (79.24%) | 65/660 (9.85%) |
| Complete valid dialogue pairs | 11/15 | 1/15 |
| Actual requests | 30 | 19 |
| Structurally rejected replies | 4/30 | 14/19 |
| Female passes skipped after male failure | 0 | 11 |
| Requests ending at context capacity (`length`) | 0 | 14 |
| Sum of request wall times | 91.43 s | 2232.00 s (37m 12s) |
| Median actual request time | 2.305 s | 124.74 s |
| Generated tokens reported by Ollama | 4,390 | 131,929 |
| Thinking text characters | 0 | 505,669 |

Thinking on used about **24.4 times the total request wall time** and **30.1 times
the generated tokens**, despite making fewer requests because failures prevented
female passes. Token counts are Ollama's total `eval_count`, not a separately
measured exact thinking-token count. Thinking length is recorded in characters.

The main score includes failed and skipped output; it is a reliability-sensitive
expected-form score, not a percentage of translation quality. Scores on valid
replies alone were 65/67 checks (97.01%) for thinking on and 523/604 (86.59%) for
thinking off. That conditional comparison is strongly biased toward requests
that finish: thinking on returned translations for only two of the five datasets,
and most of its intended outputs were missing. It cannot be used as evidence of
an overall 97% translation accuracy or as a winner-selection metric.

| Dataset | Thinking off | Thinking on | Thinking-on complete pairs |
|---|---:|---:|---:|
| InkGallery v2 | 234/270 | 0/270 | 0/3 |
| Ambiguous addressees | 53/66 | 20/66 | 1/3 |
| Multiple NPCs | 112/132 | 0/132 | 0/3 |
| Original female variants | 42/90 | 45/90 | 0/3 |
| Reused strings | 82/102 | 0/102 | 0/3 |

## What failed

All fourteen rejected actual replies had an empty `message.content` and
`done_reason=length`. The validation error is consequently a JSON parse failure;
there is no translation JSON to recover from the answer field. Their reasoning
traces are retained, but drafts inside a trace were not substituted for answers.

For every such request, the reported prompt tokens plus generated tokens equal
8192 exactly. This is direct evidence of the existing context capacity being
exhausted while reasoning. Examples:

| Request | Prompt tokens | Generated tokens | Total | Wall time |
|---|---:|---:|---:|---:|
| InkGallery, male repeat 1 | 1,203 | 6,989 | 8,192 | 123.06 s |
| Multiple NPCs, male repeat 1 | 785 | 7,407 | 8,192 | 125.22 s |
| Reused strings, male repeat 1 | 684 | 7,508 | 8,192 | 126.92 s |

The configured context is finite even though no thinking/output budget was added.
A small source dialogue does not imply a short thought process. All three
InkGallery male passes, all three multi-NPC male passes, all three shared-string
male passes, two ambiguous-dialogue male passes and all three original-female
edit passes returned no answer. No result was rerun to obtain a better score.

## Manual reading of the returned translations

All five valid replies were read against the English sources: the two passes of
one ambiguous-dialogue repeat, and the three male passes of the original-female
fixture. There are no other returned translations to assess. Empty rejected
answer fields cannot establish the gender or meaning quality of a translation.

**Ambiguous addressees, repeat 2:** both replies preserve the same natural,
gender-neutral wording, including `Ты меня слышишь?` and `Я тебя слышу, но
Селена — нет.` The female version copies the male exactly. Both pass 10/11 checks;
the missed `current retained` check requires a form of `течение`, whereas the
model uses the reasonable synonym `Поток слишком силен.` This is a known narrow
regex miss; the frozen score has not been changed. The rope sentence
`Оставайся на том берегу, пока канат не станет надёжным` is understandable but
less precise/natural than making clear that the rope must be securely fastened.
The pair takes 238.85 seconds. This is not a difficult gender-edit case: no
Player1-dependent gender words need changing.

**Original female variants, all male repeats:** all three return good short
translations such as `Я был его учеником`, `Герцог послал тебя забрать его
печать`, `Я принёс серебряный ключ` and `Я подожду здесь`. Each passes 15/15 checks
and is better than some thinking-off replies that mistranslated duke or the key
material. The three male replies take 64.17, 90.61 and 97.43 seconds. However,
every corresponding female request returns no JSON. We therefore cannot assess
whether thinking fixes the mentor/patron gender changes, bronze key, or explicit
empty female literal. No valid two-pass export results from this fixture.

No live thinking-on answer was returned for the shared-speaker readiness string,
so the earlier `Я готова` failure is neither confirmed nor fixed by this run.
The copy-only wording diagnostic passes for the five lines of the one complete
ambiguous pair. Most other comparisons are unavailable; original female sources
that differ remain marked not applicable rather than being compared literally.

## Interpretation and next decisions

Under the fixed comparison settings, thinking on substantially reduces useful
throughput and completion reliability. The few completed replies can be good,
but they do not offset the missing output. Keep this as the unmodified baseline;
no production model or prompt was changed and no cap has been implemented.

If translation quality with thinking is to be investigated further, context
capacity must be considered explicitly. A separate larger/native-context pilot
could let reasoning reach an answer, at potentially greater latency and memory
cost; it would not be the same 8192-context comparison. A genuinely separate
thinking budget would be a different experiment/backend capability. Neither
follow-up has been run. The current results should not be presented as evidence
that all thinking modes, budgets or context sizes are inferior.

## Reproducibility and artifacts

The baseline uses the same uncommitted evaluation code on top of commit `f01ac30`
as the previous comparison. The local results folder is Git-ignored; this report
is a portable summary and raw links may not exist in another checkout.

- [Run manifest, exact commands, model metadata and SHA-256 values](results/thinking-on-20261027-223158/manifest.json)
- [Aggregate thinking-off/on metrics](results/thinking-on-20261027-223158/comparison_metrics.json)
- [Per-request timings, generated tokens, thought/answer lengths and completion reasons](results/thinking-on-20261027-223158/comparison_requests.csv)
- [Input and runtime code snapshots](results/thinking-on-20261027-223158/snapshot)
- [InkGallery scores](results/thinking-on-20261027-223158/qwen35/inkgallery/summary.md)
- [Ambiguous-addressee scores](results/thinking-on-20261027-223158/qwen35/ambiguous_addressees/summary.md)
- [Multiple-NPC scores](results/thinking-on-20261027-223158/qwen35/multiple_npcs/summary.md)
- [Original-female-variant scores](results/thinking-on-20261027-223158/qwen35/original_female_variants/summary.md)
- [Reused-string scores](results/thinking-on-20261027-223158/qwen35/reused_strings/summary.md)

Each dataset folder also has `runs.jsonl` (exact requests, raw answer and thinking
fields, timings and validation failures), `outputs.csv`, and `pair_reviews.csv`.
The run driver and analysis script are saved at the results root.

Equivalent command for one dataset, from the repository root:

```bash
python3 -u tra_files_llm_translating/experiments/diagnose_translation.py \
  --models qwen3.5:9b \
  --checks tra_files_llm_translating/experiments/inkgallery_checks.json \
  --prompts production --scopes full --think on --temperatures default \
  --repeats 3 --num-ctx 8192 --out <fresh-dataset-folder>
```

Verification: all five stages finished; all nineteen actual payloads have
`think:true` and the exact uncapped-generation options above; all fourteen
rejections have empty answers and reached the context boundary; snapshot and
runtime-input hashes match. No runtime code was changed for this experiment.
