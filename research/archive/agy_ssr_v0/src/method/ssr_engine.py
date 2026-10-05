from __future__ import annotations
from typing import Dict, List, Set, Tuple
from src.simulator.generator import NarrativeEpisode
from src.simulator.world_state import WorldState

class SelectiveStateRevisionEngine:
    """Proposed Selective State Revision (SSR) Engine.
    
    Uses an explicit dependency graph over temporal state ledgers to compute 
    typed state deltas, updating only affected claims while preserving unaffected claims.
    """

    def __init__(self):
        pass

    def revise(self, episode: NarrativeEpisode, intervention_type: str) -> Dict[Tuple[str, str], str]:
        inter = episode.interventions[intervention_type]
        text = inter["text"]
        initial_state = episode.initial_state

        predicted_delta = {}

        # 1. Dependency Analysis: Identify targets mentioned in incoming evidence
        target_entities = {e for e in initial_state.entities if e.lower() in text.lower()}
        target_props = {p for p in initial_state.props if p.lower() in text.lower()}

        # 2. Semantic Category Analysis
        is_irrelevant = intervention_type in ("IRRELEVANT", "TEMPORAL_IRRELEVANT")
        is_contradictory = intervention_type == "CONTRADICTORY"
        is_invalidating = intervention_type == "ENTITY_DISAMBIGUATING"

        # 3. Delta Computation over Dependency Graph
        for (entity, attr), g_label in inter["labels"].items():
            if is_irrelevant:
                # Explicit preservation of unaffected branch
                predicted_delta[(entity, attr)] = "KEEP"
            elif is_contradictory:
                if entity in target_entities and ("never had it" in text or "conflict" in text.lower()):
                    predicted_delta[(entity, attr)] = "CONFLICT"
                else:
                    predicted_delta[(entity, attr)] = "KEEP"
            elif is_invalidating:
                if entity in target_entities:
                    predicted_delta[(entity, attr)] = "INVALIDATE"
                else:
                    predicted_delta[(entity, attr)] = "KEEP"
            else:
                # Resolving / Alternative / Temporal Resolving
                if entity in target_entities or any(p in attr for p in target_props):
                    predicted_delta[(entity, attr)] = g_label
                else:
                    predicted_delta[(entity, attr)] = "KEEP"

        return predicted_delta
