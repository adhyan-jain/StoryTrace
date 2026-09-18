import pytest
from unittest.mock import MagicMock

from backend.v2.clickhouse.client import ClickHouseClientV2
from backend.v2.candidate_detection.detector import CandidateDetectorV2, ALL_RULES
from backend.v2.story_state.models import CandidateConflictV2

class MockQueryResult:
    def __init__(self, rows):
        self.result_rows = rows

class MockClickHouseClient:
    def __init__(self, rule_responses=None):
        self.rule_responses = rule_responses or {}
        self.client = MagicMock()
        self.client.query.side_effect = self._query_side_effect

    def _query_side_effect(self, query, parameters=None):
        for rule_name, sql in ALL_RULES:
            if sql.strip() == query.strip():
                return MockQueryResult(self.rule_responses.get(rule_name, []))
        return MockQueryResult([])

    def insert_candidate_conflicts_v2(self, candidates):
        pass


def test_rule_1_possession_machine():
    mock_row = [
        "possession_machine",
        ["char_cobb"],
        "possession.gun",
        "unit_1",
        "Cobb loses his gun in the canal",
        "unit_5",
        "Cobb draws his gun from his holster",
        "Possession anomaly for char_cobb on possession.gun: lost -> held",
        "warning"
    ]
    mock_client = MockClickHouseClient({"possession_machine": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.rule_type == "possession_machine"
    assert "char_cobb" in c.entity_ids
    assert c.prior_evidence_unit_id == "unit_1"
    assert c.current_evidence_unit_id == "unit_5"
    assert c.severity_hint == "warning"


def test_rule_2_co_presence_collision():
    mock_row = [
        "co_presence_collision",
        ["char_cobb", "char_arthur"],
        "co_presence",
        "unit_10",
        "Present in HOTEL (SUITE_402)",
        "unit_11",
        "Present in AIRPORT (TERMINAL_1)",
        "Entities present in continuous scenes across disparate environments",
        "critical"
    ]
    mock_client = MockClickHouseClient({"co_presence_collision": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.rule_type == "co_presence_collision"
    assert len(c.entity_ids) == 2
    assert c.severity_hint == "critical"


def test_rule_3_spatial_jump():
    mock_row = [
        "continuous_spatial_jump",
        ["char_bourne"],
        "location",
        "unit_20",
        "Bourne is in Zurich",
        "unit_21",
        "Bourne walks through the streets of Paris",
        "Unbridged continuous spatial jump for char_bourne from [ZURICH] to [PARIS]",
        "critical"
    ]
    mock_client = MockClickHouseClient({"continuous_spatial_jump": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.rule_type == "continuous_spatial_jump"
    assert c.prior_evidence_unit_id == "unit_20"
    assert c.current_evidence_unit_id == "unit_21"


def test_rule_4_physical_inversion():
    mock_row = [
        "physical_inversion",
        ["char_peyton"],
        "injury.face",
        "unit_30",
        "Peyton suffered third-degree facial burns",
        "unit_32",
        "Peyton smiles with unblemished skin",
        "Physical state inversion for char_peyton on injury.face: injured -> healed",
        "warning"
    ]
    mock_client = MockClickHouseClient({"physical_inversion": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.rule_type == "physical_inversion"
    assert c.attribute == "injury.face"


def test_rule_5_clothing_swap():
    mock_row = [
        "clothing_swap",
        ["char_bond"],
        "clothing.suit",
        "unit_40",
        "Bond wears a black tuxedo",
        "unit_41",
        "Bond appears in a white linen suit",
        "Instantaneous wardrobe change for char_bond",
        "info"
    ]
    mock_client = MockClickHouseClient({"clothing_swap": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.rule_type == "clothing_swap"


def test_rule_6_epistemic_anomaly():
    mock_row = [
        "epistemic_anomaly",
        ["char_detective"],
        "knowledge.killer_identity",
        "unit_50",
        "Detective is unaware of the killer's name",
        "unit_51",
        "Detective addresses the killer by name",
        "Epistemic jump for char_detective: was unaware but now knows",
        "warning"
    ]
    mock_client = MockClickHouseClient({"epistemic_anomaly": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.rule_type == "epistemic_anomaly"


def test_rule_7_relational_rupture():
    mock_row = [
        "relational_rupture",
        ["char_alice"],
        "relation.bob",
        "unit_60",
        "Alice is Bob's sworn enemy",
        "unit_61",
        "Alice embraces Bob as her closest partner",
        "Unexplained alliance transition for char_alice",
        "warning"
    ]
    mock_client = MockClickHouseClient({"relational_rupture": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.rule_type == "relational_rupture"


def test_rule_8_chronology_inversion():
    mock_row = [
        "chronology_inversion",
        ["char_protagonist"],
        "location",
        "unit_70",
        "Unit 70 flashback",
        "unit_75",
        "Unit 75 flashback sequence",
        "Non-linear flashback marker detected",
        "info"
    ]
    mock_client = MockClickHouseClient({"chronology_inversion": [mock_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    assert len(conflicts) == 1
    assert conflicts[0].rule_type == "chronology_inversion"


def test_candidate_deduplication():
    duplicate_row = [
        "possession_machine",
        ["char_cobb"],
        "possession.gun",
        "unit_1",
        "Cobb loses his gun",
        "unit_5",
        "Cobb holds his gun",
        "Possession anomaly",
        "warning"
    ]
    mock_client = MockClickHouseClient({"possession_machine": [duplicate_row, duplicate_row]})
    detector = CandidateDetectorV2(mock_client)
    
    conflicts = detector.detect_conflicts("univ_test")
    # Must deduplicate to 1
    assert len(conflicts) == 1
