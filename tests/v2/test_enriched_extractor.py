import json
import pytest
from unittest.mock import MagicMock

from backend.ingestion.models import NarrativeUnit
from backend.llm.base import LLMProvider, LLMRequest, LLMResult, LLMParseError
from backend.pipeline.entity_resolution import EntityRegistry
from backend.v2.story_state.models import (
    SceneExtractionV2, TemporalAnchor, StateCategoryV2,
    StateEventV2, SceneCoPresence, RawSceneMetadataV2,
    RawStateFactV2, RawNarrativeEventV2, HierarchicalLocationV2
)
from backend.v2.pipeline.enriched_extractor import (
    EnrichedExtractor, _match_verbatim_excerpt
)

class MockLLMProvider(LLMProvider):
    def __init__(self, result_value: SceneExtractionV2 = None, should_fail: bool = False):
        self.result_value = result_value
        self.should_fail = should_fail
        self.last_request = None
        self.tier = "local"

    @property
    def model(self) -> str:
        return "mock_model"

    def complete(self, request: LLMRequest, schema):
        self.last_request = request
        if self.should_fail:
            raise LLMParseError("Mock parse error")
        return LLMResult(
            value=self.result_value,
            model="mock_model",
            tier="local"
        )


def test_match_verbatim_excerpt():
    text = "Cobb enters the hotel room and checks his briefcase."
    assert _match_verbatim_excerpt("hotel room", text) == "hotel room"
    assert _match_verbatim_excerpt("nonexistent phrase", text) is None


def test_valid_scene_extraction():
    extraction_obj = SceneExtractionV2(
        scene_metadata=RawSceneMetadataV2(
            setting_type="INT",
            environment="HOTEL",
            specific_room="SUITE_402",
            city_region="PARIS",
            time_of_day="NIGHT",
            time_anchor=TemporalAnchor.CONTINUOUS,
            present_entity_names=["COBB", "ARTHUR", "TOTEM"]
        ),
        state_facts=[
            RawStateFactV2(
                entity_name="COBB",
                entity_type="character",
                category=StateCategoryV2.POSSESSION,
                attribute="possession.totem",
                value="held",
                raw_excerpt="Cobb spins his brass totem on the table",
                confidence=0.95,
                establishment_type="explicit",
                spatial_details=HierarchicalLocationV2(
                    setting_type="INT",
                    environment="HOTEL",
                    specific_room="SUITE_402",
                    city_region="PARIS"
                )
            ),
            RawStateFactV2(
                entity_name="COBB",
                entity_type="character",
                category=StateCategoryV2.SPATIAL,
                attribute="location",
                value="SUITE_402",
                raw_excerpt="inside suite 402",
                confidence=0.9,
                establishment_type="explicit"
            )
        ],
        narrative_events=[
            RawNarrativeEventV2(
                event_type="transfer",
                actor_entity_names=["ARTHUR"],
                target_entity_names=["COBB"],
                raw_excerpt="Arthur hands the passport to Cobb",
                description="Arthur passes passport"
            )
        ]
    )
    
    mock_provider = MockLLMProvider(result_value=extraction_obj)
    extractor = EnrichedExtractor(mock_provider)
    
    unit = NarrativeUnit(
        unit_id="unit_101",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=5,
        title="INT. HOTEL PARIS - SUITE 402 - NIGHT",
        raw_text="Cobb spins his brass totem on the table inside suite 402. Arthur hands the passport to Cobb.",
        page_start=12,
        page_end=13
    )
    
    extraction = extractor.extract_scene(unit)
    assert extraction.scene_metadata.environment == "HOTEL"
    assert extraction.scene_metadata.specific_room == "SUITE_402"
    assert extraction.scene_metadata.city_region == "PARIS"
    assert extraction.scene_metadata.time_anchor == TemporalAnchor.CONTINUOUS
    assert len(extraction.scene_metadata.present_entity_names) == 3
    assert len(extraction.state_facts) == 2


def test_malformed_json_fallback():
    mock_provider = MockLLMProvider(should_fail=True)
    extractor = EnrichedExtractor(mock_provider)
    
    unit = NarrativeUnit(
        unit_id="unit_102",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=6,
        title="EXT. STREET - DAY",
        raw_text="People walk by.",
        page_start=14,
        page_end=14
    )
    
    extraction = extractor.extract_scene(unit)
    assert extraction.scene_metadata.setting_type == "EXT"
    assert extraction.scene_metadata.time_anchor == TemporalAnchor.CONTINUOUS
    assert len(extraction.state_facts) == 0


def test_possession_and_relational_transfer():
    extraction_obj = SceneExtractionV2(
        scene_metadata=RawSceneMetadataV2(
            setting_type="INT",
            environment="POLICE_STATION",
            specific_room="EVIDENCE_ROOM",
            city_region="NEW_YORK",
            time_of_day="DAY",
            time_anchor=TemporalAnchor.MOMENTS_LATER,
            present_entity_names=["MAYA", "COLE", "BADGE"]
        ),
        state_facts=[
            RawStateFactV2(
                entity_name="MAYA",
                entity_type="character",
                category=StateCategoryV2.POSSESSION,
                attribute="possession.badge",
                value="acquired",
                raw_excerpt="Maya confiscated Cole's badge",
                confidence=0.95,
                establishment_type="explicit",
                related_entity_name="COLE"
            ),
            RawStateFactV2(
                entity_name="COLE",
                entity_type="character",
                category=StateCategoryV2.POSSESSION,
                attribute="possession.badge",
                value="lost",
                raw_excerpt="Maya confiscated Cole's badge",
                confidence=0.95,
                establishment_type="explicit",
                related_entity_name="MAYA"
            )
        ],
        narrative_events=[]
    )
    
    mock_provider = MockLLMProvider(result_value=extraction_obj)
    extractor = EnrichedExtractor(mock_provider)
    
    unit = NarrativeUnit(
        unit_id="unit_103",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=7,
        title="INT. POLICE STATION - EVIDENCE ROOM - DAY",
        raw_text="Maya confiscated Cole's badge and locked it in the cabinet.",
        page_start=15,
        page_end=15
    )
    
    extraction = extractor.extract_scene(unit)
    state_events, co_presence = extractor.to_clickhouse_records(extraction, unit, "univ_1")
    
    assert len(state_events) == 2
    assert co_presence.environment == "POLICE_STATION"
    assert co_presence.specific_room == "EVIDENCE_ROOM"
    assert co_presence.time_anchor == "MOMENTS_LATER"
    
    maya_evt = [e for e in state_events if "maya" in e.entity_id][0]
    assert maya_evt.value == "acquired"
    assert maya_evt.related_entity_id == "cole"


def test_v1_failure_case_fine_grained_location():
    """Verify that V2 captures room-level transitions in the same building (V1 missed room-level shifts)."""
    extraction_obj = SceneExtractionV2(
        scene_metadata=RawSceneMetadataV2(
            setting_type="INT",
            environment="RESIDENCE",
            specific_room="KITCHEN",
            city_region="MINNEAPOLIS",
            time_of_day="DAY",
            time_anchor=TemporalAnchor.CONTINUOUS,
            present_entity_names=["JERRY", "JEAN"]
        ),
        state_facts=[
            RawStateFactV2(
                entity_name="JERRY",
                entity_type="character",
                category=StateCategoryV2.SPATIAL,
                attribute="location.room",
                value="KITCHEN",
                raw_excerpt="Jerry walks into the kitchen",
                confidence=0.9,
                establishment_type="explicit",
                spatial_details=HierarchicalLocationV2(
                    setting_type="INT",
                    environment="RESIDENCE",
                    specific_room="KITCHEN",
                    city_region="MINNEAPOLIS"
                )
            )
        ],
        narrative_events=[]
    )
    
    mock_provider = MockLLMProvider(result_value=extraction_obj)
    extractor = EnrichedExtractor(mock_provider)
    
    unit = NarrativeUnit(
        unit_id="unit_104",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=8,
        title="INT. RESIDENCE - KITCHEN - DAY",
        raw_text="Jerry walks into the kitchen, looking for his coffee.",
        page_start=16,
        page_end=16
    )
    
    extraction = extractor.extract_scene(unit)
    state_events, _ = extractor.to_clickhouse_records(extraction, unit, "univ_1")
    assert state_events[0].hier_specific_room == "KITCHEN"
    assert state_events[0].hier_environment == "RESIDENCE"
    assert state_events[0].hier_city_region == "MINNEAPOLIS"

def test_missing_optional_fields_and_defaults():
    sample_json = {
        "scene_metadata": {
            "setting_type": "EXT",
            "environment": "FOREST"
        },
        "state_facts": [],
        "narrative_events": []
    }
    mock_provider = MockLLMProvider(
        result_value=SceneExtractionV2(
            scene_metadata=RawSceneMetadataV2(
                setting_type="EXT",
                environment="FOREST",
                time_anchor=TemporalAnchor.CONTINUOUS
            ),
            state_facts=[],
            narrative_events=[]
        )
    )
    extractor = EnrichedExtractor(mock_provider)
    unit = NarrativeUnit(
        unit_id="unit_105",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=9,
        title="EXT. FOREST - DAY",
        raw_text="The trees rustle in the wind.",
        page_start=17,
        page_end=17
    )
    extraction = extractor.extract_scene(unit)
    state_events, co_presence = extractor.to_clickhouse_records(extraction, unit, "univ_1")
    assert co_presence.setting_type == "EXT"
    assert co_presence.environment == "FOREST"
    assert co_presence.specific_room == ""
    assert co_presence.time_anchor == "CONTINUOUS"
    assert len(state_events) == 0


def test_temporal_anchors_and_flashback():
    extraction_obj = SceneExtractionV2(
        scene_metadata=RawSceneMetadataV2(
            setting_type="INT",
            environment="MEMORIAL_HOSPITAL",
            specific_room="ICU",
            city_region="CHICAGO",
            time_of_day="NIGHT",
            time_anchor=TemporalAnchor.FLASHBACK,
            temporal_phrase="FIVE YEARS EARLIER",
            present_entity_names=["DR_WEST", "PEYTON"]
        ),
        state_facts=[
            RawStateFactV2(
                entity_name="PEYTON",
                entity_type="character",
                category=StateCategoryV2.PHYSICAL,
                attribute="injury.burns",
                value="injured",
                raw_excerpt="Peyton lies bandaged across his entire face",
                confidence=0.98,
                establishment_type="explicit"
            )
        ],
        narrative_events=[]
    )
    mock_provider = MockLLMProvider(result_value=extraction_obj)
    extractor = EnrichedExtractor(mock_provider)
    unit = NarrativeUnit(
        unit_id="unit_106",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=10,
        title="INT. MEMORIAL HOSPITAL - ICU - FLASHBACK",
        raw_text="FIVE YEARS EARLIER. Peyton lies bandaged across his entire face as Dr. West checks the monitors.",
        page_start=18,
        page_end=19
    )
    extraction = extractor.extract_scene(unit)
    state_events, co_presence = extractor.to_clickhouse_records(extraction, unit, "univ_1")
    assert co_presence.time_anchor == "FLASHBACK"
    assert state_events[0].time_anchor == "FLASHBACK"
    assert state_events[0].attribute == "injury.burns"
    assert state_events[0].value == "injured"


def test_epistemic_and_relational_extraction():
    extraction_obj = SceneExtractionV2(
        scene_metadata=RawSceneMetadataV2(
            setting_type="INT",
            environment="BANK_VAULT",
            specific_room="SAFETY_DEPOSIT_BOXES",
            city_region="ZURICH",
            time_of_day="DAY",
            time_anchor=TemporalAnchor.CONTINUOUS,
            present_entity_names=["BOURNE", "BANK_OFFICER"]
        ),
        state_facts=[
            RawStateFactV2(
                entity_name="BOURNE",
                entity_type="character",
                category=StateCategoryV2.EPISTEMIC,
                attribute="knowledge.true_identity",
                value="discovers",
                raw_excerpt="Bourne stares at the American passport bearing the name Jason Bourne",
                confidence=0.92,
                establishment_type="explicit"
            ),
            RawStateFactV2(
                entity_name="BOURNE",
                entity_type="character",
                category=StateCategoryV2.CLOTHING,
                attribute="clothing.jacket",
                value="red knit sweater",
                raw_excerpt="wearing a tattered red knit sweater",
                confidence=0.88,
                establishment_type="explicit"
            )
        ],
        narrative_events=[
            RawNarrativeEventV2(
                event_type="revelation",
                actor_entity_names=["BOURNE"],
                target_entity_names=[],
                raw_excerpt="Bourne stares at the American passport bearing the name Jason Bourne",
                description="Bourne discovers his identity name"
            )
        ]
    )
    mock_provider = MockLLMProvider(result_value=extraction_obj)
    extractor = EnrichedExtractor(mock_provider)
    unit = NarrativeUnit(
        unit_id="unit_107",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=11,
        title="INT. BANK VAULT - ZURICH - DAY",
        raw_text="Bourne, wearing a tattered red knit sweater, stares at the American passport bearing the name Jason Bourne.",
        page_start=20,
        page_end=20
    )
    extraction = extractor.extract_scene(unit)
    state_events, _ = extractor.to_clickhouse_records(extraction, unit, "univ_1")
    
    epistemic_evt = [e for e in state_events if "knowledge" in e.attribute][0]
    assert epistemic_evt.value == "discovers"
    assert epistemic_evt.hier_city_region == "ZURICH"
    
    clothing_evt = [e for e in state_events if "clothing" in e.attribute][0]
    assert clothing_evt.value == "red knit sweater"


def test_excerpt_grounding_rejects_hallucinations():
    extraction_obj = SceneExtractionV2(
        scene_metadata=RawSceneMetadataV2(
            setting_type="INT",
            environment="OFFICE"
        ),
        state_facts=[
            RawStateFactV2(
                entity_name="AGENT_SMITH",
                entity_type="character",
                category=StateCategoryV2.POSSESSION,
                attribute="possession.gun",
                value="held",
                raw_excerpt="COMPLETELY FABRICATED SENTENCE THAT DOES NOT EXIST",
                confidence=0.9,
                establishment_type="explicit"
            )
        ],
        narrative_events=[]
    )
    mock_provider = MockLLMProvider(result_value=extraction_obj)
    extractor = EnrichedExtractor(mock_provider)
    unit = NarrativeUnit(
        unit_id="unit_108",
        story_universe_id="univ_1",
        document_id="doc_1",
        unit_type="scene",
        sequence_number=12,
        title="INT. OFFICE - DAY",
        raw_text="The office is quiet. The clock ticks on the wall.",
        page_start=21,
        page_end=21
    )
    extraction = extractor.extract_scene(unit)
    # The hallucinated fact must be rejected
    assert len(extraction.state_facts) == 0
