# StoryTrace Formal Human Annotation Guidelines

> **Version:** 1.0 (Publication Freeze)  
> **Status:** Active Standard for Research Gold Dataset Annotation  
> **Target Scope:** StoryTrace 10-Film Narrative Continuity Benchmark

---

## 1. Core Definition of a Narrative Continuity Conflict

A **narrative continuity conflict** is defined as an inconsistency between state assertions about the same entity and attribute at temporal points $T_1 < T_2$ where the state asserted at $T_2$ contradicts, invalidates, or renders physically/logically impossible the state asserted at $T_1$ **without any intervening narrative explanation**.

### Intervening Narrative Explanations (Bridging Events)
A state transition from $T_1$ to $T_2$ is **NOT** a continuity conflict if any of the following bridging conditions are present in the text between $T_1$ and $T_2$:
1. **Explicit Action / Event**: The text explicitly describes the event causing the state change (e.g., character picked up an item, walked to a location, changed clothes, or bandaged a wound).
2. **Explicit Dialogue Acknowledgment**: A character verbally states that an event occurred off-screen (e.g., *"I just got back from Paris"* or *"The medic wrapped my arm"*).
3. **Explicit Off-Screen Time Skip**: The narrative explicitly notes a passage of time (e.g., *"Three days later"*, *"The next morning"*) during which routine state transitions naturally occur.

If a state change occurs **without** an intervening narrative explanation or time skip, it is flagged as an unbridged transition (`verified` conflict).

---

## 2. Fixed Taxonomy (5 Categories)

Every continuity conflict must be assigned to exactly one of the following 5 standard taxonomy categories:

| Category | Definition | Example Attributes | Example States |
| :--- | :--- | :--- | :--- |
| `possession` | Physical items held, worn, equipped, acquired, lost, transferred, or destroyed. | `possession.weapon`, `possession.journal`, `possession.key` | `held`, `dropped`, `acquired`, `destroyed` |
| `injury` | Physical wounds, scars, impairments, bleeding, fractures, or health state transitions. | `injury.left_arm`, `injury.face`, `injury.leg` | `wounded`, `bleeding`, `healed`, `bandaged` |
| `location` | Character or object spatial positioning, city, room, vehicle location, or setting. | `location.city`, `location.room`, `location.setting` | `Paris`, `police_station`, `int. chevy` |
| `clothing/appearance` | Garments, outfits, physical appearance markers, hairstyle, glasses, accessories. | `clothing.jacket`, `appearance.glasses`, `hair.style` | `wearing_tuxedo`, `barefoot`, `wet`, `glasses_on` |
| `other` | Roles, relationships, vehicle operational status, or named properties not fitting above. | `vehicle.engine`, `status.employment`, `role.detective` | `running`, `stalled`, `retired`, `active` |

---

## 3. Verdict Status & Severity Tiers

### 3.1 Verdict Status

Annotators must classify each candidate state pair into one of three verdict statuses:

- `verified`: A genuine, unbridged state contradiction exists in the text. The state at $T_2$ invalidates $T_1$ with no intervening narrative bridge.
- `resolved`: The transition appears suspicious initially, but a careful reading reveals an intervening narrative explanation (e.g., explicit dialogue, medical treatment, or travel narration).
- `ambiguous`: The evidence is incomplete, open to artistic interpretation, or impossible to determine strictly from text.

### 3.2 Severity Tiers

For entries marked as `verified` or `ambiguous`, annotators assign a severity level:

- `critical`: A major plot hole or physical impossibility that breaks narrative logic (e.g., a deceased character appearing alive in the next scene, a destroyed prop re-appearing).
- `warning`: A noticeable continuity oversight or unbridged state flip (e.g., a character switching locations without travel narration, an unmentioned wound healing).
- `info`: A minor background detail inconsistency or temporal ambiguity (e.g., minor scene-heading time jumps).

---

## 4. Grounding & Verbatim Excerpt Rules

To ensure publication-grade reproducibility, **every annotation entry must be grounded in exact source text excerpts**:

1. **Verbatim Excerpt Requirement**: Both `earlier_excerpt` ($T_1$) and `later_excerpt` ($T_2$) MUST be exact, case-sensitive substrings copied directly from the screenplay narrative units.
2. **Minimal Sufficient Span**: Excerpts should contain the shortest substring necessary to establish the state assertion (typically 1–2 sentences).
3. **Temporal Monotonicity**: The earlier scene unit sequence number ($T_1$) MUST be strictly less than the later scene unit sequence number ($T_2$).

---

## 5. Handling Ambiguity, Multiple Acceptable States & Temporal Bounds

### 5.1 Representation of Multiple Acceptable State Values
In natural language narratives, state values may be described using synonym phrases (e.g., `"wearing a leather coat"` vs `"wearing a black jacket"`). 
- If two phrases describe the **same underlying physical state**, annotators MUST mark the status as `resolved` or record normalized state values in `earlier_state` / `later_state`.
- If the text is genuinely ambiguous between multiple interpretations, record `verdict_status: "ambiguous"` and list alternative acceptable states in the notes.

### 5.2 Implicit Scene Transitions
Screenplays naturally transition across scene headings (e.g., `INT. POLICE STATION - DAY` -> `EXT. STREET - NIGHT`).
- Location changes occurring **across explicit scene headings** where a time skip is implied by the heading (e.g. `DAY` -> `NIGHT`) are classified as `resolved` (narratively implied time skip).
- Location changes occurring **within the same scene block** without travel narration are classified as `verified` (unbridged spatial teleportation).

---

## 6. Strict Independence Protocol

To prevent model bias or priming:
1. **Blind Annotation**: Annotators MUST perform annotations directly on raw screenplay text files (**without** access to StoryTrace model predictions, candidate outputs, or investigator trace logs).
2. **Ground Truth Independence**: Model outputs MUST NEVER be used as ground truth or candidate prompts.
3. **Immutability of Definition**: The definition of a continuity conflict remains strictly fixed as defined in Section 1 and cannot be modified after inspecting model results.
