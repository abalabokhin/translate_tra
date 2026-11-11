# Prompt A/B: female-pass noun rule

Status: interrupted_by_daemon_restart. Started 2026-10-29T22:01:51.667044+00:00, finished 2026-10-29T22:27:11.393916+00:00.
Model `mistral-small3.2:24b`, think default, ctx native, 3 repeats, full dialogues.

Rule added to the female-pass instruction in `production-nouns`: "This includes every noun, adjective and participle that refers to Player1, not only verbs, e.g. гость → гостья, герой → героиня, чужак → чужачка, уставший → уставшая."

Checks are targeted assertions, not overall quality. Wording flags (male/female differences outside listed gender edits) should not rise: the rule must not cause unrelated rewrites.

| Dataset | Prompt | Checks | Rejected / requests | Wording flags |
|---|---|---:|---:|---:|
| **all** | production | 0/0 | 0/0 | 0 |
| **all** | production-nouns | 0/0 | 0/0 | 0 |

## Checks whose failure count differs

| Dataset | Line | Gender | Check | production fails | production-nouns fails |
|---|---|---|---|---:|---:|
| - | | | | | |

## Manual review

Pending: compare the female outputs.csv rows of both prompts per dataset.

Interrupted after one saved male reply; no full dataset completed. See RECOVERY.json in prompt_ab/20261029-220151-recovered for the fresh continuation.
