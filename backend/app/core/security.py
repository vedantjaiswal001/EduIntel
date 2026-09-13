"""Authentication-ready security primitives.

The demo runs without authentication so it works out of the box, but the
architecture is auth-ready: setting `API_KEY` in the environment turns on a
simple API-key gate, and `require_role` provides role-based access control
hooks that a real deployment would back with a user store / OIDC provider.

Roles model the intended production separation of duties:
  * admin      - full platform + BI views
  * instructor - course/topic/student views for their courses
  * analyst    - read-only analytics
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import Header, HTTPException, status

from app.core.config import settings


class Role(str, Enum):
    admin = "admin"
    instructor = "instructor"
    analyst = "analyst"


async def api_key_auth(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Dependency that enforces an API key when one is configured.

    When `API_KEY` is unset (development / demo) this is a no-op so the
    platform is usable without credentials.
    """
    if settings.API_KEY is None:
        return
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def require_role(*_roles: Role):
    """Return a dependency enforcing that the caller holds one of `_roles`.

    This is a placeholder that a production system would wire to real
    identity. It is included so route definitions can already declare their
    authorization intent.
    """

    async def _dependency() -> None:  # pragma: no cover - stub for demo
        # In the demo every caller is treated as an admin. A real system
        # would resolve the caller's role from a verified token here.
        return None

    return _dependency
