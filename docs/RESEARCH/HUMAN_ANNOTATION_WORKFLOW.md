# StoryTrace Human Annotation Workflow & Package Documentation

> **Publication-Grade Protocol Version:** 1.0 (Freeze Gate)  
> **Target Scope:** Ground Truth Human Annotation for 10-Film Benchmark Corpus  
> **Model Independence Guarantee:** 100% Blind Annotation Protocol

---

## 1. Overview & Package Architecture

This package provides a publication-grade, model-independent annotation framework for building StoryTrace's ground truth benchmark corpus. All annotation protocols are strictly decoupled from StoryTrace system outputs, ensuring that gold labels are never derived from LLM candidate predictions or model verdicts.

### Package File Structure
```
StoryTrace/
├── docs/
│   ├── ANNOTATION_GUIDELINES.md        # Formal definition, 5-taxonomy categories & verdict rules
│   └── HUMAN_ANNOTATION_WORKFLOW.md     # This step-by-step workflow guide & execution documentation
├── data/
│   ├── annotation/
│   │   ├── annotation_schema.json       # JSON Schema enforcing data structural validity
│   │   ├── blind_annotation_template.json # Blind JSON template for human annotators
│   │   ├── blind_annotation_template.csv  # Spreadsheet CSV template for human annotators
│   │   └── adjudication_template.json   # Template for resolving multi-annotator disagreements
│   └── eval/
│       ├── corpus_manifest.json         # Frozen 10-film manifest with text SHA256 hashes & scene counts
│       └── gold_dataset_v3.json         # Machine-readable output gold dataset (compiled post-adjudication)
└── scripts/
    └── eval/
        ├── validate_gold_dataset.py     # Syntax validation & verbatim text grounding check
        └── compute_iaa.py              # Inter-Annotator Agreement (Cohen's & Fleiss' Kappa) script
```

---

## 2. Step-by-Step Instructions for Human Annotators

### Step 1: Prepare Raw Screenplay Texts
- Refer to `data/eval/corpus_manifest.json` for the 10 film screenplays in the research corpus.
- Open the raw screenplay file (e.g., `data/test_documents/seven.txt`).
- **CRITICAL**: Do NOT open any system prediction files, candidate audit outputs, or model trace logs.

### Step 2: Read Narrative Units Sequentially
- Read each scene unit $U_1, U_2, \dots, U_n$ in order.
- Maintain a mental or written state tracker for key entities (characters, weapons, key props, locations, injuries, clothing).

### Step 3: Record Continuity Conflicts
When you discover an unbridged or suspicious state change for an entity/attribute between $T_1$ and $T_2$:
1. Open a copy of `data/annotation/blind_annotation_template.json` or `.csv`.
2. Fill out an entry with:
   - `earlier_scene_unit`: Scene unit sequence number at $T_1$.
   - `later_scene_unit`: Scene unit sequence number at $T_2$.
   - `entity`: Canonical character/object identifier (e.g., `character_mills`, `possession_journal`).
   - `attribute`: Dot-separated attribute (e.g., `location.city`, `injury.arm`, `possession.weapon`).
   - `earlier_state` / `later_state`: Descriptive state values.
   - `conflict_type`: One of `possession`, `injury`, `location`, `clothing/appearance`, `other`.
   - `verdict_status`: `verified` (unbridged gap), `resolved` (bridged by text), or `ambiguous`.
   - `severity`: `critical`, `warning`, or `info`.
   - `exact_evidence_excerpts`: Copy and paste **exact verbatim substrings** from the screenplay for both $T_1$ and $T_2$.

---

## 3. Representation of Complex Cases

### 3.1 Ambiguous Cases
When evidence is incomplete or open to multiple artistic interpretations:
- Set `"verdict_status": "ambiguous"`.
- Provide a clear explanation in `"annotator_notes"`.

### 3.2 Multiple Acceptable State Values
When a state assertion can be phrased in multiple ways (e.g., `"wearing a tux"` vs `"wearing a black suit"`):
- Use the most concise canonical description in `earlier_state` and `later_state`.
- Document phrase variations in `"annotator_notes"`.

### 3.3 Temporal Sequence Bounds
- `earlier_scene_unit` MUST be strictly less than `later_scene_unit`.
- Multi-scene span bounds are preserved via the exact scene sequence numbers.

---

## 4. Multi-Annotator Adjudication Protocol

To guarantee high reliability:
1. Two independent annotators complete blind annotations (`annotator_1.json` and `annotator_2.json`).
2. Run `scripts/eval/compute_iaa.py` to calculate Cohen's Kappa ($\kappa$).
3. For any items where annotators disagreed on verdict, taxonomy category, or severity, copy the entries into `data/annotation/adjudication_template.json`.
4. A lead adjudicator reviews the source screenplay, resolves the disagreement, and records the consensus resolution in `final_consensus_verdict`.

---

## 5. Execution Commands for Scripts

### 1. Validate Human Annotations & Compile Gold Dataset
Runs structural JSON schema validation, sequence monotonicity checks, and verbatim text excerpt matching against the source screenplay:
```bash
python3 -m scripts.eval.validate_gold_dataset path/to/annotator_1.json
```

### 2. Compute Inter-Annotator Agreement (IAA)
Calculates Cohen's Kappa ($\kappa$) and observed agreement percentage across category, verdict, and severity:
```bash
python3 -m scripts.eval.compute_iaa data/annotation/annotator_1.json data/annotation/annotator_2.json
```

---

## 6. Summary of Remaining Human Work for Annotators

The infrastructure, scripts, templates, schema, guidelines, and frozen corpus manifest are **100% complete and ready for use**.

### Remaining Manual Human Annotator Tasks:
1. **Annotator 1 Execution**: Read the screenplays listed in `data/eval/corpus_manifest.json` and record blind entries into `data/annotation/annotator_1.json`.
2. **Annotator 2 Execution**: Independently read the same screenplays and record blind entries into `data/annotation/annotator_2.json`.
3. **Run Agreement Calculation**: Execute `python3 -m scripts.eval.compute_iaa data/annotation/annotator_1.json data/annotation/annotator_2.json`.
4. **Adjudication**: Fill `data/annotation/adjudication_template.json` to resolve any consensus mismatches.
5. **Final Compile**: Run `python3 -m scripts.eval.validate_gold_dataset data/annotation/adjudication_template.json` to generate `data/eval/gold_dataset_v3.json`.

> **Note**: Do NOT begin the automated A/B/C/D research evaluation until the human gold annotations are compiled into `data/eval/gold_dataset_v3.json`.
