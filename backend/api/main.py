import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import fitz
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.agent.investigator import InvestigationAgent
from backend.auth import (
    UserPublic,
    create_access_token,
    get_current_user_id,
    hash_password,
    new_id,
    verify_password,
)
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
from backend.seed_demo_projects import seed_demo_projects_for_user


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

# A wildcard origin plus credentialed requests (Authorization headers) is a
# real exposure once the API holds per-user data -- restrict to the actual
# frontend origin(s) instead. FRONTEND_ORIGIN accepts a comma-separated list
# for local dev + a deployed origin.
_frontend_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-IP limiter for the unauthenticated auth endpoints (login/signup are the
# only routes an attacker can hit without a token, so they're the only ones
# that need brute-force throttling). Keyed by remote address rather than
# email/user, since the attack this guards against is credential stuffing
# from one source, not abuse of one account.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


# -- Auth ---------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user: UserPublic


@app.post("/auth/signup", response_model=AuthResponse)
@limiter.limit("5/minute")
def signup(request: Request, req: SignupRequest):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    client = ClickHouseClient()
    # Best-effort uniqueness check: ReplacingMergeTree dedups on email async,
    # not synchronously, so this narrows (does not eliminate) a race between
    # two near-simultaneous signups for the same address -- a known,
    # disclosed tradeoff of using ClickHouse (not a real OLTP store with a
    # unique constraint) for user records.
    if client.get_user_by_email(req.email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user_id = new_id()
    client.create_user(user_id, req.email, hash_password(req.password))

    # Post-insert re-check: ReplacingMergeTree hasn't merged duplicate rows
    # yet at this point, so a plain SELECT (no FINAL) still sees every row
    # inserted for this email, including one from a concurrent request that
    # slipped past the pre-insert check above. Deterministically pick the
    # earliest (created_at, then id) as the winner; if it isn't the row this
    # request just wrote, this request lost the race and must not hand back
    # a token for an account that won't end up owning the email. This closes
    # the window to "two inserts land within the same query's visibility",
    # not zero -- a real unique constraint is not available on this table
    # engine, so a vanishingly rare double-signup is an accepted residual
    # risk, not a fixed one.
    winner_id = client.get_earliest_user_id_for_email(req.email)
    if winner_id != user_id:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # Every new account starts with the demo projects (pre-run, results
    # included) so the dashboard isn't empty on first login -- see
    # backend/seed_demo_projects.py and docs/deployment-improvements.md.
    try:
        seed_demo_projects_for_user(client, user_id)
    except Exception:
        pass  # demo seeding is a nice-to-have; must never block real signup

    token = create_access_token(user_id, req.email)
    row = client.get_user_by_id(user_id)
    return AuthResponse(
        access_token=token,
        user=UserPublic(id=row[0], email=row[1], created_at=str(row[2])),
    )


@app.post("/auth/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(request: Request, req: LoginRequest):
    client = ClickHouseClient()
    row = client.get_user_by_email(req.email)
    # Same generic error whether the email doesn't exist or the password is
    # wrong -- distinguishing the two lets an attacker enumerate registered
    # emails.
    if row is None or not verify_password(req.password, row[2]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token(row[0], row[1])
    return AuthResponse(
        access_token=token,
        user=UserPublic(id=row[0], email=row[1], created_at=str(row[3])),
    )


@app.get("/auth/me", response_model=UserPublic)
def get_me(user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    row = client.get_user_by_id(user_id)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    return UserPublic(id=row[0], email=row[1], created_at=str(row[2]))


def _authorize_story_universe(client: ClickHouseClient, story_universe_id: str, user_id: str) -> None:
    """Every project-linked story_universe_id must belong to the caller.
    story_universe_ids with no project_versions row predate this feature
    (CLI-inserted test data) and have no owner to check against -- treated
    as legacy/ungated rather than blocked, so existing demo data keeps
    working. Every NEW upload always creates a project_versions row, so this
    gap only ever covers pre-existing data, never new uploads."""
    rows = client.client.query(
        "SELECT project_id FROM project_versions WHERE id = {id:String} LIMIT 1",
        parameters={"id": story_universe_id},
    ).result_rows
    if not rows:
        return
    project = client.get_project(rows[0][0])
    if project is None or project[1] != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this document.")


@app.post("/screenplay/upload")
async def upload_screenplay(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    project_id: Optional[str] = Form(default=None),
    user_id: str = Depends(get_current_user_id),
):
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _EXT_PARSERS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Use .pdf, .epub, .txt, or .fountain.")

    client = ClickHouseClient()

    if project_id:
        project = client.get_project(project_id)
        if project is None or project[1] != user_id:
            raise HTTPException(status_code=403, detail="You do not have access to this project.")
        version_number = client.get_latest_version_number(project_id) + 1
    else:
        project_id = new_id()
        client.create_project(project_id, user_id, filename)
        version_number = 1

    story_universe_id = uuid.uuid4().hex
    client.create_project_version(story_universe_id, project_id, version_number, filename)

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

    background_tasks.add_task(_run_pipeline_job, story_universe_id, tmp_path, ParserCls, project_id)

    return {"story_universe_id": story_universe_id, "project_id": project_id, "version_number": version_number}


def _run_pipeline_job(story_universe_id: str, file_path: str, ParserCls, project_id: str) -> None:
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
        registry = EntityRegistry(story_universe_id, id_scope=project_id)
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
def get_overview(story_universe_id: str, user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    _authorize_story_universe(client, story_universe_id, user_id)
    job = _JOBS.get(story_universe_id)
    if job is not None:
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
def get_scenes(story_universe_id: str, user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    _authorize_story_universe(client, story_universe_id, user_id)
    units_res = client.client.query(
        f"""SELECT id, title, unit_type, sequence_number, start_page, end_page, text
            FROM narrative_units WHERE story_universe_id = '{story_universe_id}'
            ORDER BY sequence_number"""
    )

    # Severity dot per unit: the worst verdict severity among conflicts that
    # touch this unit as prior or current evidence, or "resolved" if every
    # touching verdict resolved cleanly.
    # v.id is selected alongside severity/status purely as a join-miss
    # sentinel: ClickHouse's LEFT JOIN returns an Enum8 column's zero-value
    # (displayed as the first-declared name, e.g. "verified"/"critical") for
    # unmatched rows rather than a real NULL, so severity/status can't be
    # trusted on their own -- only rows where v.id is non-empty had an
    # actual investigation_verdicts match.
    severity_res = client.client.query(
        f"""
        SELECT unit_id, groupArray(severity) AS severities, groupArray(status) AS statuses
        FROM (
            SELECT c.prior_evidence_unit_id AS unit_id, v.severity AS severity, v.status AS status, v.id AS verdict_id
            FROM candidate_conflicts c
            LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
            WHERE c.story_universe_id = '{story_universe_id}'
            UNION ALL
            SELECT c.current_evidence_unit_id AS unit_id, v.severity AS severity, v.status AS status, v.id AS verdict_id
            FROM candidate_conflicts c
            LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
            WHERE c.story_universe_id = '{story_universe_id}'
        )
        WHERE verdict_id != ''
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
        SELECT c.id, v.severity, unit_id, excerpt, v.id AS verdict_id FROM candidate_conflicts c
        LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
        ARRAY JOIN [c.prior_evidence_unit_id, c.current_evidence_unit_id] AS unit_id,
                   [c.prior_evidence_excerpt, c.current_evidence_excerpt] AS excerpt
        WHERE c.story_universe_id = '{story_universe_id}'
        """
    )
    conflict_by_unit_excerpt: Dict[tuple, Dict[str, Any]] = {
        (row[2], row[3]): {"conflict_id": row[0], "severity": row[1] if row[4] else None} for row in conflict_res.result_rows
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
def get_entities(story_universe_id: str, user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    _authorize_story_universe(client, story_universe_id, user_id)
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
def get_conflicts(story_universe_id: str, user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    _authorize_story_universe(client, story_universe_id, user_id)
    query = f"""
        SELECT c.id, c.entity_id, c.attribute, c.prior_evidence_unit_id, c.prior_evidence_excerpt,
               c.current_evidence_unit_id, c.current_evidence_excerpt, c.description,
               v.status, v.severity, v.confidence, v.id AS verdict_id
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
        has_verdict = bool(r[11])
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
            "status": r[8] if has_verdict else "uninvestigated",
            "severity": r[9] if has_verdict else None,
            "confidence": r[10] if has_verdict else None,
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
def get_autopsy(conflict_id: str, user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    c_res = client.client.query(f"SELECT * FROM candidate_conflicts WHERE id = '{conflict_id}'")
    if not c_res.result_rows:
        raise HTTPException(status_code=404, detail="Conflict not found")

    c = c_res.result_rows[0]
    story_universe_id = c[1]
    _authorize_story_universe(client, story_universe_id, user_id)
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
def mark_intentional(conflict_id: str, user_id: str = Depends(get_current_user_id)):
    from backend.story_state.models import InvestigationVerdict

    client = ClickHouseClient()
    c_res = client.client.query(f"SELECT story_universe_id FROM candidate_conflicts WHERE id = '{conflict_id}'")
    if not c_res.result_rows:
        raise HTTPException(status_code=404, detail="Conflict not found")
    _authorize_story_universe(client, c_res.result_rows[0][0], user_id)

    verdict = InvestigationVerdict(
        id=f"verdict_manual_{conflict_id}",
        candidate_id=conflict_id,
        status="intentional",
        severity="info",
        explanation="User marked as intentional.",
        confidence=1.0,
        investigation_actions=[json.dumps({"step": "verdict", "verdict": {"status": "intentional", "note": "Manual override"}})],
    )
    client.insert_investigation_verdicts([verdict])
    return {"status": "success"}


# -- Projects / versions / diff / report ---------------------------------


@app.get("/projects")
def list_projects(user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    projects = client.list_projects(user_id)

    result = []
    for project_id, _user_id, title, created_at in projects:
        versions = client.list_project_versions(project_id)
        if not versions:
            continue
        latest = versions[-1]
        latest_story_universe_id = latest[0]
        verdict_counts = _verdict_counts_by_status(client, latest_story_universe_id)
        if verdict_counts.get("verified", 0) > 0:
            severity = "critical"
        elif verdict_counts.get("uncertain", 0) > 0:
            severity = "warning"
        else:
            severity = "resolved"
        result.append({
            "project_id": project_id,
            "title": title,
            "created_at": str(created_at),
            "version_count": len(versions),
            "latest_story_universe_id": latest_story_universe_id,
            "latest_version_number": latest[2],
            "severity": severity,
        })
    return result


@app.get("/projects/{project_id}/versions")
def list_versions(project_id: str, user_id: str = Depends(get_current_user_id)):
    client = ClickHouseClient()
    project = client.get_project(project_id)
    if project is None or project[1] != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this project.")

    versions = client.list_project_versions(project_id)
    return [
        {
            "story_universe_id": v[0],
            "version_number": v[2],
            "document_title": v[3],
            "created_at": str(v[4]),
        }
        for v in versions
    ]


@app.get("/projects/{project_id}/versions/{version_number}/diff")
def get_version_diff(project_id: str, version_number: int, user_id: str = Depends(get_current_user_id)):
    """Compares this version's candidate_conflicts against the immediately
    prior version's, joined on (entity_id, attribute) -- conflict/verdict IDs
    are scoped per-upload and never match across versions, but entity_id is
    now stable across a project's versions (see EntityRegistry's id_scope),
    so that pair is the real join key."""
    client = ClickHouseClient()
    project = client.get_project(project_id)
    if project is None or project[1] != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this project.")

    versions = {v[2]: v[0] for v in client.list_project_versions(project_id)}
    if version_number not in versions:
        raise HTTPException(status_code=404, detail="Unknown version_number for this project.")
    current_id = versions[version_number]
    prior_id = versions.get(version_number - 1)

    def _conflict_rows(story_universe_id: str) -> Dict[tuple, dict]:
        res = client.client.query(
            f"""SELECT c.id, c.entity_id, c.attribute, c.description,
                       c.prior_evidence_excerpt, c.current_evidence_excerpt,
                       v.status, v.severity, c.prior_evidence_unit_id, c.current_evidence_unit_id,
                       v.id AS verdict_id
                FROM candidate_conflicts c
                LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
                WHERE c.story_universe_id = '{story_universe_id}'"""
        )
        names = _entity_names(client, story_universe_id)
        rows = {}
        for r in res.result_rows:
            key = (r[1], r[2])
            has_verdict = bool(r[10])
            rows[key] = {
                "id": r[0],
                "entity_id": r[1],
                "entity_name": names.get(r[1], r[1]),
                "attribute": r[2],
                "description": r[3],
                "prior_excerpt": r[4],
                "current_excerpt": r[5],
                "status": r[6] if has_verdict else None,
                "severity": r[7] if has_verdict else None,
                "prior_unit_id": r[8],
                "current_unit_id": r[9],
            }
        return rows

    current_rows = _conflict_rows(current_id)

    if prior_id is None:
        diff = [{**row, "diff_status": "new"} for row in current_rows.values()]
        return {
            "has_previous": False,
            "current_story_universe_id": current_id,
            "prior_story_universe_id": None,
            "conflicts": diff,
            "entities_with_issues": list({row["entity_id"] for row in diff}),
        }

    prior_rows = _conflict_rows(prior_id)
    current_keys = set(current_rows)
    prior_keys = set(prior_rows)

    diff = []
    for key in current_keys & prior_keys:
        diff.append({**current_rows[key], "diff_status": "recurring"})
    for key in current_keys - prior_keys:
        diff.append({**current_rows[key], "diff_status": "new"})
    for key in prior_keys - current_keys:
        # The transition no longer triggers the detector in this version --
        # honestly, this means "not detected here anymore," not verified
        # proof the narrative gap was intentionally fixed.
        diff.append({**prior_rows[key], "diff_status": "resolved_in_version"})

    return {
        "has_previous": True,
        "current_story_universe_id": current_id,
        "prior_story_universe_id": prior_id,
        "conflicts": diff,
        "entities_with_issues": list({
            row["entity_id"] for row in diff if row["diff_status"] in ("recurring", "new")
        }),
    }


@app.get("/screenplay/{story_universe_id}/report")
def get_report(story_universe_id: str, user_id: str = Depends(get_current_user_id)):
    """Assembles a real Markdown findings report from the same data the
    /scenes, /entities, /conflicts endpoints already query -- no separate
    report-generation logic to keep in sync with the actual pipeline output."""
    client = ClickHouseClient()
    _authorize_story_universe(client, story_universe_id, user_id)

    units = client.client.query(
        f"""SELECT id, title, sequence_number FROM narrative_units
            WHERE story_universe_id = '{story_universe_id}' ORDER BY sequence_number"""
    ).result_rows
    entities = client.client.query(
        f"SELECT id, name, type FROM entities WHERE story_universe_id = '{story_universe_id}'"
    ).result_rows
    conflicts_res = client.client.query(
        f"""SELECT c.id, c.entity_id, c.attribute, c.description,
                   c.prior_evidence_excerpt, c.current_evidence_excerpt,
                   v.status, v.severity, v.explanation, v.confidence, v.suggested_fix, v.id AS verdict_id
            FROM candidate_conflicts c
            LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
            WHERE c.story_universe_id = '{story_universe_id}'"""
    ).result_rows
    names = _entity_names(client, story_universe_id)

    lines = [f"# StoryTrace Continuity Report", "", f"`story_universe_id`: `{story_universe_id}`", ""]
    lines.append(f"## Overview")
    lines.append(f"- {len(units)} narrative units")
    lines.append(f"- {len(entities)} tracked entities")
    lines.append(f"- {len(conflicts_res)} detected conflicts")
    lines.append("")

    lines.append("## Entities")
    for entity_id, name, etype in entities:
        lines.append(f"- **{name}** ({etype})")
    lines.append("")

    lines.append("## Findings")
    if not conflicts_res:
        lines.append("No continuity conflicts were detected.")
    for r in conflicts_res:
        entity_id, attribute, description = r[1], r[2], r[3]
        has_verdict = bool(r[11])
        status = r[6] if has_verdict else "uninvestigated"
        severity = r[7] if has_verdict else "n/a"
        explanation = r[8] if has_verdict else ""
        suggested_fix = r[10] if has_verdict else ""
        lines.append(f"### {names.get(entity_id, entity_id)} -- {attribute}")
        lines.append(f"- **Status**: {status} ({severity})")
        lines.append(f"- **Description**: {description}")
        lines.append(f"- **Prior**: \"{r[4]}\"")
        lines.append(f"- **Current**: \"{r[5]}\"")
        if explanation:
            lines.append(f"- **Investigation**: {explanation}")
        if suggested_fix:
            lines.append(f"- **Suggested fix**: {suggested_fix}")
        lines.append("")

    from fastapi.responses import PlainTextResponse

    return PlainTextResponse("\n".join(lines), media_type="text/markdown")
