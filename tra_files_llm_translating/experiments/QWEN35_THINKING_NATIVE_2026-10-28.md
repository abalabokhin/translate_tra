# Qwen3.5 9B — native-context thinking rerun

All 30 requests completed at the installed native context of 262144. None hit a
length limit. The 8192-context exhaustion was avoided, but translation quality
and instruction-following remain unreliable. No production settings changed.

| Configuration | Checks /660 | Complete pairs /15 | Actual requests | Rejected | Request seconds | Generated tokens |
|---|---:|---:|---:|---:|---:|---:|
| Thinking off, 8192 | 523 | 11 | 30 | 4 | 91.43 | 4390 |
| Thinking on, 8192 | 65 | 1 | 19 | 14 | 2232.00 | 131929 |
| Thinking on, 262144 | 587 | 12 | 30 | 3 | 4358.28 | 255895 |

Eleven female requests were skipped after male failures in the old 8192 thinking
run. New run: all 30 end with `stop`; all five observed placements were 100% GPU,
about 14 GB. The GPU has 16 GiB VRAM. The exact installed model digest is retained
in the JSON companion. Request times exclude delays outside inference. Native
thinking takes 47.67 times the request wall time of the thinking-off baseline.

## Method

The user requested this exact rerun. Same five datasets, full dialogues, production
prompt, three repeats, model-default sampling, no seed, `think:true`,
`num_predict:-1`. No output cap, timeout, budget, splitting, retries or repair.
Only context changes relative to the old thinking run. Frozen runtime/input hashes
match the prior comparison. Male prompts and schema were checked against the
thinking-off requests. Female input naturally contains each run's own male draft.
No reference translations were supplied to the model.

| Dataset | Native-thinking checks |
|---|---:|
| InkGallery | 267/270 |
| Ambiguous addressees | 62/66 |
| Multiple NPCs | 123/132 |
| Original female source variants | 45/90 |
| Reused strings | 90/102 |

## Manual review

All male/female replies and repeats, including three rejected replies, were read.
Representative failures:

- Female InkGallery greeting retains `авантюрист` or `приключенец` in two repeats.
  The latter escapes the frozen noun regex. Third repeat correctly uses странница,
  but seen all my books becomes прочитал/прочитала, changing meaning.
- Multiple-NPC female repeats 2/3 change narrated `him` from его to её. The gender
  of this third person should stay male. Repeat 2 also produces `Ты спас её,
  путница`: feminine noun with masculine verb after 14357 generated tokens.
- All female original-variant replies copy `Дверь открыта` into an explicitly empty
  female source. They reject; other correctly translated lines are not salvaged.
  Repeat 2 also writes `Я принела бронзовый ключ` instead of принесла.
- All male reused readiness strings are incompatible with one of the two speakers:
  Я готова (repeat 1) or Я готов (repeats 2/3). Female Я готова fits both speakers;
  the frozen readiness check is overly strict in this female pass.
- Addressee repeat 1 has `Поток слишком сильное`; female pass corrects the adjective
  despite instructions to preserve unrelated wording. Repeat 3 ferryman becomes
  проводник, an unchecked meaning error. Some rope-until-secure wording is weak.
- Awkward Russian such as заплатив плату and научусь по всем этим книгам persists.

Scores count targeted assertions, not overall translation accuracy. Narrow
promise/current/injury regexes reject plausible alternatives; noun, narrated-pronoun
and meaning checks miss genuine errors. Fixtures are small, partially synthetic,
not independently reviewed gold data. Sampling is not seed-controlled. Both
thinking and context change relative to thinking off: improvements cannot be
attributed solely to one. No native-context thinking-off control was run.

The larger context made this run complete, and the pooled score rose by 64 checks
(9.70 percentage points) versus thinking off. This is not evidence that gender,
fidelity or export reliability is solved. The model is not approved for unattended
export. Other already downloaded thinking models were subsequently authorized;
see [the plan](THINKING_NATIVE_PLAN_2026-10-28.md).

## Artifacts

[Portable metrics and metadata](QWEN35_THINKING_NATIVE_2026-10-28.json).
Raw local, Git-ignored root:
`results/thinking-native-20261028-094842/`: manifest, pre-run plan, driver, source
snapshots, hashes, per-request raw reasoning and answers, summaries, CSVs,
three-way comparison metrics/analyzer and manual review notes. No new tests were
needed for an inference-only rerun; production code and evaluator are unchanged.
