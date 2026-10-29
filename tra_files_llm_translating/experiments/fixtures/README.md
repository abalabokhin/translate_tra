# Synthetic dialogue evaluation fixtures

These four small dialogues were authored on 2026-10-27 after the InkGallery pilot.
They were not used in its prompt examples. They were first sent to translation
models in the subsequent [two-model comparison](../MODEL_COMPARISON_2026-10-27.md). They are synthetic diagnostic cases, not extracted game content or an
independently curated benchmark. References and review notes were checked by the
same assistant that authored them. See [evaluation design](../EVALUATION.md) for
scoring rules and limitations.

| Fixture | Rows / distinct TRA keys | Primary coverage |
|---|---:|---|
| [multiple_npcs](multiple_npcs/input.csv) | 6 / 6 | Male/female NPCs speaking to each other and Player1; third-person gender; name and location preservation. |
| [ambiguous_addressees](ambiguous_addressees/input.csv) | 5 / 5 | Blank listener facts, alternative predecessors, ambiguous singular/group address; avoid inventing gender. |
| [reused_strings](reused_strings/input.csv) | 6 / 4 | Same string used by female NPC and Player1; repeated replies; merged graph; stage directions, engine tokens, actual newline. |
| [original_female_variants](original_female_variants/input.csv) | 5 / 5 | Female English changes mentor/patron gender and key material; explicit empty female literal; fallback when absent. |

Each folder contains `input.csv`, `checks.json`, and `reference.csv`. Shared actor
facts are in [actors.csv](actors.csv). The reference CSV supplies illustrative
Russian variants and line-by-line `Review_Notes`. It is used by tests and readers,
never loaded into a model request. Alternative faithful Russian is acceptable.

The checks are at `-v2` since 2026-10-29: they were revised after the manual reviews
of the model runs ([Evaluation v3](../EVALUATION.md#evaluation-v3-2026-10-29)). The
references also serve as correct text in the translate + verify planted-error test
([verify_mutations.json](../verify_mutations.json)). These fixtures are synthetic;
person-reviewed real dialogues belong in [real_set](../real_set/README.md).

## Manual review rubric

For each output pair, read the English and follow the incoming alternatives.
Score each category as acceptable, needs editing, or uncertain, with a short
reason. Do not collapse uncertainty into an automatic failure or gender guess.

1. **Meaning and completeness:** every proposition, condition, negation, name,
   material, place, and singular/plural distinction survives. No invented kitchen,
   extra motive, missing sentence, or changed group.
2. **Russian:** idiomatic phrasing, agreement, case, punctuation, and character
   voice. A regex match alone cannot establish these.
3. **Roles:** first person follows the speaker; second person follows the actual
   listener where known; third persons keep their own gender. NPC genders stay
   fixed in both player passes. In ambiguous cases, accept natural neutral wording
   and discuss context-supported alternatives instead of requiring a guessed role.
4. **Pair stability:** use `pair_reviews.csv`; classify changed wording as required
   by gender, required by a different original female source, a correction of a
   male error, or an unrelated rewrite. A flag is a request to read, not a verdict.
5. **Engine structure and reuse:** tokens, line breaks, stage-direction markers,
   and repeated TRA strings survive. The ready string shared by Selene and Player1
   must suit both speakers; neutral `Можно начинать` is one option, not the only
   acceptable wording. Full-scope duplicate equality is enforced by merging.
6. **Original variants:** use the actual female English. Do not preserve male-only
   `silver`, `duke` or `his` when the female source says otherwise. An explicitly
   empty female source is intentionally empty. Check source metadata rather than
   treating it as a dropped translation.

Line-specific decisions, including alternative readings and fixed subjects, are
in each `reference.csv`. The ambiguous fixture deliberately has no universal
singular-ты check. Named NPC addressees may follow non-adjacent speakers: adjacency
alone is not sufficient evidence. All predecessor IDs are local and valid; merged
reuse can create cycles, just as in real repeated dialogue.

## Running later

A first live comparison of both installed models has now been completed; see
the linked report for scores, failures and manual reading. To inspect request counts
without contacting Ollama (repeat for each fixture):

```bash
python3 tra_files_llm_translating/experiments/diagnose_translation.py \
  --checks tra_files_llm_translating/experiments/fixtures/multiple_npcs/checks.json \
  --models qwen3.5:9b --prompts production --scopes full --think off \
  --temperatures default --repeats 3 --num-ctx 8192 --dry-run
```

When a live run is wanted, remove `--dry-run` and choose a **fresh, separate**
`--out` folder for each fixture/model/settings run. Use `--think default` for a
model that does not support thinking. The 8192 context is an explicit experimental
choice, not the production model-native default. The same configuration on all
four fixtures makes 24 requests (four dialogues × three repeats × two passes).
Do not concatenate disconnected dialogues into one CSV or mix their logs in one
results directory. Report each fixture's results separately before pooling checks:
longer dialogues and extra regexes otherwise receive greater weight.

The `reframed-addressee` variant has oracle listener information in known cases.
Merged uses with different listener labels omit that fact. It has no extra facts
for the ambiguous fixture. Never compare this oracle result as if production had
those labels available.

To verify all references, prompt construction, score populations and mock request
round trips without models:

```bash
python3 -m unittest discover -s tra_files_llm_translating/tests
```
