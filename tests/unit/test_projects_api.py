"""Tests for /projects, /projects/{id}/versions, the version diff, and the
markdown report endpoint in backend/api/main.py.

Auth is bypassed via a FastAPI dependency override (get_current_user_id),
and ClickHouseClient is patched at its import site in backend.api.main.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test-secret-please-do-not-use-in-prod")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.auth import get_current_user_id

USER_ID = "user-1"


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user_id, None)


def _query_result(rows):
    res = MagicMock()
    res.result_rows = rows
    return res


def test_list_projects(client):
    mock = MagicMock()
    mock.list_projects.return_value = [("proj-1", USER_ID, "My Screenplay", "2026-01-01 00:00:00")]
    mock.list_project_versions.return_value = [("su-1", "proj-1", 1, "Draft v1", "2026-01-01 00:00:00")]
    mock.client.query.return_value = _query_result([])  # verdict counts query

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.get("/projects")

    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 1
    assert body[0]["project_id"] == "proj-1"
    assert body[0]["severity"] == "resolved"


def test_list_versions_forbidden_for_other_users_project(client):
    mock = MagicMock()
    mock.get_project.return_value = ("proj-1", "someone-else", "Title", "2026-01-01")

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.get("/projects/proj-1/versions")

    assert res.status_code == 403


def test_list_versions_ok(client):
    mock = MagicMock()
    mock.get_project.return_value = ("proj-1", USER_ID, "Title", "2026-01-01")
    mock.list_project_versions.return_value = [("su-1", "proj-1", 1, "Doc Title", "2026-01-01 00:00:00")]

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.get("/projects/proj-1/versions")

    assert res.status_code == 200
    assert res.json() == [
        {"story_universe_id": "su-1", "version_number": 1, "document_title": "Doc Title", "created_at": "2026-01-01 00:00:00"}
    ]


def test_version_diff_first_version_has_no_previous(client):
    mock = MagicMock()
    mock.get_project.return_value = ("proj-1", USER_ID, "Title", "2026-01-01")
    mock.list_project_versions.return_value = [("su-1", "proj-1", 1, "Doc Title", "2026-01-01 00:00:00")]
    mock.client.query.return_value = _query_result([])  # conflict rows + entity name lookups

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.get("/projects/proj-1/versions/1/diff")

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["has_previous"] is False
    assert body["conflicts"] == []


def test_version_diff_unknown_version_number(client):
    mock = MagicMock()
    mock.get_project.return_value = ("proj-1", USER_ID, "Title", "2026-01-01")
    mock.list_project_versions.return_value = [("su-1", "proj-1", 1, "Doc Title", "2026-01-01 00:00:00")]

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.get("/projects/proj-1/versions/99/diff")

    assert res.status_code == 404


def test_report_returns_markdown(client):
    mock = MagicMock()
    mock.get_project.return_value = ("proj-1", USER_ID, "Title", "2026-01-01")

    def _query(sql, **kwargs):
        if "project_versions" in sql:
            return _query_result([])  # legacy/ungated story_universe_id, per _authorize_story_universe
        if "narrative_units" in sql:
            return _query_result([("u1", "Scene 1", 1)])
        if "candidate_conflicts" in sql and "JOIN" not in sql:
            return _query_result([])
        if "entities" in sql and "candidate_conflicts" not in sql:
            return _query_result([("e1", "Alice", "character")])
        return _query_result([])

    mock.client.query.side_effect = _query

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.get("/screenplay/su-1/report")

    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/markdown")
    assert "StoryTrace Continuity Report" in res.text
