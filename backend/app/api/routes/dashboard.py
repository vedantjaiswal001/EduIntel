"""Executive dashboard endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.dashboard import dashboard_overview
from app.api.deps import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    return dashboard_overview(db)
