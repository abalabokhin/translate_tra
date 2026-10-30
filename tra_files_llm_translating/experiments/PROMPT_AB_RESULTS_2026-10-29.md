# Prompt A/B results — 2026-10-29

## Original five datasets — complete

[Report](prompt_ab/20261029-212402/REPORT.md),
[manual review](prompt_ab/20261029-212402/MANUAL_REVIEW.md),
[audit](prompt_ab/20261029-212402/AUDIT.json), and raw outputs in the same folder.

| Prompt | Checks | Rejected replies | Wording flags |
|---|---:|---:|---:|
| production | 703/717 | 0/30 | 0 |
| production-nouns | 704/717 | 0/30 | 0 |

Mistral Small3.2 24B, native context 131072, uncapped generation, model-default
sampling, full graphs, three repeats. All 60 actual requests are structurally valid;
no thinking output. Same male prompts and input hashes verified. Total request time
2249.58 s; observed placement 50.9% GPU, with CPU offload. Timing is not comparable
to the earlier smaller-context/full-GPU results. Model digest/settings are preserved.

**Decision for this set: do not adopt the added noun rule.** Both variants miss
`приключенец` in all three female InkGallery repeats and `странник` in all three
female multiple-NPC repeats. The single-check gain is a verb, with no noun benefit.
Male drafts are independently sampled; minor male differences are not caused by a
rule that only changes the female prompt. Three repeats cannot establish a small
stochastic gain as a causal improvement.

All six explicit-empty female cases now export empty and the whole source-variant
fixture passes. Mixed-gender shared readiness still fails in all six male drafts
across the two prompts, including a `готов(а)` placeholder. Grammar and register
errors remain outside the checks (see manual review). No unattended export approved.

## Fresh InkGallery extension — partial results, serving interruption

Three new encounters (36 rows), references/checks written and reviewed by the
assistant before inference under the user's instruction; human review pending.
[Run report](prompt_ab/20261029-220151-recovered/REPORT.md). Same model/settings/repeat count,
36 scheduled logical reply slots. Results are separate from the frozen five-set
comparison. The reference freeze is in REAL_SET_PREINFERENCE_2026-10-29.json.

| Completed encounter | production | production-nouns |
|---|---:|---:|
| Beholder | 90/90 | 88/90 |
| Moon Sisters | 112/114 | 112/114 |

All 24 logical replies for these two encounters were reviewed. The Beholder
two-check difference is likely a frozen-check false positive on dead-magic
wording. Both Moon Sisters prompts actually miss the female real-self adjective
in every repeat; the checks miss the истинного wording. In Beholder, three female
replies incorrectly assume the selected party member must be female. These totals
are targeted assertions, not overall translation accuracy. No adoption is justified.

Sewers has one valid male reply. The first female request stalled saving prompt
cache and ended after 27271.85 seconds when serving restarted. Five subsequent
male connections were refused; their female passes skipped. Preserve these as
infrastructure failures. The guarded agent recovery script performed no restart
because serving state had already changed. See the run's RUNTIME_DIAGNOSTICS.json
and SERVING_LOG_2026-10-30.txt for evidence and user-approved recovery decision.

Ten calls for those five unsubmitted configurations are queued after the active
translate + verify experiment. The interrupted production repeat-1 female stays
a serving failure; it is not resubmitted. See
[continuation state](AB_TRANSPORT_CONTINUATION_QUEUE_2026-10-30.json).

[Detailed finished-dialogue review](review/20261029/FINISHED_DIALOGUE_REVIEW_2026-10-30.md)
and [annotated translations / complete proposed lines](review/20261029/ASSISTANT_REVIEW_2026-10-30.csv)
are ready. Human approval is pending; editorial proposals have not been applied.

All artifacts are saved outside ignored results/. Do not commit until the user
reviews everything and explicitly asks. No production prompt/model change made.
