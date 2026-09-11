"""Main eval orchestrator: runs the real pipeline against a golden dataset,
then measures each phase concurrently.

Four workstreams:
  A. run_pipeline_subagent    -- parsing -> extraction -> detection -> investigation
  B. measure_extraction_subagent
  C. measure_detection_subagent
  D. measure_investigation_subagent

B, C, D are independent reads against ClickHouse and run concurrently via
asyncio.gather once A has finished writing. This module never modifies
backend/pipeline, backend/candidate_detection, or backend/agent -- it only
calls their existing public functions with a dedicated eval
story_universe_id ("eval_controlled_test" for the shipped golden dataset).
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.state_extraction import extract_state_events, write_state_events
from data.eval.golden_dataset import GOLDEN_DATASET, GoldenDataset
from scripts.eval.engine import (
    EvalReport,
    PhaseMetrics,
    compute_metrics,
    match_conflict,
    match_state_event,
    match_verdict,
)

# Demo story_universe_ids the eval must never touch -- see CLAUDE.md /
# docker-compose.yml conventions. The eval is only ever allowed to clear
# rows for an "eval_"-prefixed id.
DEMO_IDS = {"demo_se7en", "demo_dark_knight", "demo_controlled_test"}
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_provider():
    """Same provider selection as scripts/run_pipeline_on_text.py, kept as
    a separate copy (not imported) since that script hardcodes its own
    module-level STORY_UNIVERSE_ID and isn't meant to be imported."""
    provider = os.environ.get("MODEL_PROVIDER", "ollama")
    if provider == "vertexai":
        from backend.llm.vertexai import VertexAIProvider

        return VertexAIProvider()
    if provider == "gemini":
        from backend.llm.client import GeminiProvider

        return GeminiProvider()
    from backend.llm.ollama import OllamaProvider

    return OllamaProvider()


def load_units(golden: GoldenDataset) -> list[NarrativeUnit]:
    """Same paragraph-splitting convention as scripts/run_pipeline_on_text.py
    (blank-line-separated paragraphs, 1-indexed sequence_number)."""
    doc_path = golden.document_path
    if not os.path.isabs(doc_path):
        doc_path = os.path.join(_REPO_ROOT, doc_path)
    with open(doc_path, encoding="utf-8") as f:
        text = f.read()

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units = []
    for i, paragraph in enumerate(paragraphs, start=1):
        units.append(
            NarrativeUnit(
                unit_id=f"{golden.story_universe_id}_unit_{i}",
                story_universe_id=golden.story_universe_id,
                document_id=golden.story_universe_id,
                unit_type="scene",
                sequence_number=i,
                title=f"Scene {i}",
                page_start=1,
                page_end=1,
                raw_text=paragraph,
            )
        )
    return units


def _wait_for_count(
    client: ClickHouseClient, table: str, story_universe_id: str, expected: int, timeout_s: float = 10.0
) -> None:
    """Poll until `table` actually reports `expected` rows for this
    story_universe_id, or give up after timeout_s.

    Needed because ClickHouse Cloud's SharedMergeTree does not appear to
    give the same immediate-read-your-write guarantee as local/Docker
    ClickHouse for a table whose rows were deleted moments earlier: a real
    run had `insert_narrative_units` return normally, extraction/detection/
    investigation all complete successfully downstream (state_events and
    candidate_conflicts are inserted much later, with LLM calls in between,
    and were consistently visible), yet a `SELECT count()` against
    narrative_units run right after the insert returned 0 -- the metrics
    phases then resolved every unit_id -> sequence_number lookup to -1,
    silently zeroing out Detection/Investigation's scores without raising
    any error. Only narrative_units (inserted immediately after the
    per-run DELETE, with no delay before the next read) was ever observed
    doing this; state_events/candidate_conflicts happen to get a natural
    delay from the LLM calls in between and were never observed stale.
    """
    deadline = time.time() + timeout_s
    last_seen = -1
    while time.time() < deadline:
        last_seen = client.client.command(
            f"SELECT count() FROM {table} WHERE story_universe_id = {{sid:String}}",
            parameters={"sid": story_universe_id},
        )
        if int(last_seen) == expected:
            return
        time.sleep(0.25)
    raise RuntimeError(
        f"{table} never reached {expected} rows for {story_universe_id!r} within "
        f"{timeout_s}s (last saw {last_seen}) -- ClickHouse Cloud consistency lag, not a pipeline bug"
    )


def _clear_eval_data(client: ClickHouseClient, story_universe_id: str) -> None:
    if story_universe_id in DEMO_IDS or not story_universe_id.startswith("eval_"):
        raise RuntimeError(
            f"refusing to clear story_universe_id {story_universe_id!r} -- "
            "eval may only ever clear an 'eval_'-prefixed id, never a demo id"
        )
    settings = {"mutations_sync": "1"}
    for table in ("narrative_units", "entities", "state_events", "candidate_conflicts", "processing_status"):
        client.client.command(
            f"ALTER TABLE {table} DELETE WHERE story_universe_id = {{sid:String}}",
            parameters={"sid": story_universe_id},
            settings=settings,
        )
    # investigation_verdicts has no story_universe_id column; candidate_id is
    # f"{story_universe_id}_{hex}" (backend/candidate_detection/detector.py).
    client.client.command(
        "ALTER TABLE investigation_verdicts DELETE WHERE candidate_id LIKE {prefix:String}",
        parameters={"prefix": f"{story_universe_id}_%"},
        settings=settings,
    )


async def _entity_map(client: ClickHouseClient, story_universe_id: str) -> dict[str, tuple[str, str]]:
    def q():
        return client.client.query(
            "SELECT id, name, type FROM entities WHERE story_universe_id = {sid:String}",
            parameters={"sid": story_universe_id},
        ).result_rows

    rows = await asyncio.to_thread(q)
    return {r[0]: (r[1], r[2]) for r in rows}


async def _unit_seq_map(client: ClickHouseClient, story_universe_id: str) -> dict[str, int]:
    def q():
        return client.client.query(
            "SELECT id, sequence_number FROM narrative_units WHERE story_universe_id = {sid:String}",
            parameters={"sid": story_universe_id},
        ).result_rows

    rows = await asyncio.to_thread(q)
    return {r[0]: r[1] for r in rows}


async def run_pipeline_subagent(golden: GoldenDataset, provider) -> dict:
    """Subagent A. Clears any prior eval run for this story_universe_id,
    then runs parsing -> extraction -> detection -> investigation against
    the real pipeline code, so the eval always measures current behavior."""
    notes: list[str] = []
    client = ClickHouseClient()
    eval_id = golden.story_universe_id

    await asyncio.to_thread(_clear_eval_data, client, eval_id)

    units = load_units(golden)
    notes.append(f"Loaded {len(units)} narrative units from {golden.document_path}")
    await asyncio.to_thread(client.insert_narrative_units, units)
    await asyncio.to_thread(_wait_for_count, client, "narrative_units", eval_id, len(units))

    registry = EntityRegistry(eval_id)
    total_events = 0
    for unit in units:
        events = await extract_state_events(unit, eval_id, provider, registry)
        await write_state_events(events, client)
        total_events += len(events)
    await asyncio.to_thread(client.insert_entities, registry.get_all())
    notes.append(f"Extracted {total_events} state events across {len(units)} units")

    detector = CandidateDetector(client)
    conflicts = await asyncio.to_thread(detector.detect_conflicts, eval_id)
    await asyncio.to_thread(client.insert_candidate_conflicts, conflicts)
    notes.append(f"Detected {len(conflicts)} candidate conflicts")

    agent = InvestigationAgent(provider, eval_id)
    verdict_count = 0
    for conflict in conflicts:
        try:
            verdict = await agent.investigate_async(conflict)
            await asyncio.to_thread(client.insert_investigation_verdicts, [verdict])
            verdict_count += 1
        except Exception as e:  # one bad investigation must not abort the eval run
            notes.append(f"Investigation failed for candidate {conflict.id}: {e}")
    notes.append(f"Produced {verdict_count}/{len(conflicts)} investigation verdicts")

    return {"notes": notes, "total_events": total_events, "conflicts": len(conflicts)}


async def measure_extraction_subagent(golden: GoldenDataset) -> tuple[PhaseMetrics, dict]:
    """Subagent B. Fetches extracted StateEvents (joined against `entities`
    for entity_name/type, since state_events itself only stores entity_id)
    and compares against golden.state_events."""
    client = ClickHouseClient()
    entity_map = await _entity_map(client, golden.story_universe_id)

    def q():
        return client.client.query(
            """SELECT entity_id, attribute, value, sequence_number, raw_excerpt, confidence
               FROM state_events WHERE story_universe_id = {sid:String}
               ORDER BY sequence_number""",
            parameters={"sid": golden.story_universe_id},
        ).result_rows

    rows = await asyncio.to_thread(q)

    extracted = []
    for entity_id, attribute, value, seq, raw_excerpt, confidence in rows:
        name, etype = entity_map.get(entity_id, (entity_id, "unknown"))
        extracted.append(
            {
                "entity_name": name,
                "entity_type": etype,
                "attribute": attribute,
                "value": value,
                "sequence_number": seq,
                "raw_excerpt": raw_excerpt,
                "confidence": confidence,
            }
        )

    metrics = compute_metrics(
        phase="extraction",
        predicted=extracted,
        golden=golden.state_events,
        match_fn=lambda pred, gold: match_state_event(pred, gold, tolerance_sequences=1),
    )

    # Step 6: per-unit breakdown, keyed by sequence number.
    per_unit: dict[int, dict] = {}

    def _bucket(seq: int) -> dict:
        return per_unit.setdefault(seq, {"extracted": 0, "matched": 0, "missed_attrs": []})

    for event in extracted:
        _bucket(event["sequence_number"])["extracted"] += 1
    for gold in golden.state_events:
        _bucket(gold.sequence_number)
    for detail in metrics.details:
        if detail["status"] == "TP":
            _bucket(detail["predicted"]["sequence_number"])["matched"] += 1
        elif detail["status"] == "FN":
            gold = detail["golden"]
            _bucket(gold.sequence_number)["missed_attrs"].append(f"{gold.attribute}={gold.value}")

    return metrics, per_unit


async def measure_detection_subagent(golden: GoldenDataset) -> PhaseMetrics:
    """Subagent C. Fetches CandidateConflicts, resolves entity_id ->
    entity_name and unit_id -> sequence_number, compares against
    golden.conflicts regardless of expected_verdict (this phase only
    measures whether the SQL detector finds the right candidates at all)."""
    client = ClickHouseClient()
    entity_map = await _entity_map(client, golden.story_universe_id)
    unit_seq = await _unit_seq_map(client, golden.story_universe_id)

    def q():
        return client.client.query(
            """SELECT id, entity_id, attribute, prior_evidence_unit_id, current_evidence_unit_id
               FROM candidate_conflicts WHERE story_universe_id = {sid:String}""",
            parameters={"sid": golden.story_universe_id},
        ).result_rows

    rows = await asyncio.to_thread(q)

    candidates = []
    for cid, entity_id, attribute, prior_unit, current_unit in rows:
        name, _ = entity_map.get(entity_id, (entity_id, "unknown"))
        candidates.append(
            {
                "id": cid,
                "entity_name": name,
                "attribute": attribute,
                "prior_sequence": unit_seq.get(prior_unit, -1),
                "current_sequence": unit_seq.get(current_unit, -1),
            }
        )

    return compute_metrics(
        phase="detection",
        predicted=candidates,
        golden=golden.conflicts,
        match_fn=lambda pred, gold: match_conflict(pred, gold, tolerance_sequences=2),
    )


async def measure_investigation_subagent(golden: GoldenDataset) -> PhaseMetrics:
    """Subagent D. Joins InvestigationVerdicts against their CandidateConflict
    (investigation_verdicts has no story_universe_id column of its own, only
    candidate_id), resolves entity/sequence context, and compares the
    verdict's status against golden.conflicts' expected_verdict."""
    client = ClickHouseClient()
    entity_map = await _entity_map(client, golden.story_universe_id)
    unit_seq = await _unit_seq_map(client, golden.story_universe_id)

    def q():
        return client.client.query(
            """SELECT v.status, v.confidence, c.entity_id, c.attribute,
                      c.prior_evidence_unit_id, c.current_evidence_unit_id
               FROM investigation_verdicts v
               JOIN candidate_conflicts c ON v.candidate_id = c.id
               WHERE c.story_universe_id = {sid:String}""",
            parameters={"sid": golden.story_universe_id},
        ).result_rows

    rows = await asyncio.to_thread(q)

    verdicts = []
    for status, confidence, entity_id, attribute, prior_unit, current_unit in rows:
        name, _ = entity_map.get(entity_id, (entity_id, "unknown"))
        verdicts.append(
            {
                "entity_name": name,
                "attribute": attribute,
                "status": status,
                "confidence": confidence,
                "prior_sequence": unit_seq.get(prior_unit, -1),
                "current_sequence": unit_seq.get(current_unit, -1),
            }
        )

    return compute_metrics(
        phase="investigation",
        predicted=verdicts,
        golden=golden.conflicts,
        match_fn=lambda pred, gold: match_verdict(pred, gold, tolerance_sequences=2),
    )


async def run_full_eval(golden: GoldenDataset | None = None, run_adversarial: bool = True) -> EvalReport:
    golden = golden or GOLDEN_DATASET
    start = time.time()
    provider = get_provider()

    # A must finish before B/C/D can read anything meaningful -- detection
    # depends on extraction's output and investigation depends on detection's.
    pipeline_result = await run_pipeline_subagent(golden, provider)

    (extraction_metrics, per_unit), detection_metrics, investigation_metrics = await asyncio.gather(
        measure_extraction_subagent(golden),
        measure_detection_subagent(golden),
        measure_investigation_subagent(golden),
    )

    overall_f1 = (extraction_metrics.f1 + detection_metrics.f1 + investigation_metrics.f1) / 3

    notes = list(pipeline_result.get("notes", []))
    adversarial = None
    if run_adversarial:
        from scripts.eval.adversarial import run_adversarial_baseline

        try:
            adversarial = await run_adversarial_baseline(golden, provider)
        except Exception as e:
            notes.append(f"Adversarial baseline failed: {e}")

    elapsed = time.time() - start
    notes.append(f"Eval completed in {elapsed:.1f}s")

    return EvalReport(
        document=golden.document_path,
        timestamp=datetime.now(timezone.utc).isoformat(),
        extraction=extraction_metrics,
        detection=detection_metrics,
        investigation=investigation_metrics,
        overall_f1=overall_f1,
        notes=notes,
        per_unit=per_unit,
        adversarial=adversarial,
    )
