# Evaluation v3 rescoring — 2026-10-29

Offline rescoring only; no new model requests. Existing rejected/skipped replies remain failed. New requests with empty female sources omitted are measured separately in the new experiments.

| Batch | Model | Old checks | v3 checks |
|---|---|---:|---:|
| NON_THINKING_RESCORED_V3.csv | gemma3:12b | 570/660 | 618/717 |
| NON_THINKING_RESCORED_V3.csv | hf.co/t-tech/T-lite-it-2.1-GGUF:Q4_K_M | 523/660 | 570/717 |
| NON_THINKING_RESCORED_V3.csv | aya-expanse:8b | 427/660 | 470/717 |
| NON_THINKING_RESCORED_V3.csv | hf.co/VlSav/Vikhr-Nemo-12B-Instruct-R-21-09-24-Q6_K-GGUF:Q6_K | 490/660 | 541/717 |
| NON_THINKING_RESCORED_V3.csv | mistral-small3.2:24b | 592/660 | 650/717 |
| NON_THINKING_RESCORED_V3.csv | gemma4:12b | 564/660 | 619/717 |
| NON_THINKING_RESCORED_V3.csv | qwen3:14b | 503/660 | 552/717 |
| THINKING_NATIVE_QWEN35_RESCORED_V3.csv | qwen3.5:9b | 587/660 | 640/717 |
| THINKING_NATIVE_REMAINING_RESCORED_V3.csv | gemma4:12b | 592/660 | 650/717 |
| THINKING_NATIVE_REMAINING_RESCORED_V3.csv | huihui_ai/qwen3-abliterated:14b | 0/660 | 0/717 |
| THINKING_NATIVE_REMAINING_RESCORED_V3.csv | huihui_ai/qwen3.5-abliterated:9b | 460/660 | 507/717 |
| THINKING_NATIVE_REMAINING_RESCORED_V3.csv | qwen3:14b | 534/660 | 578/717 |

These targeted assertion totals are not overall translation accuracy. The denominator changed from 660 to 717; compare v3 totals with v3 totals only. Native-context thinking runs also changed context versus the old non-thinking runs, so they do not isolate thinking.

Mistral without thinking and Gemma4 with native-context thinking both score 650/717. Neither is approved for unattended export. Existing manual reviews remain relevant; rescoring does not correct translations.

Source folders: `results/non-thinking-20261028-013515/`, `results/thinking-native-20261028-094842/`, and `results/thinking-native-remaining-20261028-214626/`. CSVs next to this report preserve per-model, per-dataset scores and old evaluation versions.

Files are saved for user review. No commit is authorized until the user reviews the work and explicitly asks.
