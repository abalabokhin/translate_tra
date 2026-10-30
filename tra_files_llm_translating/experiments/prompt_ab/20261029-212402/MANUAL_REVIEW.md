# Manual review — prompt A/B

Follow-up review: [finished-dialogue report, 2026-10-30](../../review/20261029/FINISHED_DIALOGUE_REVIEW_2026-10-30.md)
and [annotated output / full-line proposals](../../review/20261029/ASSISTANT_REVIEW_2026-10-30.csv).
The explicit addressee metadata resolves the earlier uncertainty about reused
string 304: it addresses Player1, so singular commands are recommended. The
follow-up also flags the awkward book-learning phrasing at InkGallery @19.

Review by the assistant against English, actors and graph, not an independent
human Russian review. This file is updated as replies arrive; conclusions remain
pending until all datasets and repeats finish. Regex checks and wording flags are
read as diagnostics, not judgments of overall quality.

## InkGallery

### production, repeat 1 — both full replies read

- Female @16 retains masculine `приключенец`; female @48 retains `зашёл`.
  Both are genuine agreement errors caught by v3.
- Both columns @16: `Наша Галерея Чернил рады приветствовать` has broken
  singular/plural agreement. It should use a singular predicate or a plural subject.
  The male reply nevertheless passes all 45 targeted checks; grammar is unscored.
- @16 `Здравствуйте` introduces formal/plural greeting alongside singular `тебя`.
  Treat as a register issue under the singular-ты instruction; the ты/вы regex
  does not catch that greeting.
- Female @23, @100, @17, @24 make the required changes. Female @18 correctly
  preserves Velcealle as female; Cormyr and gallery meaning remain.
- @48 idiom is retained correctly. Remaining rows keep the source propositions,
  engine token and wording across columns. No unrelated female rewrites observed.
- All pair-wording diagnostics pass despite the two missed gender edits. Those
  flags test unwanted differences, not whether required edits actually happened.

### production, repeat 2 — both full replies compared with repeat 1

The male text differs only at @48 (`стоит`, `узнать`) and punctuation at @100;
all changed text was read. @16 repeats the broken `Галерея ... рады` agreement
and formal greeting. Female @48 now correctly uses `зашла`; @100 keeps correct
female agreement. The female @16 noun remains masculine. Other lines match the
reviewed repeat 1 texts exactly. No unrelated female edits; one genuine v3 failure.

### production, repeat 3 — both full replies compared with reviewed repeats

Male @48 combines `стоит` with `посмотреть`; @100 uses the em dash again. These
are acceptable sampled alternatives. @16 repeats the same agreement/register
problems. Female differs from repeat 1 only by `стоит` at @48, retaining both
`приключенец` and `зашёл`. Both genuine gender errors are caught. Other texts match
already reviewed output. No unrelated female rewrites.

### production-nouns, repeat 1 — both full replies read/compared

The male prompt is byte-for-byte equal to production repeat 1, as required. Its
only translation difference is acceptable wording at @48 (`стоит`, `узнать`).
Female @16 still has masculine `приключенец`, despite the added noun instruction;
@48 correctly changes `зашёл` to `зашла`. Both columns retain the gallery agreement
error and greeting issue. Remaining female gender edits, fixed NPC gender, source
meaning and tokens are preserved. No unrelated female rewrites or wording flags.
One failed check, the genuine noun error; no evidence of noun improvement yet.

### production-nouns, repeat 2 — both full replies compared/read

Male differs from production repeat 1 at @17/@24: `пошлину` instead of `сбор`.
This is a more bureaucratic choice for a fee, but retains payment and its effect.
Female preserves that wording and makes the required verbs feminine; @48 correctly
has `зашла`. @16 again keeps `приключенец` and the gallery agreement/register
problems. Other rows match already reviewed output. No unrelated female rewrites,
no wording flags; one genuine noun-check failure.

### production-nouns, repeat 3 — both full replies read/compared

Male changes @48 (`стоит`, `узнать`), @100 (`может`), @17/@24 (`пошлину`,
`Так что я понял`) and @18 (`сказала`). Source propositions and Velcealle's gender
remain; @17/@24 syntax is less natural than `как я понял`. Female preserves its
own male wording except required gender edits, but misses both `приключенец`
and `зашёл`. All other female changes are correct; no unrelated rewrites.

### InkGallery conclusion (all 12 replies assessed)

Production 265/270; noun rule 266/270. No rejected replies or wording flags in
either. Both variants miss the feminine address noun in every repeat (3/3 each).
The single-check difference is a verb at @48, not the noun rule's target. This
sample does not justify adopting the rule. Every reply also retains the unchecked
gallery agreement error. No production change is made on these partial results.

## Ambiguous addressees

### production, repeat 1 — both full replies read

All five propositions and the rope's until-condition are preserved. `Вы должны`
at 205 can address Bram and Selene together, as permitted by this ambiguous graph;
it is not automatically a formal-singular error. 202 uses singular `ты`, which can
address one listener before the later branch/group address. No invented listener
gender. Names, ferryman and current meaning are correct. Female text copies male
exactly, as expected. Both replies pass all 15 checks.

### Ambiguous addressees — remaining 10 replies assessed by full text/differences

All production repeats and both prompts preserve ferryman, current and the
until-condition; both score 90/90. Accepted name variants are Брам/Брэм.
Noun-rule repeat 1 uses singular neutral `Тебе нужно`; repeat 3 uses plural-neutral
`Вам нужно`; other 205 variants use group `Вы должны`. Every female reply copies
its own male draft exactly. No listener gender is invented, no unrelated rewrites
or rejected replies. This fixture requires no gendered Player1 nouns and shows
no advantage for the rule.

## Multiple NPCs

### production, repeat 1 — both full replies read

Female 105 has correct `спасла` but masculine `странник`; genuine v3 failure.
NPC Selene/Orin and narrated `его` stay fixed correctly. 101 adds `тебя` to Orin
waiting downstairs; plausible context but more explicit than the source. 106
`Встретимся` is natural but leaves the source's explicit `us` less clear. These
meaning nuances are outside the targeted checks. No unrelated female changes.

### production, repeat 2 male — full text compared

Only 104 (`волновалась за тебя`) and 106 (`сдержи слово`) differ from repeat 1;
these are acceptable. Gender, third persons and meaning remain as above.

### production, repeats 2 female and 3 both — compared/read

Repeat 2 female keeps the same genuine `странник` error; its verbs and fixed
NPC/third-person genders are correct. Repeat 3 male writes `Селене, ты была права`
at 102: the dative form is wrong for direct address (needs Селена), though all
checks pass. The female repeats that source error. It also retains `странник`.
No unrelated female edits; added `тебя` and less explicit `Встретимся` persist.

### production-nouns, repeat 1 — both full replies compared/read

Male differs from production repeat 1 only by the acceptable `волновалась за тебя`
at 104. Female changes required verbs but retains masculine `странник`; fixed NPC
and narrated genders remain correct. No unrelated female rewrites. Same source
nuances at 101/106; no noun-rule improvement in this repeat.

### production-nouns, repeats 2 and 3 — both pairs compared/read

Both males use `Селена, ты была права. Я слишком поспешил, обвиняя его.` at 102
and `волновалась за тебя` at 104. These are valid choices and avoid production
repeat 3's name-case error; the male prompt is unchanged, so that difference is
sampling, not the added female noun instruction. Females preserve fixed NPC and
third-person genders, change required verbs, and again retain masculine `странник`.
No unrelated female edits. The same added `тебя`/implicit `us` nuances persist.

### Multiple-NPC conclusion (all 12 replies assessed)

Both variants score 147/150. Both miss the female address noun in all three
repeats. No rejected replies, unrelated female rewrites or wording flags. The
noun rule has not improved this second diagnostic noun case either.

## Original female variants

### production, repeat 1 — both full replies read

All original meaning differences are honored: his mentor -> her mentor, duke ->
duchess with corresponding possessives, silver -> bronze, and brought/apprentice
forms follow Player1 gender. Explicit empty 404 is exported empty; schema ids
omit 4 from the female request while retaining 1/2/3/5. 405 is unchanged. Male
`принес` without ё is valid Russian here. Both replies pass all 35 pair checks.

### Original female variants — remaining 10 replies compared/read

Production repeat 2 uses `вернуть` for retrieve and `принёс` in the male draft;
the female preserves `вернуть` and the required female source changes. This is
plausible retrieval/return of the owner's seal. Remaining repeats are equal to
the already reviewed baseline texts except valid е/ё spelling. Both variants
score 105/105, with all six female requests correctly excluding the explicit empty
source. No added omissions or unrelated rewrites. The noun rule adds no measured
benefit on this fixture; the empty-source code fix is directly exercised.

## Reused strings

### production, repeat 1 — both full replies read

Male 301 is `Я готов.` for both Selene and Player1, despite the explicit mixed-
speakers neutral-wording note in the request. It cannot suit female Selene; two
expanded-row check failures represent one shared game-string error. Female 301
`Я готова.` suits both female speakers and correctly passes v3. These are not
independent choices on each repeated row: merging enforces duplicate equality.

Both columns use `откройте` at 302, where the expected listener is Selene; this
formal/plural command needs review under the singular-ты policy. 304 similarly
uses `Подождите`/`Не трогайте`; a group reading is more plausible there, so context
should be checked before calling every plural form wrong. The checks do not
establish correct register. Stage direction, actual newline and both engine tokens
are preserved. No unrelated female rewrites; 301's change is required for the
female pass, but it does not solve the male-pass shared-string conflict.

### Reused strings — remaining 10 replies compared/read

All later texts match the reviewed repeat 1 columns, except production repeat 3
male 301 writes `Я готов(а).` on both expanded rows. That is a displayed gender
placeholder, not natural neutral wording; v3 correctly rejects it. Both variants
score 96/102: all three male shared-key cases fail, and every female case is valid.
Plural-command concerns, preserved structure/tokens and absence of unrelated
female rewrites remain as above. The note is present in the actual male request
with speaker genders female/male; prompt delivery succeeded but the model ignored
or failed to implement the neutral wording requirement.

## Completed five-dataset conclusion

All 60 replies were assessed, reading full unique texts and exact differences
against already-read repeats. Production 703/717; noun rule 704/717. Both have zero
rejected requests and zero unrelated-edit flags. Both fail the female address noun
in all 3 InkGallery and all 3 multiple-NPC repeats. The single-check gain is a verb,
not a noun. Do not adopt the noun rule on this evidence. The real-mod extension
is a separate pending comparison, not part of these frozen totals.

Explicit empty female handling works in all six new pairs. Mixed-gender neutral
wording remains unreliable despite the new note, so the manual-review requirement
is justified. No production model or prompt is promoted. Grammar/register/meaning
nuances outside the checks remain, as detailed above.
