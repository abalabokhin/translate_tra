# T-lite: correcting a metadata-only exclusion

The initial skip was wrong: no inference had been run before classifying T-lite
as ineligible. The user pointed out the publisher's explicit non-thinking note.
Actual tests found no reasoning. The installed Ollama artifact has a metadata /
channel compatibility problem, and a verified serving configuration now allows
the model to participate in the full comparison.

## Evidence

Model: `hf.co/t-tech/T-lite-it-2.1-GGUF:Q4_K_M`, digest
`24727915b419e9949ba993e59353f72b84650693c73af70d4a0886e0b5416cf9`.
Ollama 0.40.11 reports `thinking.values=[true]` and its installed template opens
`<think>`. Neither observation proves actual reasoning. The
[publisher's model card](https://huggingface.co/t-tech/T-lite-it-2.1) says this is
a non-thinking model and no explicit disabling flag is required.

| Probe | Observed result | Wall time |
|---|---|---:|
| Short translation, default mode, non-streaming | Clean `Дверь открыта.`, no thinking field | 2.90 s including load |
| Short translation, explicit false, non-streaming | Same answer preceded by stray `</think>`; no reasoning | 0.10 s |
| Full production prompt + JSON schema, default, streaming | Complete JSON in content, no thinking field | 5.54 s |
| Full production prompt + JSON schema, explicit false, streaming | Complete JSON in content, no thinking field | 3.59 s |
| Full production prompt + JSON schema, default, non-streaming | Translation JSON in thinking field, content empty; no reasoning prose | 7.81 s |
| Full production prompt + JSON schema, explicit false, non-streaming | Complete JSON in content, no thinking field or stray tags | 3.59 s |

An earlier pending non-streaming request was manually interrupted to inspect
streaming behavior. Its lack of a returned result is not proof of thinking and is
not a translation-quality failure. All incomplete artifacts are archived.

The default non-streaming reply placed `assistant` followed by translation JSON
inside `message.thinking`. A populated thinking field alone therefore also failed
to establish reasoning. The precise contribution of the imported template,
Ollama channel parsing and generated control tokens has not been fully isolated.
No reasoning trace was observed in the completed probes.

## Verified full-suite configuration and result

Use explicit `think:false` together with the production JSON schema and the
existing non-streaming evaluator. This is a serving-compatibility choice, not
stripping control tokens, moving text into another field, or repairing a reply.
The exception is pinned to the tested digest; another artifact needs validation.
Other model metadata is not blindly overridden. Context 8192, production prompt,
full scope, default sampling and 3 repeats remain unchanged.

All 30 requests across the five frozen datasets completed with no nonempty
thinking output. The model passed **523/660 checks (79.24%)**; 3 female replies
failed structural validation for keeping text where the original female literal
is explicitly empty. Twelve of fifteen pairs have both replies structurally
valid. This is now a real quality evaluation rather than a metadata-based skip.
These scores do not prove overall translation accuracy.

Latency includes two substantial outliers (48.4 s and 21.8 s) despite short final
answers and no thinking output. The surrounding batch had begun Vikhr's download;
the main client was held to prevent overlapping inference, but download/server
load and scheduling are not controlled. Do not interpret every latency spike as
reasoning or treat total wall time as pure decoder speed.

## Chronology and artifacts

The original runner was cleanly interrupted during Aya's pull to correct T-lite.
Two subsequent default-mode attempts were retained: the diagnostic interruption
and the reply whose JSON was routed into the thinking field. Aya's tests finished
before the explicit-off backfill. The backfill held the main runner during
Vikhr's download, then resumed it. This departs from the intended test order due
to the serving correction and is disclosed; completed Gemma/Aya tests were not
repeated. No frozen checks or prompts were tuned to improve T-lite's score.

Local artifacts (Git-ignored, may be absent in another checkout):

- [Raw probes, requests, responses and streamed chunks](results/non-thinking-20261028-013515/tlite-runtime-probe)
- [Rejected default-mode channel response](results/non-thinking-20261028-013515/02/inkgallery/unexpected_thinking.json)
- [Verified-off full-suite manifest](results/non-thinking-20261028-013515/02-validated-off/manifest.json)
- [Verified-off results](results/non-thinking-20261028-013515/02-validated-off)
- [Completed backfill entry for final merge](results/non-thinking-20261028-013515/completed_tlite_backfill.json)

The seven-model batch is complete. The successful explicit-off backfill is merged
into the final main manifest, combined report and scores. The earlier main manifest
is preserved as `manifest-main-run-before-backfill-merge.json`. See the
[final comparison](NON_THINKING_RESULTS_2026-10-28.md). All prior attempts remain
serving-compatibility history. Tests cover the artifact-pinned override and manual
continuation; all 45 tests pass. No production settings or model defaults changed.
