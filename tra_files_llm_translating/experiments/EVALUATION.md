# Evaluation changes after the baseline pilot

Date: 2026-10-27. Requested scope: improve diagnostic checks using the pilot,
add unseen dialogue fixtures, and document the work. No model comparison or new
live translation run was requested in this step.

## Why change the evaluation

The baseline pilot at commit `f01ac30` used twelve InkGallery source lines but
scored eight of them. Production/default sampling won among production-eligible
prompts at 127/138 checks. However, manual reading found untranslated English,
invented names, meaning changes, and unrelated rewrites in the female pass.
One reframed run passed 46/46 checks while translating downstairs as a kitchen and
Ink Gallery as a gallery of grass. See [the historical pilot](PILOT_2026-10-27.md).
Those observations motivate diagnostic coverage, not an automatic translation
repair system or a claim that any prompt is now reliable.

## InkGallery v2

`inkgallery_checks.json` now has version `inkgallery-v2`. All twelve source lines
are targets in both full and pair scope, including lines with only global checks.
Full scope still supplies the entire dialogue as context. The same expected
checks are applied to the same targets in both scopes.

- **Untranslated English:** `no_latin: true` flags any remaining ASCII Latin
  letter outside recognized engine placeholders, printf substitutions, literal
  escapes, and formatting controls. For example, `downstairs` fails, while
  `<CHARNAME>`, `%gate_lock%`, `%s`, and a literal `\n` do not. Top-level and
  per-line `allowed_latin` arrays contain exact, case-sensitive names or phrases
  that may remain in Latin script. Matching uses word boundaries. Nothing is
  automatically allowed merely because it appeared in the English source.
- **Gallery name:** lines @16 and @18 must retain an ink/gallery name, accepting
  forms of `Галерея Чернил`, `Чернильная галерея`, or `Галерея туши`. Known
  invented grass/thaw/Ink-transliteration names are also flagged. This is a
  diagnostic accepted-name list, not a decision to change the production glossary
  or a definitive canonical localization. Some valid names or punctuation may
  still require manual adjudication.
- **Location:** @48 requires downstairs wording (`внизу`, `вниз`, a lower floor,
  or first floor) and forbids the invented kitchen. A floor interpretation still
  needs context review; the regex does not prove the location is accurate.
- **Idiom:** the existing bad literal `как я делаю` remains forbidden. The
  positive check now also accepts `как я справляюсь`, self-feeling formulations,
  and `как мне живётся`, alongside affairs/well-being wording. Accepted wording
  is context-dependent; a matching fragment is not proof of faithful translation.
- **Versioning:** each newly written request record contains `evaluation_version`.
  Keep results from different evaluation versions in separate directories.

The extra checks and four additional target lines change the denominator and
weighting. V1 and v2 percentages are not directly comparable. The original pilot
was not silently rescored. `--summarize` only reads the checks already stored in a
log; it does not apply updated checks. Run the new evaluation in a fresh folder
when new model outputs are wanted.

## Male/female wording review

A female result now also records `pair_reviews` and the summary writes
`pair_reviews.csv`, with both translations side by side. These diagnostics are
separate from expected-form checks and never affect automatic winner selection.
They do not alter, repair, or reject model text in production.

For lines with identical male/female English, the evaluator compares the Russian
literally after normalizing only explicitly listed surface-form pairs from
`pair_review.allowed_changes` and per-line `allowed_changes`. Pairs are literal,
case-sensitive words or phrases, bounded by non-word characters. Overlapping
pairs are joined into equivalence classes, so `пришёл` and `пришел` may both
correspond to `пришла`. No Russian morphological analyzer or gender inference is
used. Punctuation, unlisted spelling, word order and wording changes remain visible.

Statuses:

| Status | Interpretation |
|---|---|
| `pass` | Identical outside listed forms; gender and meaning may still be wrong. |
| `review` | An unlisted wording, capitalization, punctuation or form change needs reading. |
| `missing` | A validated male/female pair is unavailable; request failures are already penalized by the main checks. |
| `not_applicable` | The original female English differs, including an explicitly empty variant; exact wording equality is not expected. |

Normalization treats listed forms as equivalent in either direction. It does not
check which form belongs in which gender pass; the gender checks and a reader do
that. A consistently masculine pair can pass this review and fail female gender
checks. Conversely, an entirely valid gender edit using an unlisted synonym can
be flagged for review. A female pass that fixes a male mistake is also flagged:
the flag measures departure from the copy-only instruction, not whether that
particular change made the Russian worse. A shared bad translation can pass.
Read both outputs and the English before judging a flag.

## New fixtures

No distinct source-game dialogues were available locally. The four new fixtures
are **synthetic**, authored after the pilot, and were not sent to a translation
model during this task. They are unseen with respect to that pilot, not an
independent corpus or a permanently blind benchmark. Their design intentionally
targets known failure modes. References were reviewed by the same assistant that
authored the fixtures; there is no independent human/native-editor sign-off.

There are 22 rows and 20 distinct TRA strings. See
[the fixture guide](fixtures/README.md) for the coverage matrix, source files,
line-by-line review rules and commands. Every fixture includes:

- English input, graph links, TRA references, hand-labelled addressees where
  knowable, and original female source metadata.
- A versioned checks file with targeted diagnostic regexes.
- Illustrative male/female Russian references and line-specific review notes.
  These are examples of acceptable translations, not exact-match gold answers.

References and review notes are never supplied to the translation model. Standard
production/reframed/examples/markup variants receive no fixture addressee facts;
only `reframed-addressee` receives a hand-labelled fact where one exists. Ambiguous
listener facts are left blank, not guessed. The ambiguous fixture does not forbid
`вы` globally, because addressing both NPCs is a plausible reading in some lines.

## Harness changes required by the fixtures

The new cases exposed experiment behavior that did not match production:

1. Experimental reframed/examples female passes always used male English. They
   now use `female_source`, including explicit empty variants. Their female-edit
   instruction explicitly preserves differences in original female meaning.
2. Markup receives `female_english` only when the original source variants differ,
   and is instructed to encode those meaning differences with the same notation.
   Empty alternatives are allowed. This extends the experimental prompt; its
   behavior has only been checked with reference replies, not live LLM output.
3. The harness previously sent each reused TRA row independently. The existing
   production merge logic is now a shared `merge_dialogue_rows` helper. Every
   experimental prompt sends shared strings once, with all speakers and graph
   predecessors, then expands the response to the original rows for scoring.
   Reused strings with conflicting source pairs are rejected. Conflicting
   hand-labelled addressees are omitted from a merged prompt rather than attaching
   the first use's listener to all uses. Within a full dialogue, identical reused
   outputs are a property of this merge, not evidence that the LLM independently
   chose consistent wording. In pair scope the row subsets may still differ.

Production translation instructions, engine settings and export behavior are
unchanged; production calls the extracted merge helper in place of its previous
inline block. No new translator reviewer pass, batching, retry, limit, model
switch or automatic text replacement was added.

## Validation and limits

Automated tests cover Latin tokens and allowlists, accepted/rejected names and
idioms, wording normalization and missing pairs, all fixture references against
structural and regex checks, original female/empty variants across all five
prompts, shared-string merging/expansion, and reference-reply round trips for all
four fixtures, all five prompts, and both scopes. Reference round trips use a
mock chat response; they validate the harness, not translation quality.

Run from the repository root:

```bash
python3 -m unittest discover -s tra_files_llm_translating/tests
python3 tra_files_llm_translating/experiments/diagnose_translation.py --dry-run --scopes full
```

Read the entire output against the English, including unscored nuances and graph
branches. Review failures by category rather than interpreting the total percent
as translation accuracy. Do not tune repeatedly against these references and then
report them as blind generalization. Before deploying a winning approach, use
additional authentic mod dialogues and an independent Russian review if available.

The subsequent two-model comparison and first live fixture translations are now
completed under these fixed checks; see
[MODEL_COMPARISON_2026-10-27.md](MODEL_COMPARISON_2026-10-27.md). The design and
mock-test statements above describe fixture creation before that live run. No
production model or prompt was changed. The subsequent uncapped thinking-on baseline is also completed; see
[THINKING_BASELINE_2026-10-27.md](THINKING_BASELINE_2026-10-27.md). Neither run
changed the frozen evaluation or production instructions.
