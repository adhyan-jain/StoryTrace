"""Model Selection & Comparison Script.

Runs controlled_test_v3.txt (50 narrative units) through the complete pipeline
with both `qwen2.5:7b` and `qwen3:8b` local Ollama models.

Measures:
1. Extraction quality & event count
2. Canonicalization consistency & attribute distribution
3. Candidate conflict generation
4. Investigation completion rate & verdict distribution
5. Malformed-output rate (retries / errors)
6. Total runtime (s) and per-unit latency
7. Pipeline integrity verification

Saves detailed raw JSON results to data/eval/model_comparison_results.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from backend.llm.ollama import OllamaProvider
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.integrity import verify_pipeline_integrity, PipelineIntegrityError
from backend.pipeline.state_extraction import extract_state_events, write_state_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEXT_PATH = os.path.join(REPO_ROOT, "data/test_documents/controlled_test_v3.txt")


def load_v3_units(sid: str) -> list[NarrativeUnit]:
    with open(TEXT_PATH, encoding="utf-8") as f:
        text = f.read()

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units = []
    for i, p in enumerate(paragraphs, start=1):
        units.append(
            NarrativeUnit(
                unit_id=f"{sid}_unit_{i}",
                story_universe_id=sid,
                document_id=sid,
                unit_type="scene",
                sequence_number=i,
                title=f"Scene {i}",
                page_start=1,
                page_end=1,
                raw_text=p,
            )
        )
    return units


def clear_universe(client: ClickHouseClient, sid: str) -> None:
    settings = {"mutations_sync": "1"}
    for table in ("narrative_units", "entities", "state_events", "candidate_conflicts", "processing_status"):
        client.client.command(f"ALTER TABLE {table} DELETE WHERE story_universe_id = '{sid}'", settings=settings)
    client.client.command(
        f"ALTER TABLE investigation_verdicts DELETE WHERE candidate_id LIKE '{sid}_%'",
        settings=settings,
    )


async def evaluate_model(model_name: str, run_index: int = 1) -> dict:
    sid = f"val_model_{model_name.replace(':', '_').replace('.', '_')}_r{run_index}"
    logger.info(f"=== Starting Evaluation for {model_name} (universe_id: {sid}) ===")

    provider = OllamaProvider(model_name=model_name)
    if not provider.available():
        raise RuntimeError(f"Ollama provider for {model_name} is not reachable!")

    client = ClickHouseClient()
    clear_universe(client, sid)

    units = load_v3_units(sid)
    client.insert_narrative_units(units)

    registry = EntityRegistry(sid)
    start_time = time.time()

    # Extraction phase
    total_events = 0
    extraction_errors = 0
    unit_latencies = []

    for i, u in enumerate(units, 1):
        u_start = time.time()
        try:
            events = await extract_state_events(u, sid, provider, registry)
            await write_state_events(events, client)
            total_events += len(events)
        except Exception as e:
            extraction_errors += 1
            logger.error(f"Extraction error on unit {i}: {e}")
        u_dur = time.time() - u_start
        unit_latencies.append(u_dur)
        if i % 10 == 0 or i == len(units):
            logger.info(f"[{model_name}] Extracted {i}/{len(units)} units... ({total_events} events so far)")

    client.insert_entities(registry.get_all())
    extraction_dur = time.time() - start_time

    # Detection phase
    det_start = time.time()
    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(sid)
    client.insert_candidate_conflicts(conflicts)
    detection_dur = time.time() - det_start

    # Investigation phase
    inv_start = time.time()
    agent = InvestigationAgent(provider, sid)
    verdict_counts = {"verified": 0, "resolved": 0, "uncertain": 0, "intentional": 0}
    verdict_details = []
    investigation_errors = 0

    for c in conflicts:
        try:
            v = await agent.investigate_async(c)
            client.insert_investigation_verdicts([v])
            verdict_counts[v.status] = verdict_counts.get(v.status, 0) + 1
            verdict_details.append({
                "candidate_id": c.id,
                "attribute": c.attribute,
                "status": v.status,
                "confidence": v.confidence,
                "explanation": v.explanation,
                "actions": v.investigation_actions,
            })
        except Exception as e:
            investigation_errors += 1
            logger.error(f"Investigation error on candidate {c.id}: {e}")

    investigation_dur = time.time() - inv_start
    total_dur = time.time() - start_time

    # Verification of pipeline integrity
    integrity_stats = verify_pipeline_integrity(
        client=client,
        story_universe_id=sid,
        expected_unit_count=len(units),
        require_events=True,
    )

    # Attribute distribution check
    attr_query = client.client.query(
        f"SELECT attribute, count() FROM state_events WHERE story_universe_id = '{sid}' GROUP BY attribute ORDER BY count() DESC"
    ).result_rows
    attr_dist = {r[0]: r[1] for r in attr_query}

    result = {
        "model": model_name,
        "story_universe_id": sid,
        "units": len(units),
        "total_events": total_events,
        "entities_registered": integrity_stats["entity_count"],
        "candidates": len(conflicts),
        "verdict_counts": verdict_counts,
        "verdict_details": verdict_details,
        "extraction_errors": extraction_errors,
        "investigation_errors": investigation_errors,
        "total_runtime_sec": round(total_dur, 2),
        "extraction_sec": round(extraction_dur, 2),
        "detection_sec": round(detection_dur, 2),
        "investigation_sec": round(investigation_dur, 2),
        "avg_unit_latency_sec": round(sum(unit_latencies) / len(unit_latencies), 3),
        "attribute_distribution": attr_dist,
        "integrity_verified": True,
    }

    logger.info(f"=== Completed {model_name}: {total_events} events, {len(conflicts)} candidates, {verdict_counts} in {total_dur:.1f}s ===")
    return result


async def main():
    models = ["qwen2.5:7b", "qwen3:8b"]
    results = {}

    for model in models:
        try:
            res = await evaluate_model(model)
            results[model] = res
        except Exception as e:
            logger.error(f"Model evaluation failed for {model}: {e}", exc_info=True)
            results[model] = {"error": str(e)}

    out_file = os.path.join(REPO_ROOT, "data/eval/model_comparison_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results written to {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
