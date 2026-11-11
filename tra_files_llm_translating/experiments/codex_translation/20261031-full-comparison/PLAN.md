# Full Codex CLI comparison

User authorized the whole test after reviewing the Luna pilot.

Two models (Luna, Sol), two methods (both, two-pass), all eight existing
datasets, three repeats: 96 dialogue pairs / up to 144 CLI requests.
Fresh run; pilot kept separate. Original complete-line prompts and validation;
no added context/output cap, timeout, retries, splitting, or production changes.
Snapshot and hashes preserved before inference. Runner stops on CLI or
structural failure; retain any failed reply and report before any recovery.
Review all results, including meaning beyond regex checks; human approval
remains pending. No new commit authorized.
