# ROCm investigation — 2026-10-31

## Result

The original successful Mistral parameters have already been reused exactly.
The last replay failed during model-weight upload, not prompt processing.
No root cause for either the upload fault or earlier thermal shutdowns is proven.
User prefers the original experimental protocol: stop synthetic parameter sweeps.
No more inference, service changes, driver installation, or GPU tuning performed.

## Successful vs failed startup comparison

| Item | Successful Oct 29 17:24 startup | Failed Oct 31 08:15 startup |
| --- | --- | --- |
| Model blob | 41a5b0c36a28a3a0480ce2e4007d3a21e3298be70e2b9a103960581412997dca | Same |
| Backend | ROCm /usr/local/lib/ollama/rocm_v7_2/libggml-hip.so | Same |
| Backend build | 9ff0d7e90, GNU 13.3.1 | Same |
| Context requested | 131072 | 131072 |
| Batch / microbatch launch flags | 512 / 512 | 512 / 512 |
| GPU layers selected | 16/41 | 16/41 |
| GPU weights | 5375.18 MiB | 5375.18 MiB |
| CPU mapped weights | 7924.61 MiB + 360 MiB | Same |
| Outcome | Initialized and generated successfully | hipMemcpyAsync failure during load |

The exact request for the failed replay equals the archived successful Beholder
request as parsed JSON (messages, format/schema, stream=false, options included).
Original options: num_ctx=131072, num_predict=-1; batch left to backend default.
Fan override and external thermal/time monitoring were diagnostic additions;
they did not modify request JSON. No evidence shows those additions caused the
upload fault. The original experiment has no imposed generation/client time cap;
the diagnostic wrapper had its separate 120 s limit, which was not reached.

## Upload fault

At 08:15:47 the backend failed in ggml_backend_cuda_buffer_set_tensor,
calling hipMemcpyAsync(..., hipMemcpyHostToDevice, stream 2), from
llama_model_loader::load_all_data. Backend reported illegal memory access.
Kernel identifies gfxhub / SDMA0 (0xd), PERMISSION_FAULTS=0x3, RW=0x0,
and fault addresses near 0x00007014b955d000. No successful context initialization
or generation followed. Junction peak 44°C; this instance was not a thermal
cutoff. Full service and kernel evidence is in gpu-thermal-20261031-081527/.

## Integrity and change audit

- Full SHA256 of the 13.34-GiB primary model blob matches its filename exactly:
  41a5b0c36a28a3a0480ce2e4007d3a21e3298be70e2b9a103960581412997dca.
- Both saved experiment manifests report Ollama 0.40.11.
- Successful and failed logs identify identical backend build 9ff0d7e90.
- libllama, libggml-hip, libamdhip64 and libhsa-runtime64 inode change times
  are Oct 25, before the successful runs. This supports no recent replacement;
  it is not a historical binary checksum comparison.
- Current dynamic-link resolution uses Ollama's bundled ROCm 7.2 libraries,
  not the separate ComfyUI ROCm 10 venv. Standalone ldd cannot find
  libggml-base without the launcher's library path; the crash stack confirms
  that library was loaded, so this is not evidence of a missing runtime library.
- Service config only adds OLLAMA_MODELS; no HSA_ENABLE_SDMA or LD_LIBRARY_PATH
  override found in the inspected system configuration files. Actual historic
  full process environments were not saved/compared.
- Apt history since the successful runs shows a kernel update Oct 29,
  old-kernel cleanup Oct 30, and Chrome updates. No ROCm/Ollama/firmware
  update was identified there. Current module is in-tree amdgpu from kernel
  7.3.0-9. Thermal spike reproduced on both -9 and -10.
- Historical kernel journal confirms explicit thermal shutdowns Oct 30 at
  18:32:53 and 22:26:15. The 08:15 upload fault is the only matching page-fault
  burst found since Oct 27 in retained logs. No claim of recurrent upload faults.
- Separate historical failure: Oct 30 05:53:15 system OOM killer killed
  llama-server PID 59919. This explains an earlier service interruption,
  independently of today's upload fault and thermal cutoffs.

## Matching upstream evidence (leads, not confirmed diagnosis)

ROCm issue 14258 reports an intermittent copy fault from read-only file-backed
mmap on Linux 7.3, reproduced independently of inference, with matching
SDMA0 permission-fault signature. It uses different GPUs (7900 XTX/7800 XT).
Source: https://github.com/ROCm/rocm-systems/issues/14258

ROCm issue 4817 documents a related KFD host-page mapping lifetime fault and
an upstream fix. A later report still reproduces a related symptom on 7.3.
Do not assume the old fix is missing here or install DKMS based on this alone.
Source: https://github.com/ROCm/rocm-systems/issues/4817

AMD documents HSA_ENABLE_SDMA=0 as disabling DMA copy engines. This is a
potential controlled copy-path diagnostic, not a verified fix and not a
thermal remedy. It needs to affect the server/backend process, not just curl.
Source: https://rocm.docs.amd.com/projects/ROCR-Runtime/en/docs-6.1.1/environment_variables.html

## Next targeted work

Keep original model/request/settings frozen. Test model loading separately
from text generation before another dialogue run, potentially comparing the
normal copy path with SDMA disabled or non-mmap loading. Check actual backend
launch flags: this version exposes use_mmap in API types, but forwarding it to
llama-server is not established by the inspected launcher file. Do not claim
an API use_mmap=false request changes the load path without verifying logs.
A passing load-only test would address upload stability, not the thermal issue.
No such test has been launched or system setting changed during this audit.
