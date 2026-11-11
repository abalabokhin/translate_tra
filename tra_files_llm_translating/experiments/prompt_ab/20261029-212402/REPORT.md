# Prompt A/B: female-pass noun rule

Status: finished. Started 2026-10-29T21:24:02.181112+00:00, finished 2026-10-29T22:01:48.487532+00:00.
Model `mistral-small3.2:24b`, think default, ctx native, 3 repeats, full dialogues.

Rule added to the female-pass instruction in `production-nouns`: "This includes every noun, adjective and participle that refers to Player1, not only verbs, e.g. гость → гостья, герой → героиня, чужак → чужачка, уставший → уставшая."

Checks are targeted assertions, not overall quality. Wording flags (male/female differences outside listed gender edits) should not rise: the rule must not cause unrelated rewrites.

| Dataset | Prompt | Checks | Rejected / requests | Wording flags |
|---|---|---:|---:|---:|
| inkgallery | production | 265/270 | 0/6 | 0 |
| inkgallery | production-nouns | 266/270 | 0/6 | 0 |
| ambiguous_addressees | production | 90/90 | 0/6 | 0 |
| ambiguous_addressees | production-nouns | 90/90 | 0/6 | 0 |
| multiple_npcs | production | 147/150 | 0/6 | 0 |
| multiple_npcs | production-nouns | 147/150 | 0/6 | 0 |
| original_female_variants | production | 105/105 | 0/6 | 0 |
| original_female_variants | production-nouns | 105/105 | 0/6 | 0 |
| reused_strings | production | 96/102 | 0/6 | 6 |
| reused_strings | production-nouns | 96/102 | 0/6 | 6 |
| **all** | production | 703/717 | 0/30 | 6 |
| **all** | production-nouns | 704/717 | 0/30 | 6 |

## Checks whose failure count differs

| Dataset | Line | Gender | Check | production fails | production-nouns fails |
|---|---|---|---|---:|---:|
| inkgallery | @48 | female | masculine verb for female Player1 | 2 | 1 |

## Manual review

Completed by the assistant; see [line-by-line findings](MANUAL_REVIEW.md) and
[request/input audit](AUDIT.json). Human review remains pending.

Production: 703/717. Noun rule: 704/717. Neither fixes the feminine address nouns
in any of the six target repeats per prompt. The single-check gain is a verb.
Do not adopt the rule on this evidence. Empty female sources are handled correctly;
neutral wording for mixed-gender shared strings remains unreliable. All raw replies,
translations, runtime/input snapshots and diagnostic flags are retained.

No commit is authorized until user review and a later explicit request.
