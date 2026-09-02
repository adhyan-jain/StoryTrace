"""Email/password + JWT auth.

Passwords are hashed with bcrypt directly (not passlib -- passlib 1.7.4's
bcrypt backend detection is broken against bcrypt>=4.1's removed `__about__`
attribute, so this avoids a real, currently-shipping compatibility bug rather
than pinning an old bcrypt). Tokens are signed HS256 JWTs; the secret comes
only from the JWT_SECRET env var, never a literal in code.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Optional

import bcrypt
import jwt
from fastapi import Header, HTTPException
from pydantic import BaseModel

ACCESS_TOKEN_TTL_SECONDS = 24 * 60 * 60


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET is not set. Generate one with `openssl rand -hex 32` and put it in .env."
        )
    return secret


class UserPublic(BaseModel):
    """Allow-listed user shape -- password_hash must never appear here or in
    any API response, by construction rather than by remembering to strip it."""

    id: str
    email: str
    created_at: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, email: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def new_id() -> str:
    return uuid.uuid4().hex


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")


def get_current_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency: decodes the Bearer token and returns just the user
    id. Kept separate from a full `get_current_user` (which would need a
    ClickHouseClient) so routes that only need the id for an ownership check
    don't pay for an extra query."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")
    token = authorization[len("Bearer ") :]
    claims = _decode(token)
    return claims["sub"]
