# Session handoff — start here

## Current status — GPU investigation documented, 2026-10-31

Read the [thermal results and decisions](experiments/gpu_thermal/20261031/README.md)
and [ROCm investigation](experiments/gpu_thermal/20261031/ROCM_INVESTIGATION.md).
User requested documenting everything and committing the necessary investigation
artifacts. Translation outputs predating this investigation remain separate.

- Thermal spikes reproduced on both kernels, with Mistral at 131K and 4K,
  and Gemma4 at 4K. Manual 60% fans did not prevent them.
- Default interactive Mistral at 4K completed with all 41 layers on GPU. Peak
  temperature during that interactive request was not recorded. A longer
  synthetic prompt at the same 4K context reached 99°C junction.
- Gemma batch 64 failed model initialization, not a successful cool inference.
  Qwen2.5 14B at 4K / batch 64 completed, peak 87°C junction / 261 W.
- Exact archived successful Mistral request was replayed without JSON changes.
  It failed with ROCm illegal memory access during weight upload, peak only
  44°C; kernel identifies SDMA0 page faults. Same backend build and offload
  layout as earlier success, model SHA256 valid. No root cause proven.
- User wants earlier successful settings and is interested in Mistral fully
  on GPU. Stop synthetic sweeps. Real dialogue at 4K was discussed but **not
  run**; no production context change or full-queue restart performed.
- No drivers/services/tuning changed during the latest audit. Manual fans
  restored to automatic and models unloaded at last check. Do not resume the
  long translation queue automatically. Historic running statements below
  need live verification before any recovery.

## Active power-loss recovery — 2026-10-31 02:11 UTC

User requested **commit everything, find the stopping point, and continue tests**.
Commit `6b42b6e` preserves all then-uncommitted work (90 files). After host reboot,
no inference client or loaded model remained. All 59 offline tests pass; frozen
input/runtime hashes and both model digests match.

The 22:06 continuation completed ambiguous_addressees, multiple_npcs,
original_female_variants and reused_strings (three successful verifier replies each).
Beholder's first male request failed transport and its female pass was skipped.
No other real-set translation or planted control was saved. See that run's STOPPED.md.
Together with original InkGallery, **five datasets are complete; do not repeat them**.

New continuation: `tra_files_llm_translating/experiments/translate_verify/20261031-021108-continuation`.
Driver: `experiments/translate_verify/POWER_LOSS_CONTINUATION_2026-10-30.py`.
Live execution session at launch: `63431`; check queue/process before any inference.
It runs Beholder, Moon Sisters and Sewers under `remaining-translations/` (27 calls),
then all seven complete-reference datasets under `planted-controls/` (54 calls),
then ten pending Sewers A/B requests. These are separate stage manifests.
Native contexts, uncapped generation, three repeats, no automatic retry/resume.
Do not relaunch the earlier seven-dataset driver: that would repeat completed work.
Manual review and final combined report remain pending; no production change approved.
The prior active-status sections below are historical.

## Active continuation — 2026-10-30 22:06 UTC

The user requested conflict resolution and continued testing. Rebase completed at
`3eaee4f`; both the remote stop note and local connection-failure evidence were
preserved. All 59 offline tests passed. Frozen input/runtime hashes and both model
digests match the original run.

**Continuation is running** in
`experiments/translate_verify/20261030-220610-continuation/` under
`experiments/translate_verify/CONTINUATION_LAUNCH_2026-10-30.py`.
Check `experiments/VERIFY_QUEUE_2026-10-29.json` and live process status before
starting any inference. It runs the seven remaining datasets plus planted controls,
then launches the ten pending Sewers A/B requests sequentially. Native contexts,
uncapped generation, three repeats; no automatic retries/resume. InkGallery is
reused from the completed original dataset. Manual review/report consolidation is
still pending after inference. No production change is approved.

Local artifacts clarify the original stop: ambiguous_addressees has six saved
translation replies and one failed verifier request (`Remote end closed connection
without response`), followed by connection refusal. There is no successful verifier
reply for it. The other PC's five-reply snapshot is historical; the fresh rerun
remains appropriate. Existing untracked raw outputs were preserved.

## Previous stopped state — 2026-10-30

**No job is running.** The translate + verify run `experiments/translate_verify/20261030-095325/`
stopped after InkGallery (complete) and 5 of 6 ambiguous_addressees translations; the
queued Sewers A/B continuation never started. Both queue files now say so. The user
agreed to **finish the translate + verify test before deciding** anything. To continue
on another machine follow
[experiments/translate_verify/CONTINUATION_2026-10-30.md](experiments/translate_verify/CONTINUATION_2026-10-30.md):
a new run folder for the remaining seven datasets and the planted stage, same settings,
then the 10 Sewers A/B requests, then review. Interim InkGallery result: 264→268/270,
6 real fixes, 1 harmful edit, a non-standard `приключенница` in all 3 repeats
([STOPPED.md](experiments/translate_verify/20261030-095325/STOPPED.md)). Process IDs
and "running" statements below are history.

## Earlier status

The user explicitly authorized **commit everything** on 2026-10-30. The current
commit is an in-progress experiment snapshot; see
`experiments/COMMIT_SNAPSHOT_2026-10-30.md`. At its pre-commit check six InkGallery
translation replies and one verifier reply are saved. The third translation pair
and that verifier reply still need review. Existing jobs continue; do not start
duplicates. Earlier no-commit notes describe the prerequisite now satisfied by
the explicit request. This authorization does not promote a production prompt/model.

Latest review (2026-10-30, user requested review of finished dialogue): see
`experiments/review/20261029/FINISHED_DIALOGUE_REVIEW_2026-10-30.md` and
`ASSISTANT_REVIEW_2026-10-30.csv` in the same directory. All saved translation
replies at its hashed snapshot are annotated: 89 logical records / 767 cells,
43 distinct full-line editorial proposals. Human approval remains pending;
proposals are separate from raw replies/references and were not fed to the
verifier. Two completed InkGallery translation pairs from the active verifier
run are reviewed in that run's MANUAL_REVIEW.md; no Gemma result is claimed.
Metadata confirms the dated source-log scope. Continue existing inference queues;
do not duplicate them or commit. See later status sections for process IDs.

Documentation check after that review: six InkGallery translation replies are
now saved in the active verification run; the last pair arrived after the dated
four-reply review snapshot and still needs manual review. No verifier/planted
JSONL results existed at this check. Main README, experiment README, review index
and A/B results summary now distinguish completed encounters from the serving
interruption and queued continuation. Treat older timestamped status notes as history.

Read [README.md](README.md) for the full workflow, experiment history, commands,
limitations and code review. This handoff records the latest decisions so the next
session does not restart abandoned experiments.

## Experiment decisions confirmed — 2026-10-29

The user confirmed both decisions after reviewing the latest commit:

- **No imposed context limit for now.** Use each model's native context, discovered
  from Ollama, for the prompt A/B translator and both translate + verify models.
  Do not impose the prepared runners' 8192-token translator context. Native context
  is the model's finite capacity, not an unlimited window. This decision concerns
  context; it does not approve the verifier's separate generation-token cap.
- **Verifier corrections must be complete lines.** Keep the error category and
  explanation, but ask the LLM for the whole corrected line and validate/apply that
  line. Do not splice proposed fragments into text with Python. The LLM must handle
  all related noun, adjective, verb and pronoun agreement together. Continue measuring
  false alarms, damaging edits and unrelated rewrites.

The user subsequently authorized rescoring, both experiments, manual review and
saving all artifacts, **without committing**. Do not commit until the user has
reviewed everything and explicitly asks. This overrides earlier requests in these
documents to commit experiment results automatically.

The runners now default to native context. The verifier returns complete corrected
lines (one issue per line/column), and Python validates and applies whole lines.
Uncapped generation (`num_predict=-1`) follows the standing instruction below;
no smaller context, generation cap, client timeout, retry or splitting is introduced.
New results will be recorded below once the authorized runs finish.

The user subsequently authorized assistant reference review, requested fresh text
from the same mod (InkGallery), and offered to review translations afterwards.
Three complete encounters (sewers, beholder, Moon Sisters; 36 rows) are now in
`experiments/real_set/`, with references/checks written before inference and source
snapshots/hashes. Human review is pending; do not call this independent human gold
data. Keep the current five-dataset A/B batch frozen and run a three-fixture A/B
extension separately. Translate + verify will include all eight datasets.


## Runtime decision reaffirmed after slowdown

The user explicitly chose **keep native context and continue uncapped** after a
normal 390-token Mistral reply took 3733.93 seconds. The following request was
also slow; read-only diagnostics showed memory pressure and substantial disk I/O.
Do not reduce context, switch translators, impose time/token limits, or restart
requests to improve timings. Preserve the slow observations. The job continues
under the same authorized protocol. Evidence and the decision are in
`experiments/prompt_ab/20261029-220151-recovered/RUNTIME_DIAGNOSTICS.json`.
Current active unified session: 5879; client PID 59881 (verify liveness before any
recovery). The original 60-request five-dataset run is finished; do not repeat it.

## Authorized evaluation status — 2026-10-29

- v3 rescoring complete: [report](experiments/RESCORED_V3_RESULTS_2026-10-29.md)
  and three portable CSVs next to the old reports.
- Five-dataset prompt A/B complete: production 703/717, nouns 704/717; 60 valid
  replies, zero unrelated-edit flags. All outputs reviewed by the assistant.
  Neither variant fixes either address noun in any repeat. Do not adopt the rule
  on this evidence. [Results](experiments/PROMPT_AB_RESULTS_2026-10-29.md).
- Three fresh InkGallery fixtures ready (36 rows); assistant references validated
  before inference. The separate real-set A/B extension is running under
  `experiments/prompt_ab/20261029-220151-recovered/` (session 5879).
- The daemon restart ended the first extension client after one male reply was
  saved. Original partial run `20261029-220151/` is preserved. A one-off documented
  recovery in `20261029-220151-recovered/` reuses that successful male reply (exact
  prompt/schema/options checked) and issues only the remaining 35 requests. The
  lost in-flight female output is unavailable and unscored. Recovery driver and
  metadata are archived; normal runners gain no automatic resume/retry behavior.
- Translate + verify is actively queued after A/B via a one-off sequential launcher.
  Unified session 94364; queue PID 64134. Check
  `experiments/VERIFY_QUEUE_2026-10-29.json` before launching anything: **do not start
  a second verifier run**. Once A/B reports finished, it starts all eight datasets
  (up to 72 stage-1 and 54 planted/clean requests), native contexts, uncapped.
  The launcher checks frozen inputs/runtime and exits on interruption or drift;
  it adds no inference retry/resume behavior. Source is archived under
  `experiments/translate_verify/SEQUENTIAL_LAUNCH_2026-10-29.py`.
- 59 offline tests pass with system Python. The stale venv lacks chardet; no
  environment changes needed. The experiment runners need no extra packages.
- Source-selection finding: L#IGCS6 CHAIN-final EXTERN continuations are split by
  the current parser. Those candidates were excluded; the selected sewers,
  beholder and Moon Sisters graphs were checked through EXIT against their D files.
  No parser behavior changed. See `experiments/real_set_source/20261029/README.md`.
- [Review index](experiments/REVIEW_2026-10-29.md). User review pending; no commit.

## Fixes and two experiments prepared — 2026-10-29 (historical preparation)


The user agreed thinking adds little value for translation. Work done on a
machine without Ollama. Everything below is tested offline (57 unit tests), and no
model has been run.

Production (`translate_dialogs.py`):
- A line whose original female text is explicitly empty is no longer sent to the
  female pass; it is exported empty. Every model had failed these lines by copying
  the male translation.
- A string shared by speakers of different genders, or of unknown gender, gets a
  `note` asking for neutral wording, and is listed after export in
  `<name>.shared_strings_review.txt` for a person to check.

Evaluation:
- [Evaluation v3](experiments/EVALUATION.md#evaluation-v3-2026-10-29): checks now
  catch the errors found in manual reviews and accept the valid wording they rejected.
  Old totals are not comparable. **On the experiment machine, run `rescore.py` on
  the three 2026-10-28 result folders and commit the `rescored.csv` files.**
- [Real-mod set](experiments/real_set/README.md) scaffolding plus
  `make_real_fixture.py`. **Empty: the user needs to add and review real dialogues.**

Experiments prepared, **not run**:
- [Prompt A/B](experiments/PROMPT_AB_PLAN.md) (`run_prompt_ab.py`): female-pass noun
  rule vs production prompt, Mistral by default. Production prompt unchanged until
  measured.
- [Translate + verify](experiments/TRANSLATE_VERIFY_PLAN.md) (`run_translate_verify.py`):
  Mistral Small3.2 translates without thinking; Gemma4 verifies with thinking (both
  configurable), plus a planted-error test of the verifier.

**The actual results of both experiments (translations, verifier issues, reports,
manual review) must be committed to the repo**, under `experiments/prompt_ab/` and
`experiments/translate_verify/`, not left in the ignored `results/` folder. The raw
outputs of earlier experiments exist only on the machine that ran them, so they
could not be reviewed from another checkout.

Test environment note: the tests need `chardet` and `antlr4-python3-runtime==4.9.2`
(the generated parser requires exactly 4.9.2). On Windows, run them with
`PYTHONUTF8=1`.

## Native-context thinking comparison completed — 2026-10-28

The user requested Qwen3.5 thinking at native context, then the same suite for
all other already downloaded thinking models. All five scheduled suites finished.
No batch process remains active. See the [full comparison](experiments/THINKING_NATIVE_RESULTS_2026-10-28.md),
its JSON companion, the [pre-run plan](experiments/THINKING_NATIVE_PLAN_2026-10-28.md)
and the [Qwen3.5 three-way report](experiments/QWEN35_THINKING_NATIVE_2026-10-28.md).

- Qwen3.5 9B: 587/660, 12/15 complete pairs, 4358.28 request seconds.
- Gemma4 12B: 592/660, 12/15 pairs, 1027.74 seconds.
- Qwen3 14B: 534/660, 12/15 pairs, 1002.91 seconds.
- Huihui Qwen3.5 abliterated 9B: 460/660, 8/15 pairs, 10629.27 seconds.
- Huihui Qwen3 abliterated 14B: 0/660 due to malformed JSON/channel contamination;
  all 15 male replies reject and all female passes skip. This is a protocol
  failure in the installed serving configuration, not zero linguistic ability.

Same five datasets, production prompt, full dialogue graphs, model-default
sampling, three repeats, thinking enabled and `num_predict=-1`. Native contexts:
262144 for Qwen3.5/Gemma4/Huihui Qwen3.5; 40960 for Qwen3/Huihui Qwen3. All 25
observed placements were 100% GPU. No downloads, imposed timeouts, token caps,
retries, splitting, repairs, production changes or automatic promotion.

There are 150 records, 133 actual calls and 17 skipped female passes. Frozen
runtime/input hashes and identical male prompts/schema across all five models
were verified. Standard-model digests match their non-thinking baselines. All
returned translation texts, including rejected answer portions, were manually
read. Missing/skipped female translations cannot be assessed. No new unit tests
were needed for this inference-only run; production and evaluator code unchanged.

Qwen3.5's native run avoids all length failures, unlike the old 8192 thinking run.
Huihui Qwen3.5 addressees repeat 1 female exhausts even 262144 after 6438.77 s:
870 prompt + 261274 generated; empty content; two reasoning lines repeated over
6500 times each. Raw reasoning and serving logs are preserved. The optional user
choice to stop that model was unanswered, so the authorized suite finished
without intervention. No stop decision remains pending for this completed batch.

Gender and meaning errors persist: Gemma4 retains masculine address nouns;
Qwen3.5 female passes sometimes change narrated him to her. All four models that
reach female source-variant requests fill the deliberately empty source and
reject. Shared mixed-gender readiness strings remain wrong; Qwen3 sometimes
passes the check by changing I to we. Frozen checks have documented blind spots.
No model is approved for unattended export. Improvements versus thinking off
also change context, so they do not isolate thinking. No native-context off
control or new compatibility repair is authorized.

Git-ignored raw roots:
`experiments/results/thinking-native-20261028-094842/` and
`experiments/results/thinking-native-remaining-20261028-214626/`. Both retain final
comparison/metrics, manifests, exact settings, snapshots, driver copies, raw
requests/replies, summaries and manual reviews. Do not repeat completed suites
blindly. The temporary summarizer is archived in the remaining-model root.
The user explicitly requested committing all completed reports, plan and handoff
updates on 2026-10-29. Raw Git-ignored experiment artifacts remain local.

## Completed seven-model comparison — 2026-10-28

All seven models finished; no batch process remains active. Final results and
manual review: [comparison](experiments/NON_THINKING_RESULTS_2026-10-28.md).
In approved model order: Gemma3 570/660, T-lite 523/660, Aya 427/660,
Vikhr 490/660, Mistral 592/660, Gemma4 564/660, Qwen3 503/660.
None is approved for unattended export. Production settings remain unchanged.

T-lite’s initial metadata-only exclusion was wrong. Actual probes found no
reasoning; default non-streaming sometimes put translation JSON in the thinking
field. Its digest-pinned explicit-off suite completed all 30 requests. The final
manifest/report includes this backfill; prior attempts and main manifest are
archived. Aya finished before the backfill; the order exception is documented.
See [runtime evidence](experiments/TLITE_RUNTIME_VALIDATION_2026-10-28.md).

Raw root: `experiments/results/non-thinking-20261028-013515/` (Git-ignored).
Portable metrics, exact model digests and frozen hashes are in the comparison’s
JSON companion. All outputs/repeats were manually read. Frozen inputs, settings,
and identical male prompts were verified; no scored response contains thinking.
All 45 tests passed after the final runner change. No further commit was requested.

Potential next work needs agreement: improve evaluation blind spots and shared/
empty-string handling, then compare shortlisted drafts on independent real
examples. No new thinking phase or production model change is authorized.

## Historical decisions (superseded where completion above says otherwise)

## Ordered non-thinking batch authorized — 2026-10-27

The user approved the seven-model order proposed after the thinking baseline:
Gemma3 12B, T-lite 2.1, Aya Expanse 8B, Vikhr-Nemo 12B, Mistral Small3.2 24B,
Gemma4 12B thinking off, Qwen3 14B thinking off. They explicitly requested
**document everything before proceeding**, then download one model, test it,
advance to the next. The pre-run plan is
[experiments/NON_THINKING_PLAN_2026-10-27.md](experiments/NON_THINKING_PLAN_2026-10-27.md).
Five tags are from the Ollama library; T-lite and Vikhr weights come from Hugging
Face through Ollama's `hf.co` support. All inference stays in Ollama. Models are
retained, no automatic deletion. This step does not authorize commits.

The dedicated `experiments/run_non_thinking.py` reuses the pull client and frozen
evaluator, implements per-model sequencing across all five dialogues, saves
incremental manifest/report/CSV and snapshots, and checks thinking is off. It was
documented and tested before the first download. Default settings match the
previous non-thinking comparison: production/full/default sampling/3 repeats/8192
context, no inference cap/timeout/retry. Exact tags and failure handling are in the
plan. See the eventual linked report for actual outcomes; no production model is
changed automatically based on scores.

## Uncapped thinking baseline completed — 2026-10-27

The user explicitly requested thinking on with no added limit, to establish a
baseline. Qwen3.5 ran the same five datasets, production prompt, default sampling,
full dialogues, 3 repeats and the prior 8192 context. Actual options were
`num_ctx=8192`, `num_predict=-1`, `think=true`; no thinking budget, brief-reasoning
instruction, timeout or retry. Runtime code/inputs/checks match the earlier
thinking-off snapshot. No production code or settings were changed.

Result: 19 actual requests, 14 empty answers at `done_reason=length`, 11 female
passes skipped after male failure. Only 1/15 complete pairs, 65/660 checks
(9.85%), versus thinking off 11/15 pairs and 523/660 (79.24%). Request wall time
2232 seconds (37m 12s), versus 91.43 seconds off; 131,929 generated tokens.
Every length failure has prompt + generated tokens exactly 8192. The few returned
translations were good but are a selected subset; the context exhaustion prevents
an assessment of most intended outputs. This is not evidence against thinking
at all context sizes. Larger/native context and budgeted thinking remain separate,
unperformed experiments and require an explicit decision.

Details, manual review and reproduction:
[experiments/THINKING_BASELINE_2026-10-27.md](experiments/THINKING_BASELINE_2026-10-27.md).
Local ignored artifacts: `experiments/results/thinking-on-20261027-223158/`,
including raw thinking/replies, manifests, hashes, input/code snapshots, metrics,
per-request CSV, driver and analysis script. Changes remain uncommitted.

## Installed-model comparison completed — 2026-10-27

The user next requested the comparison of `qwen3.5:9b` and `qwen2.5:14b`. Both
were run on InkGallery v2 and all four synthetic fixtures: production prompt,
full dialogues, default sampling, 3 repeats, context 8192, thinking off for
Qwen3.5 and default for non-thinking Qwen2.5. Sixty actual requests; no retries,
model downloads, production model change or new commit. Checks were frozen.

Qwen2.5: 541/660 checks (81.97%), 3/30 structurally rejected replies.
Qwen3.5: 523/660 (79.24%), 4/30 rejected. Qwen2.5 copies unchanged female-pass
wording more consistently but remains unreliable; both fail the shared-gender
string and all three explicit-empty female cases. All valid outputs and seven
rejected replies were read. Full results, examples, evaluation blind spots and
reproducibility notes are in
[experiments/MODEL_COMPARISON_2026-10-27.md](experiments/MODEL_COMPARISON_2026-10-27.md).
Raw local logs, code/input snapshots, SHA-256 values, model metadata and commands:
`experiments/results/comparison-20261027-221323/` (Git-ignored).

The proposed Qwen3.5 thinking-on experiment was subsequently completed with the
same frozen suite/settings; see the latest section above. Do not silently change regexes or salvage rejected lines when
comparing to these scores. Genuine unseen mod text and independent Russian review
remain desirable before deployment.

## Latest evaluation work — 2026-10-27

The user approved improving the checks and adding unseen fixtures, with full
documentation. See [experiments/EVALUATION.md](experiments/EVALUATION.md) for the
implementation, limits, validation and next steps. The original pilot is preserved
in [experiments/PILOT_2026-10-27.md](experiments/PILOT_2026-10-27.md): 53 actual
requests, production/default 127/138 on the original checks, with serious errors
outside the checks. The raw local pilot logs remain in the ignored results folder.

InkGallery v2 now scores all 12 lines, flags leftover Latin text and incorrect
names/locations, and accepts more idiom variants. Separate male/female wording
flags appear in `pair_reviews.csv`; they do not rewrite text or affect winner
selection. Four synthetic fixtures (22 rows, 20 TRA strings) cover multiple NPCs,
ambiguous listeners, reuse and original female source variants. They are new to
the pilot, not independently curated or human-approved gold data. At fixture creation no live LLM
fixture translation or model comparison had been run; the subsequent comparison
is recorded above.

The harness now honors female source variants for all experimental prompts and
uses the same shared-string merge helper as production. Production's existing
merge block was extracted to `translation_common.merge_dialogue_rows`; production
instructions/settings are unchanged. References are only for tests/manual review,
never included in model requests. Use fresh result folders: old scores are not
comparable to v2. Test validation: 39 tests pass, including all-fixture/all-prompt/
both-scope reference-reply round trips without Ollama. Current evaluation changes
have not been committed; the user's earlier commit instruction applied to the
review fixes already committed as `f01ac30`.

## User instructions that remain in force

- **Do not commit** unless explicitly instructed. Commit `f01ac30` was explicitly requested and contains the review fixes.
- Agree on **any new approach or mechanism** with the user before implementing it.
  No silent limits, retries, partitioning, fallbacks, model changes or extra QA passes.
- Keep changes minimal. Preserve existing function flow; avoid cosmetic moves or
  refactoring unrelated to a demonstrated defect. Review against the relevant git
  baseline, not just an intermediate assistant version.
- Use complete dialogue graphs in requests. No automatic batching or splitting.
- Use the model's native context to make use of available GPU memory, rather than
  an arbitrary smaller context. No fixed generation cap (`num_predict=-1`) or
  client time cap. Explicit user overrides are distinct from imposed defaults.
- The LLM must handle complete Russian gender agreement: nouns, adjectives, verbs,
  pronouns and related wording. **The user rejected mechanical word replacement.**
  Do not implement or re-propose a noun/span patch workflow unless the user
  explicitly reopens that idea. The agreed female pass edits full lines with the LLM.
- Give brief progress reports during long-running work. Explain genuine test
  failures instead of silently restarting or changing the experiment.

## Current implementation

`translate_dialogs.py` keeps the original male-first, female-edit sequence:

1. Send the entire source dialogue for male Player1, with actor data and the
   relevant glossary. The model infers addressees from speakers and the graph.
2. Supply original English plus validated male Russian lines to a female-only edit
   request. NPC genders remain fixed. Require complete lines and exact copying of
   unaffected wording.
3. Each model response is JSON: `{"translations":{"1":"Russian text", ...}}`.
   Short request IDs map back to original metadata. Python writes the final CSV
   with original English/metadata plus `Russian_Male,Russian_Female`.
4. Both responses must validate before export. Existing ID/token/format checks are
   structural checks, not a proof of gender agreement, meaning or completeness.

Agreed fixes (2026-10-27): a TRA string reused by several rows of one CSV is sent once
and its translation copied to every row (previously copies could differ and the TRA
export failed); rejected replies are kept as `<name>.<male|female>.rejected.txt`;
capitalised glossary entries match case-sensitively and match English plurals.

Native context is read through `/api/show`. Thinking and sampling use model
settings by default; optional `--think` / `--no-think` and `--num-ctx` are explicit
user choices. No automatic retry, splitting, timeout, checkpoint/resume or repair
mechanism remains in the translator.

The `Addressee` field was removed by user decision: the parser cannot fill it
reliably, and explicit addressees did not prevent the @18 error. The prompt no
longer marks addressees "unknown" or forbids inferring them; the model infers them
from speakers and predecessors, and prefers gender-neutral wording when unclear.
Archived examples predate this change and still include addressee facts.

The shared `tra_format.py` and `translation_common.py` contain necessary literal
parsing, validation and atomic CSV writing. They are required runtime files.
TRA fixes preserve original female literals, both sounds, comments and literal
surroundings, reject conflicts, handle filename case, and avoid overwriting source
with failed/empty translations. See README for remaining parser boundaries.

Last automated verification (2026-10-27, Windows machine, after the review
fixes): 27 tests ran and 25 pass. The 2 grammar subprocess tests fail only because `chardet` is not
installed there. Re-run when code changes justify it:

```bash
python3 -m unittest discover -s tra_files_llm_translating/tests -v
```

## Live tests already performed

Do not repeat them blindly. Exact inputs, actor facts, prompts, raw replies,
Python-written CSVs, metrics and annotated Russian-first reviews are archived.

### Qwen3.5 9B — production JSON two-pass client

[Review](examples/inkgallery-json-two-pass/RUSSIAN_REVIEW.md)

- Same 12 InkGallery lines, explicit speaker/addressee facts, existing glossary.
- Native context 262144, approximately 14 GB, 100% GPU; no fixed output cap or split.
- Male 156.02 s / 9085 tokens; female 175.82 s / 10405 tokens.
- All structural checks passed. Earlier female @16 sentence omission did not recur;
  Cormyr became Кормира and seen stayed видел/видела.
- Still wrong: male @18 addressed female Velcealle with masculine verbs despite
  correct input metadata; female @16 retained путник; @48 produced как я делаю.
- Six identical strings and six variants are not equivalent to six correct shared
  translations. This output is **not approved**.

### Installed Qwen2.5 14B — same production test

[Side-by-side review](examples/inkgallery-qwen25-json-two-pass/RUSSIAN_REVIEW.md)

- User explicitly requested this comparison. Installed tag `qwen2.5:14b`, digest
  prefix `7cdf5a0187d5`.
- Same system prompt, English, roles, graph and glossary. Female input naturally
  contains this model's own male translation.
- This installed model reports native context **32768**; it was not a new imposed
  budget. Approximately 15 GB, 100% GPU; no fixed output cap, retry or splitting.
- Male 21.58 s / 374 tokens; female 10.86 s / 375 tokens. About 32 seconds total.
- Both @16 sentences preserved; путешественник/путешественница, понял/поняла,
  хотел/хотела and the idiom как у меня дела were handled better in this sample.
- Major remaining problem: systematic **вы/вас** for a singular addressee, contrary
  to the explicit **ты** instruction. Plural/formal agreement hides gender, so
  identical lines do not prove it understood Velcealle's or Player1's gender.
- Колпаковые Маги for Cowled Wizards needs terminology review.
- Eight identical lines/four variants. Output is **not approved**; the production
  default model remains `qwen3.5:9b`. Do not silently switch it based on this test.

Latest discussion: Qwen2.5 finished faster mainly because it generated **749**
tokens versus Qwen3.5's **19,490 including reasoning**. Measured decode rates were
about **44 vs 60 tokens/s**, respectively: Qwen2.5 was not decoding faster; it did
far less generation. Model defaults and native context differ, so this is not an
isolated architecture, parameter-count or decoding-speed benchmark.

### Earlier experiments

[Direct-CSV two-pass review](examples/inkgallery-two-pass/RUSSIAN_REVIEW.md)

The English input was valid. The model's male CSV had **five wrong-width rows**
because Russian commas were unquoted. That raw answer was passed to the female
editor, an avoidable test flaw. Female CSV was structurally valid but omitted the
second sentence of @16. Thus neither valid CSV nor valid JSON proves completeness.
The current JSON workflow eliminates that transport flaw; do not describe the
original English input as malformed.

One-request mandatory male/female JSON and shared-or-variants JSON were tried.
Tiny three-line tests succeeded; larger tests misgendered NPCs or labelled
masculine-only text as shared. They are rejected as the default. Do not infer
large-dialogue reliability from the tiny success.

The 34-line L#IGSTA questions/menu trial was stopped after 12 completed lines
because gender quality failed. **There is no completed or approved 34-line result.**
Fixed token caps, 12-row batching, retry feedback and splitting caused wasted
reasoning and were not approved; they were removed. See README for exact history.

Glossary case fix (2026-10-27, after review): every English entry in `dict.csv` is
capitalised, so an entry is treated as a proper noun (case-sensitive) only when its
Russian side is capitalised too. The 292 common nouns (Archmage → архимаг...) match in
any case again.

## 2026-10-27 code review findings — fixed with user approval

1. A reused TRA string with different speakers lists every speaker and gender in the
   prompt, plus a note that one translation must agree with all of them.
2. A string shared by two dialogue CSVs takes the translation already exported in
   the target folder (first file by name; the console names it). An old export
   therefore decides the wording: remove it to re-translate.
3. Glossary plurals are generated per entry (-s/-es/-ies, -f/-fe → -ves, -man → -men
   or -mans). `Rob` no longer matches "Robes".
4. Old `*.rejected.txt` files are removed when a file is processed again. A failure
   to write one no longer hides the validation error.
5. Cleanup: simpler merge bookkeeping; glossary text and actor list come from the
   merged rows already in memory. The user declined the regex speed change, because
   LLM time dominates.

## Remaining work — needs agreement, not automatic action

- **Agreed next step:** run the diagnostic grid in
  [experiments/README.md](experiments/README.md) (`diagnose_translation.py`) on the GPU
  machine to separate model ability, prompt framing, request size, thinking and
  sampling noise. It scores outputs against `experiments/inkgallery_checks.json`.
  Production code is unchanged by it. Change production only after reading its results.
  One command does everything: `python3 experiments/run_all.py` pulls the candidate
  models, runs the staged grid and writes `REPORT.md`. **Not run yet** (this machine
  has no GPU/Ollama); it was only checked against a mock Ollama server.
- Prompt variants agreed for that grid (2026-10-27): `examples` (six worked
  male/female examples) and `markup` (one request; the model writes each line once
  with `{masculine|feminine}` for Player1-dependent words and Python picks a side).
  The user approved `markup` as an **experiment only**. It is not the rejected
  mechanical replacement, because the model writes every word. It must not go into
  production without the user agreeing after seeing the results.
- Idea #3, liked by the user but **not implemented**: a separate read-back check
  where the model reports per line who "я"/"ты" are and their gender, and offers a
  corrected line only on a mismatch. The correction would go to a review column, not
  replace the translation automatically. Decide after the grid shows how often
  gender is still wrong.

- User may choose to test stricter singular-address instructions with Qwen2.5,
  discuss another model, or review/edit the drafts. No such next change is agreed.
- Do not claim omissions, semantic drift or gender are solved. Prompt improvements
  and structural checks help but do not establish reliable automatic translation.
- Agree on canonical terminology before changing the glossary. Cormyr already has
  Кормир in `dict.csv`; Cowled Wizards lacks an exact entry there.
- No additional linguistic reviewer model, sentence/length heuristics, parser-side
  addressee inference, guardrails or new experiment without agreement.

## Workspace and persistence

Original mod `/home/paladin/source/InkGallery-v1.5/` was not modified. Production
code/prompts were not changed during the latest model comparisons.

At handoff, `git status --short` lists README, this handoff, examples, tests,
`tra_format.py` and `translation_common.py` as **untracked**. Preserve these files:
some are required by the tracked scripts. A session restart keeps disk files, but
untracked files are not protected by git history. Do not commit or discard them
without instructions.

As of 2026-10-27 the new `experiments/` folder is untracked, and README, this handoff,
the tests and `translate_dialogs.py` have uncommitted changes. Nothing was committed.

Only extended transient traces/test runners live in `/tmp/translate-tra-inkgallery/`.
The important examples, exact requests/replies and metrics are already copied into
this repository; continuing should not depend solely on `/tmp`.

## Serving observation — 2026-10-30 morning

A/B has completed beholder and Moon Sisters. Sewers production repeat 1 male is
saved (2439.48 s / 497 tokens); its female pass has been pending since 02:18 UTC.
Host service logs show the last backend progress at 02:18:49 UTC saving prompt
cache (1831 tokens, 286.116 MiB), then no generation progress for seven hours.
This appears to be a serving/cache stall rather than active long generation.
Evidence: `prompt_ab/20261029-220151-recovered/SERVING_LOG_2026-10-30.txt`.
A new user choice is pending: restart serving backend and count current pass as
serving failure, or keep waiting. Native context and uncapped generation remain
unchanged either way. **Do not restart without the reply.** All three prior choices
still stand: no caps, whole-line verifier corrections, no commits before review.
Partial sewer male review sheet is under `experiments/review/20261029/`.

## Status after serving restart — 2026-10-30

The user approved restarting serving while preserving native context and uncapped
generation, recording the current pass as serving failure. Before the guarded
recovery script acted, the service restarted and the A/B request state changed,
so the script safely performed no restart. Old sewer female pass ended with
Remote end closed connection (27271.85 s); five subsequent male connections were
refused and females skipped. Preserve those outage records, do not score them as
linguistic ability. The original A/B manifest is finished with infrastructure errors.

Verifier queue is now RUNNING at `tra_files_llm_translating/experiments/translate_verify/20261030-095325`; session 94364,
queue/client PID 64134. It has four translation replies on InkGallery at
this update, no completed verifier/planted records. Native contexts, num_predict=-1.
Do not launch a duplicate verifier. Read current state before any recovery.

A one-off continuation is queued after verification: session 99354, PID
78159, state in `experiments/AB_TRANSPORT_CONTINUATION_QUEUE_2026-10-30.json`.
It issues only production repeats 2/3 and nouns repeats 1/2/3 for Sewers, whose
connections never reached Ollama; it excludes production repeat 1 entirely,
retaining the saved male and the serving-failed female as the user instructed.
No model response is retried. Inputs/options checked against frozen records.
The regular runners gain no automatic retry/resume behavior.

Completed review sheets: REFERENCE_REVIEW.csv, AB_BEHOLDER_REVIEW.csv,
AB_MOON_SISTERS_REVIEW.csv, and partial AB_SEWERS_R1_MALE_REVIEW.csv under
`experiments/review/20261029/`. Human review remains pending. No commits.
