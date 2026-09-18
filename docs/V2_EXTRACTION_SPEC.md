# StoryTrace V2 Enriched Extraction Specification

**Specification:** Structured Scene & Narrative State Extraction Engine  
**Module:** `backend/v2/pipeline/enriched_extractor.py`  
**Data Models:** `backend/v2/story_state/models.py`  
**Storage Schema:** `backend/v2/clickhouse/schema_v2.sql`  
**Date:** September 18, 2026  

---

## 1. Objective & Purpose

In StoryTrace V1, the state extraction ontology was tightly restricted to macroscopic physical attributes (`possession.<prop>` in `{held, acquired, lost}`, `injury.<body_part>` in `{injured, healed, dead}`, and `location.city`). This created a theoretical recall ceiling of **8.49%** against the 989 gold-annotated narrative continuity conflicts.

**StoryTrace V2's Enriched Extraction Pipeline** expands the addressable state space by decoupling structured structural typing from rigid semantic value vocabularies. The extractor serves as a strict, impartial **Observer**, extracting rich spatial hierarchies, temporal pacing anchors, scene co-presence indices, multi-party possession transfers, physical states, clothing, relational bonds, and epistemic discoveries.

---

## 2. Core Extraction Ontology

```
+----------------------------------------------------------------------------------------------------+
|                                    STORYTRACE V2 EXTRACTION ONTOLOGY                                |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  1. SCENE METADATA & CO-PRESENCE (`RawSceneMetadataV2`)                                            |
|     ├── Spatial Hierarchy: [setting_type, environment, specific_room, city_region]                 |
|     ├── Temporal Anchor: CONTINUOUS | MOMENTS_LATER | SAME_DAY | NEXT_DAY | DAYS_LATER | FLASHBACK   |
|     ├── Time-of-Day: DAY | NIGHT | DUSK | DAWN | UNKNOWN                                           |
|     └── Co-Presence Index: [char_1, char_2, prop_1, vehicle_1]                                     |
|                                                                                                    |
|  2. TYPED STATE FACTS (`RawStateFactV2`)                                                           |
|     ├── Category: spatial | possession | physical | clothing | relational | epistemic              |
|     ├── Attribute Path: location | possession.<item> | injury.<part> | clothing.<item> | relation  |
|     ├── Normalized Value: acquired | held | lost | transferred | injured | healed | dead | knows   |
|     ├── Related Entity: Target character in transfer or relationship                               |
|     └── Verbatim Excerpt: Substring quote from scene source text                                   |
|                                                                                                    |
|  3. NARRATIVE EVENTS (`RawNarrativeEventV2`)                                                       |
|     ├── Event Type: travel | transfer | injury_inflicted | death | revelation | confrontation      |
|     ├── Actors & Targets: [actor_ids], [target_ids]                                                |
|     └── Description & Excerpt: Verbatim action span                                                |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Schema Semantics

### 3.1 Spatial Hierarchy (`HierarchicalLocationV2`)
Rather than flattening all locations into an isolated `city` string, V2 captures 4-tier spatial tuples:
- `setting_type`: `INT`, `EXT`, `INT/EXT` (parsed directly from screenplay sluglines).
- `environment`: The primary building, complex, or natural setting (e.g. `POLICE_STATION`, `HOTEL`, `AIRPORT`, `WAREHOUSE`, `FOREST`, `CAR`).
- `specific_room`: The specific room, compartment, or blocking area (e.g. `INTERROGATION_ROOM`, `SUITE_402`, `LOADING_DOCK`, `KITCHEN`, `ROOFTOP`).
- `city_region`: The explicit city, state, or geographic region (e.g. `PARIS`, `NEW_YORK`, `BOSTON`) populated **only** when explicitly named in the scene text or slugline.

### 3.2 Temporal Pacing Anchors (`TemporalAnchor`)
V2 explicitly differentiates between continuous scene progressions and discrete temporal jumps:
- `CONTINUOUS`: Immediate temporal continuity from the prior scene.
- `MOMENTS_LATER`: Short elapsed time (seconds to minutes) in or around the same vicinity.
- `SAME_DAY`: Later that day (hours elapsed).
- `NEXT_DAY`: Following morning/day.
- `DAYS_LATER` / `MONTHS_LATER` / `YEARS_LATER`: Substantial chronological jumps.
- `FLASHBACK`: Narrative departure into historical backstory.
- `DREAM_SEQUENCE`: Subjective cognitive hallucination or dream.

### 3.3 Multi-Party Possession State Machine
V2 transitions possession from a static boolean into a multi-entity transfer graph:
- `acquired`: Entity takes, picks up, or purchases an item for the first time.
- `held`: Entity is actively carrying or holding the item.
- `transferred`: Entity hands, yields, or transfers custody of the item to `related_entity_name`.
- `lost`: Entity drops, has stolen, or loses custody of the item.

### 3.4 Physical Traumas & Medical Status
- `injured`: Traumatic wound, fracture, or impairment inflicted or present on a specific body part (`injury.forearm`).
- `healed`: Wound treated, stitched, or resolved.
- `dead`: Character deceased.
- `restrained` / `free`: Physical bondage (handcuffed, tied) vs. unhindered mobility.

### 3.5 Epistemic & Relational States
- `epistemic` (`knowledge.<fact>`): Tracks explicit moments where a character learns (`discovers`), is confirmed to know (`knows`), or is explicitly stated to be ignorant of (`unaware`) a critical plot point.
- `relational` (`relation.<type>`): Explicit shifts in character alliances (`ally`, `enemy`, `partner`, `captive`).

---

## 4. Grounding & Evidence Provenance Rules

1. **Verbatim Substring Enforcement**: Every `raw_excerpt` emitted by the LLM is checked against `unit.raw_text`.
2. **Hallucination Rejection**: Any state fact whose excerpt cannot be grounded (either via exact substring or normalized whitespace match) is discarded.
3. **Database Provenance**: Every row stored in `state_events_v2` retains `unit_id`, `sequence_number`, `page_ref`, and `raw_excerpt`, guaranteeing that all downstream candidate conflicts and agent verdicts link directly to source script text.

---

## 5. Permitted vs. Forbidden Inferences

| Permitted (Observer Role) | Forbidden (Investigator Role) |
| :--- | :--- |
| Extracting explicit scene sluglines (`INT. HOTEL - NIGHT`). | Speculating whether a character had time to travel between cities. |
| Extracting explicit character actions ("Maya took Cole's gun"). | Adjudicating whether a missing gun is an intentional plot twist or continuity defect. |
| Extracting explicit time phrases ("Three days later"). | Inventing exact numerical minutes/hours when the text does not state them. |
| Extracting co-present characters mentioned in dialogue or action. | Inferring co-presence for characters merely mentioned in third-person gossip. |

---

## 6. Worked Example: V1 vs. V2 Extraction Contrast

### Scene Input
```text
INT. HOTEL PARIS - SUITE 402 - NIGHT
Arthur hands the forged passport to Cobb, who places it inside his leather jacket. Cobb clutches his bandaged ribs.
```

### V1 Extraction Output
```json
[
  {
    "entity_name": "COBB",
    "attribute": "location",
    "value": "HOTEL PARIS",
    "raw_excerpt": "INT. HOTEL PARIS"
  },
  {
    "entity_name": "COBB",
    "attribute": "possession.passport",
    "value": "held",
    "raw_excerpt": "places it inside his leather jacket"
  }
]
```
*(V1 missed: Room-level hierarchy, Arthur's co-presence, custody transfer from Arthur to Cobb, city-level regional indexing, and the rib injury).*

### V2 Extraction Output
```json
{
  "scene_metadata": {
    "setting_type": "INT",
    "environment": "HOTEL",
    "specific_room": "SUITE_402",
    "city_region": "PARIS",
    "time_of_day": "NIGHT",
    "time_anchor": "CONTINUOUS",
    "present_entity_names": ["COBB", "ARTHUR", "PASSPORT"]
  },
  "state_facts": [
    {
      "entity_name": "COBB",
      "entity_type": "character",
      "category": "possession",
      "attribute": "possession.passport",
      "value": "acquired",
      "raw_excerpt": "Arthur hands the forged passport to Cobb, who places it inside his leather jacket",
      "related_entity_name": "ARTHUR"
    },
    {
      "entity_name": "ARTHUR",
      "entity_type": "character",
      "category": "possession",
      "attribute": "possession.passport",
      "value": "transferred",
      "raw_excerpt": "Arthur hands the forged passport to Cobb",
      "related_entity_name": "COBB"
    },
    {
      "entity_name": "COBB",
      "entity_type": "character",
      "category": "physical",
      "attribute": "injury.ribs",
      "value": "injured",
      "raw_excerpt": "Cobb clutches his bandaged ribs"
    }
  ],
  "narrative_events": [
    {
      "event_type": "transfer",
      "actor_entity_names": ["ARTHUR"],
      "target_entity_names": ["COBB"],
      "raw_excerpt": "Arthur hands the forged passport to Cobb",
      "description": "Arthur transfers passport to Cobb"
    }
  ]
}
```

---

## 7. Coverage Gap Resolutions & Remaining Limitations

1. **Resolved Gaps**:
   - Intra-building & room-level spatial tracking (`INT. KITCHEN` vs `INT. BEDROOM`).
   - Co-presence collisions (simultaneous presence in conflicting scenes).
   - Multi-party possession transfers and custody handoffs.
   - Pacing and elapsed time tracking via `TemporalAnchor`.
2. **Remaining Limitations**:
   - Subtextual / metaphoric subplots (e.g. symbolic transformations) remain intentionally unextracted to protect high precision.
