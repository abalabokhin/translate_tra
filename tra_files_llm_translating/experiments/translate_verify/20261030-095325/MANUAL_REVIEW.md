# Manual review — saved translation pairs, 2026-10-30

Assistant review against English and source speaker/addressee facts. Human
approval pending. This reviews the four saved Mistral replies (InkGallery repeats
1/2, male/female) available at the review snapshot. No Gemma verification or planted
control results are assessed yet. Raw replies and frozen inputs remain unchanged.

## Repeat 1

Both full replies read. Male gallery agreement is grammatical, unlike the older
A/B `Галерея ... рады` wording. Female correctly changes `понял` to `поняла` in
`@17/@24`, but misses `приключенец` at `@16`, `зашёл` at `@48`, and **both**
`видел` and `пришёл` at `@100`. The targeted checks do not enumerate every bad
word separately. Pair wording flags can pass even when required edits are absent.

Both columns mistranslate the unless-condition at `@48` as `Разве ты зашёл только
посмотреть, как я поживаю.` This is an awkward interrogative-like construction
with a final period, not a faithful rendering of the source exception. Both use
`выучу все эти книги` at `@19`, suggesting memorization rather than learning from
the books. `Так что я понял/поняла` openings at `@17/@24` need grammatical editing.
Plural souvenirs at `@100` is an acceptable pragmatic wording choice.

Fixed female Velcealle remains female in `@18`, Кормир is preserved, and
`<CHARNAME>` is intact. `Капюшонные Волшебники` needs glossary review; no unsupported
canonical spelling is imposed. Other lines preserve their source propositions.

## Repeat 2

Both full replies read and differences compared. `@48` now preserves the unless
condition with `Если только...`, but female still retains `зашёл`. Female also
keeps masculine `приключенец`; it correctly changes **both** verbs at `@100` to
`видела` / `пришла` and the player self-references at `@17/@24` to `поняла`.
Fixed NPC genders and tokens remain unchanged. The book-memorization wording
and awkward `Так что я понял/поняла` syntax remain. Other sampled wording changes
are acceptable and introduce no unrelated female rewrite.

## Review proposals

Complete editorial alternatives, exact source text, original model text and
per-cell reasons are in
[ASSISTANT_REVIEW_2026-10-30.csv](../../review/20261029/ASSISTANT_REVIEW_2026-10-30.csv).
The [finished-dialogue report](../../review/20261029/FINISHED_DIALOGUE_REVIEW_2026-10-30.md)
explains scope, terminology decisions and findings across the completed A/B data.
These proposals are separate from model output and are not fed to the running
verifier. Do not present them as Gemma corrections or change experiment scores.
