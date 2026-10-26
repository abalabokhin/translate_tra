# Session handoff — start here

Read [README.md](README.md) for the full workflow, experiment history, commands,
limitations and code review. This handoff records the latest decisions so the next
session does not restart abandoned experiments.

## User instructions that remain in force

- **Do not commit** unless explicitly instructed. The assistant made no commits.
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

1. Send the entire source dialogue for male Player1, with actor data, supplied
   addressee facts and the relevant glossary.
2. Supply original English plus validated male Russian lines to a female-only edit
   request. NPC genders remain fixed. Require complete lines and exact copying of
   unaffected wording.
3. Each model response is JSON: `{"translations":{"1":"Russian text", ...}}`.
   Short request IDs map back to original metadata. Python writes the final CSV
   with original English/metadata plus `Russian_Male,Russian_Female`.
4. Both responses must validate before export. Existing ID/token/format checks are
   structural checks, not a proof of gender agreement, meaning or completeness.

Native context is read through `/api/show`. Thinking and sampling use model
settings by default; optional `--think` / `--no-think` and `--num-ctx` are explicit
user choices. No automatic retry, splitting, timeout, checkpoint/resume or repair
mechanism remains in the translator.

`Addressee` is used when present in input CSVs. The parser does not infer or
populate it automatically. Unknown roles remain unknown. This is material: graph
predecessors and speaker labels alone do not identify every addressee or referent.

The shared `tra_format.py` and `translation_common.py` contain necessary literal
parsing, validation and atomic CSV writing. They are required runtime files.
TRA fixes preserve original female literals, both sounds, comments and literal
surroundings, reject conflicts, handle filename case, and avoid overwriting source
with failed/empty translations. See README for remaining parser boundaries.

Last automated verification: **21 tests pass**, Python compilation and
`git diff --check` pass. Re-run when code changes justify it:

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

## Remaining work — needs agreement, not automatic action

- User may choose to test stricter singular-address instructions with Qwen2.5,
  discuss another model, or review/edit the drafts. No such next change is agreed.
- Do not claim omissions, semantic drift or gender are solved. Prompt improvements
  and structural checks help but do not establish reliable automatic translation.
- Agree on canonical terminology before changing the glossary. Cormyr already has
  Кормир in `dict.csv`; Cowled Wizards lacks an exact entry there.
- No additional linguistic reviewer model, sentence/length heuristics, automatic
  addressee inference, guardrails or new experiment without agreement.

## Workspace and persistence

Original mod `/home/paladin/source/InkGallery-v1.5/` was not modified. Production
code/prompts were not changed during the latest model comparisons.

At handoff, `git status --short` lists README, this handoff, examples, tests,
`tra_format.py` and `translation_common.py` as **untracked**. Preserve these files:
some are required by the tracked scripts. A session restart keeps disk files, but
untracked files are not protected by git history. Do not commit or discard them
without instructions.

Only extended transient traces/test runners live in `/tmp/translate-tra-inkgallery/`.
The important examples, exact requests/replies and metrics are already copied into
this repository; continuing should not depend solely on `/tmp`.
