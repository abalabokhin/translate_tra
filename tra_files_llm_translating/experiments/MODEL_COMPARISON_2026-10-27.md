# Installed-model comparison — 2026-10-27

Qwen2.5:14b has a modest diagnostic advantage over Qwen3.5:9b under the tested
settings, especially on the new multi-NPC fixture and copying unchanged wording.
Neither is reliable enough for unattended translation. Both fail the shared-gender
string and the explicitly empty female source. No production model was changed.

## Method and reproducibility

- Ollama 0.40.11; run 2026-10-27 22:13:23–22:17:26 UTC.
- Models: installed `qwen3.5:9b` (9B Q4_K_M) and `qwen2.5:14b` (14.8B Q4_K_M).
  No downloads, fine-tunes or abliterated models were used.
- Production prompt, full dialogue, model-default sampling, no fixed seed,
  three repeats, male translation followed by a female edit.
- Qwen3.5 thinking explicitly off. Qwen2.5 has no thinking capability and receives
  no explicit thinking setting (`--think default`). This is not a thinking-on test.
- Context explicitly 8192 for both, consistent with the baseline pilot. This is
  smaller than their model-native production defaults. No generation-token cap,
  client timeout, retries, repair pass or automatic splitting.
- One archived game-text sample (InkGallery v2, 12 rows) and four synthetic
  fixtures (22 rows). The synthetic fixtures had not been sent to a translation
  model before this comparison. They target known failures and are not an
  independently curated blind corpus. References and review notes are withheld
  from every model request. Production does not receive hand-labelled addressees.
- Fixed evaluation throughout: `inkgallery-v2` and the four fixture `*-v1` files.
  No regexes or prompts were adjusted in response to these results. The previous
  pilot's v1 scores have a different denominator and are not directly comparable.
- Sixty actual requests, thirty per model; all finished with `done_reason=stop`.
  Seven replies failed structural validation, with no transport failures or
  skipped passes. Failed whole replies count as failures of all their expected
  checks, even if some individual lines are usable. No partial translation export
  is treated as successful.
- Both models reported 100% GPU placement at the first request of every dataset.
  Qwen3.5 reported approximately 5.86 GB resident; Qwen2.5 approximately 10.43 GB.
  The models were run sequentially, all five datasets on Qwen3.5 first, then all
  five on Qwen2.5. Ordering, first-load cost and hardware state are not randomized.
- Sampling is **model-default**, not identical numerical sampling. Qwen3.5's
  `/api/show` parameters list temperature 1, top_k 20, top_p 0.95 and
  presence_penalty 1.5. Qwen2.5's show response provides no parameters field, so
  it uses server/model defaults not established numerically here. These are
  practical configuration results, not a controlled claim about architecture or
  parameter count alone.

The run used evaluation changes uncommitted on top of `f01ac30`. Exact commands,
model digests and metadata, source-file SHA-256 values, the working-tree diff,
code/input snapshots, and the driver are saved with the raw results:

[results/comparison-20261027-221323/manifest.json](results/comparison-20261027-221323/manifest.json)

The manifest contains the command for each dataset/model. Equivalently, from the
repository root, repeat this command for each of the five checks files, then run
it for Qwen2.5 with `--think default` and a fresh output folder:

```bash
python3 -u tra_files_llm_translating/experiments/diagnose_translation.py \
  --models qwen3.5:9b \
  --checks tra_files_llm_translating/experiments/fixtures/multiple_npcs/checks.json \
  --prompts production --scopes full --think off --temperatures default \
  --repeats 3 --num-ctx 8192 --out <fresh-model-and-dataset-folder>
```

## Expected-form scores

Percentages measure the configured checks, not overall translation accuracy.
There are 660 expected checks per model over the same source lines and repeats.

| Dataset | Qwen3.5:9b | Qwen2.5:14b |
|---|---:|---:|
| InkGallery v2 | 234/270 (86.67%) | 226/270 (83.70%) |
| Ambiguous addressees | 53/66 (80.30%) | 56/66 (84.85%) |
| Multiple NPCs | 112/132 (84.85%) | 127/132 (96.21%) |
| Original female variants | 42/90 (46.67%) | 42/90 (46.67%) |
| Reused strings | 82/102 (80.39%) | 90/102 (88.24%) |
| All checks pooled | **523/660 (79.24%)** | **541/660 (81.97%)** |
| Mean of the five dataset percentages | **75.78%** | **79.93%** |
| New synthetic fixtures only, pooled | 289/390 (74.10%) | 315/390 (80.77%) |

The pooled advantage is 18 checks, or 2.73 percentage points. Equal weighting of
datasets gives a 4.16 percentage-point advantage (rounded independently in the
table). Qwen2.5 loses on the original InkGallery sample and wins three new
fixtures; the original-female fixture ties. Three repeats on five small dialogues
provide limited evidence of generalization. Repeated rows and related checks are
not independent observations, so no statistical significance claim is made.

## Structural reliability, wording and time

| Metric | Qwen3.5:9b | Qwen2.5:14b |
|---|---:|---:|
| Structurally rejected replies / actual requests | 4/30 | 3/30 |
| Dialogue pairs with both replies valid | 11/15 | 12/15 |
| Pair wording checks passing | 58/82 evaluable | 85/87 evaluable |
| Unlisted wording changes requiring review | 24 | 2 |
| Wording pairs unavailable after rejection | 8 | 3 |
| Wording comparisons not applicable: different original female source | 12 | 12 |
| Sum of request wall times | 91.43 s | 133.85 s |
| Median seconds per request | 2.305 s | 3.010 s |

Wording diagnostics are separate from the scores and winner selection. Each model
has 102 line-pair entries including repeated TRA rows; known original source
variants are excluded from wording comparison. An unchanged but wrong gender form
passes this diagnostic, as the examples below demonstrate. The time totals include
first-load effects and roughly equivalent workloads; Qwen2.5 took about 46% more
request wall time. They are not pure token-generation throughput measurements.

## Manual reading

Reviewed all valid translations in the thirty male/female dialogue pairs, plus
all seven rejected female replies. Examples below refer to the saved raw outputs;
no text was edited or salvaged for the automated scores.

### InkGallery

Qwen3.5's female pass makes substantial unrequested rewrites and sometimes changes
meaning. In repeat 3, @100 changes “seen” (`видел`) to “read” (`прочитала`); @16/@18
rename Ink Gallery to `Галерея Крови`; Cormyr becomes `Кормаир`. Repeat 2 invents
`Галерея Инк`. Its @48 idiom is still literal `как я делаю` in two male replies.
Some female replies retain masculine agreement. Formal address occurs too.

Qwen2.5 copies unaffected wording consistently across all three repeats. However,
two repeats use formal `вы` across much of the conversation, repeat 2 invents
`Галерея Инков` and `Терновыми Магами`, and repeat 3's @48 ends with the awkward
`узнать как я?`. Its phrase-level consistency does not make the underlying
translation faithful or idiomatic. Its best repeat scores 44/45 in both passes,
but still needs editing.

### Multiple NPCs

Qwen2.5 handles more of the speaker/listener structure, explaining its largest
score advantage. Both models still fail @105 (“You saved her, traveler. I owe
you my life.”). In Qwen2.5 repeat 1, male Orin says `Я тебе жизнью обязана`, which
remains feminine in both player versions. In repeats 1 and 2 the female Player1
is still addressed with masculine `спас` and `странник`/`путник`. In repeat 3 the
male version incorrectly has `спасла`; the female version scores a perfect 22/22
while still retaining masculine `путник`. That noun is not covered by this
fixture's current gender regex. Meaning is also weakened in @102 (blaming him
becomes merely drawing conclusions) and @106 (dawn becomes morning in repeat 2).

Qwen3.5 mixes speaker and player gender more often: male Player1 says `Я обещала`
in repeat 1, and the female pass retains masculine `спас` in @105 in all three
repeats. Male Orin says `укорила` in one male reply; the female edit then repairs
that gender but also changes the verb. Some @104 “worried”/“injured” regex misses
are narrow-check failures, not incorrect Russian: `боялась` and `переживала` are
valid feminine alternatives to `волновалась`, and `ранили тебя?` avoids gender.
The fixed score table was not altered to accept these after seeing the outputs.

### Ambiguous addressees

Qwen3.5 inserts a new `<NAME>` token in the first female reply, replacing Bram;
validation rejects the whole reply. Other repeats turn ferryman into a passenger
or water spirit, or use feminine plural `обе` for Bram and Selene. There are case
and agreement errors such as `Тобой нужно оставаться` and `но Селене нет`.
Its `Поток слишком силен` is a reasonable alternative that the narrow `течение`
regex flags; that is an evaluator limitation rather than proof of model error.

Qwen2.5 has no structural rejection here but leaves mixed-script `Фerryman` in
all three repeats. One male reply contains `不见。Bram和Selene都在对岸。`; its female
edit still mixes English names and Chinese text. This happens to be detected by
the Latin/name checks, but a wholly Chinese mistranslation could escape the
current Latin-only diagnostic. Other lines confuse “I can hear you” with “you
can hear me” or produce bad case agreement. Singular/plural listener choices are
not scored as errors where the English legitimately allows either.

### Reused strings

Both models choose `Я готова` for the single TRA string shared by Selene and
Player1 in every repeat. It cannot serve male Player1, even though it is correct
for Selene. The female passes keep it identical. Shared-string merging guarantees
one exported string; it does not guarantee compatibility with every speaker.
The pair-stability check passes, while the explicit shared-gender checks fail.

Qwen3.5 turns gate into `шлюз` in two repeats. Qwen2.5 preserves `ворота`, but uses
formal plural/polite imperatives `Дождитесь` and `Не трогайте` for singular Player1
in two repeats. The existing pronoun-based ты/вы check misses those imperatives.
Tokens, stage markers and the actual newline survive all these requests.

### Original female source variants

Both models fail the explicitly empty female line in all three repeats, copying
`Дверь открыта` instead of returning an empty string. Thus all six female replies
are structurally rejected and every expected female check fails. Their nonempty
female-source lines sometimes preserve changed meanings (his/her mentor,
duke/duchess, silver/bronze), but the raw replies also contain errors such as
`Я был её ученицей`, `Герцогня`, `Душе́фа` or `бронзовую ключ`. Qwen2.5 also emits
mixed-script `Дuke` in one male reply. These partial successes are not valid
whole-dialogue exports and were not counted as such.

## Decision and next experiment

Qwen2.5 is the better candidate for a further trial of this production/default
configuration: it follows the copy-only female-edit instruction more consistently
and performs better on the new NPC-role cases. It is slower and still produces
serious language, meaning and gender errors. This evidence does not justify an
automatic production model switch or unattended export.

A useful next controlled experiment is Qwen3.5 with thinking **on**, using the same
frozen checks, fixtures, production prompt, sampling and context. Compare the
quality improvement, structural failures and time against this thinking-off run.
That experiment was subsequently run without a thinking budget; see
[THINKING_BASELINE_2026-10-27.md](THINKING_BASELINE_2026-10-27.md) for the severe
completion/latency failures at the same context setting. Before any deployment decision, also use genuine
unseen mod dialogues and an independent Russian-language review if available.
Future evaluator revisions should consider the observed synonym false positives,
masculine address nouns, formal imperatives and non-Latin foreign text; do not
silently change the frozen scores in this report.

## Artifacts

The raw results directory is Git-ignored and local to this workspace. This report
is a portable summary; raw links may be absent in another checkout. Each dataset
folder contains `summary.md`, `outputs.csv`, `pair_reviews.csv` and `runs.jsonl`.

- [Qwen3.5 / InkGallery](results/comparison-20261027-221323/qwen35/inkgallery/summary.md)
- [Qwen2.5 / InkGallery](results/comparison-20261027-221323/qwen25/inkgallery/summary.md)
- [Qwen3.5 / ambiguous addressees](results/comparison-20261027-221323/qwen35/ambiguous_addressees/summary.md)
- [Qwen2.5 / ambiguous addressees](results/comparison-20261027-221323/qwen25/ambiguous_addressees/summary.md)
- [Qwen3.5 / multiple NPCs](results/comparison-20261027-221323/qwen35/multiple_npcs/summary.md)
- [Qwen2.5 / multiple NPCs](results/comparison-20261027-221323/qwen25/multiple_npcs/summary.md)
- [Qwen3.5 / original female variants](results/comparison-20261027-221323/qwen35/original_female_variants/summary.md)
- [Qwen2.5 / original female variants](results/comparison-20261027-221323/qwen25/original_female_variants/summary.md)
- [Qwen3.5 / reused strings](results/comparison-20261027-221323/qwen35/reused_strings/summary.md)
- [Qwen2.5 / reused strings](results/comparison-20261027-221323/qwen25/reused_strings/summary.md)
