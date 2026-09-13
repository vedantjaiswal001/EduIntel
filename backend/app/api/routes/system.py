"""System / meta endpoints: health and version."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import get_db
from app.core.config import settings
from app.schemas.common import HealthStatus

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthStatus)
def health(db: Session = Depends(get_db)) -> HealthStatus:
    """Liveness + DB connectivity check used by Docker health checks."""
    db_status = "up"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    return HealthStatus(
        service=settings.PROJECT_NAME,
        version=__version__,
        database=db_status,
    )
