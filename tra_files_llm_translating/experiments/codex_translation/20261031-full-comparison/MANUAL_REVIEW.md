# Assistant assessment of the complete Codex comparison

All 96 planned dialogue pairs were attempted exactly once: two models, two
methods, eight datasets, three repeats. All 144 CLI calls completed successfully.
94 dialogue pairs passed structural validation; two Luna simultaneous replies
were rejected for added/dropped quotation marks. Neither was retried. The first
launcher stopped on the first rejection; an archived explicit coordinator
continued only unattempted cases under the same frozen inputs and runtime.
Canonical state is COMPARISON.json, not results/manifest.json (initial launcher).

## Assessment

**GPT-6.1 Sol generating both genders together is the strongest candidate in this
suite.** All 24 pairs passed structural validation; frozen checks score 1014/1020.
Its six failed checks are assistant-adjudicated false alarms: valid neutral
Тебя ранили and valid paraphrases of dead magic. No definite gender/meaning
error was found in this condition in the reviewed sample. Named-faction
terminology and Russian numeric typography still need editorial agreement.
This is not a claim of universal reliability or human-approved translations.

Sol two-pass scores 1002/1020. Its female pass incorrectly changed him to her in
two multiple-NPC repeats and copied male-source details into distinct female
sources in two original-female-variant repeats. Eight of its 18 failed checks
are the same kind of neutral-phrase/dead-magic false alarms. See
SOL_FAILED_CHECK_REVIEW.csv: all 24 failed Sol checks across the two conditions
are individually adjudicated. Frozen checks and original scores remain unchanged.

Luna is faster but showed substantive errors in both methods: unresolved
recipient genders following Player1 gender, missed feminine nouns, mixed-script
Кормирa, improper shared-speaker forms, male/female source contamination, a
female pass reversing 3500/3000 fee logic, and a female simultaneous reply
turning a male third-person story protagonist into a woman. Added/dropped quote
marks also caused two structural rejections. Valid pairs alone scored 876/900
for simultaneous versus 986/1020 for two-pass; all-attempted simultaneous scores
876/1020 because rejected pairs fail all expected checks. Do not compare the
all-attempted totals without accounting for this validation difference.

## Timing and usage

Cumulative CLI call time (not total wall-clock turnaround or API pricing):
Luna both 160.244 s, Luna two-pass 232.247 s, Sol both 283.179 s,
Sol two-pass 360.172 s. Simultaneous needs 24 calls per model; two-pass needs 48.
Sol both took about 11.8 s per complete dialogue pair on average, versus 15.0 s
for Sol two-pass. Input counts include CLI scaffolding: roughly 391k vs 763k
for Sol both versus two-pass. These are token observations, not a calculation
of subscription credits; no exact billing claim is made. Default model effort
was used and may differ between models, so this is a workflow comparison.

## Review scope and limits

Assistant read every distinct raw male/female line pair in REVIEW_UNIQUE.csv:
371 unique pairs covering all 840 source-row occurrences (including repeated
TRA entries and repeated outputs). Both rejected replies are included in raw
review. Per-pair notes are in ASSISTANT_REVIEW.csv and keyed annotations are in
ASSISTANT_ANNOTATIONS.json. Identical texts may occur in multiple model/method/
repeat configurations; annotations apply to all listed occurrences. Reused
TRA rows are not independent linguistic samples.

Review labels distinguish definite errors from wording, terminology, numeric
formatting and other review suggestions. In particular the awkward Luna @48
conditional is marked for semantic review rather than treated as a proved
negation reversal. Gendered professional titles such as лидер are flagged for
review, not declared universally ungrammatical for a female referent. Counts
of these labels must not be read as independent wrong-cell counts.

All source/runtime hashes still match the pre-run snapshot; every CLI response
and successful-turn event is present and no tool activity was observed. See
INTEGRITY.json. Raw replies, prompts, references and production behavior remain
unchanged. Human review/approval is pending. This run does not measure automatic
verifier correction or independent human-gold accuracy. The initial pilot is
excluded from this full comparison.

## Next decision

Review Sol's simultaneous output before choosing a production backend. The
single-request male/female approach is supported by this suite, while the
extra female-edit pass did not improve Sol here and introduced source/third-
person errors. No production adoption, prompt change, evaluator change, new
inference or commit is made by this assessment.
