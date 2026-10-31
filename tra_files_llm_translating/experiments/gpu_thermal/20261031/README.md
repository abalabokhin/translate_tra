# GPU thermal investigation: resume after reboot

## Current status and decisions — end of session, 2026-10-31

This section supersedes the reboot instructions and historical next-step proposals
below. User requested documenting the investigation and committing necessary
artifacts. No production configuration was changed; no translation queue resumed.

User wants to reuse previously successful settings and prefers running Mistral
entirely on the GPU. The observed fully GPU-resident configuration is **4096
context, 41/41 layers, 640 MiB KV cache**. Its short interactive request completed.
This is a proposed diagnostic configuration for real dialogue, not an approved
production context change or proof of thermal stability. Native 131072 context
is still the recorded translation-experiment protocol; generation remains uncapped.
Synthetic parameter sweeps are stopped. Do not automatically restart old scripts.

| Run / configuration | Result | Peak junction | Peak sampled power |
| --- | --- | --- | --- |
| 061959 Mistral 131K, automatic fans, kernel -10 | Temperature cutoff | 97°C | 271 W |
| 062307 Mistral 131K, manual 60%, kernel -10 | Temperature cutoff | 95°C | 277 W |
| 063900 Mistral 131K, manual 60%, kernel -9 | Temperature cutoff | 95°C | 281 W |
| 0656 interactive Mistral 4K, default fans, kernel -9 | Completed 541 input / 212 output tokens | Unknown during request | Unknown during request |
| 070502 Mistral 4K, batch 512, manual 60% | Temperature cutoff | 99°C | 280 W |
| 080849 Gemma4 12B 4K, batch 512, manual 60% | Temperature cutoff | 99°C | 283 W |
| 081044 Gemma4 12B 4K, batch 64, manual 60% | Model initialization failed; no inference | 48°C | 69 W |
| 081243 Qwen2.5 14B 4K, batch 64, manual 60% | Completed 1166 input / 78 output tokens | 87°C | 261 W |
| 081527 exact archived successful Mistral request, 131K | GPU copy fault during weight upload | 44°C | 44 W |

All numeric peaks are sampled telemetry, not guaranteed instantaneous peaks.
Kernel suffixes -9/-10 denote 7.3.0-9-generic / 7.3.0-10-generic.
The last six controlled runs used kernel -9. Manual mode was verified restored
to automatic after completed runs; no model remained loaded at last inspection.

Established conclusions:

- Kernel rollback did not prevent the spike.
- Full GPU residency / smaller context did not prevent it for the synthetic prompt.
- It is not exclusive to Mistral: Gemma4 reproduced it.
- Qwen batch 64 completed, but both model and batch differ from the failing tests;
  no conclusion isolates batch size as a remedy.
- Gemma batch 64 failed its multimodal initialization even for text input. Curl
  exit 0 did not mean successful inference: inspect response JSON / HTTP status.
- The exact prior successful Mistral request was already replayed. Its JSON was
  identical, and backend build, effective batch and offload layout matched old
  logs. It now failed at low temperature in hipMemcpyAsync / SDMA0 during load.
  This does not establish why the earlier thermal spikes occurred.
- No cooling failure, damaged VRAM, sensor fault, or specific backend defect is
  proven. The related upstream mmap-copy report is a lead, not a diagnosis.

Pending: separate model-load stability from generation; if returning to a real
translation test, the discussed next comparison is the archived real dialogue at
4K with temperature monitoring. **That real-dialogue 4K comparison has not run.**
The no-mmap / SDMA-disabled load-only investigation was discussed but neither
prepared as an executable test nor run; no service overrides were installed.
See [ROCm investigation](ROCM_INVESTIGATION.md) for evidence and unresolved questions.

Scripts here are historical diagnostics, including prepared variants that never
ran. Their 256-token synthetic output cap and 120-second external limit are
separate from the uncapped translation experiment. The exact replay preserves
uncapped request generation but retains the external diagnostic limit. No script
here adds retry/resume to production. Outputs go beside the executed script.


Recorded 2026-10-31, approximately 06:25 EDT. User will reboot and select
**7.3.0-9-generic** in GRUB → Advanced options for Ubuntu. Both that kernel and
7.3.0-10-generic are installed under /boot. Verify with `uname -r` after reboot;
do not assume the selection succeeded.

## Established evidence

- GPU: AMD Radeon RX 6900 XT, PCI 0000:0c:00.0, 16 GiB VRAM.
- Oct 30 at **18:32:53 EDT** and **22:26:15 EDT**, amdgpu logged:
  `ERROR: GPU over temperature range(SW CTF) detected!` and
  `ERROR: System is going to shutdown due to GPU SW CTF!`.
  Linux then performed orderly poweroff. Both events happened 3–5 seconds after
  Mistral Small 3.2 began its first request.
- Both failed boots ran kernel 7.3.0-10-generic. The preceding Oct 28–30 boot
  ran 7.3.0-9-generic. Apt installed the newer kernel Oct 29 at 17:45 EDT.
  This correlation makes a regression worth testing; it does not establish one.
- Default GPU power cap is 281 W; exposed supported range is 252–281 W.
  Automatic fan mode is pwm1_enable=2. No power/clock tuning was changed.
- User confirmed fans rotate in a manual 60% test. During the automatic-mode
  Mistral test, user saw no rotation despite low reported RPM. During the manual
  Mistral test, user confirmed visible rotation.

## Monitored comparisons, both on 7.3.0-10-generic

| Run | Fan control | Peak edge | Peak junction | Peak memory | Peak power | Fan observation |
| --- | --- | --- | --- | --- | --- | --- |
| gpu-thermal-20261031-061959 | automatic | 75°C | 97°C | 46°C | 271 W | 318 RPM at cutoff; 431 RPM maximum, user saw no rotation |
| gpu-thermal-20261031-062307 | manual 60% | 73°C | 95°C | 44°C | 277 W | ~2090 RPM under load; user saw rotation |

In the automatic run junction rose from ~49°C to 97°C in ~1.5 seconds as load
started. Manual fans did not prevent a similarly rapid rise to the 95°C cutoff.
This disproves the earlier tentative explanation that fan startup delay alone
accounts for the problem. Cooling/contact issues and driver/firmware issues
remain hypotheses. No diagnosis of failed paste, heatsink, or sensor is proven.

Both tests cancelled the request and unloaded Mistral before system shutdown.
After the manual run junction fell to ~39°C, and fan mode was verified restored
to automatic (2). These runs measured our early cutoff, not the hardware's exact
shutdown temperature. Exposed critical limits: edge/memory 100°C, junction 110°C;
emergency limits: edge/memory 105°C, junction 115°C.

## Artifacts

Both run directories beside this README contain temperatures.csv, events.log,
kernel.log, request.json, metadata.json, and response.jsonl. The automatic run
also has summary.json. Originals remain in repository-root results/ with the
same directory names. Copies here preserve experiment evidence outside results/.

`gpu_thermal_test.py` beside this README is a copy of the executable diagnostic
at repository-root `results/gpu_thermal_test.py`. Its output goes alongside the
script being executed, under a timestamped gpu-thermal-* directory.

Request: mistral-small3.2:24b, num_ctx=131072, num_batch=512, num_predict=256,
one synthetic repeated English-to-Russian translation prompt, streaming,
keep_alive=0. The prompt and generation cap differ from the original translation
queue; native context and batch match the reproduction. No full queue resumed.

## Next steps after reboot

1. Read this note, verify `uname -r`, inspect current temperatures and Ollama
   loaded models/processes. Confirm no other inference job competes with the test.
2. Repeat the **manual 60% fan** comparison on kernel 7.3.0-9-generic, retaining
   the same request and cutoffs. User can run from repository root:

   ```bash
   sudo python3 -u results/gpu_thermal_test.py --manual-fans
   ```

   If originals are unavailable, use the script beside this README instead.
   Sudo from the agent failed because interactive authentication was required;
   the user successfully ran the command in their own terminal.
3. Inspect saved CSV and events, compare temperature rise, power and RPM with
   the two runs above. Check response content as well as curl's exit status to
   distinguish a successful completion from an HTTP error.
4. If the spike persists on the earlier kernel, investigate cooling/contact
   and/or a lower-power controlled comparison before returning to long runs.
   Do not assume kernel rollback fixes it or declare the fans the sole cause.

Logger: 0.25-second sampling, flush+fsync each CSV sample and event; also captures
kernel messages. Ten-second baseline before inference, 120-second request limit,
15-second cooldown. Cancels at edge>=85°C, junction>=95°C or memory>=85°C, or
sensor failure; manual mode additionally aborts if reported fans are below 800 RPM
after eight seconds. Cancellation closes curl and requests Ollama model unload;
it is not a hardware interlock, and fast spikes can exceed the threshold between
samples. Never deliberately raise shutdown limits. Manual mode restores previous
fan control in finally on normal completion/interrupt; hard power loss cannot
execute cleanup. No need to repeat the uncontrolled automatic-fan test first.

## Translation work preservation

The active task shifted to diagnosing shutdowns. Existing translation outputs
and uncommitted changes were left untouched. See ../../../SESSION_HANDOFF.md
for the older queue history; statements that it is running are historical.
Check continuation artifacts and live processes before restarting anything.

## Earlier-kernel comparison completed — 2026-10-31 06:39 EDT

Run `gpu-thermal-20261031-063900` verified kernel **7.3.0-9-generic**,
with the exact same request JSON as the previous manual-fan test.
Manual 60% fans held approximately 2082–2115 RPM under load. Peaks:
edge **75°C**, junction **95°C**, memory **42°C**, power **281 W**.
At 06:39:35 the temperature cutoff cancelled inference; cooldown finished at
06:39:50 without a system shutdown. Junction reached 95°C about 3.1 seconds
after the first sample above 100 W (54°C junction at that first sample).
Response contains only the unload acknowledgment, no completed translation.
No GPU thermal shutdown message appears in this run's captured kernel log.
After completion fan mode was verified **2 (automatic)** and Ollama reported
no loaded models. All raw artifacts are copied beside this note.

The rollback did **not** resolve the rapid temperature rise: the same 95°C
cutoff occurred on both kernels with manual fans. This does not isolate the
physical or software cause, but a problem exclusive to 7.3.0-10 is not supported
by this comparison. Keep the long translation queue stopped. Further controlled
power/cooling investigation requires a separate next step; no tuning changed.

## Default-context Mistral succeeded — 2026-10-31 06:56 EDT

User ran Mistral interactively with default parameters and reported it working.
Service logs confirm the same Mistral model completed a 541-token prompt and
212-token response in 8.04 s. Effective context was 4096; all 41/41 layers
were on GPU; KV cache was 640 MiB. Effective batch and microbatch were both
512, the same as the thermal reproduction. Explicit batch 512 did not increase
it relative to this default run. The 131072-context reproduction instead
 offloaded 16/41 layers and allocated 20 GiB total KV cache, including 7.5 GiB
on GPU. Prompt length also differs (1645 vs 541 tokens); these observations
do not isolate context as the cause. A post-request reading was 50°C edge /
53°C junction / 50°C memory; no continuous telemetry was taken during the
interactive request, so its peak is unknown. Service evidence saved in
`mistral-default-20261031-0656/ollama.log`. No inference launched by the agent
and no settings changed.

## Controlled 4K-context reproduction also hit cutoff — 2026-10-31 07:05 EDT

Run `gpu-thermal-20261031-070502` used the same request JSON as the 131K
reproduction except `num_ctx=4096` (JSON equality checked after normalizing
that one field). Same kernel 7.3.0-9, manual 60% fans and batch 512.
The existing 4K Mistral runner was reused; service logs confirm a 1645-token
prompt at n_ctx_slot=4096. Previous startup logs established 41/41 GPU layers
and 640 MiB KV cache for this runner. This was not a cold-load comparison.

Junction rose from 50°C to 89°C to 99°C in two successive ~0.25-second
samples. At cutoff: edge 81°C, junction 99°C, memory 52°C, power 280 W,
fans 2086 RPM. Peak memory across cooldown was 54°C. Request was cancelled
~0.76 s after launch; no translation completed. Kernel capture is empty;
no shutdown occurred. Fan mode verified restored to 2; API shows no loaded
models. Post-test junction was 46°C when inspected.

**Large context / partial CPU offloading is not required to reproduce the
spike.** Earlier successful 4K interactive request had only 541 prompt tokens;
this failed request had 1645. Prompt processing duration, cache reuse and
starting temperature remain differences, so prompt length is not yet isolated
as the cause. No hardware fault proven. No further inference or tuning launched.
Artifacts and 4K script archived beside this note.

## Gemma4 also reproduces spike — 2026-10-31 08:09 EDT

Run `gpu-thermal-20261031-080849`: gemma4:12b, 4096 context, batch/microbatch
512, same synthetic text and manual 60% fan control. Backend reports 1178
prompt tokens. At 08:09:03 cutoff: edge 80°C, junction 99°C, memory 46°C,
power 283 W, fans 2120 RPM. No completed answer; response is unload only.
Cutoff was 3.54 s after request launch including model startup. Cooldown ended
08:09:18 at 39°C edge / 43°C junction / 42°C memory. Automatic fan mode 2
and no loaded models were verified after completion. Kernel capture contains
an amdgpu workqueue CPU-duration warning, no thermal shutdown message.

The symptom is not exclusive to Mistral or its 24B size, and is reproducible
with a second architecture at 4K context. Cause remains unresolved; both models
share the GPU/backend stack. Recommend software audit and/or smaller-batch
comparison before another unchanged full-load model test. No further tests launched.

## Gemma batch-64 comparison invalid: model failed to load — 08:10 EDT

Run `gpu-thermal-20261031-081044` requested gemma4:12b at context 4096,
num_batch 64. Backend confirmed batch/microbatch 64, but its multimodal
component failed initialization: `image_max_pixels (147456) is less than
image_min_pixels (161280)`. Backend capped image_max_tokens to 64 because
of the microbatch setting. This occurred even for the text-only request.
No prompt processing or answer completed; API returned HTTP 500. The response
file concatenates an error JSON object and an unload JSON object without a
newline. Curl exited 0 because HTTP error status was not configured to fail;
`REQUEST EXIT 0` therefore does **not** establish a successful inference.
The Gemma4Assistant context warning also appears, but the explicit fatal
multimodal-load error above is the relevant startup failure in service logs.

Peak junction 48°C, edge 43°C, memory 44°C, sampled power 69 W. These low
values are **not evidence that batch 64 solves overheating**, because inference
never ran. Automatic fans restored (mode 2), no model loaded; post-test junction
40°C. Preserve this as a backend configuration failure, not a thermal success.
A text-only model such as installed Qwen2.5 14B is a candidate for a subsequent
small-batch comparison, avoiding this multimodal startup constraint. No new
inference launched. Raw artifacts and service log archived beside this note.

## Qwen batch 64 succeeded; exact historical replay prepared — 08:13 EDT

Run gpu-thermal-20261031-081243 completed inference (done_reason=stop):
1166 prompt tokens, 78 output tokens, 12.01 s total including 8.01 s load.
Peaks: junction 87°C, edge 74°C, memory 54°C, power 261 W. Fans at 60%;
automatic mode restored and no models loaded afterward. This compares both
model and batch against Gemma/Mistral failures, so it does not isolate batch.

User requested returning to older successful settings instead of further
synthetic variations. Successful Mistral records already used num_ctx=131072,
num_predict=-1. Exact request from tra_files_llm_translating/experiments/prompt_ab/20261029-220151-recovered/inkgallery_beholder/runs.jsonl, JSONL line 1,
(saved successful run wall_seconds=119.48) copied to
archived-successful-mistral-request.json. Replay driver prepared as
results/gpu_thermal_replay_successful_mistral.py and archived here. It preserves
the request exactly, including format, messages, stream=false and original
options. Monitoring wrapper retains manual 60% fans, thermal cutoffs and its
external 120 s diagnostic limit; this is not a full experiment rerun. Driver
has not been launched. No additional synthetic tests queued.

## Exact historical Mistral request: ROCm memory fault — 08:15 EDT

Run gpu-thermal-20261031-081527 request JSON equals the archived successful
Beholder request exactly (checked as parsed JSON). It used mistral-small3.2:24b,
num_ctx=131072, num_predict=-1, original messages/schema and stream=false.
Backend offloaded 16/41 layers, then failed loading with `ROCm error: an illegal
memory access was encountered`; API HTTP 500 after 11.47 s. Kernel captured
amdgpu gfxhub page faults from llama-server PID 12346, SDMA0 client and
PERMISSION_FAULTS 0x3. No successful translation; response includes error and
unload acknowledgment. Curl exit 0 again reflects transport only.

Peak junction 44°C, edge 39°C, memory 40°C, sampled power 44 W. This is a
GPU memory/backend failure at low temperature, distinct from prior thermal
cutoffs. It does not establish the cause of those cutoffs or prove a hardware
fault. Afterward automatic fans mode 2 verified, model list empty, junction
40°C. Preserve complete service/kernel logs for backend investigation; no
further inference launched. Exact older successful settings alone did not
restore operation in this attempt.
