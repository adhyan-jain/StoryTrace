import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import fitz
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.agent.investigator import InvestigationAgent
from backend.candidate_detection.detector import CandidateDetector
from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from backend.ingestion.parsers import (
    CHAPTER_PATTERN,
    FountainParser,
    HEADING_PATTERN,
    NovelParser,
    PlainTextParser,
    ScreenplayParser,
)
from backend.llm.base import LLMProvider
from backend.llm.client import GeminiProvider
from backend.llm.ollama import OllamaProvider
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.state_extraction import extract_state_events, write_state_events


def _detect_document_parser(file_path: str):
    """A .pdf/.epub could be a screenplay or a novel; the extension alone
    doesn't say. Sniff which heading style (INT./EXT. vs Chapter N) actually
    appears in the first few pages and pick the matching parser."""
    doc = fitz.open(file_path)
    sample = "\n".join(doc.load_page(i).get_text("text") for i in range(min(5, len(doc))))
    doc.close()

    screenplay_hits = len(HEADING_PATTERN.findall(sample))
    novel_hits = len(CHAPTER_PATTERN.findall(sample))
    return ScreenplayParser if screenplay_hits > novel_hits else NovelParser

app = FastAPI(title="StoryTrace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# clickhouse_connect's HTTP client can't run concurrent queries on one
# session (raises ProgrammingError) -- the frontend fires /scenes,
# /entities, /conflicts in parallel via Promise.all, so every request needs
# its own ClickHouseClient rather than sharing one module-level instance.

# In-memory job/progress tracker, keyed by story_universe_id. A single-process
# dev API; no new ClickHouse table needed just to track "is this job done yet".
_JOBS: Dict[str, Dict[str, Any]] = {}

_EXT_PARSERS = {
    ".pdf": NovelParser,
    ".epub": NovelParser,
    ".fountain": FountainParser,
    ".txt": PlainTextParser,
}


def _default_provider() -> LLMProvider:
    """MODEL_PROVIDER=ollama (default) runs free/local; =gemini switches to
    the paid API tier. Mirrors scripts/demo_pipeline._default_provider --
    duplicated rather than imported, since backend/ shouldn't depend on
    scripts/."""
    if os.environ.get("MODEL_PROVIDER", "ollama") == "gemini":
        return GeminiProvider()
    return OllamaProvider()


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/screenplay/upload")
async def upload_screenplay(file: UploadFile, background_tasks: BackgroundTasks):
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _EXT_PARSERS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Use .pdf, .epub, .txt, or .fountain.")

    story_universe_id = uuid.uuid4().hex

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    _JOBS[story_universe_id] = {
        "status": "parsing",
        "total_units": 0,
        "units_extracted": 0,
        "candidates_detected": 0,
        "verdicts_complete": 0,
        "document_title": filename,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }

    # Fountain is screenplay-shaped by format, always. A .pdf/.epub could be
    # either a screenplay or a novel -- the extension alone doesn't say, so
    # sniff the actual heading style used in the first few pages.
    if ext == ".fountain":
        ParserCls = FountainParser
    elif ext == ".txt":
        ParserCls = PlainTextParser
    else:
        ParserCls = _detect_document_parser(tmp_path)

    background_tasks.add_task(_run_pipeline_job, story_universe_id, tmp_path, ParserCls)

    return {"story_universe_id": story_universe_id}


def _run_pipeline_job(story_universe_id: str, file_path: str, ParserCls) -> None:
    """Runs synchronously inside a FastAPI background task (its own thread,
    since fitz/httpx calls here are blocking) -- kicked off, not awaited, by
    the upload endpoint so it returns immediately."""
    job = _JOBS[story_universe_id]
    client = ClickHouseClient()

    def _sync_status() -> None:
        # processing_status persists progress in ClickHouse so /overview can
        # report real state even if the API process restarts and the
        # in-memory _JOBS entry is gone.
        client.upsert_processing_status(
            story_universe_id,
            status=job["status"] if job["status"] != "error" else "failed",
            total_units=job["total_units"],
            units_extracted=job["units_extracted"],
            candidates_detected=job["candidates_detected"],
            verdicts_complete=job["verdicts_complete"],
            error_message=job["error"] or "",
        )

    try:
        _sync_status()
        parser = ParserCls(document_id=story_universe_id, story_universe_id=story_universe_id)
        units: List[NarrativeUnit] = parser.parse(file_path)
        client.insert_narrative_units(units)
        job["total_units"] = len(units)
        _sync_status()

        job["status"] = "extracting"
        llm = _default_provider()
        registry = EntityRegistry(story_universe_id)
        for unit in units:
            events = asyncio.run(extract_state_events(unit, story_universe_id, llm, registry))
            asyncio.run(write_state_events(events, client))
            job["units_extracted"] += 1
        client.insert_entities(registry.get_all())
        _sync_status()

        job["status"] = "detecting"
        detector = CandidateDetector(client)
        conflicts = detector.detect_conflicts(story_universe_id)
        client.insert_candidate_conflicts(conflicts)
        job["candidates_detected"] = len(conflicts)
        _sync_status()

        job["status"] = "investigating"
        agent = InvestigationAgent(_InvestigationLLM(llm), story_universe_id)
        for conflict in conflicts:
            verdict = agent.investigate(conflict)
            client.insert_investigation_verdicts([verdict])
            job["verdicts_complete"] += 1

        job["status"] = "complete"
        _sync_status()
    except Exception as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        _sync_status()
    finally:
        try:
            os.unlink(file_path)
        except OSError:
            pass


class _InvestigationLLM:
    """InvestigationAgent's constructor is typed for GeminiProvider, but it
    only calls .complete()/.model like any LLMProvider -- wrap whichever
    provider _default_provider() picked so Ollama-backed investigation works
    without changing the agent's signature."""

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def __getattr__(self, name):
        return getattr(self._provider, name)


@app.get("/screenplay/{story_universe_id}/overview")
def get_overview(story_universe_id: str):
    job = _JOBS.get(story_universe_id)
    if job is not None:
        client = ClickHouseClient()
        entities_tracked = client.client.query(
            f"SELECT count() FROM entities WHERE story_universe_id = '{story_universe_id}'"
        ).result_rows[0][0]
        verdict_counts = _verdict_counts_by_status(client, story_universe_id)
        return {
            "story_universe_id": story_universe_id,
            "title": job["document_title"],
            "total_units": job["total_units"],
            "units_extracted": job["units_extracted"],
            "candidates_detected": job["candidates_detected"],
            "verdicts_complete": job["verdicts_complete"],
            "status": job["status"],
            "error": job["error"],
            "document_title": job["document_title"],
            "entities_tracked": entities_tracked,
            "verified_conflicts": verdict_counts.get("verified", 0),
            "resolved_conflicts": verdict_counts.get("resolved", 0),
            "uncertain_conflicts": verdict_counts.get("uncertain", 0),
        }

    # No in-memory job (e.g. server restarted, or data was loaded outside the
    # upload flow like the CLI pipeline scripts) -- fall back to what's
    # actually in ClickHouse and report it as already complete.
    client = ClickHouseClient()
    units = client.client.query(
        f"SELECT count() FROM narrative_units WHERE story_universe_id = '{story_universe_id}'"
    ).result_rows[0][0]
    if units == 0:
        raise HTTPException(status_code=404, detail="Unknown story_universe_id")

    events = client.client.query(
        f"SELECT count(DISTINCT unit_id) FROM state_events WHERE story_universe_id = '{story_universe_id}'"
    ).result_rows[0][0]
    candidates = client.client.query(
        f"SELECT count() FROM candidate_conflicts WHERE story_universe_id = '{story_universe_id}'"
    ).result_rows[0][0]
    verdicts = client.client.query(
        f"""SELECT count() FROM investigation_verdicts
            WHERE candidate_id IN (SELECT id FROM candidate_conflicts WHERE story_universe_id = '{story_universe_id}')"""
    ).result_rows[0][0]

    entities_tracked = client.client.query(
        f"SELECT count() FROM entities WHERE story_universe_id = '{story_universe_id}'"
    ).result_rows[0][0]
    verdict_counts = _verdict_counts_by_status(client, story_universe_id)

    return {
        "story_universe_id": story_universe_id,
        "title": None,
        "total_units": units,
        "units_extracted": events,
        "candidates_detected": candidates,
        "verdicts_complete": verdicts,
        "status": "complete",
        "error": None,
        "document_title": None,
        "entities_tracked": entities_tracked,
        "verified_conflicts": verdict_counts.get("verified", 0),
        "resolved_conflicts": verdict_counts.get("resolved", 0),
        "uncertain_conflicts": verdict_counts.get("uncertain", 0),
    }


def _verdict_counts_by_status(client: ClickHouseClient, story_universe_id: str) -> Dict[str, int]:
    rows = client.client.query(
        f"""SELECT status, count() FROM investigation_verdicts
            WHERE candidate_id IN (SELECT id FROM candidate_conflicts WHERE story_universe_id = '{story_universe_id}')
            GROUP BY status"""
    ).result_rows
    return {row[0]: row[1] for row in rows}


@app.get("/screenplay/{story_universe_id}/scenes")
def get_scenes(story_universe_id: str):
    client = ClickHouseClient()
    units_res = client.client.query(
        f"""SELECT id, title, unit_type, sequence_number, start_page, end_page, text
            FROM narrative_units WHERE story_universe_id = '{story_universe_id}'
            ORDER BY sequence_number"""
    )

    # Severity dot per unit: the worst verdict severity among conflicts that
    # touch this unit as prior or current evidence, or "resolved" if every
    # touching verdict resolved cleanly.
    severity_res = client.client.query(
        f"""
        SELECT unit_id, groupArray(severity) AS severities, groupArray(status) AS statuses
        FROM (
            SELECT c.prior_evidence_unit_id AS unit_id, v.severity AS severity, v.status AS status
            FROM candidate_conflicts c
            LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
            WHERE c.story_universe_id = '{story_universe_id}'
            UNION ALL
            SELECT c.current_evidence_unit_id AS unit_id, v.severity AS severity, v.status AS status
            FROM candidate_conflicts c
            LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
            WHERE c.story_universe_id = '{story_universe_id}'
        )
        GROUP BY unit_id
        """
    )
    severity_by_unit: Dict[str, str] = {}
    for unit_id, severities, statuses in severity_res.result_rows:
        if "critical" in severities:
            severity_by_unit[unit_id] = "critical"
        elif "warning" in severities:
            severity_by_unit[unit_id] = "warning"
        elif statuses and all(s == "resolved" for s in statuses if s):
            severity_by_unit[unit_id] = "resolved"

    names = _entity_names(client, story_universe_id)

    # Conflict linkage per (unit_id, raw_excerpt): lets the center panel tell
    # "this highlighted span is a plain extracted fact" from "this one has a
    # linked conflict you can click into".
    conflict_res = client.client.query(
        f"""
        SELECT c.id, v.severity, unit_id, excerpt FROM candidate_conflicts c
        LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
        ARRAY JOIN [c.prior_evidence_unit_id, c.current_evidence_unit_id] AS unit_id,
                   [c.prior_evidence_excerpt, c.current_evidence_excerpt] AS excerpt
        WHERE c.story_universe_id = '{story_universe_id}'
        """
    )
    conflict_by_unit_excerpt: Dict[tuple, Dict[str, Any]] = {
        (row[2], row[3]): {"conflict_id": row[0], "severity": row[1]} for row in conflict_res.result_rows
    }

    events_res = client.client.query(
        f"""SELECT unit_id, entity_id, attribute, value, confidence, raw_excerpt
            FROM state_events WHERE story_universe_id = '{story_universe_id}'"""
    )
    events_by_unit: Dict[str, List[dict]] = {}
    for unit_id, entity_id, attribute, value, confidence, raw_excerpt in events_res.result_rows:
        link = conflict_by_unit_excerpt.get((unit_id, raw_excerpt))
        events_by_unit.setdefault(unit_id, []).append({
            "entity_id": entity_id,
            "entity_name": names.get(entity_id, entity_id),
            "attribute": attribute,
            "value": value,
            "confidence": confidence,
            "raw_excerpt": raw_excerpt,
            "conflict_id": link["conflict_id"] if link else None,
            "severity": link["severity"] if link else None,
        })

    return [
        {
            "unit_id": r[0],
            "title": r[1],
            "unit_type": r[2],
            "sequence_number": r[3],
            "page_start": r[4],
            "page_end": r[5],
            "raw_text": r[6],
            "severity": severity_by_unit.get(r[0]),
            "state_events": events_by_unit.get(r[0], []),
        }
        for r in units_res.result_rows
    ]


@app.get("/screenplay/{story_universe_id}/entities")
def get_entities(story_universe_id: str):
    client = ClickHouseClient()
    entities_res = client.client.query(
        f"SELECT id, name, type FROM entities WHERE story_universe_id = '{story_universe_id}'"
    )
    findings_res = client.client.query(
        f"SELECT entity_id, count() FROM candidate_conflicts WHERE story_universe_id = '{story_universe_id}' GROUP BY entity_id"
    )
    finding_counts = {row[0]: row[1] for row in findings_res.result_rows}

    return [
        {
            "entity_id": r[0],
            "name": r[1],
            "type": r[2],
            "finding_count": finding_counts.get(r[0], 0),
        }
        for r in entities_res.result_rows
    ]


def _entity_names(client: ClickHouseClient, story_universe_id: str) -> Dict[str, str]:
    res = client.client.query(
        f"SELECT id, name FROM entities WHERE story_universe_id = '{story_universe_id}'"
    )
    return {row[0]: row[1] for row in res.result_rows}


def _page_by_unit(client: ClickHouseClient, story_universe_id: str) -> Dict[str, int]:
    res = client.client.query(
        f"SELECT id, start_page FROM narrative_units WHERE story_universe_id = '{story_universe_id}'"
    )
    return {row[0]: row[1] for row in res.result_rows}


@app.get("/screenplay/{story_universe_id}/conflicts")
def get_conflicts(story_universe_id: str):
    client = ClickHouseClient()
    query = f"""
        SELECT c.id, c.entity_id, c.attribute, c.prior_evidence_unit_id, c.prior_evidence_excerpt,
               c.current_evidence_unit_id, c.current_evidence_excerpt, c.description,
               v.status, v.severity, v.confidence
        FROM candidate_conflicts c
        LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
        WHERE c.story_universe_id = '{story_universe_id}'
    """
    res = client.client.query(query)
    names = _entity_names(client, story_universe_id)
    pages = _page_by_unit(client, story_universe_id)

    conflicts = []
    for r in res.result_rows:
        entity_id = r[1]
        conflicts.append({
            "id": r[0],
            "entity_id": entity_id,
            "entity_name": names.get(entity_id, entity_id),
            "attribute": r[2],
            "prior_unit_id": r[3],
            "prior_excerpt": r[4],
            "prior_page": pages.get(r[3]),
            "current_unit_id": r[5],
            "current_excerpt": r[6],
            "current_page": pages.get(r[5]),
            "description": r[7],
            "status": r[8] if r[8] else "uninvestigated",
            "severity": r[9],
            "confidence": r[10],
        })
    return conflicts


def _parse_investigation_steps(investigation_actions: List[str]) -> List[dict]:
    steps = []
    for raw in investigation_actions:
        try:
            steps.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            # Pre-existing free-text action from before structured logging.
            steps.append({"step": "note", "message": raw})
    return steps


@app.get("/conflict/{conflict_id}/autopsy")
def get_autopsy(conflict_id: str):
    client = ClickHouseClient()
    c_res = client.client.query(f"SELECT * FROM candidate_conflicts WHERE id = '{conflict_id}'")
    if not c_res.result_rows:
        raise HTTPException(status_code=404, detail="Conflict not found")

    c = c_res.result_rows[0]
    story_universe_id = c[1]
    entity_id = c[2]
    names = _entity_names(client, story_universe_id)
    pages = _page_by_unit(client, story_universe_id)

    conflict = {
        "id": c[0],
        "entity_id": entity_id,
        "entity_name": names.get(entity_id, entity_id),
        "attribute": c[3],
        "prior_unit_id": c[4],
        "prior_excerpt": c[5],
        "prior_page": pages.get(c[4]),
        "current_unit_id": c[6],
        "current_excerpt": c[7],
        "current_page": pages.get(c[6]),
        "description": c[8],
    }

    v_res = client.client.query(
        f"SELECT * FROM investigation_verdicts WHERE candidate_id = '{conflict_id}' ORDER BY created_at DESC LIMIT 1"
    )
    verdict = None
    steps: List[dict] = []
    if v_res.result_rows:
        v = v_res.result_rows[0]
        verdict = {
            "status": v[2],
            "severity": v[3],
            "explanation": v[4],
            "confidence": v[5],
            "suggested_fix": v[7] if len(v) > 7 else "",
        }
        steps = _parse_investigation_steps(v[6])

    return {"conflict": conflict, "verdict": verdict, "steps": steps}


@app.post("/conflict/{conflict_id}/intentional")
def mark_intentional(conflict_id: str):
    from backend.story_state.models import InvestigationVerdict

    verdict = InvestigationVerdict(
        id=f"verdict_manual_{conflict_id}",
        candidate_id=conflict_id,
        status="intentional",
        severity="info",
        explanation="User marked as intentional.",
        confidence=1.0,
        investigation_actions=[json.dumps({"step": "verdict", "verdict": {"status": "intentional", "note": "Manual override"}})],
    )
    ClickHouseClient().insert_investigation_verdicts([verdict])
    return {"status": "success"}
