# Native-context thinking comparison — 2026-10-28

The user requested rerunning the failed Qwen3.5 thinking baseline at native
context, then explicitly requested the same suite for the other already
downloaded thinking models. Do not download additional models or retest
non-thinking models in this phase.

## Sequence and settings

1. `qwen3.5:9b`, 262144 context — currently running in
   `results/thinking-native-20261028-094842/`.
2. `gemma4:12b`, 262144 context.
3. `qwen3:14b`, 40960 context.
4. `huihui_ai/qwen3.5-abliterated:9b`, 262144 context.
5. `huihui_ai/qwen3-abliterated:14b`, 40960 context.

Context limits and thinking support were verified against installed Ollama
metadata. The two abliterated tags are distinct installed configurations and
receive their own full suites. T-lite is excluded: its misleading thinking
metadata was previously disproved by runtime probes and publisher information.
Gemma3, Mistral Small3.2, Aya, Vikhr and Qwen2.5 lack native thinking support in
the downloaded configurations.

For each model, use the frozen InkGallery checks plus the four existing
fixtures; production prompt; full dialogue graph; male translation followed by
female edit; model-default sampling; three repeats; `think:true` and
`num_predict:-1`. No added output limit, timeout, reasoning budget, seed,
partitioning, quality retry, fallback or automatic repair. Models run sequentially
after the current suite finishes. Record each model's native context explicitly;
do not reduce it to force GPU residency. Capture observed GPU placement and
memory: timings with CPU offload need that qualification.

## Evidence and reporting

Preserve exact tags/digests, serving metadata, commands, input/runtime hashes,
source snapshots, raw reasoning and answers, errors, structural validation,
per-request timings/tokens, per-fixture scores and male/female wording reviews.
Save incremental manifests. Read valid and rejected outputs for meaning and
gender errors; do not treat targeted checks as translation accuracy or salvage
rejected rows into the scored result.

Compare Qwen3.5 against its same-model 8192 thinking-off and thinking-on baselines.
Compare Gemma4 and Qwen3 against the prior non-thinking suite, noting that thinking
and context both change. The abliterated variants have no matching frozen
thinking-off suite; label their results accordingly. Retain frozen evaluator
limitations, including missed nouns and narrated pronouns and overly narrow
promise/current/injury checks. No production setting or model is promoted
automatically. No commit is authorized by this new experiment request.

The remaining-model driver is `/tmp/run_remaining_thinking_native_20261028.py`;
it archives itself under a fresh `results/thinking-native-remaining-<UTC>/` root.
The runner has no automatic resume. Check saved manifests and raw logs before
restarting any interrupted suite, and never repeat completed tests silently.
