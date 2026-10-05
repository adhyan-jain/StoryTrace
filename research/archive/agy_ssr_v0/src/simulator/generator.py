from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
from src.simulator.world_state import WorldState, StateClaim

CHARACTERS = ["Alice", "Bob", "Charlie", "Diana"]
PROPS = ["golden_key", "brass_lantern", "ancient_map", "silver_dagger"]
LOCATIONS = ["Library", "Armory", "Courtyard", "Tower"]

@dataclass
class NarrativeEpisode:
    episode_id: str
    base_text: List[str]
    initial_state: WorldState
    interventions: Dict[str, Dict[str, Any]]  # intervention_type -> {text, expected_delta, outcome_labels}

class StorySimulator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_episode(self, episode_id: str) -> NarrativeEpisode:
        c1, c2 = self.rng.sample(CHARACTERS, 2)
        prop = self.rng.choice(PROPS)
        loc1, loc2 = self.rng.sample(LOCATIONS, 2)

        state = WorldState()
        state.entities.update([c1, c2])
        state.props.add(prop)
        state.locations.update([loc1, loc2])

        # Step 1: Initial state
        state.set_claim(c1, "location", loc1, evidence=f"{c1} entered the {loc1}.")
        state.set_claim(c2, "location", loc2, evidence=f"{c2} rested in the {loc2}.")
        state.set_claim(c1, f"possession.{prop}", "held", evidence=f"{c1} carried the {prop}.")
        state.set_claim(c2, f"possession.{prop}", "none", evidence=f"{c2} had no items.")
        state.set_claim(c1, "status", "healthy", evidence=f"{c1} was unharmed.")

        base_text = [
            f"{c1} walked into the {loc1} holding the {prop}.",
            f"Meanwhile, {c2} remained in the {loc2} quietly reading.",
            f"{c1} inspected the {prop} carefully."
        ]

        state.sequence = 2

        # Generate 7 Minimal Intervention Types
        interventions = {}

        # 1. RESOLVING
        res_text = f"{c1} walked over to the {loc2} and handed the {prop} to {c2}."
        res_delta = {
            (c1, f"possession.{prop}"): "none",
            (c2, f"possession.{prop}"): "held",
            (c1, "location"): loc2
        }
        res_labels = {
            (c1, f"possession.{prop}"): "REVISE",
            (c2, f"possession.{prop}"): "REVISE",
            (c1, "location"): "REVISE",
            (c2, "location"): "KEEP",
            (c1, "status"): "KEEP"
        }
        interventions["RESOLVING"] = {
            "text": res_text,
            "delta": res_delta,
            "labels": res_labels
        }

        # 2. IRRELEVANT
        irr_text = "A heavy thunderstorm rattled the stained glass windows outside."
        irr_delta = {}
        irr_labels = {k: "KEEP" for k in [(c1, f"possession.{prop}"), (c2, f"possession.{prop}"), (c1, "location"), (c2, "location"), (c1, "status")]}
        interventions["IRRELEVANT"] = {
            "text": irr_text,
            "delta": irr_delta,
            "labels": irr_labels
        }

        # 3. CONTRADICTORY
        con_text = f"{c1} pulled the {prop} from {c2}'s pocket, though {c2} never had it."
        con_delta = {(c2, f"possession.{prop}"): "conflict"}
        con_labels = {
            (c1, f"possession.{prop}"): "KEEP",
            (c2, f"possession.{prop}"): "CONFLICT",
            (c1, "location"): "KEEP",
            (c2, "location"): "KEEP",
            (c1, "status"): "KEEP"
        }
        interventions["CONTRADICTORY"] = {
            "text": con_text,
            "delta": con_delta,
            "labels": con_labels
        }

        # 4. ALTERNATIVE_RESOLVING
        alt_text = f"{c2} snuck into the {loc1} and snatched the {prop} from {c1}'s bag."
        alt_delta = {
            (c1, f"possession.{prop}"): "none",
            (c2, f"possession.{prop}"): "held",
            (c2, "location"): loc1
        }
        alt_labels = {
            (c1, f"possession.{prop}"): "REVISE",
            (c2, f"possession.{prop}"): "REVISE",
            (c2, "location"): "REVISE",
            (c1, "location"): "KEEP",
            (c1, "status"): "KEEP"
        }
        interventions["ALTERNATIVE_RESOLVING"] = {
            "text": alt_text,
            "delta": alt_delta,
            "labels": alt_labels
        }

        # 5. TEMPORAL_RESOLVING
        temp_res_text = f"Hours earlier before entering the {loc1}, {c1} had left the {prop} in the vault."
        temp_res_delta = {(c1, f"possession.{prop}"): "none"}
        temp_res_labels = {
            (c1, f"possession.{prop}"): "REVISE",
            (c2, f"possession.{prop}"): "KEEP",
            (c1, "location"): "KEEP",
            (c2, "location"): "KEEP",
            (c1, "status"): "KEEP"
        }
        interventions["TEMPORAL_RESOLVING"] = {
            "text": temp_res_text,
            "delta": temp_res_delta,
            "labels": temp_res_labels
        }

        # 6. TEMPORAL_IRRELEVANT
        temp_irr_text = f"Years ago, the {loc1} was constructed by ancient stone masons."
        temp_irr_delta = {}
        temp_irr_labels = {k: "KEEP" for k in irr_labels}
        interventions["TEMPORAL_IRRELEVANT"] = {
            "text": temp_irr_text,
            "delta": temp_irr_delta,
            "labels": temp_irr_labels
        }

        # 7. ENTITY_DISAMBIGUATING
        dis_text = f"It was revealed that {c1}'s cousin, not {c1}, was the one who arrived at the {loc1}."
        dis_delta = {(c1, "location"): "unknown", (c1, f"possession.{prop}"): "unknown"}
        dis_labels = {
            (c1, "location"): "INVALIDATE",
            (c1, f"possession.{prop}"): "INVALIDATE",
            (c2, "location"): "KEEP",
            (c2, f"possession.{prop}"): "KEEP",
            (c1, "status"): "KEEP"
        }
        interventions["ENTITY_DISAMBIGUATING"] = {
            "text": dis_text,
            "delta": dis_delta,
            "labels": dis_labels
        }

        return NarrativeEpisode(
            episode_id=episode_id,
            base_text=base_text,
            initial_state=state,
            interventions=interventions
        )
