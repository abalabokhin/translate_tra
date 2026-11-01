# Sol subscription translation capacity — 2026-10-31

The user asked how much text GPT-6.1 Sol can translate within a subscription's
five-hour window, rather than asking for API-dollar pricing. The account is
authenticated through ChatGPT; its specific subscription tier and remaining
allowance have not been measured here.

## Measured workload

The [full comparison](codex_translation/20261031-full-comparison/SUMMARY.md)
contains 24 Sol simultaneous requests: eight dialogues, three repeats, with both
complete Russian gender versions returned in each request.

| Observation | Value |
| --- | ---: |
| English source words across eight dialogues, counted once | 911 |
| English source characters, counted once | 4,865 |
| Source rows, including repeated TRA entries | 70 |
| Average English words per dialogue | 113.875 |
| Average English characters per dialogue | 608.125 |
| Total reported input tokens across 24 requests | 390,647 |
| Total cached input tokens (subset of input) | 12,544 |
| Total output tokens | 12,710 |
| Total reported reasoning output tokens | 1,338 |
| Average reported input tokens per request | 16,276.96 |
| Average reported output tokens per request | 529.58 |
| Average CLI duration per complete dialogue pair | 11.80 s |

Word/character counts use English_Male once per source row; original female
variants are supplied where present. Both Russian genders are output from the
same request. Cached input is not added again to total input. CLI token counts
include scaffolding and schema/instructions, not only the English source.

## What the subscription documentation establishes

At the documentation check, OpenAI estimated 15–160 local Sol messages per
five-hour period for Plus and Standard Business. These are task-dependent
estimates, not fixed message entitlements. Pro was documented as having no
five-hour limit; other limits still apply. Usage can be shared with other Codex
work and weekly limits may apply. Account-specific limits/reset times should
be checked in the usage dashboard or CLI `/status`.

Source: [official pricing and usage documentation](https://learn.chatgpt.com/docs/pricing).
These statements are dated observations, not a guarantee of future limits.

## Rough orientation, not measured capacity

If a workload could fit 15–160 requests of our average size into a window,
the arithmetic would be about **1,700–18,200 English source words**, producing
both Russian versions. This is only a conversion of the published broad message
range to our sample size. It does not establish that this account can translate
that volume, and must not be quoted as a measured or guaranteed capacity estimate.
Longer dialogues, output length, caching, reasoning and other account activity
can change consumption. Do not substitute API prices or purchased-credit rates
for included subscription usage.

We did not capture the remaining allowance before the completed comparison.
Consequently, its token totals do not establish the percentage of a five-hour
budget consumed or how much remains. We also did not identify the user's plan,
retrieve account quota, purchase credits or run additional inference for this
capacity question.

## Next measurement

Record remaining five-hour and weekly allowance, plan, model and speed mode;
translate a representative batch with Sol/both under otherwise quiet account
activity; then record the allowance change without crossing a reset. If a batch
of W source words consumes p percent of a full window, W × 100 / p gives an
empirical full-window estimate for similar requests. Small rounded percentages
give noisy estimates. Measure larger representative batches before extrapolating
to an entire mod. This measurement is proposed, not yet performed.

The official app-server protocol also documents read-only
`account/rateLimits/read` for a future quota-aware test harness; it has not been
integrated into the runner. See [app-server documentation](https://learn.chatgpt.com/docs/app-server).
