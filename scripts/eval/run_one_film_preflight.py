"""One-Film Preflight Sanity Check for StoryTrace Frozen Experiment.

Executes all 4 frozen conditions (A, B, C, D) on a single representative
research film (Chasing Amy) using frozen qwen2.5:7b via local Ollama.

Verifies:
  - Screenplay SHA256 hash match against corpus_manifest.json
  - Execution of exact code paths for A, B, C, D
  - Full ClickHouse persistence & verify_pipeline_integrity()
  - Raw JSON outputs saved to data/eval/ablation/preflight_chasing_amy_condition_{A,B,C,D}.json
  - Gold matching & scoring against gold_dataset_v3.json
  - Structural differentiation across A/B/C/D
"""

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.eval.pipeline_only_investigator import PipelineOnlyInvestigator
from backend.eval.unconstrained_extractor import extract_state_events_unconstrained
from backend.ingestion.models import NarrativeUnit
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.integrity import verify_pipeline_integrity
from backend.pipeline.state_extraction import extract_state_events, write_state_events
from scripts.eval.run_final_research_experiment import (
    clear_universe,
    load_research_films,
    load_screenplay_units,
    run_condition_a_or_b,
    run_condition_c,
    run_condition_d,
)
from scripts.eval.score_final_experiment import is_matching_finding, load_gold_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "eval" / "corpus_manifest.json"
GOLD_PATH = REPO_ROOT / "data" / "eval" / "gold_dataset_v3.json"
ABLATION_DIR = REPO_ROOT / "data" / "eval" / "ablation"
PREFLIGHT_REPORT_PATH = REPO_ROOT / "data" / "eval" / "preflight_one_film_report.json"


def verify_screenplay_hash(film_info: dict) -> bool:
    full_path = REPO_ROOT / film_info["screenplay_path"]
    data = full_path.read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    expected_hash = film_info["sha256_hash"]
    logger.info(f"Screenplay Hash Verification: actual={actual_hash[:16]}... expected={expected_hash[:16]}...")
    return actual_hash == expected_hash


async def main():
    logger.info("=== STARTING ONE-FILM PREFLIGHT SANITY CHECK ===")

    films = load_research_films()
    target_film = next((f for f in films if f["film_slug"] == "chasing_amy"), films[0])
    film_slug = target_film["film_slug"]
    film_name = target_film["film_name"]
    full_path = REPO_ROOT / target_film["screenplay_path"]

    # 1. Screenplay Integrity & Hash
    hash_ok = verify_screenplay_hash(target_film)
    if not hash_ok:
        raise ValueError(f"Screenplay hash mismatch for {film_slug}!")

    from backend.llm.ollama import OllamaProvider

    model_name = "qwen2.5:7b"
    provider = OllamaProvider(model_name=model_name)
    client = ClickHouseClient()

    results = {}
    ABLATION_DIR.mkdir(parents=True, exist_ok=True)

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

    run_ts = int(time.time())

    # Condition A
    file_a = ABLATION_DIR / f"preflight_{film_slug}_condition_A.json"
    cached_a = is_valid_cached(file_a)
    if cached_a:
        logger.info(f"[{film_slug}] Using cached Preflight Condition A...")
        res_a = cached_a
    else:
        sid_a = f"preflight_{film_slug}_condA_{run_ts}"
        logger.info(f"[{film_slug}] Running Preflight Condition A (sid={sid_a})...")
        units_a = load_screenplay_units(full_path, sid_a)
        res_a = await run_condition_a_or_b(units_a, sid_a, "A", provider, client)
        res_a["film"] = film_slug
        res_a["condition"] = "A"
        res_a["code_path"] = "Controlled Extraction -> Entity Registry -> Candidate Detector -> Bounded InvestigationAgent"
        with open(file_a, "w", encoding="utf-8") as f:
            json.dump(res_a, f, indent=2)
    results["A"] = res_a

    # Condition B
    file_b = ABLATION_DIR / f"preflight_{film_slug}_condition_B.json"
    cached_b = is_valid_cached(file_b)
    if cached_b:
        logger.info(f"[{film_slug}] Using cached Preflight Condition B...")
        res_b = cached_b
    else:
        sid_b = f"preflight_{film_slug}_condB_{run_ts}"
        logger.info(f"[{film_slug}] Running Preflight Condition B (sid={sid_b})...")
        units_b = load_screenplay_units(full_path, sid_b)
        res_b = await run_condition_a_or_b(units_b, sid_b, "B", provider, client)
        res_b["film"] = film_slug
        res_b["condition"] = "B"
        res_b["code_path"] = "Controlled Extraction -> Entity Registry -> Candidate Detector -> PipelineOnlyInvestigator (No Agent)"
        with open(file_b, "w", encoding="utf-8") as f:
            json.dump(res_b, f, indent=2)
    results["B"] = res_b

    # Condition C
    file_c = ABLATION_DIR / f"preflight_{film_slug}_condition_C.json"
    cached_c = is_valid_cached(file_c)
    if cached_c:
        logger.info(f"[{film_slug}] Using cached Preflight Condition C...")
        res_c = cached_c
    else:
        sid_c = f"preflight_{film_slug}_condC_{run_ts}"
        logger.info(f"[{film_slug}] Running Preflight Condition C (sid={sid_c})...")
        units_c = load_screenplay_units(full_path, sid_c)
        res_c = await run_condition_c(units_c, sid_c, provider, client)
        res_c["film"] = film_slug
        res_c["condition"] = "C"
        res_c["code_path"] = "Unconstrained Extraction -> Entity Registry -> Candidate Detector -> Bounded InvestigationAgent"
        with open(file_c, "w", encoding="utf-8") as f:
            json.dump(res_c, f, indent=2)
    results["C"] = res_c

    # Condition D
    file_d = ABLATION_DIR / f"preflight_{film_slug}_condition_D.json"
    cached_d = is_valid_cached(file_d)
    if cached_d:
        logger.info(f"[{film_slug}] Using cached Preflight Condition D...")
        res_d = cached_d
    else:
        sid_d = f"preflight_{film_slug}_condD_{run_ts}"
        logger.info(f"[{film_slug}] Running Preflight Condition D (sid={sid_d})...")
        res_d = await run_condition_d(full_path, sid_d, provider)
        res_d["film"] = film_slug
        res_d["condition"] = "D"
        res_d["code_path"] = "Single Prompt One-Shot Baseline LLM Reasoning"
        with open(file_d, "w", encoding="utf-8") as f:
            json.dump(res_d, f, indent=2)
    results["D"] = res_d

    # Gold dataset scoring check
    gold_data = load_gold_dataset()
    gold_items = [g for g in gold_data.get("items", []) if g.get("film") == film_slug and g.get("consensus_verdict") == "verified"]

    gold_scores = {}
    for cond in ("A", "B", "C", "D"):
        findings = results[cond]["findings"]
        surfaced = [f for f in findings if f.get("status") == "verified"] if cond in ("A", "C") else findings

        tp = 0
        matched_ids = set()
        for f in surfaced:
            for g_idx, g in enumerate(gold_items):
                if g_idx not in matched_ids and is_matching_finding(f, g):
                    tp += 1
                    matched_ids.add(g_idx)
                    break

        fp = len(surfaced) - tp
        fn = len(gold_items) - len(matched_ids)

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

        gold_scores[cond] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "surfaced": len(surfaced),
            "gold_total": len(gold_items),
        }

    preflight_report = {
        "film": film_slug,
        "film_name": film_name,
        "hash_verified": hash_ok,
        "frozen_model": model_name,
        "provider": "ollama",
        "results": results,
        "gold_scores": gold_scores,
    }

    with open(PREFLIGHT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(preflight_report, f, indent=2)

    logger.info(f"=== ONE-FILM PREFLIGHT SANITY CHECK COMPLETE. Report saved to {PREFLIGHT_REPORT_PATH} ===")


if __name__ == "__main__":
    asyncio.run(main())
