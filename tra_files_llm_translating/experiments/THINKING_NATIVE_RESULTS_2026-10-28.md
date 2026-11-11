# Native-context thinking model comparison

Status: completed. Updated: 2026-10-29T01:20:31.824470+00:00.

Same frozen five datasets, full dialogues, production prompt, three repeats, thinking on, model-default sampling, native context and uncapped generation. Targeted assertion scores are not overall translation accuracy. Every scheduled suite finished, including recorded failures.

| Model | Status | Context | Checks | Complete pairs | Rejected / requests | Request seconds |
|---|---|---:|---:|---:|---:|---:|
| qwen3.5:9b | completed | 262144 | 587/660 | 12 | 3/30 | 4358.28 |
| gemma4:12b | completed | 262144 | 592/660 | 12 | 3/30 | 1027.74 |
| qwen3:14b | completed | 40960 | 534/660 | 12 | 3/30 | 1002.91 |
| huihui_ai/qwen3.5-abliterated:9b | completed | 262144 | 460/660 | 8 | 7/28 | 10629.27 |
| huihui_ai/qwen3-abliterated:14b | completed | 40960 | 0/660 | 0 | 15/15 | 99.06 |

[Pre-run plan](THINKING_NATIVE_PLAN_2026-10-28.md). [Qwen3.5 three-way baseline comparison](QWEN35_THINKING_NATIVE_2026-10-28.md). [Portable metrics, exact digests, model metadata, frozen hashes and manual reviews](THINKING_NATIVE_RESULTS_2026-10-28.json).

All five scheduled suites finished, including failures. There were 150 request
records: 133 actual calls and 17 female passes skipped after failed male replies.
No additional models were downloaded. No production settings or prompts changed.
All returned translation texts, including rejected answer portions, were manually
reviewed; skipped female passes have no output to assess. All observed placements were 100% GPU.

Gemma4 had the strongest targeted score at 592/660 (89.70%) with 17m 08s of
request time. Qwen3.5 reached 587/660 (88.94%) but took 72m 38s. This does not
establish reliable translation or statistical superiority. Both retain gender
errors, and all four configurations that reached female source-variant requests
failed every explicit-empty-female case. None is approved for unattended export.

Huihui Qwen3's 0/660 is a JSON/protocol failure in this installed serving
configuration: all 15 male responses were rejected and all female passes skipped.
It is not a measured zero for linguistic ability, nor a usable test of female
translation quality. No runtime/template repair was attempted. Huihui Qwen3.5
completed with 7 rejected requests, including one full-context reasoning loop.

## Comparison with previous thinking-off baselines

| Model | Off at 8192 | On at native context | Check gain | Off request time | On request time |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 9B | 523/660 | 587/660 | +64 | 91.43 s | 4358.28 s |
| Gemma4 12B | 564/660 | 592/660 | +28 | 97.80 s | 1027.74 s |
| Qwen3 14B | 503/660 | 534/660 | +31 | 133.84 s | 1002.91 s |

Both context and thinking change in these comparisons. No native-context
thinking-off control or matched off baseline for the Huihui variants was run.
Male prompts, JSON schemas and model digests match the prior baselines. Female
requests naturally contain the corresponding model/repeat's own male draft.
The input/runtime hashes match across the native-context batches. No frozen
checks were changed, and no rejected rows were salvaged.

## Per-fixture checks

| Model | InkGallery /270 | Addressees /66 | Multiple NPCs /132 | Original female /90 | Reused /102 |
|---|---:|---:|---:|---:|---:|
| qwen3.5:9b | 267 | 62 | 123 | 45 | 90 |
| gemma4:12b | 267 | 60 | 130 | 45 | 90 |
| qwen3:14b | 225 | 66 | 106 | 41 | 96 |
| huihui_ai/qwen3.5-abliterated:9b | 214 | 54 | 121 | 43 | 28 |
| huihui_ai/qwen3-abliterated:14b | 0 | 0 | 0 | 0 | 0 |

## Completion and runtime findings

The standard Qwen3.5, Gemma4 and Qwen3 suites each completed 12/15 pairs, with
three female empty-source rejections and no length failures. Huihui Qwen3.5
completed 8/15 pairs from 28 actual requests, with 7 rejected replies and 2 female
passes skipped. Huihui Qwen3 completed no pairs; all 15 male calls rejected.

Huihui Qwen3.5's first addressee female edit consumed 870 prompt + 261274 generated
tokens = 262144, returning empty content after 6438.77 seconds (1h 47m). Two
self-check lines repeated over 6500 times each. The complete raw reasoning and
serving-log excerpts are archived. No timeout, cap, retry or intervention was
imposed; the suite advanced normally. The optional user choice to skip this
model was unanswered, so its originally authorized suite was completed unchanged.

The old Qwen3.5 8192 thinking baseline exhausted context on 14/19 actual calls.
Its new native-context run has no length failures. The Huihui loop shows that
native context can still be exhausted by a model repeating its reasoning.

## Manual review

Raw root: `results/thinking-native-20261028-094842` (Git-ignored).

Native-context thinking rerun: manual observations while running.

InkGallery repeat 1: both replies structurally valid, 89/90 frozen checks. Female @16 retains masculine авантюрист. Other gender edits are correct, including заглянул/заглянула, видел/видела, понял/поняла, хотел/хотела. Female preserves unaffected wording. Male @18 correctly addresses Velcealle in feminine. Both @16 sentences retained. Awkward заплатив плату and научусь по всем этим книгам remain. First @48 renders Unless as Или, weakening the original condition. Pair-review flag on хотел/хотела is a regex blind spot, not an inappropriate rewrite.

InkGallery repeat 2: female verbs handled, masculine noun приключенец retained; frozen noun regex misses this synonym (90/90 therefore not linguistically perfect). Both passes retain awkward научусь/учусь всем этим книгам, missing punctuation and weak/changed purpose question Или чтобы открыть... at @18. No inappropriate broad female rewrite observed.

InkGallery repeat 3: male @100 changes seen to прочитал; female copies meaning error as прочитала. Female correctly changes странник to странница, verbs заглянул/заглянула, хотел/хотела, понял/поняла. @18 fixed female NPC remains feminine. Awkward Стоит нам поговорить and Или... weaken source conditional. All 6 InkGallery replies valid; 267/270 frozen checks, no length failures; 995.95 request seconds.

Addressees repeat 1: male Поток слишком сильное is ungrammatical; female repairs to сильный though unrelated wording should be copied. Frozen current regex misses plausible поток synonym (but male grammar really wrong). Перевозчик can mean ferryman in context, less precise than паромщик. Plural Вы plausible for two possible listeners. Last line пока верёвка надёжно закреплена weakens until secure; should пока верёвка не будет надёжно закреплена. Both structurally valid, 20/22 checks.

Addressees repeat 2: plausible переправщик, correct течение, natural until rope secure. Adds уже not explicit in source. Ambiguous listener assigned masculine должен in both passes instead of neutral wording; not covered by checks. Repeat 3: ferryman becomes проводник, a meaning error missed by checks. Поток synonym causes regex failure despite grammatical силен. Last rope instruction is faithful and neutral. Female repeat 3 copies exactly. Dataset 62/66, all pairs valid.

Multiple NPCs repeat 1: correct fixed genders and female verbs, but female @105 keeps путник; this noun is not checked. пообещал/пообещала falsely rejected by promise regex. Male adds тебя to Orin waiting downstairs, plausible but absent source. Repeat 2 female takes 243.5 seconds/14357 tokens and introduces two substantive errors: @102 him changes from male его to female её, although narrated male stays male; @105 becomes Ты спас её, путница (noun corrected but verb left masculine). This is a regression from its correct male source, not a context-length failure.

Multiple NPCs repeat 3: male @104 тебя не ранило is an acceptable impersonal injury question; frozen gender regex falsely rejects it. Prefixed promises also false negatives. Female inspected separately below.

Multiple NPCs repeat 3 female: correct странница and спасла, fixed male NPC обязан retained. However @102 narrated him again changes его to её. This real error is not checked. Both injury and promise failures are regex limitations. Overall 123/132, all three pairs valid, but two female passes change a narrated male to female.

Original female variants: all male replies pass 15/15; all female replies reject because @404 should be empty but model copies Дверь открыта. Rejected replies handle his/her, duke/duchess and silver/bronze source changes. Repeat 2 female has grammatical invention принела instead of принесла. No salvaged scoring; rejected female replies remain 0/15. Third pair raw output reviewed separately. Dataset 45/90, zero complete pairs.

Reused strings all repeats: one readiness string cannot serve male player and female NPC when translated Я готов (repeats 2/3) or Я готова (repeat 1). Female passes use Я готова, appropriate when both speakers female; frozen check wrongly penalizes this. All outputs preserve stage markers, literal newline, <CHARNAME> and %gate_lock%, with no extra female wording changes. Repeat 1 drops Then in reply. Dataset 90/102. All 30 native-context requests stop normally; 3 female explicit-empty-source rejections.


Raw root: `results/thinking-native-remaining-20261028-214626` (Git-ignored).

# Manual review — native-context thinking models

## Gemma4 12B
All five datasets and all male/female repeats, including rejected replies, read.
592/660 checks, 3 rejected female empty-source replies, all 30 stop normally.
InkGallery: @16 female stays искатель приключений in all repeats. Female verb
edits otherwise consistent; fixed female Velcealle remains feminine. Cowled Wizards
varies wildly: Коулд-Визардами, Магами в капюшонах, Капюшонными магами; first is
particularly poor transliteration. @19 обучусь по всем этим книгам remains awkward.
Addressees: Брэм vs Брам is plausible and causes all six narrow name-check failures;
перевозчик plausible but less precise than паромщик. Plural address plausible for
two listeners; repeat 3 chooses masculine должен for an ambiguous listener.
Multiple NPCs: fixed genders and narrated его preserved. Repeat 1 female correctly
uses странница; repeats 2/3 retain masculine путник/странник in female @105.
Promise prefix пообещал/пообещала accounts for two false-negative checks.
Original variants: male correct; all rejected female replies handle original
patron/material changes but copy Дверь открыта into explicitly empty source.
Reused strings: all male Я готов conflicts with female NPC; female Я готова fits
both female speakers but frozen check is overly strict. Tokens, markers and
newlines retained; female wording otherwise stable. Not approved for export.

## Qwen3 14B
All five datasets and all repeats, including rejected replies, read.
534/660, three female empty-source rejections; no length failures.
InkGallery repeats 1/2 mostly use forbidden formal вы; repeat 3 misgenders female
Velcealle in male @18 (Ты сказал, что пришёл). Female repeat 3 corrects that fixed
NPC but leaves masculine хотел/зашёл/видел addressing female player elsewhere.
Female greeting stays приключенец/странник. Repeat 2 invents Галерея Сказок and
changes seen to прочитали. Cowled Wizards becomes Ковёрными Магами or Кованными
Волшебниками. Other awkward literal phrases remain.
Addressees repeat 2 ferryman becomes Водяной, a serious unchecked meaning error.
Rope secure becomes rope крепкой/надёжной rather than securely fastened.
Multiple NPCs: repeated formal address, female masculine traveler and verbs;
repeat 3 Орин, тебя ранен? is ungrammatical. его stays male in these outputs.
Original variants: brought key becomes привёл/привела ключ in repeats 1/2. Female
repeat 2 misses original duke-to-duchess change as well as empty source. All female
outputs reject for copying Дверь открыта. Wait becomes останусь in repeats 1/2.
Reused strings repeats 2/3 use Мы готовы for singular I am ready, earning perfect
readiness checks by changing meaning. Female repeat 2 changes plural to Я готова;
repeat 3 keeps plural. Repeat 1 male Я готов incompatible with female speaker.
Formal/plural imperatives and missing terminal punctuation persist. Engine tokens,
stage markers and literal newline retained. Not approved for export.

## Huihui Qwen3.5 abliterated 9B — review in progress
InkGallery all three pairs read, including rejected first female reply. First
female inserts Markdown emphasis inside заглян**ула**, changing protected star
counts and causing rejection; changes seen to видала (plausible), future learn to
past научилась (meaning drift). Repeat 2 invents Инк Галери and translates test
myself as отыграть себя; seen becomes перелистал/перелистала. Female masculine
странник remains. Repeat 3 corrects авантюристка but changes смогу to смогла,
turning a future possibility into a past event. Awkward С того, как я понял and
Так что это? retained. Cowled Wizards translated as Чародеи-Затворники in repeat 3,
a terminology invention needing review. First addressee male: ferryman becomes
водовоз, a clear meaning error; поток synonym narrowly rejected. Rope instruction
канат не закрепится sounds as if it fastens itself but retains until relation.

Operational issue: Huihui Qwen3.5 addressees repeat 1 female does not return for over an hour. Service journal task 63455 confirms generation beyond 196000 tokens, still ~34 tokens/s. ollama ps reports Stopping... while GPU ~98% busy; this label does not establish generation stopped. No intervention, timeout or cap imposed. Journal excerpt archived; await raw final reply before diagnosing actual output.

Huihui Qwen3.5 addressees repeat 1 female finally fails at length after 6438.77
seconds: prompt=870, generated=261274, sum=262144; content empty; reasoning
906018 characters. Two short self-check lines repeat 6546 and 6542 times. This is
an observed reasoning loop, not just a slow response or stale Ollama ps label.
Raw failure is preserved and female checks remain failed. No timeout/cap/retry
was imposed. The driver advances normally to repeat 2. An optional user choice
about skipping this model was asked while it was running; absent an answer,
the authorized uncapped suite continues unchanged.

Huihui Qwen3.5 addressees repeats 2/3 female finish normally. Repeat 2 паромщик correct but last line Тебе стоять... пока верёвка не затянет is awkward/incomplete and fails to convey secure fastening. Repeat 3 лодочник plausible; rope secure becomes станет крепкой. Both pass 11/11, illustrating unchecked meaning issues. Female copies exactly. Aggregate addressees 54/66 due first failed female and поток synonym regex.

Huihui Qwen3.5 multiple-NPC replies: all six read. First female corrects verbs
but retains путник. Male/female first worried becomes думала, a meaning loss.
Second pair female verbs correct, путник remains; ты права and prefixed promises
are legitimate alternatives missed by regex. Орин ей должен извинение is awkward.
Third pair male встретиться becomes ungrammatical Встреться нам; тревожилась is
valid worry synonym rejected by regex. Fixed NPC and narrated male genders are
otherwise retained in these male outputs; final female inspected separately.

Huihui Qwen3.5 multiple-NPC final female changes narrated его to её, despite fixed third-person male, and keeps masculine спас and путник addressing female player. Awkward Встреться нам unchanged. Total 121/132, all pairs structurally valid; meaning and gender still wrong.

Huihui Qwen3.5 original female variants all replies read. Male first two use Дюк
instead of герцог; third correct. All female replies fill explicitly empty source
with door text and reject. Female first two also miss duke-to-duchess and
silver-to-bronze source changes, retaining Дюк and серебряный. First writes принёсла
instead of принесла. Third rejected female inspected separately. No salvaged
scores; male checks 14+14+15, female 0+0+0, total 43/90.

Huihui Qwen3.5 original-variant third female likewise keeps Герцог отправил and серебряный, writes принёсла, and fills empty door source. Thus all three miss original patron/material changes, not merely empty-string handling.

Huihui Qwen3.5 reused strings all raw replies inspected. First pair retains
Я готова: wrong for male player; female fits both female speakers. Lock becomes
засов, changing specificity; marker, engine-token and newline counts preserved.
Second male drops closing star on stage direction, so structurally rejects and
female is skipped. Third male adds quotation marks to shared readiness string,
so rejects and female skipped; raw final reply separately inspected. No repairs
or retries. This suite is complete with failures, not abandoned or capped.

Huihui Qwen3.5 reused third raw male adds quotation marks around every line,
changes punctuation and stage markers (an unmatched star with parentheses), and
therefore cannot be exported. Female skips after this failure. Final result:
460/660, 28 actual requests, 7 rejected, 2 skipped female passes, 8 complete pairs,
10629.27 request seconds; one full-context length failure. No intervention.

## Huihui Qwen3 abliterated 14B
All 15 actual male replies across five datasets/three repeats read, including
raw prefixes and apparent JSON portions; all 15 female passes skipped after male
failures. Every male answer is invalid JSON as returned: extraneous Chinese or
other text, leaked reasoning and/or closing </think> before answer JSON. No prefix
stripping, salvage or compatibility fix was applied. All requests stop normally;
none length-fails. The installed metadata says thinking supported, and request
think=true was used, but the returned content mixes channels. No usable female
comparison can be made. Its 0/660 is a pipeline/protocol failure, not measured
zero linguistic ability. Runtime/template/parser compatibility diagnosis remains
unperformed; do not attribute this entire failure solely to model reasoning.
Even the unscored apparent translation portions have defects: InkGallery becomes
Галерея Стихий or Инк-Галерея; seen becomes прочитал. Ferryman becomes Переводчик;
Селена gets wrong dative Селене. Multiple-NPC repeat 3 male addresses male player
as спасла, changes meeting at dawn to Нас ждёт в полночь, and writes свою обещание.
Original variants duke becomes граф in two repeats; key brought becomes привёл.
All shared male readiness strings are feminine Я готова/Готова, incompatible with
male player. These observations are manual only and do not salvage scoring.


## Interpretation limits

Context and thinking both differ from earlier thinking-off baselines; no native-context thinking-off control was run. Model-default sampling differs. The two Huihui variants have no matched frozen thinking-off suite. Frozen checks miss some nouns, narrated pronouns and meaning changes; narrow regexes also reject valid alternatives. The readiness check is too strict when both speakers are female. Four fixtures are synthetic and not independent human gold data. No production model/prompt change, automatic repair or promotion was performed. Rejected replies remain rejected; partial good lines are not salvaged.
