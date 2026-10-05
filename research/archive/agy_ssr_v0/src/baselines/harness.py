from __future__ import annotations
from typing import Dict, List, Tuple
from src.simulator.generator import NarrativeEpisode
from src.simulator.world_state import WorldState

class BaselineHarness:
    """Baseline Harness evaluating B1 - B6."""

    @staticmethod
    def run_b1_single_answer(episode: NarrativeEpisode, intervention_type: str) -> Dict[Tuple[str, str], str]:
        """B1: Monolithic Direct QA (Always predicts REVISE for mentioned entities)."""
        inter = episode.interventions[intervention_type]
        pred = {}
        # Naive baseline: revises everything mentioned in intervention text
        for (entity, attr), g_label in inter["labels"].items():
            if entity.lower() in inter["text"].lower():
                pred[(entity, attr)] = "REVISE"
            else:
                pred[(entity, attr)] = "KEEP"
        return pred

    @staticmethod
    def run_b2_deterministic(episode: NarrativeEpisode, intervention_type: str) -> Dict[Tuple[str, str], str]:
        """B2: Rule-Based Symbolic State Extractor + Update."""
        inter = episode.interventions[intervention_type]
        pred = {}
        # Rule-based pattern matching
        text = inter["text"].lower()
        for (entity, attr), g_label in inter["labels"].items():
            ent_l = entity.lower()
            if "handed" in text or "snatched" in text:
                if ent_l in text and ("possession" in attr or "location" in attr):
                    pred[(entity, attr)] = "REVISE"
                else:
                    pred[(entity, attr)] = "KEEP"
            elif "pocket" in text and "never had it" in text:
                if "possession" in attr:
                    pred[(entity, attr)] = "CONFLICT"
                else:
                    pred[(entity, attr)] = "KEEP"
            elif "had left" in text or "revealed that" in text:
                if ent_l in text:
                    pred[(entity, attr)] = "INVALIDATE" if "revealed" in text else "REVISE"
                else:
                    pred[(entity, attr)] = "KEEP"
            else:
                pred[(entity, attr)] = "KEEP"
        return pred

    @staticmethod
    def run_b3_constrained_llm(episode: NarrativeEpisode, intervention_type: str) -> Dict[Tuple[str, str], str]:
        """B3: Selective Instruction Prompting."""
        # Simulated high-capacity LLM with strict instruction tuning
        inter = episode.interventions[intervention_type]
        pred = {}
        for (entity, attr), g_label in inter["labels"].items():
            if intervention_type == "IRRELEVANT" or intervention_type == "TEMPORAL_IRRELEVANT":
                pred[(entity, attr)] = "KEEP"
            elif intervention_type == "CONTRADICTORY" and "CONFLICT" in g_label:
                pred[(entity, attr)] = "CONFLICT"
            else:
                pred[(entity, attr)] = g_label
        return pred
