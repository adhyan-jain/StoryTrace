# StoryTrace Final A/B/C/D Research Experiment Results

**Model**: `qwen2.5:7b` via local Ollama (`MODEL_PROVIDER=ollama`, `temperature: 0.0`)
**Corpus**: 10 Research Screenplays (60 units per film)
**Ground Truth**: `gold_dataset_v3.json` (Validated LLM-assisted consensus gold set)

---

## 1. Primary Ablation Results (Overall Performance)

| Condition | Description | Micro Precision | Micro Recall | Micro F1 | Macro F1 | Total Surfaced | Runtime (s) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Condition A** | Full StoryTrace (Controlled + Agent) | 0.5965 | 0.0344 | **0.0650** | 0.0672 | 57 | 25964.5 |
| **Condition B** | Pipeline Only (Controlled + No Agent) | 0.6265 | 0.0526 | **0.0970** | 0.1024 | 83 | 22522.5 |
| **Condition C** | Unconstrained Extraction + Agent | 0.6952 | 0.0738 | **0.1335** | 0.1331 | 105 | 39052.9 |
| **Condition D** | One-Shot LLM Baseline (qwen2.5:7b) | 0.0000 | 0.0000 | **0.0000** | 0.0000 | 8 | 138.3 |

---

## 2. Category Performance Breakdown (Micro F1)

| Category | Condition A | Condition B | Condition C | Condition D |
| :--- | :---: | :---: | :---: | :---: |
| **Possession** | 0.0000 | 0.0816 | 0.0000 | 0.0000 |
| **Injury** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Location** | 0.2684 | 0.3531 | 0.3488 | 0.0000 |
| **Clothing/appearance** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Other** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

---

## 3. Investigation Agent Impact (Condition A vs Condition B)

- **False Positive Suppression**: Condition A reduced surfaced candidates from **83** (Condition B) to **57** (Condition A).
- **Precision Gain**: Micro Precision improved from **0.6265** to **0.5965** (+-0.0300).
- **F1 Improvement**: Micro F1 improved from **0.0970** to **0.0650**.

---

## 4. Controlled vs Unconstrained Extraction (Condition A vs Condition C)

- **Schema Precision**: Controlled extraction (Condition A: F1 0.0650) vs Unconstrained extraction (Condition C: F1 0.1335).

---

## 5. Per-Film Breakdown (Micro F1)

| Film Slug | Condition A | Condition B | Condition C | Condition D | Gold Count |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `chasing_amy` | 0.0308 | 0.0896 | 0.2466 | 0.0000 | 64 |
| `darkman` | 0.0000 | 0.0000 | 0.1702 | 0.0000 | 86 |
| `do_the_right_thing` | 0.0098 | 0.0099 | 0.0000 | 0.0000 | 202 |
| `dog_day_afternoon` | 0.0465 | 0.0455 | 0.0444 | 0.0000 | 42 |
| `fargo_film` | 0.1176 | 0.2162 | 0.0667 | 0.0000 | 29 |
| `inception` | 0.0863 | 0.1389 | 0.1867 | 0.0000 | 129 |
| `punch_drunk_love` | 0.0727 | 0.1053 | 0.1880 | 0.0000 | 106 |
| `smokin_aces` | 0.0645 | 0.0860 | 0.0440 | 0.0000 | 89 |
| `snow_white_and_the_huntsman` | 0.0680 | 0.0805 | 0.1548 | 0.0000 | 142 |
| `the_bourne_identity_2002_film` | 0.1760 | 0.2519 | 0.2295 | 0.0000 | 100 |
