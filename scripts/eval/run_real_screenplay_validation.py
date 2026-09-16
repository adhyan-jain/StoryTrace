"""Unseen Real-Screenplay Validation & Repeatability Harness.

Evaluates 5 real screenplays:
- seven.txt
- pulp_fiction.txt
- gladiator.txt
- aliens_film.txt
- scream_2.txt

Performs repeatability testing (3 runs per film on 2 films) with the selected model.
Enforces pipeline integrity on every run. Saves raw audit logs and summary metrics to data/eval/real_screenplay_validation_results.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from backend.llm.ollama import OllamaProvider
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.integrity import verify_pipeline_integrity
from backend.pipeline.state_extraction import extract_state_events_batch, extract_state_events, write_state_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCREENPLAYS = {
    "seven": os.path.join(REPO_ROOT, "data/test_documents/seven.txt"),
    "pulp_fiction": os.path.join(REPO_ROOT, "data/test_documents/pulp_fiction.txt"),
    "gladiator": os.path.join(REPO_ROOT, "data/test_documents/gladiator.txt"),
    "aliens": os.path.join(REPO_ROOT, "data/eval/screenplays/aliens_film.txt"),
    "scream_2": os.path.join(REPO_ROOT, "data/eval/screenplays/scream_2.txt"),
}


def load_screenplay_units(path: str, sid: str, max_units: int = 60) -> list[NarrativeUnit]:
    with open(path, encoding="utf-8") as f:
        text = f.read()

    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # Group small paragraphs into rich scene blocks (~1500 chars each)
    scene_blocks = []
    current_block = []
    current_len = 0

    for p in raw_paragraphs:
        if current_len + len(p) > 1500 and current_block:
            scene_blocks.append("\n\n".join(current_block))
            current_block = [p]
            current_len = len(p)
        else:
            current_block.append(p)
            current_len += len(p)

    if current_block:
        scene_blocks.append("\n\n".join(current_block))

    # Cap to max_units for efficient, representative validation
    selected_blocks = scene_blocks[:max_units]

    units = []
    for i, block_text in enumerate(selected_blocks, start=1):
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
                raw_text=block_text[:4000],
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


async def run_single_screenplay_validation(
    film_name: str,
    path: str,
    model_name: str = "qwen2.5:7b",
    run_index: int = 1,
    batch_size: int = 5,
) -> dict:
    sid = f"val_real_{film_name}_r{run_index}"
    logger.info(f"=== Starting Screenplay Validation: {film_name} (run {run_index}, model {model_name}) ===")

    provider = OllamaProvider(model_name=model_name)
    client = ClickHouseClient()
    clear_universe(client, sid)

    units = load_screenplay_units(path, sid)
    client.insert_narrative_units(units)

    registry = EntityRegistry(sid)
    start_time = time.time()

    # Per-unit extraction for screenplay scale
    total_events = 0
    extraction_failures = 0

    for i, u in enumerate(units, 1):
        try:
            events = await extract_state_events(u, sid, provider, registry)
            await write_state_events(events, client)
            total_events += len(events)
        except Exception as e:
            extraction_failures += 1
            logger.error(f"Extraction failed for unit {u.unit_id}: {e}")

        if i % 10 == 0 or i == len(units):
            logger.info(f"[{film_name}] Extracted {i}/{len(units)} units... ({total_events} events so far)")

    client.insert_entities(registry.get_all())
    extraction_dur = time.time() - start_time

    # Candidate detection
    det_start = time.time()
    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(sid)
    client.insert_candidate_conflicts(conflicts)
    detection_dur = time.time() - det_start

    # Investigation
    inv_start = time.time()
    agent = InvestigationAgent(provider, sid)
    verdict_counts = {"verified": 0, "resolved": 0, "uncertain": 0, "intentional": 0}
    candidates_audit = []
    investigation_failures = 0

    for c in conflicts:
        try:
            v = await agent.investigate_async(c)
            client.insert_investigation_verdicts([v])
            verdict_counts[v.status] = verdict_counts.get(v.status, 0) + 1
            candidates_audit.append({
                "candidate_id": c.id,
                "entity_id": c.entity_id,
                "attribute": c.attribute,
                "prior_evidence": c.prior_evidence_excerpt,
                "current_evidence": c.current_evidence_excerpt,
                "description": c.description,
                "verdict_status": v.status,
                "verdict_confidence": v.confidence,
                "verdict_explanation": v.explanation,
                "actions": v.investigation_actions,
            })
        except Exception as e:
            investigation_failures += 1
            logger.error(f"Investigation failed for candidate {c.id}: {e}")

    investigation_dur = time.time() - inv_start
    total_dur = time.time() - start_time

    integrity_stats = verify_pipeline_integrity(
        client=client,
        story_universe_id=sid,
        expected_unit_count=len(units),
        require_events=total_events > 0,
    )

    candidate_density = len(conflicts) / len(units) if units else 0.0

    res = {
        "film": film_name,
        "run_index": run_index,
        "model": model_name,
        "story_universe_id": sid,
        "units": len(units),
        "total_events": total_events,
        "entities": integrity_stats["entity_count"],
        "candidates": len(conflicts),
        "candidate_density_per_unit": round(candidate_density, 4),
        "verdicts": verdict_counts,
        "extraction_failures": extraction_failures,
        "investigation_failures": investigation_failures,
        "total_runtime_sec": round(total_dur, 2),
        "extraction_sec": round(extraction_dur, 2),
        "detection_sec": round(detection_dur, 2),
        "investigation_sec": round(investigation_dur, 2),
        "candidates_audit": candidates_audit,
    }

    logger.info(f"=== {film_name} Run {run_index} Done: {len(units)} units, {total_events} events, {len(conflicts)} candidates in {total_dur:.1f}s ===")
    return res


async def run_full_screenplay_validation_and_repeatability(model_name: str = "qwen2.5:7b"):
    results = {"screenplay_validation": {}, "repeatability": {}}

    # Step 5: Unseen Real-Screenplay Validation (1 run for each of 5 films)
    for film, path in SCREENPLAYS.items():
        try:
            res = await run_single_screenplay_validation(film, path, model_name=model_name, run_index=1)
            results["screenplay_validation"][film] = res
        except Exception as e:
            logger.error(f"Validation failed for screenplay {film}: {e}", exc_info=True)
            results["screenplay_validation"][film] = {"error": str(e)}

    # Step 7: Repeatability (2 selected screenplays x 3 runs)
    repeat_films = ["aliens", "seven"]
    for film in repeat_films:
        path = SCREENPLAYS[film]
        runs = []
        for r in range(1, 4):
            try:
                res = await run_single_screenplay_validation(film, path, model_name=model_name, run_index=r)
                runs.append(res)
            except Exception as e:
                logger.error(f"Repeatability run {r} failed for {film}: {e}")
                runs.append({"error": str(e)})
        results["repeatability"][film] = runs

    out_file = os.path.join(REPO_ROOT, "data/eval/real_screenplay_validation_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Screenplay validation & repeatability results written to {out_file}")


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:7b"
    asyncio.run(run_full_screenplay_validation_and_repeatability(model))
