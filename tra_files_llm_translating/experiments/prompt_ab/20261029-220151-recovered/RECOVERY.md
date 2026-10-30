# Manual recovery after the Codex server restart

The original partial run is preserved at ../20261029-220151/. It saved one
successful male reply before the client process ended. That exact reply is reused
here, with prompt, schema, options and model digest checked; it was not generated
again. Its record is explicitly marked `recovered_from`.

The old client may already have started its following female request. No completed
record or response survived for that attempt. The pending female slot was issued
in this manual continuation. That is a documented resubmission after external
interruption, not a measured linguistic rejection or an automatic retry feature.
Do not claim that no request slot could have been submitted twice. The unavailable
attempt is unscored and its time/output cannot be reconstructed from these files.

This continuation has 36 planned saved replies: one reused prior male reply and
up to 35 new requests (fewer actual calls if normal male failures skip females).
Regular runners still have no inference retry, resume, splitting or repair feature.
Previously completed five-dataset results were not rerun. No model settings or
checks changed to recover this run. The exact one-off driver is archived here.
