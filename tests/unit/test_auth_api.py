"""Tests for the /auth/* endpoints in backend/api/main.py.

ClickHouseClient is patched at its import site in backend.api.main so no real
ClickHouse connection is needed; each test wires up just the methods its
route touches.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("JWT_SECRET", "test-secret-please-do-not-use-in-prod")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app, limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Each test gets a clean rate-limit bucket so one test's requests can't
    trip the limiter for the next."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def _mock_ch_client(**overrides):
    m = MagicMock()
    m.get_user_by_email.return_value = None
    m.get_earliest_user_id_for_email.side_effect = lambda email: m._last_created_id
    for name, value in overrides.items():
        setattr(m, name, value)
    return m


def test_signup_success(client):
    mock = _mock_ch_client()

    def _create_user(user_id, email, password_hash):
        mock._last_created_id = user_id
        mock.get_user_by_id.return_value = (user_id, email, "2026-01-01 00:00:00")

    mock.create_user.side_effect = _create_user

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.post("/auth/signup", json={"email": "new@example.com", "password": "password123"})

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["access_token"]


def test_signup_password_too_short(client):
    with patch("backend.api.main.ClickHouseClient", return_value=_mock_ch_client()):
        res = client.post("/auth/signup", json={"email": "a@example.com", "password": "short"})
    assert res.status_code == 400


def test_signup_duplicate_email(client):
    mock = _mock_ch_client()
    mock.get_user_by_email.return_value = ("existing-id", "dupe@example.com", "hash", "2026-01-01")

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.post("/auth/signup", json={"email": "dupe@example.com", "password": "password123"})

    assert res.status_code == 409
    mock.create_user.assert_not_called()


def test_signup_loses_race_after_insert(client):
    """Two near-simultaneous signups both pass the pre-insert check; the
    post-insert re-check must reject whichever one didn't win."""
    mock = _mock_ch_client()
    mock.get_earliest_user_id_for_email.side_effect = None
    mock.get_earliest_user_id_for_email.return_value = "the-other-request-id"

    def _create_user(user_id, email, password_hash):
        mock._last_created_id = user_id

    mock.create_user.side_effect = _create_user

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.post("/auth/signup", json={"email": "race@example.com", "password": "password123"})

    assert res.status_code == 409


def test_login_success(client):
    from backend.auth import hash_password

    mock = _mock_ch_client()
    mock.get_user_by_email.return_value = (
        "user-1",
        "user@example.com",
        hash_password("password123"),
        "2026-01-01 00:00:00",
    )

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.post("/auth/login", json={"email": "user@example.com", "password": "password123"})

    assert res.status_code == 200, res.text
    assert res.json()["user"]["email"] == "user@example.com"


def test_login_invalid_credentials(client):
    mock = _mock_ch_client()
    mock.get_user_by_email.return_value = None

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        res = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})

    assert res.status_code == 401


def test_login_rate_limited_after_five_attempts(client):
    mock = _mock_ch_client()
    mock.get_user_by_email.return_value = None

    with patch("backend.api.main.ClickHouseClient", return_value=mock):
        statuses = [
            client.post("/auth/login", json={"email": "x@example.com", "password": "wrongpass"}).status_code
            for _ in range(6)
        ]

    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
