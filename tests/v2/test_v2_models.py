import pytest
from backend.v2.story_state.models import (
    TemporalAnchor, VerdictStatusV2, StateEventV2,
    SceneCoPresence, CandidateConflictV2, InvestigationVerdictV2
)

def test_temporal_anchor_enum():
    assert TemporalAnchor.CONTINUOUS.value == "CONTINUOUS"
    assert TemporalAnchor.MOMENTS_LATER.value == "MOMENTS_LATER"
    assert TemporalAnchor.FLASHBACK.value == "FLASHBACK"

def test_state_event_v2_instantiation():
    event = StateEventV2(
        id="evt_123",
        story_universe_id="univ_abc",
        entity_id="char_cobb",
        attribute="location.room",
        value="HOTEL_ROOM",
        unit_id="unit_1",
        sequence_number=1,
        page_ref=1,
        raw_excerpt="Cobb sits in the hotel room.",
        hier_setting_type="INT",
        hier_environment="HOTEL",
        hier_specific_room="HOTEL_ROOM",
        hier_city_region="MOMBASA",
        time_anchor=TemporalAnchor.CONTINUOUS.value,
        related_entity_id="char_mal"
    )
    assert event.entity_id == "char_cobb"
    assert event.hier_environment == "HOTEL"
    assert event.hier_city_region == "MOMBASA"
    assert event.time_anchor == "CONTINUOUS"

def test_scene_co_presence():
    co_pres = SceneCoPresence(
        id="cp_1",
        story_universe_id="univ_abc",
        unit_id="unit_1",
        sequence_number=1,
        entity_ids=["char_cobb", "char_arthur", "prop_totem"],
        setting_type="INT",
        environment="WORKSHOP",
        specific_room="BASEMENT",
        time_of_day="DAY",
        time_anchor="CONTINUOUS"
    )
    assert len(co_pres.entity_ids) == 3
    assert "char_arthur" in co_pres.entity_ids

def test_candidate_conflict_v2():
    conflict = CandidateConflictV2(
        id="cand_1",
        story_universe_id="univ_abc",
        rule_type="co_presence_collision",
        entity_ids=["char_cobb", "char_saito"],
        attribute="co_presence",
        prior_evidence_unit_id="unit_1",
        prior_evidence_excerpt="Cobb is in Tokyo.",
        current_evidence_unit_id="unit_2",
        current_evidence_excerpt="Cobb is in Paris with Saito moments later.",
        description="Impossible co-presence and instantaneous travel under CONTINUOUS pacing.",
        severity_hint="critical"
    )
    assert conflict.rule_type == "co_presence_collision"
    assert len(conflict.entity_ids) == 2

def test_investigation_verdict_v2():
    verdict = InvestigationVerdictV2(
        id="verd_1",
        candidate_id="cand_1",
        status=VerdictStatusV2.VERIFIED_HARD_CONFLICT,
        severity="critical",
        explanation="Cobb transitions between Tokyo and Paris across continuous scenes with no temporal bridge.",
        confidence=0.95,
        investigation_actions=["get_entity_timeline_v2", "get_spatial_trajectory"],
        suggested_fix="Insert an establishing scene or temporal bridge."
    )
    assert verdict.status == VerdictStatusV2.VERIFIED_HARD_CONFLICT
    assert verdict.confidence == 0.95
