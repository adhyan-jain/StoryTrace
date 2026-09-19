# StoryTrace V2 Calibrated Investigation Agent Specification

**Specification:** FastMCP Tool-Augmented Bounded ReAct Investigation Agent  
**Module:** `backend/v2/agent/investigator.py`  
**Tool Bridge:** `backend/v2/agent/tools.py`  
**Data Models:** `backend/v2/story_state/models.py` (`InvestigationVerdictV2`)  
**Date:** September 19, 2026  

---

## 1. Executive Summary & Purpose

StoryTrace V2 candidate generation surfaces a high-recall candidate pool (capturing **78.08%** of addressable continuity conflicts across the 989 gold benchmark items). The **Investigation Agent** acts as the high-precision filter, autonomously querying the Story Universe through ClickHouse FastMCP tools to adjudicate candidates against verbatim narrative evidence.

### Core Innovations in V2:
- **Two-Tier Calibrated Verdict Schema**: Replaces V1's single `verified` status with `verified_hard_conflict` (direct physical/logical impossibilities) vs. `verified_narrative_anomaly` (unbridged jumps/temporal slips), preventing over-suppression of soft anomalies while preserving rock-solid proof for hard errors.
- **Hierarchical & Co-Presence Tools**: Agents query spatial trajectories (`get_spatial_trajectory`) and scene co-presence lists (`get_scene_co_presence`) directly.
- **Strict Proof & Provenance Standard**: Forces step-by-step textual reasoning before enum status selection, requiring verbatim retrieved quotes in all verdicts.
- **Bounded Latency Guarantee**: Strictly capped at $\mathbf{\max\_calls = 6}$ tool calls with automated duplicate loop termination.

---

## 2. FastMCP Tool Bridge Architecture

```
                                  INVESTIGATION AGENT (ReAct)
                                               │
                                 ┌─────────────┴─────────────┐
                                 │ StdIO Client (FastMCP)    │
                                 └─────────────┬─────────────┘
                                               │
         ┌───────────────────┬─────────────────┼───────────────────┬───────────────────┐
         ▼                   ▼                 ▼                   ▼                   ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│get_entity_timeline││get_scene_co_pres ││get_spatial_traject││find_attribute_chg││  get_unit_text   │
│       _v2        ││       _v2        ││       _v2        ││       _v2        ││       _v2        │
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                   │                   │                   │
         └───────────────────┴─────────────────┬─┴───────────────────┴───────────────────┘
                                               ▼
                              [ClickHouse V2 Analytical Tables]
                              (state_events_v2, scene_co_presence_v2, narrative_units)
```

### The 5 Investigation Tools:
1. `get_entity_timeline_v2(entity_id, from_sequence, to_sequence)`: Returns ordered state events with hierarchical spatial context and temporal anchors.
2. `get_scene_co_presence(from_sequence, to_sequence)`: Returns scene environment, specific room, present entities, and temporal anchors.
3. `get_spatial_trajectory(entity_id)`: Traces the chronological physical locations occupied by an entity across the script.
4. `find_attribute_changes(entity_id, attribute)`: Filters transitions specifically for a given property key.
5. `get_unit_text(unit_id)`: Retrieves verbatim scene text for source quote extraction.

---

## 3. Two-Tier Calibrated Verdict Schema

```
+----------------------------------------------------------------------------------------------------+
|                                    V2 CALIBRATED VERDICT SCHEMA                                    |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  1. `verified_hard_conflict` (Critical / Severity: critical)                                       |
|     • Definition: Direct, incontrovertible logical or physical contradiction.                       |
|     • Examples: Deceased character actively leading squad; character simultaneously present in     |
|       two distant cities in concurrent scenes; unique prop possessed by two people at once.        |
|                                                                                                    |
|  2. `verified_narrative_anomaly` (Warning / Severity: warning)                                     |
|     • Definition: Unbridged narrative leap or unexplained state reset under continuous pacing.    |
|     • Examples: Character jumping between distant buildings in continuous scene flow without       |
|       travel scene; sudden unexplained costume/item swap.                                          |
|                                                                                                    |
|  3. `resolved` (Clean Transition / Severity: info)                                                 |
|     • Definition: Narratively justified transition verified through retrieved textual evidence.    |
|     • Examples: Paramedic treatment in prior scene resolving wound; off-screen transit during       |
|       established time gap ('THREE DAYS LATER'); legitimate flashback or dream sequence.           |
|                                                                                                    |
|  4. `uncertain` (Inconclusive / Severity: warning)                                                 |
|     • Definition: Insufficient textual evidence in script to definitively prove or disprove.       |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 4. ReAct Execution Bounds & Guardrails

- **Maximum Tool Calls**: Strictly bounded to **6 tool calls** per candidate.
- **Duplicate Call Detection**: Identifies repeated identical `(tool_name, kwargs)` queries and forces early finalization.
- **Reasoning-First Schema Enforcement**: The Pydantic `FinalVerdictV2` model deliberately orders `explanation` before `status` to ensure model output reasoning precedes categorical commitment.
- **Suggested Fix Generation**: Automatically triggers for all `verified_hard_conflict` and `verified_narrative_anomaly` verdicts, generating a single concise bridging sentence.
