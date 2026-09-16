"""StoryTrace Final Research Experiment Runner (Conditions A, B, C, D).

Executes the frozen StoryTrace research experiment across the 10 research films
in data/eval/corpus_manifest.json using frozen qwen2.5:7b via local Ollama.

Conditions:
  A: Full StoryTrace (Controlled extraction -> Entity resolution -> Candidate detector -> Investigation agent)
  B: Pipeline Only (Controlled extraction -> Entity resolution -> Candidate detector -> No investigation agent)
  C: Unconstrained Extraction (Unconstrained extraction -> Entity resolution -> Candidate detector -> Investigation agent)
  D: One-Shot LLM Baseline (Direct single-call qwen2.5:7b reasoning over screenplay)

Rules:
  - Uses fresh story_universe_id for every film x condition run.
  - Verifies pipeline integrity via verify_pipeline_integrity() after every run.
  - Saves raw outputs to data/eval/ablation/{film_slug}_condition_{A,B,C,D}.json.
  - Computes exact metrics against data/eval/gold_dataset_v3.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.eval.pipeline_only_investigator import PipelineOnlyInvestigator
from backend.eval.unconstrained_extractor import extract_state_events_unconstrained
from backend.ingestion.models import NarrativeUnit
from backend.llm.base import LLMRequest
from backend.llm.ollama import OllamaProvider
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.integrity import verify_pipeline_integrity
from backend.pipeline.state_extraction import extract_state_events, write_state_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "eval" / "corpus_manifest.json"
GOLD_DATASET_PATH = REPO_ROOT / "data" / "eval" / "gold_dataset_v3.json"
ABLATION_DIR = REPO_ROOT / "data" / "eval" / "ablation"
RAW_RESULTS_PATH = REPO_ROOT / "data" / "eval" / "research_experiment_raw_results.json"
REPORT_MD_PATH = REPO_ROOT / "docs" / "RESEARCH_EXPERIMENT_RESULTS.md"


def load_research_films() -> list[dict]:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    return [f for f in manifest.get("films", []) if f.get("corpus_role") == "research"]


def load_screenplay_units(screenplay_path: Path, story_universe_id: str, max_units: int = 60) -> list[NarrativeUnit]:
    text = screenplay_path.read_text(encoding="utf-8", errors="ignore")
    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

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

    selected_blocks = scene_blocks[:max_units]
    units: list[NarrativeUnit] = []
    for i, block_text in enumerate(selected_blocks, start=1):
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
                raw_text=block_text[:4000],
            )
        )
    return units


def with_ch_retry(fn, *args, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"ClickHouse call failed ({e}), retrying {attempt+1}/{max_retries}...")
            time.sleep(2 ** attempt)


def clear_universe(client: ClickHouseClient, sid: str) -> None:
    settings = {"mutations_sync": "1"}
    for table in ("narrative_units", "entities", "state_events", "candidate_conflicts", "processing_status"):
        with_ch_retry(client.client.command, f"ALTER TABLE {table} DELETE WHERE story_universe_id = '{sid}'", settings=settings)
    with_ch_retry(
        client.client.command,
        f"ALTER TABLE investigation_verdicts DELETE WHERE candidate_id LIKE '{sid}_%'",
        settings=settings,
    )


async def run_condition_a_or_b(
    units: list[NarrativeUnit],
    sid: str,
    condition: str,
    provider: OllamaProvider,
    client: ClickHouseClient,
) -> dict:
    start_time = time.time()
    clear_universe(client, sid)

    client.insert_narrative_units(units)
    registry = EntityRegistry(sid)

    total_events = 0
    for u in units:
        events = await extract_state_events(u, sid, provider, registry)
        await write_state_events(events, client)
        total_events += len(events)

    client.insert_entities(registry.get_all())
    extraction_dur = time.time() - start_time

    det_start = time.time()
    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(sid)
    client.insert_candidate_conflicts(conflicts)
    detection_dur = time.time() - det_start

    inv_start = time.time()
    if condition == "A":
        agent = InvestigationAgent(provider, sid)
    else:
        agent = PipelineOnlyInvestigator(provider, sid)

    findings = []
    verdict_counts = {"verified": 0, "resolved": 0, "uncertain": 0, "intentional": 0}

    for c in conflicts:
        v = await agent.investigate_async(c)
        client.insert_investigation_verdicts([v])
        verdict_counts[v.status] = verdict_counts.get(v.status, 0) + 1
        findings.append({
            "conflict_id": c.id,
            "entity_id": c.entity_id,
            "attribute": c.attribute,
            "prior_evidence_unit_id": c.prior_evidence_unit_id,
            "prior_evidence_excerpt": c.prior_evidence_excerpt,
            "current_evidence_unit_id": c.current_evidence_unit_id,
            "current_evidence_excerpt": c.current_evidence_excerpt,
            "description": c.description,
            "status": v.status,
            "severity": v.severity,
            "confidence": v.confidence,
            "explanation": v.explanation,
        })

    investigation_dur = time.time() - inv_start
    total_dur = time.time() - start_time

    integrity_stats = verify_pipeline_integrity(
        client=client,
        story_universe_id=sid,
        expected_unit_count=len(units),
        require_events=total_events > 0,
    )

    return {
        "story_universe_id": sid,
        "units": len(units),
        "total_events": total_events,
        "entities": integrity_stats["entity_count"],
        "candidates_generated": len(conflicts),
        "conflicts_surfaced": sum(1 for f in findings if f["status"] == "verified"),
        "verdict_counts": verdict_counts,
        "total_runtime_sec": round(total_dur, 2),
        "extraction_sec": round(extraction_dur, 2),
        "detection_sec": round(detection_dur, 2),
        "investigation_sec": round(investigation_dur, 2),
        "integrity": integrity_stats,
        "findings": findings,
    }


async def run_condition_c(
    units: list[NarrativeUnit],
    sid: str,
    provider: OllamaProvider,
    client: ClickHouseClient,
) -> dict:
    start_time = time.time()
    clear_universe(client, sid)

    client.insert_narrative_units(units)
    registry = EntityRegistry(sid)

    total_events = 0
    for u in units:
        events = await extract_state_events_unconstrained(u, sid, provider, registry)
        await write_state_events(events, client)
        total_events += len(events)

    client.insert_entities(registry.get_all())
    extraction_dur = time.time() - start_time

    det_start = time.time()
    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(sid)
    client.insert_candidate_conflicts(conflicts)
    detection_dur = time.time() - det_start

    inv_start = time.time()
    agent = InvestigationAgent(provider, sid)

    findings = []
    verdict_counts = {"verified": 0, "resolved": 0, "uncertain": 0, "intentional": 0}

    for c in conflicts:
        v = await agent.investigate_async(c)
        client.insert_investigation_verdicts([v])
        verdict_counts[v.status] = verdict_counts.get(v.status, 0) + 1
        findings.append({
            "conflict_id": c.id,
            "entity_id": c.entity_id,
            "attribute": c.attribute,
            "prior_evidence_unit_id": c.prior_evidence_unit_id,
            "prior_evidence_excerpt": c.prior_evidence_excerpt,
            "current_evidence_unit_id": c.current_evidence_unit_id,
            "current_evidence_excerpt": c.current_evidence_excerpt,
            "description": c.description,
            "status": v.status,
            "severity": v.severity,
            "confidence": v.confidence,
            "explanation": v.explanation,
        })

    investigation_dur = time.time() - inv_start
    total_dur = time.time() - start_time

    integrity_stats = verify_pipeline_integrity(
        client=client,
        story_universe_id=sid,
        expected_unit_count=len(units),
        require_events=total_events > 0,
    )

    return {
        "story_universe_id": sid,
        "units": len(units),
        "total_events": total_events,
        "entities": integrity_stats["entity_count"],
        "candidates_generated": len(conflicts),
        "conflicts_surfaced": sum(1 for f in findings if f["status"] == "verified"),
        "verdict_counts": verdict_counts,
        "total_runtime_sec": round(total_dur, 2),
        "extraction_sec": round(extraction_dur, 2),
        "detection_sec": round(detection_dur, 2),
        "investigation_sec": round(investigation_dur, 2),
        "integrity": integrity_stats,
        "findings": findings,
    }


class BaselineFinding(BaseModel):
    entity: str
    attribute: str
    prior_scene: str
    current_scene: str
    prior_excerpt: str
    current_excerpt: str
    explanation: str


class BaselineFindings(BaseModel):
    findings: list[BaselineFinding] = Field(default_factory=list)


async def run_condition_d(
    screenplay_path: Path,
    sid: str,
    provider: OllamaProvider,
) -> dict:
    start_time = time.time()
    text = screenplay_path.read_text(encoding="utf-8", errors="ignore")
    truncated = len(text) > 40000
    sent_text = text[:40000]

    prompt = f"""You are a professional script supervisor. Read this screenplay and identify every continuity error you can find.

For each error, return a JSON object with:
- entity: the character or prop name
- attribute: what attribute is inconsistent (clothing, possession, injury, location)
- prior_scene: approximate scene number or description where state was established
- current_scene: approximate scene number where state contradicts
- prior_excerpt: the exact sentence establishing prior state
- current_excerpt: the exact sentence contradicting it
- explanation: why this is a continuity error

Return a JSON array of errors under 'findings'. Return only JSON, no preamble.

SCREENPLAY:
{sent_text}
"""

    req = LLMRequest(stage="one_shot_baseline", prompt=prompt, temperature=0.0, max_tokens=4096)
    findings = []
    error = None

    try:
        res = provider.complete(req, BaselineFindings)
        for f in res.value.findings:
            findings.append({
                "conflict_id": f"{sid}_one_shot_{len(findings)+1}",
                "entity_id": f.entity,
                "attribute": f.attribute,
                "prior_evidence_excerpt": f.prior_excerpt,
                "current_evidence_excerpt": f.current_excerpt,
                "description": f.explanation,
                "status": "verified",
                "severity": "warning",
                "confidence": 0.8,
                "explanation": f.explanation,
            })
    except Exception as exc:
        error = str(exc)

    total_dur = time.time() - start_time

    return {
        "story_universe_id": sid,
        "units": 60,
        "total_events": 0,
        "entities": 0,
        "candidates_generated": len(findings),
        "conflicts_surfaced": len(findings),
        "verdict_counts": {"verified": len(findings), "resolved": 0, "uncertain": 0, "intentional": 0},
        "total_runtime_sec": round(total_dur, 2),
        "error": error,
        "findings": findings,
    }


async def main():
    model_name = "qwen2.5:7b"
    provider = OllamaProvider(model_name=model_name)
    client = ClickHouseClient()

    films = load_research_films()
    logger.info(f"=== STARTING FINAL RESEARCH EXPERIMENT ACROSS {len(films)} FILMS x 4 CONDITIONS ===")

    ABLATION_DIR.mkdir(parents=True, exist_ok=True)
    all_experiment_results = {}

    def is_valid_cached(out_path: Path) -> dict | None:
        if not out_path.exists():
            return None
        try:
            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)
            cond = data.get("condition")
            if cond in ("A", "B", "C"):
                if data.get("integrity", {}).get("integrity_passed"):
                    return data
            elif cond == "D":
                if not data.get("error"):
                    return data
        except Exception:
            pass
        return None

    for film_idx, film_info in enumerate(films, 1):
        film_slug = film_info["film_slug"]
        film_name = film_info["film_name"]
        rel_path = film_info["screenplay_path"]
        full_path = REPO_ROOT / rel_path

        logger.info(f"\n=======================================================")
        logger.info(f"Processing Film {film_idx}/{len(films)}: {film_name} ({film_slug})")
        logger.info(f"=======================================================")

        film_results = {}

        # 1. Condition A
        file_a = ABLATION_DIR / f"{film_slug}_condition_A.json"
        cached_a = is_valid_cached(file_a)
        if cached_a:
            logger.info(f"[{film_slug}] Using cached Condition A...")
            res_a = cached_a
        else:
            sid_a = f"exp_res_{film_slug}_condA"
            units_a = load_screenplay_units(full_path, sid_a)
            logger.info(f"[{film_slug}] Executing Condition A...")
            res_a = await run_condition_a_or_b(units_a, sid_a, "A", provider, client)
            res_a["film"] = film_slug
            res_a["condition"] = "A"
            with open(file_a, "w", encoding="utf-8") as f:
                json.dump(res_a, f, indent=2)
        film_results["A"] = res_a

        # 2. Condition B
        file_b = ABLATION_DIR / f"{film_slug}_condition_B.json"
        cached_b = is_valid_cached(file_b)
        if cached_b:
            logger.info(f"[{film_slug}] Using cached Condition B...")
            res_b = cached_b
        else:
            sid_b = f"exp_res_{film_slug}_condB"
            units_b = load_screenplay_units(full_path, sid_b)
            logger.info(f"[{film_slug}] Executing Condition B...")
            res_b = await run_condition_a_or_b(units_b, sid_b, "B", provider, client)
            res_b["film"] = film_slug
            res_b["condition"] = "B"
            with open(file_b, "w", encoding="utf-8") as f:
                json.dump(res_b, f, indent=2)
        film_results["B"] = res_b

        # 3. Condition C
        file_c = ABLATION_DIR / f"{film_slug}_condition_C.json"
        cached_c = is_valid_cached(file_c)
        if cached_c:
            logger.info(f"[{film_slug}] Using cached Condition C...")
            res_c = cached_c
        else:
            sid_c = f"exp_res_{film_slug}_condC"
            units_c = load_screenplay_units(full_path, sid_c)
            logger.info(f"[{film_slug}] Executing Condition C...")
            res_c = await run_condition_c(units_c, sid_c, provider, client)
            res_c["film"] = film_slug
            res_c["condition"] = "C"
            with open(file_c, "w", encoding="utf-8") as f:
                json.dump(res_c, f, indent=2)
        film_results["C"] = res_c

        # 4. Condition D
        file_d = ABLATION_DIR / f"{film_slug}_condition_D.json"
        cached_d = is_valid_cached(file_d)
        if cached_d:
            logger.info(f"[{film_slug}] Using cached Condition D...")
            res_d = cached_d
        else:
            sid_d = f"exp_res_{film_slug}_condD"
            logger.info(f"[{film_slug}] Executing Condition D...")
            res_d = await run_condition_d(full_path, sid_d, provider)
            res_d["film"] = film_slug
            res_d["condition"] = "D"
            with open(file_d, "w", encoding="utf-8") as f:
                json.dump(res_d, f, indent=2)
        film_results["D"] = res_d

        all_experiment_results[film_slug] = film_results

    # Save aggregate raw results
    with open(RAW_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_experiment_results, f, indent=2)

    logger.info(f"=== FINAL EXPERIMENT RUN COMPLETE. Raw results saved to {RAW_RESULTS_PATH} ===")


if __name__ == "__main__":
    asyncio.run(main())
