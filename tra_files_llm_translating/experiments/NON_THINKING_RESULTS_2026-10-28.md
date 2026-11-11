# Non-thinking model comparison — 2026-10-28

All seven approved candidates completed. Mistral Small3.2 has the highest pooled
check score; Gemma3 and Gemma4 are the next candidates to review. None is reliable
enough for unattended export. Production model and prompt remain unchanged.

## Method and completion

The [pre-run plan](NON_THINKING_PLAN_2026-10-27.md) records the approved order,
downloads, settings and subsequent serving corrections. Five datasets (archived
InkGallery plus four synthetic fixtures), three repeats, production prompt, full
dialogue scope, context 8192, model-default sampling and `num_predict=-1` were used.
Reference translations were withheld. No fixed seed, automatic quality retries,
splitting or token caps were added. All models were retained.

The batch ran from 2026-10-28T01:35:15.445774+00:00 to 2026-10-28T03:34:04.120728+00:00.
This roughly two-hour elapsed time includes downloads, probes and interruptions.
There are 210 request records, 209 actual scored requests; Aya skipped one female
request after its male reply failed validation. Compatibility probes are separate.
No scored reply has a nonempty thinking field.

## Frozen results

Checks passed are targeted assertions, not overall translation accuracy. Pooled
scores weight larger fixtures more heavily; macro is the mean of five fixture
percentages. Complete pairs require both male and female replies to pass structural
validation; this does not establish linguistic correctness. Times sum request wall
time and exclude downloads. GPU placement is the observed Ollama allocation.

| Order / model | Checks | Pooled | Macro | Complete pairs | Rejected requests | Request seconds | GPU |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1. Gemma3 12B | 570/660 | 86.36% | 83.65% | 12/15 | 3 | 142.33 | 100% |
| 2. T-lite 2.1 Q4_K_M | 523/660 | 79.24% | 79.21% | 12/15 | 3 | 122.81 | 100% |
| 3. Aya Expanse 8B | 427/660 | 64.70% | 63.82% | 10/15 | 5 | 70.24 | 100% |
| 4. Vikhr-Nemo 12B Q6_K | 490/660 | 74.24% | 76.61% | 11/15 | 4 | 128.49 | 100% |
| 5. Mistral Small3.2 24B | 592/660 | 89.70% | 85.45% | 12/15 | 3 | 256.30 | 96.7% |
| 6. Gemma4 12B (off) | 564/660 | 85.45% | 83.84% | 12/15 | 3 | 97.80 | 100% |
| 7. Qwen3 14B (off) | 503/660 | 76.21% | 76.57% | 12/15 | 3 | 133.84 | 100% |

Mistral used some CPU offload; its timing is not a full-GPU speed comparison.
T-lite timing includes 48.4 s and 21.8 s outliers without observed thinking.

| Model | InkGallery /270 | Addressees /66 | Multiple NPCs /132 | Original female /90 | Reused strings /102 |
|---|---:|---:|---:|---:|---:|
| Gemma3 12B | 257 | 66 | 112 | 45 | 90 |
| T-lite 2.1 Q4_K_M | 217 | 66 | 111 | 39 | 90 |
| Aya Expanse 8B | 189 | 58 | 93 | 42 | 45 |
| Vikhr-Nemo 12B Q6_K | 174 | 58 | 125 | 43 | 90 |
| Mistral Small3.2 24B | 269 | 62 | 126 | 45 | 90 |
| Gemma4 12B (off) | 235 | 62 | 132 | 45 | 90 |
| Qwen3 14B (off) | 211 | 66 | 98 | 38 | 90 |

Prior same-evaluation baselines: Qwen2.5 14B 541/660 (81.97%), Qwen3.5 9B
thinking off 523/660 (79.24%). Mistral improves on Qwen2.5 by 51 checks (7.73
percentage points). These small, overlapping tests do not establish statistical
significance or general model superiority.

## Manual review

All seven configurations were read across all datasets and repeats, including
raw rejected replies. Representative observations:

- **Mistral:** strongest pooled result and generally good verb genders, but feminine
  dialogue retains masculine `приключенец` and `странник`; awkward agreement and
  mixed singular/formal address survive even perfect fixture scores.
- **Gemma3:** often fluent, but female player lines retain masculine nouns/verbs;
  Orin becomes Один and ferryman becomes a crossing. Its perfect addressee score
  misses that meaning error. One reply leaves “downstairs” in English.
- **Gemma4:** fast, strong checked role verbs; all multiple-NPC checks pass, yet a
  female traveler remains `путник`. Other replies include awkward phrasing and a
  masculine verb addressed to female Player1.
- **T-lite:** no reasoning observed, but formal address, missing gender edits and
  invented clauses remain. Ferryman becomes carpenter/farmer despite a perfect
  addressee score; one phrase reads `я пойдём`.
- **Qwen3:** formal address, renamed locations, “seen” changed to “read”, case errors
  and literal awkward phrasing. Some female verbs improve while nouns stay male.
- **Vikhr:** extensive female rewrites, invented motivations and mixed-script names;
  one female reply invents a protected engine token and is rejected. Fifty-two
  wording-review flags are a useful signal, not fifty-two proven errors.
- **Aya:** weaker fidelity, including invented names and two repeats that shift
  text between syntactically valid line IDs. Additional replies lose stage markers
  or translate protected engine tokens.

Every candidate fails all three explicit-empty female-literal requests (21
rejections). Aya adds two structural failures and Vikhr adds one: 24 rejected
actual requests overall. A further Aya female request is skipped. In total, 81/105
pairs are structurally complete. All seven also fail the mixed-speaker readiness
case in the male pass: one gendered translation cannot serve both speakers.

## T-lite correction

The initial metadata-only skip was wrong and had no inference evidence. The
publisher describes T-lite as non-thinking. Actual probes showed no reasoning.
One default non-streaming response routed translation JSON into `message.thinking`,
leaving content empty; that field was not a reasoning trace. The tested GGUF digest
uses explicit `think:false` as an Ollama serving workaround. All 30 scored requests
completed without thinking output. See the detailed
[runtime validation](TLITE_RUNTIME_VALIDATION_2026-10-28.md).

The correction interrupted the original runner. Aya finished before T-lite’s final
backfill, which ran during the subsequent Vikhr download with main inference held.
Thus execution departed from the planned order. Completed Gemma/Aya quality tests
were not repeated. Failed/default attempts and diagnostic probes remain archived
outside the scored suite. The final manifest/report incorporates the successful
T-lite backfill and preserves the prior manifest.

## Evaluation limits and interpretation

Frozen scores were retained throughout; manual inspection identified limitations:

- The readiness check also forbids feminine wording in the female pass, where both
  speakers are female. That is overly strict; the male-pass conflict is real.
- Noun checks miss synonyms such as `приключенец` and the synthetic traveler.
  Singular-address checks also miss some polite/plural imperatives.
- Narrow regexes reject valid `пообещал/пообещала`, alternative injury wording,
  `этажом ниже` and plausible `Брэм` spelling. Mistral’s six multiple-NPC misses
  are valid prefixed promise verbs. Gemma4’s six-check advantage across the four
  new fixtures is entirely explained by that check limitation.
- Newline counts can pass after the newline moves. Valid IDs do not ensure that
  meaning remains attached to the right ID. Structural success is insufficient.
- Four fixtures are synthetic and authored/reviewed by the same assistant. These
  are not independent human judgements or a blind real-mod corpus. Three repeats
  are small, and assertions and repeated strings are not independent samples.
- Default sampling differs between models. Vikhr uses Q6_K, others Q4_K_M.
  Serving templates, quantization and hardware placement confound architecture
  comparisons; this measures practical installed configurations.

Mistral, Gemma3 and Gemma4 merit further reviewed draft comparisons. First fix
the evaluation blind spots and shared/empty-string handling, then use a separately
reviewed real-dialogue set. This is a recommendation; no new phase, thinking run,
production promotion or commit was started automatically.

## Reproducibility and artifacts

The portable [JSON results](NON_THINKING_RESULTS_2026-10-28.json) retain exact tags,
digests, quantization, sizes, per-fixture metrics, serving version and frozen hashes.
Ollama version: 0.40.11. Frozen input/runtime hashes and identical male prompts
across candidates were verified; scored requests match 8192 context and uncapped
generation. The runner and tests passed all 45 tests after compatibility changes.

The Git-ignored [raw batch directory](results/non-thinking-20261028-013515/) holds
the final `manifest.json`, `REPORT.md`, `scores.csv`, `final_metrics.json`, source
snapshots, per-model request/reply logs, outputs, pair reviews, intervention history,
prior runner revisions and `MANUAL_REVIEW_NOTES.md`. They are local artifacts and
may be absent in another checkout. T-lite’s scored folder is `02-validated-off/`;
`02/` is compatibility history. `manifest-main-run-before-backfill-merge.json`
preserves the superseded main manifest.

To reproduce a fresh run from the repository root:

```bash
python3 -u tra_files_llm_translating/experiments/run_non_thinking.py
```

Use a fresh results directory; the runner has no automatic resume. Future tags
may move: compare digests in the JSON before claiming an exact reproduction.
