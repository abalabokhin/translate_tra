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

## Evaluation v3 (2026-10-29)

The manual reviews of the 2026-10-28 runs found checks that missed real errors and
checks that rejected valid Russian. They are fixed here. Versions: `inkgallery-v3`,
and `-v2` for each synthetic fixture. **Scores under v3 are not comparable with
earlier totals:** denominators changed. Use `rescore.py` (below) to put old runs on
the same footing. Every new check passes the reference translations. A regression
test (`test_v3_checks_match_observed_errors_and_accept_observed_valid_wording`)
pins each observed case listed here.

Missed real errors, now caught:

| Fixture / line | Change | Observed error it catches |
|---|---|---|
| InkGallery @16 female | masculine address nouns now include `приключенец`; male pass forbids `приключенка` | female greeting kept `приключенец` (Qwen3.5, Mistral) |
| multiple_npcs 105 | male/female address-noun checks added (`путник`/`путница` etc.) | female `путник` with a correct verb (Gemma4, Mistral, Qwen3.5) |
| multiple_npcs 102 | narrated man must stay `его`; `её` forbidden | female pass turned his `его` into `её` (Qwen3.5, Huihui) |
| ambiguous_addressees 201 | ferryman required (`паромщик/перевозчик/переправщик/лодочник`) | `проводник`, `Водяной`, `водовоз`, `Переводчик` |
| ambiguous_addressees 204 | `поток` now accepted, but agreement with сильный/сильное checked | `Поток слишком сильное` |
| ambiguous_addressees 205 | until-condition `пока … не` required; `должен/должна` forbidden for the ambiguous listener | `пока верёвка надёжно закреплена`, `станет крепкой`; `Ты должен…` |
| original_female_variants 401 | `учеником`/`ученицей` per pass | female pass kept the masculine apprentice |
| original_female_variants 403 | `привёл/привела` (led) forbidden; misspelled `принёсла`, `принела` forbidden | Qwen3 key "led"; Qwen3.5 and Huihui misspellings |

Valid Russian that was rejected, now accepted:

| Fixture / line | Change |
|---|---|
| ambiguous_addressees 201 | `Брэм` and `Брем` accepted alongside `Брам` |
| ambiguous_addressees 204 | `поток` accepted for current |
| multiple_npcs 101 | `этажом ниже` accepted for downstairs |
| multiple_npcs 103 | `пообещал/пообещала` accepted |
| multiple_npcs 104 | impersonal `тебя (не) ранило` and `тревожилась`, `переживала` accepted |
| reused_strings 301 | the readiness check is now per pass. Male pass (male Player1 + female Selene): any gendered `готов/готова` fails. Female pass (both speakers female): only `готов` fails, so `Я готова` passes. |

Still unchecked: overall fluency, register, many meaning changes and context-dependent
pronouns. The checks are targeted assertions, not a quality score.

### Rescoring old runs

`rescore.py <results folder>` re-scores every stored `runs.jsonl` in a batch folder
whose dataset folder is named `inkgallery` or a fixture name, as the batch runners
write them. It writes `rescored.csv` with the old and new totals. Rejected and skipped
replies stay failed: rescoring never salvages them. Old runs still lose the three
empty-female requests, because the fix to that pipeline step (2026-10-29) changes the
request, not the scoring. Only a new run measures it. The raw logs of the 2026-10-28
runs exist only on the machine that ran them, so rescore them there:

```bash
cd tra_files_llm_translating/experiments
python3 rescore.py results/non-thinking-20261028-013515
python3 rescore.py results/thinking-native-20261028-094842
python3 rescore.py results/thinking-native-remaining-20261028-214626
```

Commit the resulting `rescored.csv` files, copied next to the result reports, for example
as `NON_THINKING_RESCORED_V3.csv`, so the comparison can be reviewed elsewhere.

## Real-mod set (2026-10-29)

`real_set/` holds real mod dialogues with references written or reviewed by a person;
see [real_set/README.md](real_set/README.md). It is empty until such dialogues are
added. The translate + verify and prompt A/B runners include it automatically.

### v3 rescoring completed (2026-10-29)

The three stored 2026-10-28 batches have now been rescored offline. See
[results and interpretation](RESCORED_V3_RESULTS_2026-10-29.md),
[non-thinking CSV](NON_THINKING_RESCORED_V3.csv),
[Qwen3.5 native CSV](THINKING_NATIVE_QWEN35_RESCORED_V3.csv) and
[remaining native models CSV](THINKING_NATIVE_REMAINING_RESCORED_V3.csv).
The new pooled denominator is 717. Rejected/skipped replies remain failed; no
new inference or fixes are part of rescoring. Files await user review; do not
commit without the user's later explicit request.

### Observed limits in the frozen fresh InkGallery run (2026-10-29)

[Manual review](prompt_ab/20261029-220151-recovered/MANUAL_REVIEW.md) records these
new examples without changing checks during the A/B comparison:

- Beholder: `мёртвая зона магии` misses the adjacent dead-magic regex despite
  conveying a magic dead zone; likely false positive, with awkward phrasing.
- Moon Sisters: female `истинного меня` is a real masculine-adjective error, but
  the real-self check only forbids `настоящего`, so it passes. Observed false negative.
- Generic selected `человек` can wrongly become `женщина`/`героиня` even though
  the graph also offers unknown-gender Player2–Player6. A wording flag prompts
  review, but the targeted assertions do not establish correct selection semantics.
- Gender-motivated `лидерша` or a changed Child title can raise unlisted-wording
  flags. Flags alone cannot distinguish necessary agreement from unwanted rewriting.

Any later check revision must be versioned and old/new totals kept separate. These
findings are documented for review; no post-output tuning or new scoring run is
part of the current frozen experiments. Human review of references remains pending.
