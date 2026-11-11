# Manual review — fresh InkGallery prompt A/B

Latest editorial pass: [finished-dialogue review, 2026-10-30](../../review/20261029/FINISHED_DIALOGUE_REVIEW_2026-10-30.md)
and [complete proposed lines beside the saved outputs](../../review/20261029/ASSISTANT_REVIEW_2026-10-30.csv).
Beholder and Moon Sisters are fully reviewed; Sewers has only the saved male reply.
Its female pass ended as a serving failure (not still pending). Earlier arrival
notes below are chronological. The latest review distinguishes the leader noun's
register/policy choice from universal grammatical requirements.

Assistant review against English and complete D graphs. Human review pending.
Three new encounters; references/checks fixed before inference. Ordinary translation
requests do not receive the references. Exact repeated texts will be compared with
already-read output, and every unique output will be read.

## Recovery

The server restart ended the first client after one successful male reply. That
reply is retained in the original partial folder and explicitly reused here, with
prompt/schema/options and model digest checked. No completed translation was
requested again. An in-flight female output was lost and is unavailable/unscored.
See RECOVERY.json and the archived one-off driver; no automatic retry/resume was
added to the ordinary runners.

## Beholder, production repeat 1 male — full reply read

All prices, creature facts, dead magic, tokens and narrated masculine agreement
are preserved; all 15 targeted checks pass. Significant unchecked issues:
- `Нежить и дикий одновременно` has incompatible noun/adjective construction.
- `Тот же человек узнает из этой книги` is incomplete/unnatural for learning from
  a book; the source describes the same selected person's learning, not merely
  receiving an unspecified fact.
- `Только справедливо, чтобы...` is a calque; `плата за этого` is awkward and
  vague. These need editing despite a perfect targeted score.
- `Зомби-созерцатель` is a terminology choice for zombie beholder; compare with
  the user's preferred game glossary, rather than scoring a single spelling as
  objectively required when the glossary provides no entry.
- `Я пропущу` is understandable as declining the encounter for now, but less
  idiomatic than a direct refusal. Other reply tokens and continuation are intact.

The male draft is the saved pre-restart response, not a second model attempt.

## Beholder, production repeat 1 female — full reply compared

The sole change from its own male draft is `сразился` -> `сразилась` for Player1.
Narrated monster, NPCs, prices and all engine tokens stay fixed. All 15 targeted
checks pass, with no wording flags. The phrase still has masculine modifier
`первоначальный лидер` next to the feminine verb; this needs review under the
project's complete-agreement policy (a neutral or feminine alternative can avoid
mixed naming). The frozen checks do not cover that modifier. The unchecked male
phrasing/grammar problems persist. A perfect pair score is not approval for export.

## Beholder, production repeat 2 male — full unique differences read

The narration now uses `Неживой и дикий`, avoiding repeat 1's noun/adjective
mismatch. NPC reply introduces `Его заслуженно уничтожить`, a broken construction
for "It deserves to be destroyed". Book learning becomes `будет учиться из этой
книги`, an awkward source-language collocation (natural Russian would use learning
по книге or drawing knowledge из книги). Prices lose English commas, which is a
valid formatting change accepted by the frozen check. Final `давай начнём` is
acceptable. All remaining texts equal the reviewed male baseline; all 15 checks
pass despite the new grammar error. No parameter or prompt changed between repeats.

## Beholder, production repeat 2 female — full differences assessed

The Player1 leader verb correctly changes to feminine. However, the NPC's generic
`Тот же человек` becomes `Та же самая женщина`. That narrows the selected fighter
to a woman even though the complete graph also offers <PLAYER2>–<PLAYER6>, whose
genders are unspecified. The female column depends on Player1, not on whichever
party member is selected. This is a genuine inappropriate meaning/gender edit;
the pair-wording diagnostic correctly flags it. All 15 targeted checks still pass.
Unchecked male grammar/learning-collocation problems and the masculine leader
modifier persist. This is not an exact copy outside the necessary verb edit.

## Beholder, production repeat 3 male — full unique differences read

Narration uses `замечал` and `зона мёртвой магии`, both faithful. `Неживой и дикий`
avoids the first construction error. NPC reply matches the valid repeat 1 wording,
avoiding repeat 2's `заслуженно уничтожить`. Payment text uses `один на один` and
`плата за это`, both clearer. `будет учиться у этой книги` is understandable but an
awkward personification of the learning source. Prices, facts, tokens and remaining
texts are preserved; all 15 checks pass. Leader wording remains unchanged.

## Beholder, production repeat 3 female — full differences assessed

Only the required leader verb changes to feminine. The generic selected `человек`
is preserved, so repeat 2's over-gendering does not recur. Fixed roles, facts,
tokens and other wording match the reviewed male draft. No wording flag; all 15
checks pass. The leader modifier and awkward learning phrasing remain.

## Beholder, production-nouns repeat 1 male — full unique differences read

Narration returns to broken `Нежить и дикий одновременно`. It uses `мёртвая зона
магии`, rejected by the frozen adjacent "dead magic" regex: understandable as a
magic dead zone, though awkwardly phrased. Treat this as a likely check false
positive, not evidence of a causal noun-rule regression; the male prompts are
identical and independently sampled. Do not retune the check after seeing output.
Reply choices use `с этим существом`, a valid alternative to `с этой тварью`.
Learning remains `будет учиться у этой книги`; final `давай начнём` is acceptable.
All creature facts, prices and tokens remain. 14/15 checks; broader grammar still
needs editing. Female result is assessed separately when available.

## Beholder, production-nouns repeat 1 female — full differences assessed

Player1's leader phrase becomes `первоначальная лидерша ... сразилась`: complete
feminine forms, though `лидерша` has a colloquial register for user review. This
necessary gender edit produces an unlisted-change flag because the illustrative
allowed list does not contain that noun. Separately, generic `Тот же человек`
becomes `Та же самая героиня`: an inappropriate narrowing of the selected party
member's gender, just as production repeat 2 over-gendered the same line. This
second flag is a genuine meaning issue. The inherited dead-magic regex miss is
unchanged (14/15); other male grammar/phrasing problems persist.

## Beholder, production-nouns repeat 2 — both full replies/differences assessed

Male uses `Созерцатель-зомби`, `Как только ... замечал`, and `используя свои острые
зубы`: faithful alternatives. The undead adjective and destroy construction are
now grammatically coherent. Prices and source facts remain; learning phrasing is
still awkward. Female changes only the leader phrase to `первоначальная лидерша
... сразилась`; this is a required gender edit, not a gratuitous rewrite despite
the wording flag. Generic selected `человек` stays neutral. Both score 15/15.

## Beholder, production-nouns repeat 3 — both full replies/differences assessed

Male uses `Созерцатель-зомби`, a coherent `Неживой и дикий` construction, and
`Его нужно уничтожить`: faithful alternatives without the earlier grammar error.
Learning is still awkward `учиться из этой книги`. Prices, roles and other texts
match reviewed output. Female makes the complete feminine leader edit, but also
changes generic selected `человек` to `героиня`, repeating the inappropriate
assumption about whichever party member is selected. Two wording flags: one
necessary gender edit, one genuine meaning/gender error. Both replies pass 15/15.

## Beholder conclusion — all 12 logical replies assessed

Production 90/90, nouns 88/90; the two-point difference is the inherited likely
false-positive dead-magic wording in one male/female pair. No rejected replies.
Raw wording flags are 1 vs 5, but manual interpretation is essential: nouns has
three required leader edits plus two inappropriate generic-person edits; production
has one inappropriate generic-person edit. Nouns improves this leader wording,
but still does not yield reliably minimal edits. This is mixed evidence, not a
reason to adopt the rule. Grammar and terminology review remain necessary.
One male reply was explicitly reused after the daemon interruption; all remaining
completed logical replies in this encounter were new requests.

## Moon Sisters, production repeat 1 — both full replies read

Male: all 18 checks pass. Meaning, three female sisters, emphatic COSMOS/DREAMS/LOVE,
blood-marked path and threat are preserved. `МЕЧТЫ` vs reference `СНЫ` is an English
ambiguity, not automatically wrong. Several unchecked wording issues need editing:
`пришёл за судом` is awkward for coming to judgment; `по причине` is an incomplete
collocation for "for a reason"; `Возьмите свои оружия` uses a nonidiomatic plural
where normal Russian uses `оружие` or a command to take up arms. `Кровавый Ребёнок`
is a title choice for Bloodied Child that may weaken the specifically blood-stained
meaning. The masculine grammatical noun ребёнок can denote a girl; do not blindly
force a feminine adjective onto that noun. A neutral `Окровавленное Дитя` avoids
that issue without inventing biological gender.

Female correctly changes both arrivals and `отмечен` to `отмечена`, but leaves
`настоящего меня` in the player's reply; genuine missed feminine adjective, caught
by the frozen check. The path correctly remains masculine `путь отмечен`. Other
NPC facts and wording are preserved. This demonstrates selective agreement success,
not complete correctness. No unrelated rewrite flagged in the first pair.

## Moon Sisters, production repeat 2 — both full replies/differences read

Male's COSMOS/DREAMS relative-clause choices and `лишь смерть` are faithful;
`ЛЮБОВЬ, что прорезается ...` is poetic but less natural than cutting through.
The real-self reply uses `истинного меня`. Female changes arrival and marked forms,
but keeps that masculine `истинного меня`. This is the same agreement failure as
repeat 1, yet all 20 female checks pass: the frozen check only forbids настоящего.
Record this observed false negative; do not broaden checks mid-comparison. The
path remains correctly masculine and there are no unrelated female edits. Earlier
`по причине`/`свои оружия` issues remain. Both raw totals pass (18/18, 20/20), which
must not be described as complete language correctness.

## Moon Sisters, production repeat 3 male — full unique differences read

Only the path/threat sentence differs from repeat 1, using repeat 2's equally
faithful `Этого достаточно, чтобы мы знали...`. All other text exactly matches the
already-read baseline, including its unchecked collocations and `настоящего меня`
(which is appropriate in the male column). All 18 checks pass.

## Moon Sisters, production repeat 3 female — full differences assessed

Arrival and marked forms change correctly; masculine `настоящего меня` remains.
All other wording matches its own male draft, including correctly masculine path
agreement. One genuine check failure (19/20), no unrelated rewrite flag. Thus all
three production repeats miss the real-self adjective: two настоящего cases are
caught; one истинного case is an observed false negative.

## Moon Sisters, production-nouns repeat 1 — both full replies/differences read

Male changes the incomplete `по причине` to the more natural `по какой-то причине`,
uses `Кажется, вы видите настоящего меня`, and `просто чепуха`; source meaning is
preserved, with the other baseline wording issues remaining. Female changes arrival
and marked forms but again leaves masculine `настоящего меня` (19/20). It also
changes the title `Кровавый Ребёнок` to `Кровавая Девочка`, raising a wording flag.
This is a gender-motivated title change, not automatically an unrelated error,
but its age/register/lineage implications need human review: a neutral дитя can
preserve the fantasy Child title without forcing a feminine noun. No improvement
on the real-self adjective in this repeat. Path and fixed NPC forms stay correct.

## Moon Sisters, production-nouns repeat 2 male — full differences read

A valid short reply took 3733.93 seconds for 390 generated tokens. This is severe
runtime latency, not long generated content; see RUNTIME_DIAGNOSTICS.json. Model,
native context, sampling and generation settings remained unchanged.

Male uses `ЛЮБОВЬ, которая прорезается`, `Кажется, вы видите настоящего меня`,
`просто чепуха`, and `Это достаточно для нас, чтобы знать...`. Facts/roles remain,
with awkward collocations as above. All 18 targeted checks pass. The corresponding
female output has not yet returned at the time of this note.

## Moon Sisters, production-nouns repeat 2 female — full differences assessed

Returned after 2123.53 seconds with 370 generated tokens. Arrival/marked forms
change correctly, and the Child title again becomes `Кровавая Девочка` (gender-
motivated title flag requiring review). Masculine `настоящего меня` remains,
causing the genuine 19/20 result. Path and other wording match its own male draft;
no additional unrelated edit observed. Long wall time did not produce a longer
answer or remove the missed agreement error.

## Moon Sisters, production-nouns repeat 3 male — full unique differences read

Returned after 2831.58 seconds for 393 generated tokens. Relative to the reviewed
baseline it uses `МЕЧТЫ, дарующие надежду`, `ЛЮБОВЬ, способная прорваться`,
`истинного меня`, and `лишь смерть`: faithful alternatives. The real-self adjective
is correctly masculine in this column. Known baseline collocation/title issues
remain. All 18 checks pass. Female response is assessed separately when returned.

## Moon Sisters, production-nouns repeat 3 female — full differences assessed

Returned after 742.02 seconds for 373 tokens. Arrival/marked forms change and the
Child title becomes `Кровавая Девочка`. The male's `истинного меня` remains
unchanged: a genuine feminine-agreement error missed by the frozen настоящего-only
check. Thus the 20/20 result is an observed false negative, not a perfect translation.
Other text, fixed NPCs and masculine path agreement match the reviewed male draft.
Only the gender-motivated Child title raises a wording flag.

## Moon Sisters conclusion — all 12 saved replies assessed

Both prompts score 112/114. Both actually miss the real-self adjective in all
three female repeats: two настоящего misses are scored; one истинного miss escapes
in each prompt. The noun rule changes the Child title in all three repeats, but
fixes none of these adjective errors. Raw wording flags 0 vs 3 are title changes,
not automatically three damaging rewrites. Title meaning/register and the shared
unchecked collocations still need human review. No rejected replies or corrupted
path/NPC agreement. Long delays are retained in the measurements.

## Sewers, production repeat 1 male — full reply read

497 tokens after 2439.48 seconds; all targeted checks pass. The narrated adventurer
stays male, Jan's cousin remains female, and Jan correctly says `я должен` in
masculine. Prices and all six player tokens are preserved. Idiom `козырей в рукаве`
is retained. Several unscored issues need editing: `или хотя бы не эти туннели` is
a broken/awkward rendering of the source's at-least qualifier; `один-на-один бой`
is an English-like word order; `оригинальный лидер` is a false-friend choice for
the initial/original party leader. Repeated `с этими вещами` literally translates
"these things" but weakly conveys the worm-like creatures in context. `Я пропущу`
is understandable as declining for now but less idiomatic. `авантюрист` and
`группа` are lexical/register choices for review, not automatically meaning errors.
The female pass has not yet produced an output.
