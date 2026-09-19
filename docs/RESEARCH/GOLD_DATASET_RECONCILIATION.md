# StoryTrace Gold Dataset Reconciliation & Lineage Audit

**Audit Target:** `data/eval/gold_dataset_v3.json`  
**SHA-256 Hash:** `0170762fc7c5abc15f33cc2241ea317cc9657e2f30de21aa50b92da2358d25b7`  
**Date:** September 19, 2026  
**Auditor:** Antigravity Scientific Integrity Engine  

---

## 1. Executive Summary & Core Finding

The apparent discrepancy between earlier notes citing **1,180 total items** and the evaluation denominator citing **989 verified conflicts** is completely reconciled by inspecting the full ground-truth structure in `gold_dataset_v3.json`:

1. **Total Annotations in Dataset:** Exactly **1,180 items** across 10 benchmark films.
2. **Positive Ground Truth (`verified`):** Exactly **989 items** (83.81%).
3. **Negative Controls (`resolved`):** Exactly **191 items** (16.19%).
4. **Conclusion:** No items were discarded or silently deleted. **989** is the exact number of positive continuity contradictions, and is the mathematically required denominator for all Precision, Recall, and F1 metrics. The 191 resolved items serve as negative controls for false-positive validation.

---

## 2. Lineage & Adjudication Pipeline

The gold dataset was created through a formal two-pass independent annotation and consensus adjudication process:

```
                  ┌────────────────────────────────────────┐
                  │ 10 Benchmark Screenplays (224k words)   │
                  └───────────────────┬────────────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
     ┌───────────────────────┐                 ┌───────────────────────┐
     │      PASS A           │                 │        PASS B         │
     │ 1,180 Candidate Items │                 │ 1,180 Candidate Items │
     └───────────┬───────────┘                 └───────────┬───────────┘
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      ▼
                    ┌───────────────────────────────────┐
                    │ Consensus Engine & Adjudicator    │
                    │ 1,034 Direct Unanimous Matches    │
                    │ 146 Disagreements Adjudicated     │
                    └─────────────────┬─────────────────┘
                                      ▼
                 ┌─────────────────────────────────────────┐
                 │       `gold_dataset_v3.json`            │
                 │ 1,180 Total Ground Truth Annotations    │
                 │ ├─ 989 Positive Conflicts (VERIFIED)    │
                 │ └─ 191 Negative Controls (RESOLVED)     │
                 └─────────────────────────────────────────┘
```

### Breakdown of Adjudication:
- **Direct Unanimous Consensus Matches:** 1,034 items (87.63% agreement rate).
  - 896 direct unanimous `verified`
  - 138 direct unanimous `resolved`
- **Disagreements Resolved by Adjudicator (`llm_adjudication.json`):** 146 items (12.37%).
  - 93 adjudicated as `verified` (under unbridged transition preference rules)
  - 53 adjudicated as `resolved` (justified by established narrative distance or off-screen transit)
- **Final Totals:**
  - $896 + 93 = \mathbf{989\text{ verified}}$
  - $138 + 53 = \mathbf{191\text{ resolved}}$
  - $\text{Total} = 989 + 191 = \mathbf{1,180\text{ items}}$

---

## 3. Film-by-Film Ground Truth Distribution

```
+--------------------------------+-----------------+-------------------+-------------------+
| FILM SLUG                      | TOTAL ANNOTATED | POSITIVE (VERIF)  | NEGATIVE (RESOLV) |
+--------------------------------+-----------------+-------------------+-------------------+
| chasing_amy                    | 70              | 64                | 6                 |
| darkman                        | 107             | 86                | 21                |
| do_the_right_thing             | 242             | 202               | 40                |
| dog_day_afternoon              | 46              | 42                | 4                 |
| fargo_film                     | 32              | 29                | 3                 |
| inception                      | 161             | 129               | 32                |
| punch_drunk_love               | 129             | 106               | 23                |
| smokin_aces                    | 109             | 89                | 20                |
| snow_white_and_the_huntsman    | 166             | 142               | 24                |
| the_bourne_identity_2002_film  | 118             | 100               | 18                |
+--------------------------------+-----------------+-------------------+-------------------+
| TOTAL                          | 1,180           | 989 (83.81%)      | 191 (16.19%)      |
+--------------------------------+-----------------+-------------------+-------------------+
```

---

## 4. Conflict Category Distribution (989 Verified Items)

- **Location / Spatial Transitions:** 942 items (95.25%)
- **Possession / Prop Transitions:** 47 items (4.75%)

*Note on Category Labeling:* Within the 942 location items, the gold annotations encompass hierarchical spatial jumps (city/region: 24, environment/building: 412, specific room: 506). In V1, only coarse `location.city` (24 items) and narrow possession items were representable, leading to V1's 84-item addressable ceiling. V2's 4-tier spatial hierarchy expands representability across 812 of these 989 items.

---

## 5. Canonical Evaluation Population Statement

- **Recall Denominator:** $\mathbf{N = 989}$ (all positive verified continuity errors).
- **Precision Denominator:** Total system-surfaced findings.
- **Negative Control Role:** The 191 `resolved` items verify that the deterministic candidate detector and investigation agent correctly avoid surfacing resolved transitions as hard errors.
- **Audit Conclusion:** **PASS**. The gold dataset is mathematically intact, fully accounted for, and unambiguously defined.
