# Commit snapshot — 2026-10-30

The user explicitly requested **“commit everything”**, authorizing this commit
after reviewing the documented work. Earlier no-commit instructions were the
review prerequisite; this request satisfies that prerequisite for this snapshot.

This snapshot includes native-context/uncapped experiment defaults, whole-line
verifier corrections and tests, v3 rescores, prompt A/B raw data and frozen input
snapshots, three fresh InkGallery fixtures, source preparation (including clearly
superseded Alora candidates), serving diagnostics, manual reviews and editorial
proposals. The proposals remain separate from production translations. No prompt
or model is promoted.

The experiment is **not finished**. At the pre-commit check, translate + verify
has six InkGallery translation replies and one saved verifier reply. The dated
manual review covers the first four translation replies; the last pair and the
verifier reply still need review. Planted controls and the queued unsubmitted
Sewers configurations remain pending. See VERIFY_QUEUE_2026-10-29.json and
AB_TRANSPORT_CONTINUATION_QUEUE_2026-10-30.json. The jobs continue running; this
commit preserves available results rather than claiming final completion.

Start with [the review index](REVIEW_2026-10-29.md) and
[finished-dialogue review](review/20261029/FINISHED_DIALOGUE_REVIEW_2026-10-30.md).
Historical status notes are dated observations. New replies saved after staging
will appear as subsequent working-tree changes and are not covered by this snapshot.
