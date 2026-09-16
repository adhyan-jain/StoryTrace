"""Unit tests for Pipeline Integrity assertions.

Ensures that zero-row ClickHouse reads, missing units, dangling entity references,
and candidate/verdict mismatches trigger PipelineIntegrityError immediately.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from backend.pipeline.integrity import verify_pipeline_integrity, PipelineIntegrityError


class DummyQuery:
    def __init__(self, result_rows):
        self.result_rows = result_rows


class TestPipelineIntegrity:
    def test_zero_units_raises_error(self):
        client = MagicMock()
        client.client.query.return_value = DummyQuery([])
        with pytest.raises(PipelineIntegrityError, match="0 narrative units found"):
            verify_pipeline_integrity(client, "test_su", expected_unit_count=5)

    def test_unit_count_mismatch_raises_error(self):
        client = MagicMock()
        client.client.query.side_effect = [
            DummyQuery([("u1", 1, "text1"), ("u2", 2, "text2")]),  # 2 units found
        ]
        with pytest.raises(PipelineIntegrityError, match="Unit count mismatch"):
            verify_pipeline_integrity(client, "test_su", expected_unit_count=5)

    def test_zero_events_when_required_raises_error(self):
        client = MagicMock()
        client.client.query.side_effect = [
            DummyQuery([("u1", 1, "text1")]),  # units
            DummyQuery([]),  # events
        ]
        with pytest.raises(PipelineIntegrityError, match="0 state events extracted"):
            verify_pipeline_integrity(client, "test_su", expected_unit_count=1, require_events=True)

    def test_dangling_unit_reference_raises_error(self):
        client = MagicMock()
        client.client.query.side_effect = [
            DummyQuery([("u1", 1, "text1")]),  # unit u1
            DummyQuery([("e1", "ent1", "u999", "attr", "val", "excerpt")]),  # event referencing u999
        ]
        with pytest.raises(PipelineIntegrityError, match="Dangling unit_id"):
            verify_pipeline_integrity(client, "test_su", expected_unit_count=1)

    def test_unregistered_entity_raises_error(self):
        client = MagicMock()
        client.client.query.side_effect = [
            DummyQuery([("u1", 1, "text1")]),  # unit u1
            DummyQuery([("e1", "ent1", "u1", "attr", "val", "excerpt")]),  # event referencing ent1
            DummyQuery([("ent999",)]),  # entities table has ent999, not ent1
        ]
        with pytest.raises(PipelineIntegrityError, match="unregistered entity_ids"):
            verify_pipeline_integrity(client, "test_su", expected_unit_count=1)

    def test_candidate_verdict_count_mismatch_raises_error(self):
        client = MagicMock()
        client.client.query.side_effect = [
            DummyQuery([("u1", 1, "text1"), ("u2", 2, "text2")]),  # units
            DummyQuery([("e1", "ent1", "u1", "attr", "val", "excerpt")]),  # events
            DummyQuery([("ent1",)]),  # entities
            DummyQuery([("c1", "u1", "u2")]),  # 1 candidate
            DummyQuery([]),  # 0 verdicts
        ]
        with pytest.raises(PipelineIntegrityError, match="Verdict count mismatch"):
            verify_pipeline_integrity(client, "test_su", expected_unit_count=2)

    def test_all_invariants_pass(self):
        client = MagicMock()
        client.client.query.side_effect = [
            DummyQuery([("u1", 1, "text1"), ("u2", 2, "text2")]),  # units
            DummyQuery([("e1", "ent1", "u1", "attr", "val", "excerpt")]),  # events
            DummyQuery([("ent1",)]),  # entities
            DummyQuery([("c1", "u1", "u2")]),  # candidate c1
            DummyQuery([("v1", "c1", "verified")]),  # verdict for c1
        ]
        res = verify_pipeline_integrity(client, "test_su", expected_unit_count=2)
        assert res["unit_count"] == 2
        assert res["event_count"] == 1
        assert res["candidate_count"] == 1
        assert res["verdict_count"] == 1
        assert res["entity_count"] == 1
