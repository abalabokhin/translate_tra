# Prompt A/B: female-pass noun rule

**Interpretation note, 2026-10-30:** Beholder and Moon Sisters completed normally.
Sewers includes a serving interruption, refused connections and skipped female
passes. Its failures and the pooled totals below are bookkeeping under the frozen
scorer, not a valid linguistic comparison. Use the
[dated results summary](../../PROMPT_AB_RESULTS_2026-10-29.md) and
[manual review](MANUAL_REVIEW.md) to interpret them. The unsubmitted configurations
are queued separately; the interrupted female pass remains a serving failure.

Status: finished. Started 2026-10-29T22:27:11.416342+00:00, finished 2026-10-30T09:53:17.488261+00:00.
Model `mistral-small3.2:24b`, think default, ctx native, 3 repeats, full dialogues.

Rule added to the female-pass instruction in `production-nouns`: "This includes every noun, adjective and participle that refers to Player1, not only verbs, e.g. гость → гостья, герой → героиня, чужак → чужачка, уставший → уставшая."

Checks are targeted assertions, not overall quality. Wording flags (male/female differences outside listed gender edits) should not rise: the rule must not cause unrelated rewrites.

| Dataset | Prompt | Checks | Rejected / requests | Wording flags |
|---|---|---:|---:|---:|
| inkgallery_beholder | production | 90/90 | 0/6 | 1 |
| inkgallery_beholder | production-nouns | 88/90 | 0/6 | 5 |
| inkgallery_moon_sisters | production | 112/114 | 0/6 | 0 |
| inkgallery_moon_sisters | production-nouns | 112/114 | 0/6 | 3 |
| inkgallery_sewers | production | 16/99 | 3/4 | 0 |
| inkgallery_sewers | production-nouns | 0/99 | 3/3 | 0 |
| **all** | production | 218/303 | 3/16 | 1 |
| **all** | production-nouns | 200/303 | 3/15 | 8 |

## Checks whose failure count differs

| Dataset | Line | Gender | Check | production fails | production-nouns fails |
|---|---|---|---|---:|---:|
| inkgallery_beholder | 100_INITIAL_0_SAY_0 | female | dead magic preserved | 0 | 1 |
| inkgallery_beholder | 100_INITIAL_0_SAY_0 | male | dead magic preserved | 0 | 1 |
| inkgallery_sewers | 100_BLOCK_0_ELEMENT_0_SAY_1 | male | Jans cousin stays female | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_0_ELEMENT_0_SAY_1 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_3 | male | male original leader | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_3 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_4 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_5 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_6 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_7 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_8 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_REPLY_9 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_SAY_2 | male | both prices retained | 2 | 3 |
| inkgallery_sewers | 100_BLOCK_1_ELEMENT_0_SAY_2 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_INITIAL_0_SAY_0 | male | narrated adventurer stays male | 2 | 3 |
| inkgallery_sewers | 100_INITIAL_0_SAY_0 | male | no untranslated Latin text outside engine tokens | 2 | 3 |
| inkgallery_sewers | 100_INITIAL_0_SAY_0 | male | worms remain creatures | 2 | 3 |
| inkgallery_sewers | 101_INITIAL_0_SAY_10 | male | no untranslated Latin text outside engine tokens | 2 | 3 |

## Manual review

Pending: compare the female outputs.csv rows of both prompts per dataset.
