"""StoryTrace V2 End-to-End Evaluation Orchestrator.

Runs the full V2 pipeline across the benchmark screenplays:
  1. Scene Parsing -> NarrativeUnits
  2. Enriched Scene & State Extraction (Hierarchical Location, Temporal Anchors, Co-Presence, Transitions)
  3. ClickHouse V2 Analytics Ingestion (state_events_v2, scene_co_presence_v2)
  4. Expanded 8-Rule Deterministic Candidate Detection (candidate_conflicts_v2)
  5. Calibrated Two-Tier ReAct Investigation Agent (FastMCP + investigation_verdicts_v2)

Writes raw outputs to data/eval/v2/{film_slug}_v2_output.json
and data/eval/v2/v2_experiment_raw_results.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.ingestion.models import NarrativeUnit
from backend.pipeline.entity_resolution import EntityRegistry
from backend.v2.clickhouse.client import ClickHouseClientV2
from backend.v2.pipeline.enriched_extractor import EnrichedExtractor
from backend.v2.candidate_detection.detector import CandidateDetectorV2
from backend.v2.agent.investigator import InvestigationAgentV2
from backend.llm.base import LLMProvider
from backend.llm.ollama import OllamaProvider
from backend.llm.client import GeminiProvider
from backend.llm.vertexai import VertexAIProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_v2_eval")

OUT_DIR = REPO_ROOT / "data" / "eval" / "v2"
CORPUS_MANIFEST_PATH = REPO_ROOT / "data" / "eval" / "corpus_manifest.json"
_SCENE_HEADER_RE = re.compile(r"^\s*((?:INT|EXT|INT\./EXT|I/E)[./ ].*)$", re.MULTILINE | re.IGNORECASE)


def get_provider() -> LLMProvider:
    provider = os.environ.get("MODEL_PROVIDER", "ollama")
    if provider == "vertexai":
        return VertexAIProvider()
    if provider == "gemini":
        return GeminiProvider()
    return OllamaProvider()


def load_screenplay_units(screenplay_path: Path, story_universe_id: str) -> List[NarrativeUnit]:
    text = screenplay_path.read_text(encoding="utf-8", errors="ignore")
    matches = list(_SCENE_HEADER_RE.finditer(text))
    if not matches:
        # Fallback to paragraph splitting
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        units: List[NarrativeUnit] = []
        for i, paragraph in enumerate(paragraphs, start=1):
            units.append(
                NarrativeUnit(
                    unit_id=f"{story_universe_id}_unit_{i}",
                    story_universe_id=story_universe_id,
                    document_id=story_universe_id,
                    unit_type="scene",
                    sequence_number=i,
                    title=f"Scene {i}",
                    page_start=1,
                    page_end=1,
                    raw_text=paragraph,
                )
            )
        return units

    units: List[NarrativeUnit] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        scene_text = text[start:end].strip()
        if not scene_text:
            continue
        units.append(
            NarrativeUnit(
                unit_id=f"{story_universe_id}_unit_{i + 1}",
                story_universe_id=story_universe_id,
                document_id=story_universe_id,
                unit_type="scene",
                sequence_number=i + 1,
                title=m.group(1).strip()[:120],
                page_start=1,
                page_end=1,
                raw_text=scene_text,
            )
        )
    return units


def clear_v2_eval_data(client: ClickHouseClientV2, story_universe_id: str) -> None:
    settings = {"mutations_sync": "1"}
    tables = [
        "narrative_units", "entities", "state_events_v2",
        "scene_co_presence_v2", "candidate_conflicts_v2"
    ]
    for table in tables:
        try:
            client.client.command(
                f"ALTER TABLE {table} DELETE WHERE story_universe_id = {{sid:String}}",
                parameters={"sid": story_universe_id},
                settings=settings,
            )
        except Exception as e:
            logger.debug(f"Clear {table} for {story_universe_id}: {e}")
    try:
        client.client.command(
            "ALTER TABLE investigation_verdicts_v2 DELETE WHERE candidate_id LIKE {prefix:String}",
            parameters={"prefix": f"{story_universe_id}_%"},
            settings=settings,
        )
    except Exception as e:
        logger.debug(f"Clear investigation_verdicts_v2 for {story_universe_id}: {e}")


async def run_v2_for_film(
    film_slug: str,
    story_universe_id: str,
    screenplay_path: Path,
    provider: LLMProvider,
    client: ClickHouseClientV2,
) -> Dict[str, Any]:
    t0 = time.time()
    logger.info(f"=== Starting V2 Pipeline for {film_slug} ({story_universe_id}) ===")

    # 0. Clean prior eval data
    clear_v2_eval_data(client, story_universe_id)

    # 1. Load Narrative Units
    units = load_screenplay_units(screenplay_path, story_universe_id)
    logger.info(f"Loaded {len(units)} NarrativeUnits for {film_slug}")

    # Insert narrative units to ClickHouse
    client.insert_narrative_units(units)

    # 2. Extract Enriched Scene & State
    extractor = EnrichedExtractor(provider=provider, client=client)
    all_state_events = []
    all_co_presences = []
    
    t_extract_start = time.time()
    for u in units:
        try:
            extraction = extractor.extract_scene(u, story_universe_id)
            if extraction:
                all_state_events.extend(extraction.state_events)
                if extraction.co_presence:
                    all_co_presences.append(extraction.co_presence)
        except Exception as e:
            logger.warning(f"Extraction error on unit {u.unit_id}: {e}")
    
    t_extract = time.time() - t_extract_start
    logger.info(f"Extraction complete for {film_slug}: {len(all_state_events)} events, {len(all_co_presences)} co-presence records in {t_extract:.2f}s")

    # Persist extracted state to ClickHouse V2 tables
    client.insert_state_events_v2(all_state_events)
    client.insert_scene_co_presence_v2(all_co_presences)

    # 3. Deterministic Candidate Detection (8 SQL Window Rules)
    t_det_start = time.time()
    detector = CandidateDetectorV2(client=client)
    candidates = detector.detect_conflicts(story_universe_id)
    t_det = time.time() - t_det_start
    logger.info(f"Candidate detection complete for {film_slug}: {len(candidates)} candidates across 8 rules in {t_det:.2f}s")

    # Persist candidates to ClickHouse V2
    client.insert_candidate_conflicts_v2(candidates)

    # 4. Calibrated Bounded Investigation Agent
    t_inv_start = time.time()
    investigator = InvestigationAgentV2(provider=provider, client=client, max_calls=6)
    
    verdicts = []
    investigation_actions_total = 0
    verdict_distribution = {
        "verified_hard_conflict": 0,
        "verified_narrative_anomaly": 0,
        "resolved": 0,
        "uncertain": 0,
    }

    surfaced_findings = []
    for cand in candidates:
        try:
            verdict = await investigator.investigate(cand, story_universe_id)
            verdicts.append(verdict)
            client.insert_verdict_v2(verdict)

            status_str = verdict.status.value
            verdict_distribution[status_str] = verdict_distribution.get(status_str, 0) + 1
            investigation_actions_total += len(verdict.investigation_actions)

            if status_str in ("verified_hard_conflict", "verified_narrative_anomaly"):
                finding_dict = {
                    "candidate_id": cand.id,
                    "rule_type": cand.rule_type,
                    "entity_ids": cand.entity_ids,
                    "entity_id": cand.entity_ids[0] if cand.entity_ids else "",
                    "attribute": cand.attribute,
                    "status": status_str,
                    "severity": verdict.severity,
                    "confidence": verdict.confidence,
                    "explanation": verdict.explanation,
                    "suggested_fix": verdict.suggested_fix,
                    "prior_unit_id": cand.prior_evidence_unit_id,
                    "prior_excerpt": cand.prior_evidence_excerpt,
                    "current_unit_id": cand.current_evidence_unit_id,
                    "current_excerpt": cand.current_evidence_excerpt,
                    "investigation_actions": verdict.investigation_actions,
                }
                surfaced_findings.append(finding_dict)
        except Exception as e:
            logger.error(f"Investigation error on candidate {cand.id}: {e}")

    t_inv = time.time() - t_inv_start
    t_total = time.time() - t0

    result = {
        "film_slug": film_slug,
        "story_universe_id": story_universe_id,
        "unit_count": len(units),
        "state_event_count": len(all_state_events),
        "co_presence_count": len(all_co_presences),
        "candidate_count": len(candidates),
        "verdict_distribution": verdict_distribution,
        "surfaced_findings_count": len(surfaced_findings),
        "total_tool_calls": investigation_actions_total,
        "avg_tool_calls_per_candidate": round(investigation_actions_total / len(candidates), 2) if candidates else 0.0,
        "timings": {
            "extraction_sec": round(t_extract, 2),
            "detection_sec": round(t_det, 2),
            "investigation_sec": round(t_inv, 2),
            "total_runtime_sec": round(t_total, 2),
        },
        "findings": surfaced_findings,
        "candidates": [
            {
                "id": c.id,
                "rule_type": c.rule_type,
                "entity_ids": c.entity_ids,
                "attribute": c.attribute,
                "description": c.description,
                "prior_unit_id": c.prior_evidence_unit_id,
                "current_unit_id": c.current_evidence_unit_id,
            }
            for c in candidates
        ]
    }

    # Save individual film output
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    film_out_path = OUT_DIR / f"{film_slug}_v2_output.json"
    with open(film_out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved {film_slug} results to {film_out_path}")

    return result


async def main():
    parser = argparse.ArgumentParser(description="StoryTrace V2 Benchmark Evaluation Runner")
    parser.add_argument("--film", type=str, default="all", help="Specific film slug to run, or 'all'")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of films")
    args = parser.parse_args()

    with open(CORPUS_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    films = manifest.get("films", [])
    research_films = [f for f in films if f.get("corpus_role") in ("research", "validation_excluded")]

    if args.film != "all":
        research_films = [f for f in research_films if f.get("film_slug") == args.film]

    if args.limit:
        research_films = research_films[:args.limit]

    logger.info(f"Found {len(research_films)} benchmark films to evaluate.")

    provider = get_provider()
    client = ClickHouseClientV2()

    all_results = {}
    for film_info in research_films:
        film_slug = film_info["film_slug"]
        story_universe_id = f"v2_{film_slug}"
        screenplay_path = REPO_ROOT / film_info["screenplay_path"]
        
        if not screenplay_path.exists():
            logger.warning(f"Screenplay not found at {screenplay_path}, skipping.")
            continue

        res = await run_v2_for_film(
            film_slug=film_slug,
            story_universe_id=story_universe_id,
            screenplay_path=screenplay_path,
            provider=provider,
            client=client,
        )
        all_results[film_slug] = res

    # Save aggregate results
    raw_results_path = OUT_DIR / "v2_experiment_raw_results.json"
    with open(raw_results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"=== StoryTrace V2 Evaluation Complete. Saved raw results to {raw_results_path} ===")


if __name__ == "__main__":
    asyncio.run(main())
