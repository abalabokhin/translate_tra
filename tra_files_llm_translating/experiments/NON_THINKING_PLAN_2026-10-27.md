# Ordered non-thinking comparison — plan recorded before downloads

User authorization (2026-10-27): run the seven proposed models in the specified
order, downloading one model, testing it, then moving to the next. Document the
procedure before proceeding. Thinking should be reconsidered only after this
non-thinking comparison, not enabled automatically by this runner.

No new download or inference request for this batch had started when this plan
was written. The existing `run_all.py` pulls all models before its three stages
and tests only one dialogue checks file. The dedicated `run_non_thinking.py`
reuses its Ollama pull client and the frozen experiment implementation, but runs
the requested per-model lifecycle across all five dialogues.

## Exact order and distribution sources

| Order | Candidate | Exact Ollama pull tag | Source |
|---|---|---|---|
| 1 | Gemma 3 12B | `gemma3:12b` | Ollama library |
| 2 | T-lite 2.1 | `hf.co/t-tech/T-lite-it-2.1-GGUF:Q4_K_M` | Publisher's Hugging Face GGUF through Ollama |
| 3 | Aya Expanse 8B | `aya-expanse:8b` | Ollama library |
| 4 | Vikhr-Nemo 12B | `hf.co/VlSav/Vikhr-Nemo-12B-Instruct-R-21-09-24-Q6_K-GGUF:Q6_K` | Community Hugging Face GGUF through Ollama |
| 5 | Mistral Small 3.2 24B | `mistral-small3.2:24b` | Ollama library |
| 6 | Gemma 4 12B | `gemma4:12b` | Ollama library, thinking explicitly off |
| 7 | Qwen3 14B | `qwen3:14b` | Ollama library, thinking explicitly off |

Ollama manages all seven downloads and serves all inference. No Transformers,
separate inference service, Hugging Face login or new backend is planned.
Hugging Face is the weights source for two models. The Vikhr quantization is the
Q6_K entry already in the repository's candidate list. T-lite uses the publisher's
Q4_K_M GGUF tag. Actual model digests, quantization, templates, sampling defaults
and thinking metadata are saved after installation. Mutable library tags are
identified by their recorded digests, not assumed immutable.

Sources checked before the run:

- [Gemma 3](https://ollama.com/library/gemma3:12b)
- [T-lite publisher GGUF](https://huggingface.co/t-tech/T-lite-it-2.1-GGUF)
- [Aya Expanse](https://ollama.com/library/aya-expanse)
- [Vikhr community GGUF](https://huggingface.co/VlSav/Vikhr-Nemo-12B-Instruct-R-21-09-24-Q6_K-GGUF)
- [Mistral Small 3.2](https://ollama.com/library/mistral-small3.2)
- [Gemma 4](https://ollama.com/library/gemma4:12b)
- [Qwen3](https://ollama.com/library/qwen3:14b)

## Fixed test configuration

Reuse the production prompt, whole-dialogue scope, model-default sampling, no
fixed seed, 3 repeats, male translation then female edit. Context stays at the
explicit experimental value 8192 to match the completed comparisons. Generation
remains `num_predict=-1`; no output cap, timeout, retries, splitting or repairs.
Thinking is disabled for switchable models and left unset for native non-thinking
models. Models that only support reasoning are skipped with a recorded reason.

Dataset order within every model:

1. InkGallery v2 (12 rows).
2. Ambiguous addressees (5 synthetic rows).
3. Multiple NPCs (6 synthetic rows).
4. Original female variants (5 synthetic rows, including an intentionally empty female literal).
5. Reused strings (6 synthetic rows, 4 unique TRA strings).

Each model schedules 15 dialogue pairs / up to 30 requests and 660 expected checks.
The seven-model batch schedules up to 210 requests. A male failure skips its
female pass; both missing outputs fail their expected checks. The exact frozen
checks, source CSVs, actor facts and glossary from the previous comparisons are
retained. Reference translations remain withheld. Wording-review flags stay
separate from automatic scores. No tuning is performed between models.

## Sequential lifecycle and failure handling

For each candidate: check installation, pull if absent, save metadata, verify
non-thinking support, test all five datasets, write summaries, then proceed to
the next candidate. Downloads are not parallelized or prefetched. Installed models
are reused. Downloaded models are retained; no model deletion is authorized by
this plan. Ollama manages GPU residency. GPU placement is recorded; partial CPU
offload is reported and timing is not treated as comparable. Context is not
silently reduced to force a model to fit.

A pull/show failure is recorded and that candidate is skipped without replacing
its tag, quantization or repository. Ordinary request/validation failures are
recorded by the existing experiment with no retries. If a supposedly disabled
model emits a nonempty thinking field, stop using that candidate for this
non-thinking batch, retain its evidence and record the issue. Never fall back to
thinking mode. A failed stage is retained and the next model can still run.

Ctrl+C retains completed logs and the incremental manifest/report. There is no
automatic resume or re-execution; a fresh output directory is required for a new
run. No commits or production translator/model changes are part of this batch.

## Artifacts and review

Before the first download, save this plan, the ordered manifest, baseline model
inventory/version, checks/input/runtime SHA-256 values and source snapshots in a
fresh `experiments/results/non-thinking-<UTC timestamp>/` directory. Record exact
commands, pull status and model show metadata incrementally. Per-dataset artifacts
are `runs.jsonl`, `summary.md`, `outputs.csv` and `pair_reviews.csv`. Save a combined
report and per-model/per-dataset score CSV while progressing.

Compare completed-pair rate, failures, per-fixture and equally weighted scores,
wording-review flags and time, with the earlier Qwen baselines as references.
Scores do not establish translation accuracy. Inspect actual translations from
the leading models and representative failures from the others, noting any
narrow regex misses. Do not change frozen checks or salvage rejected lines to
improve the ranking. Report review coverage explicitly.

Run from repository root:

```bash
python3 tra_files_llm_translating/experiments/run_non_thinking.py --dry-run
python3 -u tra_files_llm_translating/experiments/run_non_thinking.py
```

Defaults implement this exact order, all five datasets, 3 repeats and context
8192. Results and final review will be linked here after the run.

## Correction before continuation — T-lite runtime validation

The initial runner skipped T-lite based solely on Ollama's `thinking.values=[true]`
and a template that opens `<think>`. The user challenged this using the publisher's
explicit statement that T-lite 2.1 is non-thinking and no `enable_thinking=False`
is required. No inference had supported the initial skip; it was too strict.

The batch was held during two direct translation probes on 2026-10-28 UTC:

- Native default request: `Дверь открыта.` in 2.90 s including model load; clean
  `message.content`, no thinking field, seven generated tokens, `stop`.
- Explicit `think:false`: `</think>\n\nДверь открыта.` in 0.10 s; no reasoning,
  but a stray closing marker. No marker-stripping repair is introduced.

Thus metadata is not sufficient evidence of actual reasoning for this artifact.
The correction uses native/default mode for **only** the directly verified
T-lite tag and digest
`24727915b419e9949ba993e59353f72b84650693c73af70d4a0886e0b5416cf9`.
The actual-response guard against nonempty thinking remains active for every
request. Other thinking-only metadata is not automatically overridden, and a
future changed T-lite digest requires fresh validation.

T-lite will receive the full frozen suite before Aya inference begins. Aya's
weights had already begun downloading after the premature skip; this order
exception is retained in the history rather than hidden. Gemma 3 is not rerun and
no inference failed on T-lite before this correction. The earlier runner is
cleanly interrupted to avoid stale in-memory state overwriting corrected results.
An explicit manual continuation runs orders 2–7 in the existing result directory;
this is not automatic resume/retry behavior. Preserve the original manifest and
runner snapshot, archive the updated runner and probe requests/responses, and
record this intervention in the manifest. The evaluator, frozen checks, prompt,
context and other sampling settings are unchanged.

Further production-prompt probes also returned full JSON without thinking: native
default/streaming 5.54 s, explicit false/streaming 3.59 s. A pending non-streaming
suite request was manually interrupted to inspect streamed behavior; its incomplete
artifacts and manifest are archived under `tlite-runtime-probe/`. This diagnostic
interruption is disclosed separately from model validation failures, and the T-lite
suite starts fresh without rerunning Gemma. All scoring settings stay fixed.

### Final T-lite serving configuration after real non-streaming validation

A subsequent native/default non-streaming request returned `stop` in 7.81 s but
put the translation JSON itself (prefixed by `assistant`) in `message.thinking`,
with empty `message.content`. This is misrouted answer text, not a reasoning trace.
The initial actual-response guard stopped the candidate, preserving the full
response. It must not be described as proof that the model reasons.

Explicit `think:false` with the **production JSON schema and non-streaming API**
returned clean JSON in `message.content` in 3.59 s, no thinking field or stray tags.
Therefore the verified artifact exception now selects explicit `off`, not native
default. No content is stripped, moved between fields or salvaged. Other settings
remain frozen. A separate full T-lite suite at `02-validated-off/` will be run
while the main runner is temporarily held during Vikhr's download. Aya has already
finished its tests by this point; that chronology is disclosed. Completed Gemma
and Aya results are retained. The backfill has its own incremental manifest and
will be merged into the final combined report after the main runner finishes,
retaining the default-mode attempts as compatibility evidence. This is a manual
serving-compatibility correction following the user's challenge, not an automatic
retry or a search over translation prompts/temperatures.
