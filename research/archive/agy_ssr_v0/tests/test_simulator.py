import pytest
from src.simulator.generator import StorySimulator

def test_simulator_generation():
    sim = StorySimulator(seed=42)
    ep = sim.generate_episode("test_1")
    assert ep.episode_id == "test_1"
    assert len(ep.base_text) == 3
    assert len(ep.interventions) == 7
    for itype in ["RESOLVING", "IRRELEVANT", "CONTRADICTORY", "ALTERNATIVE_RESOLVING", "TEMPORAL_RESOLVING", "TEMPORAL_IRRELEVANT", "ENTITY_DISAMBIGUATING"]:
        assert itype in ep.interventions
