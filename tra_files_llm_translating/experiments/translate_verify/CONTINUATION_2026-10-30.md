# Translate + verify — continuation after the stop (2026-10-30)

## Continuation launched — 22:06 UTC

The user authorized continuing on this PC. Run
`20261030-220610-continuation/` is active via
`CONTINUATION_LAUNCH_2026-10-30.py`; check the queue/process before launching anything.
All 59 offline tests passed; frozen hashes and both model digests match. The launcher
runs steps 1 and 2 sequentially. Step 3 review remains pending.

The rebased local failure records include the sixth ambiguous_addressees translation
and a failed first verifier request, followed by connection refusal. No successful
verifier reply exists; the fresh dataset rerun below still applies. Five-reply
counts below describe the earlier other-PC snapshot.

## Where it stopped

Run `20261030-095325/` is **stopped**, not running (confirmed by the user on
2026-10-30). Its `manifest.json` and `REPORT.md` still say `running` because the
process ended without writing a final status; they are left unedited as raw records.
See [20261030-095325/STOPPED.md](20261030-095325/STOPPED.md).

| Dataset | State in `20261030-095325/` | Use |
|---|---|---|
| inkgallery | complete: 6 translations + 3 verifier replies | **final result**, do not re-run |
| ambiguous_addressees | partial: 5 of 6 translations, no verifier reply | keep as a record of the stop; **re-run from scratch** |
| the other six datasets | not started | run |
| planted stage | not started | run (inkgallery has no planted cases: 0 requests) |

The runner has no resume (by design, and the user rejected automatic retry/resume),
so the remaining work runs as a **new run folder** with the same settings. The
partial ambiguous_addressees replies are not reused or scored: a translation without
its verifier step does not measure this approach.

Interim InkGallery result and assistant review: see the run's `REPORT.md`,
`MANUAL_REVIEW.md` and the summary in [STOPPED.md](20261030-095325/STOPPED.md).

## Prerequisites on the continuing machine

1. Repository at a commit that contains this file. **Use a checkout with LF line
   endings** (Linux, or `core.autocrlf=false`): the frozen SHA-256 values are of the
   committed bytes. A Windows `autocrlf=true` checkout changes the bytes and every
   hash check below fails although the content is the same.
2. Ollama serving on `http://localhost:11434` with the same model digests as the
   stopped run (pull nothing new under the same tag without checking):
   - `mistral-small3.2:24b` digest `5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b`
   - `gemma4:12b` — digest in `20261030-095325/manifest.json` → `models.verifier.digest`
3. No other inference job using the same Ollama server (jobs run one at a time).

Check the inputs are unchanged (run from the repository root; prints `[]` when
everything matches):

```bash
python3 - <<'EOF'
import json, hashlib, pathlib
m = json.load(open('tra_files_llm_translating/experiments/translate_verify/20261030-095325/manifest.json', encoding='utf-8'))
print([p for p, h in m['sha256'].items()
       if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() != h])
EOF
curl -s localhost:11434/api/tags | python3 -c "import json,sys; [print(m['name'], m['digest']) for m in json.load(sys.stdin)['models']]"
```

If a hash or model digest differs, stop and ask the user: results would not be
comparable with the InkGallery part.

## Step 1 — finish translate + verify

Same settings as the stopped run (all runner defaults): Mistral translator with the
model's default thinking, Gemma4 verifier with thinking on, native context for both,
`num_predict=-1`, 3 repeats, no timeout/retry/splitting.

```bash
cd tra_files_llm_translating/experiments
python3 run_translate_verify.py --dry-run \
  --datasets ambiguous_addressees,multiple_npcs,original_female_variants,reused_strings,inkgallery_beholder,inkgallery_moon_sisters,inkgallery_sewers
# expect: translate-verify up to 63 requests, planted up to 54 requests

python3 run_translate_verify.py \
  --datasets ambiguous_addressees,multiple_npcs,original_female_variants,reused_strings,inkgallery_beholder,inkgallery_moon_sisters,inkgallery_sewers \
  --out translate_verify/$(date -u +%Y%m%d-%H%M%S)-continuation
```

Before starting, set `VERIFY_QUEUE_2026-10-29.json` → `"state": "running"` and add
`"continuation_output"` with the new folder; set it to `"finished"` when the run
prints `FINISHED`. If the run stops again, record that the same way and continue with
another fresh folder for the datasets not yet complete. Never re-issue a dataset that
already has its verifier replies.

## Step 2 — the queued Sewers A/B slots (separate experiment)

The prompt A/B Sewers continuation (10 requests that never reached Ollama during the
outage) was waiting for verification and never ran. Its launcher waits until
`VERIFY_QUEUE_2026-10-29.json` says `"finished"`, then checks the frozen hashes and the
Mistral digest itself. After Step 1 is finished and the queue file updated:

```bash
python3 tra_files_llm_translating/experiments/prompt_ab/TRANSPORT_CONTINUATION_LAUNCH_2026-10-30.py
```

It writes `prompt_ab/<timestamp>-sewers-transport-continuation/` and updates
`AB_TRANSPORT_CONTINUATION_QUEUE_2026-10-30.json`. Production repeat 1 stays excluded
(the user decided to keep its female pass as a serving failure).

## Step 3 — report and review

1. Combine: InkGallery from `20261030-095325/`, all other datasets and the planted
   stage from the continuation folder. Present them as one experiment run in two
   parts, and say so.
2. Read every `before_after.csv` and `verifier.jsonl`. For each applied edit classify:
   fixed a real error / harmful edit (e.g. changed correct text) / unnecessary rewrite.
   Check the Russian of every replacement, not just the checks: the InkGallery part
   shows the checks miss non-standard words (`приключенница`).
3. From the planted stage report recall (planted errors found) and false alarms on
   the unmodified reference translations.
4. Write the manual review in the continuation folder, update
   `experiments/README.md`, `TRANSLATE_VERIFY_PLAN.md` results and `SESSION_HANDOFF.md`.
   Commit the results (the user wants experiment results committed to the repo).

Decision question for the user once complete: does the verifier fix more real errors
than it introduces, and should its corrections be applied automatically or only shown
for review? No production change without the user's agreement.
