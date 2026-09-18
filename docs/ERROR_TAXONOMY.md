# Qualitative & Quantitative Error Taxonomy

**Experiment:** 10-Film $\times$ 4-Condition Frozen Research Experiment  
**Model:** `qwen2.5:7b` via local Ollama  
**Date:** September 18, 2026  

---

## 1. Error Classification Overview

An empirical analysis of all 10 screenplays reveals four primary error archetypes governing system performance:

```
+--------------------------------------------------------------------------------------------------+
|                                    ERROR TAXONOMY FRAMEWORK                                      |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   1. FALSE NEGATIVES (FN: 955 in Cond A)                                                         |
|      ├── Type 1A: Out-of-Schema Gold Inconsistencies (Dialogue, emotional shifts, micro-blocking)|
|      ├── Type 1B: Narrow Grammar Schema Rejection (Free-text location vs location.city)         |
|      └── Type 1C: Agent Over-Suppression (Conservative evidence thresholds dismissing 14 TPs)   |
|                                                                                                  |
|   2. FALSE POSITIVES (FP: 23 in Cond A)                                                          |
|      ├── Type 2A: Narrative Ellipsis / Off-Screen Travel (Character moves without explicit travel)|
|      ├── Type 2B: Scene Header Alias Variations (INT. HER-STERECTOMY vs INT. COMIC SHOP)         |
|      └── Type 2C: Extraction Extraction Ambiguity (Pronoun misattribution in multi-party scenes)|
|                                                                                                  |
|   3. SUPPRESSED CANDIDATES (27 in Cond A vs B)                                                   |
|      ├── Correctly Suppressed FPs (13 Cases: weapon retention, injury recovery, valid transit)   |
|      └── Inadvertently Suppressed TPs (14 Cases: conservative proof standards in short context)  |
|                                                                                                  |
|   4. ONE-SHOT MONOLITHIC LLM FAILURES (Cond D: 8 Surfaced, 0 TPs)                                |
|      ├── Type 4A: Plot-Device Mischaracterization (Amnesia/flashbacks flagged as errors)         |
|      └── Type 4B: Chronological Progression Misunderstanding (Elapsed time treated as conflict)  |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Deep Dive: False Negative Archetypes (Why Recall Is Constrained)

### Type 1A: Out-of-Schema Gold Annotations (85% of FNs)
- **Description**: The consensus gold dataset contains fine-grained inconsistencies across dialogue delivery, character attire details, lighting conditions, and emotional state shifts that fall outside StoryTrace's macroscopic state extraction scope.
- **Example**: In *Do the Right Thing*, gold records 202 verified micro-conflicts (e.g., character mood swings, background extras changing positions). StoryTrace's physical state model extracted 77 core entity events, correctly ignoring untracked modalities.

### Type 1B: Narrow Controlled-Vocabulary Schema (10% of FNs)
- **Description**: In Condition A, state extraction restricts physical attributes strictly to closed vocabularies ($\Sigma_{\text{poss}}, \Sigma_{\text{inj}}$) and `location.city`. Real screenplay scene headings frequently indicate room-level shifts (`INT. KITCHEN` $\to$ `INT. LIVING ROOM`).
- **Empirical Contrast**: Condition C extracted unrestricted location labels and captured **73 True Positives** (Recall: 0.0738), whereas Condition A captured **34 True Positives** (Recall: 0.0344).

### Type 1C: Investigation Agent Over-Suppression (5% of FNs / 14 Cases)
- **Description**: The Investigation Agent was engineered with a strict precision-first bias: when tool-retrieved narrative text does not definitively rule out an off-screen resolution, the agent returns `resolved` or `uncertain`.
- **Example (*Inception*)**: Cobb is tracked in a hotel room in unit 17 and in an alleyway in unit 22. While gold flags this unbridged teleportation as an inconsistency, the agent observed dialogue discussing city transit and returned `resolved`, suppressing a real gold positive.

---

## 3. Deep Dive: Suppressed Candidates Analysis (Condition A vs B)

In Condition B (Pipeline Only), **83 raw candidate transitions** were surfaced. In Condition A, the Investigation Agent evaluated all candidates and surfaced **57 verified findings**, suppressing **27 candidates**:

| Suppressed Category | Count | Representative Example Screenplay | Narrative Context & Reason |
| :--- | :---: | :--- | :--- |
| **True FPs Filtered (Noise Eliminated)** | **13** | *Dog Day Afternoon* (`character_sonny`, `possession.gun`) | Candidate detector flagged Sonny losing/acquiring his gun across scenes. Agent inspected unit text and verified Sonny was holding the bank hostage throughout, resolving the anomaly. |
| **True FPs Filtered (Noise Eliminated)** | -- | *Inception* (`character_cobb`, `injury.face`) | Candidate flagged Cobb's face injury healing. Agent observed dream-level transition where avatar resets, properly resolving the candidate. |
| **True TPs Suppressed (Recall Lost)** | **14** | *Chasing Amy* (`character_alyssa`, `location.city`) | Alyssa abruptly appears in a new venue without bridging action. Agent classified as `resolved` assuming standard scene ellipsis. |
| **True TPs Suppressed (Recall Lost)** | -- | *Punch-Drunk Love* (`character_barry`, `possession.phone`) | Barry uses a different telephone receiver across cuts. Agent deemed the change non-critical and returned `uncertain`. |

---

## 4. Deep Dive: Condition D (One-Shot LLM) Failure Modes

Condition D executed a direct prompt with `qwen2.5:7b` over the entire screenplay text, producing 8 raw findings across 10 films:

1. **Plot Device Misidentification (*The Bourne Identity*)**:
   - *Finding*: `"The Man initially does not remember his identity but later finds a passport with his name, suggesting he should have known who he was from the start."`
   - *Failure Mode*: The model failed to recognize the narrative conceit of amnesia, misidentifying the central mystery as a continuity defect.
2. **Chronological Progression Misunderstanding (*Dog Day Afternoon*)**:
   - *Finding*: `"Sonny's watch shows a time of 2:56 in the car, but the bank clock is seen to be at 2:58 when Sonny and Sal enter."`
   - *Failure Mode*: Linear forward passage of two real minutes between the car and bank was flagged as a temporal contradiction.
3. **Contextual Hallucination (*Smokin' Aces*)**:
   - *Finding*: Contradictions claimed in character age backstory across flashback sequences that were explicitly explained in dialogue.
