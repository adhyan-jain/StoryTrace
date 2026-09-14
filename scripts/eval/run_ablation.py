"""Runs Conditions A, B, C, D against one or more screenplays and writes
data/eval/ablation/{film_slug}_condition_{A,B,C,D}.json.

Never modifies backend/agent/investigator.py or
backend/candidate_detection/detector.py -- Conditions B/C swap in wrapper
classes/functions (backend/eval/pipeline_only_investigator.py,
backend/eval/unconstrained_extractor.py) built specifically not to touch
those files, per the approved plan's carried-over constraints.

Requires GCP Application Default Credentials for MODEL_PROVIDER=vertexai
(gcloud auth application-default login, or running where
/app/gcloud/application_default_credentials.json is mounted -- see
backend/llm/vertexai.py). Run sequentially, one film at a time, to avoid
rate limits, per the original spec's W1.2 instruction.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.agent.investigator import InvestigationAgent  # noqa: E402
from backend.candidate_detection.detector import CandidateDetector  # noqa: E402
from backend.clickhouse.client import ClickHouseClient  # noqa: E402
from backend.eval.cost_tracker import CostTracker, TrackedProvider  # noqa: E402
from backend.eval.pipeline_only_investigator import PipelineOnlyInvestigator  # noqa: E402
from backend.eval.unconstrained_extractor import extract_state_events_unconstrained  # noqa: E402
from backend.ingestion.models import NarrativeUnit  # noqa: E402
from backend.pipeline.entity_resolution import EntityRegistry  # noqa: E402
from backend.pipeline.state_extraction import extract_state_events, write_state_events  # noqa: E402
from scripts.eval.one_shot_baseline import run_one_shot_baseline  # noqa: E402
from scripts.eval.run_eval import _clear_eval_data, _wait_for_count, get_provider  # noqa: E402

OUT_DIR = REPO_ROOT / "data" / "eval" / "ablation"
LOG_PATH = REPO_ROOT / "data" / "eval" / "ablation_run.log"

_SCENE_HEADER_RE = re.compile(r"^\s*((?:INT|EXT|INT\./EXT|I/E)[./ ].*)$", re.MULTILINE | re.IGNORECASE)


def _log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_screenplay_units(screenplay_path: Path, story_universe_id: str) -> list[NarrativeUnit]:
    """Splits screenplay text into scene-level NarrativeUnits on INT./EXT.
    headers (the actual scene boundary convention screenplays use), unlike
    run_eval.py's blank-line paragraph split which is specific to the
    golden_dataset's synthetic prose document."""
    text = screenplay_path.read_text(encoding="utf-8", errors="ignore")
    matches = list(_SCENE_HEADER_RE.finditer(text))
    if not matches:
        raise ValueError(f"no INT./EXT. scene headers found in {screenplay_path}")

    units: list[NarrativeUnit] = []
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


async def _run_condition_a_or_b(
    units: list[NarrativeUnit],
    story_universe_id: str,
    condition: str,  # "A" or "B"
    tracker: CostTracker,
) -> dict:
    # NOTE: the ClickHouse calls below run synchronously (no asyncio.to_thread)
    # deliberately. asyncio.to_thread hands each call to a *different* worker
    # thread from the default executor pool, and clickhouse_connect's client
    # is not safe to bounce across threads that way -- reproduced concretely
    # during the 2026-09-14 pilot run: a clear+insert+wait sequence wrapped in
    # asyncio.to_thread intermittently left insert_narrative_units's rows
    # invisible to an immediate follow-up count query (the exact same
    # sequence run synchronously, same client instance, never failed). The
    # prior _wait_for_count timeout message ("ClickHouse Cloud consistency
    # lag") was misdiagnosing this thread-hop bug as a Cloud-only issue.
    client = ClickHouseClient()
    _clear_eval_data(client, story_universe_id)

    client.insert_narrative_units(units)
    _wait_for_count(client, "narrative_units", story_universe_id, len(units))

    base_provider = get_provider()
    tracked_provider = TrackedProvider(base_provider, tracker)

    registry = EntityRegistry(story_universe_id)
    for unit in units:
        events = await extract_state_events(unit, story_universe_id, tracked_provider, registry)
        await write_state_events(events, client)
    client.insert_entities(registry.get_all())

    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(story_universe_id)
    client.insert_candidate_conflicts(conflicts)

    if condition == "A":
        agent = InvestigationAgent(tracked_provider, story_universe_id)
    else:  # "B": pipeline-only, no LLM investigation calls
        agent = PipelineOnlyInvestigator(tracked_provider, story_universe_id)

    findings = []
    for conflict in conflicts:
        verdict = await agent.investigate_async(conflict)
        client.insert_investigation_verdicts([verdict])
        findings.append({
            "conflict_id": conflict.id,
            "entity_id": conflict.entity_id,
            "attribute": conflict.attribute,
            "description": conflict.description,
            "prior_evidence_unit_id": conflict.prior_evidence_unit_id,
            "prior_evidence_excerpt": conflict.prior_evidence_excerpt,
            "current_evidence_unit_id": conflict.current_evidence_unit_id,
            "current_evidence_excerpt": conflict.current_evidence_excerpt,
            "status": verdict.status,
            "severity": verdict.severity,
            "confidence": verdict.confidence,
            "explanation": verdict.explanation,
        })

    return {
        "candidates_generated": len(conflicts),
        "conflicts_surfaced": sum(1 for f in findings if f["status"] == "verified"),
        "findings": findings,
    }


async def _run_condition_c(
    units: list[NarrativeUnit],
    story_universe_id: str,
    tracker: CostTracker,
) -> dict:
    """Unconstrained extraction + real SQL detection + real investigation
    agent. Uses its own ClickHouse rows (same story_universe_id, cleared and
    reused sequentially after A/B run) since the detector/agent are unmodified
    and read/write the same tables regardless of which extractor populated them."""
    # See the matching NOTE in _run_condition_a_or_b above -- these
    # ClickHouse calls are deliberately synchronous, not asyncio.to_thread.
    client = ClickHouseClient()
    _clear_eval_data(client, story_universe_id)

    client.insert_narrative_units(units)
    _wait_for_count(client, "narrative_units", story_universe_id, len(units))

    base_provider = get_provider()
    tracked_provider = TrackedProvider(base_provider, tracker)

    registry = EntityRegistry(story_universe_id)
    for unit in units:
        events = await extract_state_events_unconstrained(unit, story_universe_id, tracked_provider, registry)
        await write_state_events(events, client)
    client.insert_entities(registry.get_all())

    detector = CandidateDetector(client)
    conflicts = detector.detect_conflicts(story_universe_id)
    client.insert_candidate_conflicts(conflicts)

    agent = InvestigationAgent(tracked_provider, story_universe_id)
    findings = []
    for conflict in conflicts:
        verdict = await agent.investigate_async(conflict)
        client.insert_investigation_verdicts([verdict])
        findings.append({
            "conflict_id": conflict.id,
            "entity_id": conflict.entity_id,
            "attribute": conflict.attribute,
            "description": conflict.description,
            "status": verdict.status,
            "severity": verdict.severity,
            "confidence": verdict.confidence,
            "explanation": verdict.explanation,
        })

    return {
        "candidates_generated": len(conflicts),
        "conflicts_surfaced": sum(1 for f in findings if f["status"] == "verified"),
        "findings": findings,
    }


async def run_all_conditions(film_slug: str, screenplay_path: Path) -> None:
    story_universe_id = f"eval_{film_slug}"
    units = load_screenplay_units(screenplay_path, story_universe_id)
    _log(f"{film_slug}: loaded {len(units)} scene units from {screenplay_path}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for condition, runner in (
        ("A", lambda t: _run_condition_a_or_b(units, story_universe_id, "A", t)),
        ("B", lambda t: _run_condition_a_or_b(units, story_universe_id, "B", t)),
        ("C", lambda t: _run_condition_c(units, story_universe_id, t)),
    ):
        tracker = CostTracker()
        _log(f"{film_slug}: starting Condition {condition}")
        try:
            result = await runner(tracker)
        except Exception as exc:
            _log(f"{film_slug}: Condition {condition} FAILED: {exc}")
            continue
        out = {
            "film": film_slug,
            "condition": condition,
            **result,
            **tracker.to_summary_dict(),
        }
        out_path = OUT_DIR / f"{film_slug}_condition_{condition}.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        _log(
            f"{film_slug}: Condition {condition} done -- "
            f"{result['candidates_generated']} candidates, {result['conflicts_surfaced']} surfaced, "
            f"{tracker.api_calls_total} calls, ${tracker.estimated_cost_usd:.4f} -> {out_path}"
        )

    # Condition D: one-shot baseline, separate call surface (no ClickHouse
    # pipeline). Wrapped the same way as A/B/C above -- a Condition D failure
    # (network, credentials, malformed response) must not discard A/B/C's
    # already-written output for this film.
    _log(f"{film_slug}: starting Condition D")
    try:
        d_result = run_one_shot_baseline(str(screenplay_path), story_universe_id)
        d_out = {**d_result, "film": film_slug}
        out_path = OUT_DIR / f"{film_slug}_condition_D.json"
        out_path.write_text(json.dumps(d_out, indent=2), encoding="utf-8")
        _log(
            f"{film_slug}: Condition D done -- {d_result['conflicts_surfaced']} findings, "
            f"{d_result['api_calls_total']} calls, ${d_result['estimated_cost_usd']:.4f} -> {out_path}"
        )
    except Exception as exc:
        _log(f"{film_slug}: Condition D FAILED: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("film_slug", help="e.g. aliens_film -- output files are named {film_slug}_condition_X.json")
    parser.add_argument("screenplay_path", help="Path to cleaned screenplay .txt")
    args = parser.parse_args()

    if os.environ.get("MODEL_PROVIDER") != "vertexai":
        _log(
            "WARNING: MODEL_PROVIDER is not 'vertexai' -- the approved plan "
            "requires real Vertex AI calls for this ablation run, not Ollama."
        )

    asyncio.run(run_all_conditions(args.film_slug, Path(args.screenplay_path)))


if __name__ == "__main__":
    main()
