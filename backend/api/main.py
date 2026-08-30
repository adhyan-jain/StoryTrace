from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.clickhouse.client import ClickHouseClient
from typing import List, Dict, Any

app = FastAPI(title="StoryTrace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clickhouse = ClickHouseClient()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/api/universes/{story_universe_id}/overview")
def get_overview(story_universe_id: str):
    # Get basic counts
    units = clickhouse.client.query(f"SELECT count() FROM narrative_units WHERE story_universe_id = '{story_universe_id}'").result_rows[0][0]
    characters = clickhouse.client.query(f"SELECT count() FROM entities WHERE story_universe_id = '{story_universe_id}' AND type='character'").result_rows[0][0]
    props = clickhouse.client.query(f"SELECT count() FROM entities WHERE story_universe_id = '{story_universe_id}' AND type='prop'").result_rows[0][0]

    candidates = clickhouse.client.query(f"SELECT count() FROM candidate_conflicts WHERE story_universe_id = '{story_universe_id}'").result_rows[0][0]

    return {
        "narrative_units": units,
        "characters": characters,
        "props": props,
        "candidates": candidates
    }

@app.get("/api/universes/{story_universe_id}/conflicts")
def get_conflicts(story_universe_id: str):
    query = f"""
        SELECT c.id, c.entity_id, c.description, v.status, v.severity, v.explanation, v.confidence
        FROM candidate_conflicts c
        LEFT JOIN investigation_verdicts v ON c.id = v.candidate_id
        WHERE c.story_universe_id = '{story_universe_id}'
    """
    res = clickhouse.client.query(query)
    conflicts = []
    for r in res.result_rows:
        conflicts.append({
            "id": r[0],
            "entity_id": r[1],
            "description": r[2],
            "status": r[3] if r[3] else "uninvestigated",
            "severity": r[4],
            "explanation": r[5],
            "confidence": r[6]
        })
    return conflicts

@app.get("/api/conflicts/{conflict_id}/autopsy")
def get_autopsy(conflict_id: str):
    # Fetch candidate
    c_res = clickhouse.client.query(f"SELECT * FROM candidate_conflicts WHERE id = '{conflict_id}'")
    if not c_res.result_rows:
        raise HTTPException(status_code=404, detail="Conflict not found")

    c = c_res.result_rows[0]
    candidate = {
        "id": c[0],
        "story_universe_id": c[1],
        "entity_id": c[2],
        "prior_unit_id": c[3],
        "prior_excerpt": c[4],
        "current_unit_id": c[5],
        "current_excerpt": c[6],
        "description": c[7]
    }

    # Fetch verdict
    v_res = clickhouse.client.query(f"SELECT * FROM investigation_verdicts WHERE candidate_id = '{conflict_id}' ORDER BY created_at DESC LIMIT 1")
    verdict = None
    if v_res.result_rows:
        v = v_res.result_rows[0]
        verdict = {
            "status": v[2],
            "severity": v[3],
            "explanation": v[4],
            "confidence": v[5],
            "investigation_actions": v[6]
        }

    return {
        "candidate": candidate,
        "verdict": verdict
    }

@app.post("/api/conflicts/{conflict_id}/mark_intentional")
def mark_intentional(conflict_id: str):
    # Appends a new verdict
    data = [
        [f"verdict_manual_{conflict_id}", conflict_id, "intentional", "info", "User marked as intentional.", 1.0, ["Manual Override"]]
    ]
    clickhouse.client.insert(
        'investigation_verdicts',
        data,
        column_names=['id', 'candidate_id', 'status', 'severity', 'explanation', 'confidence', 'investigation_actions']
    )
    return {"status": "success"}
