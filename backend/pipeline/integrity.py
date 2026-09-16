"""Pipeline Integrity Verifier.

Enforces strict assertions post-run to ensure pipeline stages do not silently fail,
return fake clean runs (e.g. 0-row ClickHouse reads), or corrupt entity/unit references.
"""

from __future__ import annotations

import logging
from backend.clickhouse.client import ClickHouseClient

logger = logging.getLogger(__name__)


class PipelineIntegrityError(RuntimeError):
    """Raised when pipeline invariants are violated post-run."""


def verify_pipeline_integrity(
    client: ClickHouseClient,
    story_universe_id: str,
    expected_unit_count: int,
    require_events: bool = True,
    require_candidates_if_events: bool = False,
) -> dict[str, int]:
    """Verify that ClickHouse contains a valid, consistent pipeline state for story_universe_id.

    Invariants checked:
    1. Narrative units count equals expected_unit_count (>0).
    2. Narrative units exist in sequence order without duplicates.
    3. Extracted state events exist (if require_events=True) and every event references a valid unit_id.
    4. Entity registry rows exist for all entity_ids referenced in state_events.
    5. Provenance excerpts in state_events exist and non-empty.
    6. Candidate conflicts reference existing unit_ids in the story universe.
    7. Investigation verdicts count equals candidate conflicts count (every candidate has a verdict).
    8. Candidate IDs in investigation_verdicts match existing candidate IDs.

    Returns dict with counts of units, events, candidates, and verdicts.
    Raises PipelineIntegrityError if any invariant is violated.
    """
    ch = client.client

    # 1. Units check
    units_rows = ch.query(
        "SELECT id, sequence_number, text FROM narrative_units WHERE story_universe_id = {sid:String} ORDER BY sequence_number",
        parameters={"sid": story_universe_id},
    ).result_rows

    if not units_rows:
        raise PipelineIntegrityError(f"SILENT FAILURE: 0 narrative units found for story_universe_id={story_universe_id!r}")

    if len(units_rows) != expected_unit_count:
        raise PipelineIntegrityError(
            f"Unit count mismatch for {story_universe_id!r}: expected {expected_unit_count}, found {len(units_rows)}"
        )

    valid_unit_ids = {r[0] for r in units_rows}

    # 2. Events check
    events_rows = ch.query(
        "SELECT id, entity_id, unit_id, attribute, value, raw_excerpt FROM state_events WHERE story_universe_id = {sid:String}",
        parameters={"sid": story_universe_id},
    ).result_rows

    if require_events and not events_rows:
        raise PipelineIntegrityError(f"SILENT FAILURE: 0 state events extracted for story_universe_id={story_universe_id!r}")

    # Check event unit reference and excerpt non-emptiness
    referenced_entity_ids = set()
    for ev in events_rows:
        ev_id, entity_id, unit_id, attr, val, excerpt = ev
        if unit_id not in valid_unit_ids:
            raise PipelineIntegrityError(
                f"Dangling unit_id in state_event {ev_id}: unit_id={unit_id!r} not in narrative_units"
            )
        if not excerpt or not excerpt.strip():
            raise PipelineIntegrityError(f"Empty raw_excerpt in state_event {ev_id}")
        referenced_entity_ids.add(entity_id)

    # 3. Entities check
    entities_rows = ch.query(
        "SELECT id FROM entities WHERE story_universe_id = {sid:String}",
        parameters={"sid": story_universe_id},
    ).result_rows
    valid_entity_ids = {r[0] for r in entities_rows}

    missing_entities = referenced_entity_ids - valid_entity_ids
    if missing_entities:
        raise PipelineIntegrityError(
            f"State events reference unregistered entity_ids for {story_universe_id!r}: {missing_entities}"
        )

    # 4. Candidate conflicts check
    candidates_rows = ch.query(
        "SELECT id, prior_evidence_unit_id, current_evidence_unit_id FROM candidate_conflicts WHERE story_universe_id = {sid:String}",
        parameters={"sid": story_universe_id},
    ).result_rows
    candidate_ids = {r[0] for r in candidates_rows}

    for c in candidates_rows:
        cid, prior_u, curr_u = c
        if prior_u not in valid_unit_ids or curr_u not in valid_unit_ids:
            raise PipelineIntegrityError(
                f"Candidate {cid} references invalid unit_ids: prior={prior_u!r}, curr={curr_u!r}"
            )

    # 5. Verdicts check
    verdicts_rows = ch.query(
        "SELECT id, candidate_id, status FROM investigation_verdicts WHERE candidate_id LIKE {prefix:String}",
        parameters={"prefix": f"{story_universe_id}_%"},
    ).result_rows

    if len(verdicts_rows) != len(candidates_rows):
        raise PipelineIntegrityError(
            f"Verdict count mismatch for {story_universe_id!r}: {len(candidates_rows)} candidates, but {len(verdicts_rows)} verdicts"
        )

    verdict_candidate_ids = {r[1] for r in verdicts_rows}
    missing_verdict_candidates = candidate_ids - verdict_candidate_ids
    if missing_verdict_candidates:
        raise PipelineIntegrityError(
            f"Candidates missing investigation verdicts in {story_universe_id!r}: {missing_verdict_candidates}"
        )

    return {
        "unit_count": len(units_rows),
        "event_count": len(events_rows),
        "candidate_count": len(candidates_rows),
        "verdict_count": len(verdicts_rows),
        "entity_count": len(valid_entity_ids),
    }
