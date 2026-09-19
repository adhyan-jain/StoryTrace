import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from backend.llm.base import LLMProvider, LLMRequest, LLMResult
from backend.v2.story_state.models import (
    CandidateConflictV2, InvestigationVerdictV2, VerdictStatusV2
)
from backend.v2.agent.investigator import (
    InvestigationAgentV2, AgentActionV2, FinalVerdictV2, FixSuggestionV2
)
from backend.v2.agent.tools import AgentToolsV2

class MockLLMProviderV2(LLMProvider):
    def __init__(self, step_actions=None, final_verdict=None, fix_suggestion=None):
        self.step_actions = step_actions or []
        self.final_verdict = final_verdict
        self.fix_suggestion = fix_suggestion or FixSuggestionV2(sentence="Insert a travel cut.")
        self.call_count = 0
        self.tier = "local"

    @property
    def model(self) -> str:
        return "mock_model"

    def complete(self, request: LLMRequest, schema):
        if schema == AgentActionV2:
            if self.call_count < len(self.step_actions):
                action = self.step_actions[self.call_count]
                self.call_count += 1
                return LLMResult(value=action, model="mock", tier="local")
            return LLMResult(value=AgentActionV2(tool_name="finish", kwargs={}), model="mock", tier="local")
        elif schema == FinalVerdictV2:
            return LLMResult(value=self.final_verdict, model="mock", tier="local")
        elif schema == FixSuggestionV2:
            return LLMResult(value=self.fix_suggestion, model="mock", tier="local")
        raise ValueError(f"Unexpected schema: {schema}")


def test_final_verdict_v2_normalization():
    v = FinalVerdictV2(
        explanation="The character teleported between cities with no transit.",
        status="Verified_Hard_Conflict",
        severity="High",
        confidence="high",
        verbatim_evidence_quotes=["Bourne is in Zurich", "Bourne is in Paris"]
    )
    assert v.status == "verified_hard_conflict"
    assert v.severity == "critical"
    assert v.confidence == 0.9


def test_agent_loop_hard_conflict():
    final_v = FinalVerdictV2(
        explanation="Deceased character actively commands squad in next continuous scene.",
        status="verified_hard_conflict",
        severity="critical",
        confidence=0.95
    )
    actions = [
        AgentActionV2(tool_name="get_entity_timeline_v2", kwargs={"entity_id": "char_dan", "from_sequence": 1, "to_sequence": 5}),
        AgentActionV2(tool_name="finish", kwargs={})
    ]
    provider = MockLLMProviderV2(step_actions=actions, final_verdict=final_v)
    agent = InvestigationAgentV2(provider, "univ_test")
    
    mock_tools = MagicMock()
    mock_tools.get_entity_timeline_v2 = AsyncMock(return_value=[{"sequence_number": 2, "value": "dead"}])
    
    cand = CandidateConflictV2(
        id="cand_1",
        story_universe_id="univ_test",
        rule_type="physical_inversion",
        entity_ids=["char_dan"],
        attribute="physical.alive",
        prior_evidence_unit_id="u_2",
        prior_evidence_excerpt="Dan is killed instantly.",
        current_evidence_unit_id="u_3",
        current_evidence_excerpt="Dan orders the men to advance.",
        description="Dead entity active in continuous scene."
    )
    
    verdict = asyncio.run(agent._run_loop(cand, mock_tools))
    assert verdict.status == VerdictStatusV2.VERIFIED_HARD_CONFLICT
    assert verdict.severity == "critical"
    assert "Insert a travel cut." in verdict.suggested_fix


def test_agent_loop_narrative_anomaly():
    final_v = FinalVerdictV2(
        explanation="Character jumps between distant buildings under continuous pacing.",
        status="verified_narrative_anomaly",
        severity="warning",
        confidence=0.85
    )
    provider = MockLLMProviderV2(step_actions=[], final_verdict=final_v)
    agent = InvestigationAgentV2(provider, "univ_test")
    
    mock_tools = MagicMock()
    cand = CandidateConflictV2(
        id="cand_2",
        story_universe_id="univ_test",
        rule_type="continuous_spatial_jump",
        entity_ids=["char_cobb"],
        attribute="location",
        prior_evidence_unit_id="u_10",
        prior_evidence_excerpt="In the hotel room.",
        current_evidence_unit_id="u_11",
        current_evidence_excerpt="In the airport lobby.",
        description="Spatial jump under continuous pacing."
    )
    
    verdict = asyncio.run(agent._run_loop(cand, mock_tools))
    assert verdict.status == VerdictStatusV2.VERIFIED_NARRATIVE_ANOMALY
    assert verdict.severity == "warning"


def test_agent_loop_resolved():
    final_v = FinalVerdictV2(
        explanation="The prior scene contains explicit paramedic treatment, resolving the wound.",
        status="resolved",
        severity="info",
        confidence=0.9
    )
    provider = MockLLMProviderV2(step_actions=[], final_verdict=final_v)
    agent = InvestigationAgentV2(provider, "univ_test")
    
    mock_tools = MagicMock()
    cand = CandidateConflictV2(
        id="cand_3",
        story_universe_id="univ_test",
        rule_type="physical_inversion",
        entity_ids=["char_cole"],
        attribute="injury.arm",
        prior_evidence_unit_id="u_15",
        prior_evidence_excerpt="Paramedic cleans and bandages Cole's arm.",
        current_evidence_unit_id="u_18",
        current_evidence_excerpt="Cole's arm has healed.",
        description="Wound healed."
    )
    
    verdict = asyncio.run(agent._run_loop(cand, mock_tools))
    assert verdict.status == VerdictStatusV2.RESOLVED
    assert verdict.suggested_fix == ""


def test_agent_loop_detection_forces_finish():
    # Attempt duplicate identical tool calls
    duplicate_action = AgentActionV2(tool_name="get_spatial_trajectory", kwargs={"entity_id": "char_cobb"})
    actions = [duplicate_action, duplicate_action, duplicate_action]
    
    final_v = FinalVerdictV2(
        explanation="Loop detected, finalizing.",
        status="uncertain",
        severity="warning",
        confidence=0.5
    )
    provider = MockLLMProviderV2(step_actions=actions, final_verdict=final_v)
    agent = InvestigationAgentV2(provider, "univ_test")
    
    mock_tools = MagicMock()
    mock_tools.get_spatial_trajectory = AsyncMock(return_value=[{"room": "LOBBY"}])
    
    cand = CandidateConflictV2(
        id="cand_4",
        story_universe_id="univ_test",
        rule_type="continuous_spatial_jump",
        entity_ids=["char_cobb"],
        attribute="location",
        prior_evidence_unit_id="u_1",
        prior_evidence_excerpt="Lobby",
        current_evidence_unit_id="u_2",
        current_evidence_excerpt="Roof",
        description="Jump"
    )
    
    verdict = asyncio.run(agent._run_loop(cand, mock_tools))
    assert verdict.status == VerdictStatusV2.UNCERTAIN
