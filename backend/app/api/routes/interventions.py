"""Intervention Center endpoints: create, list, record outcome, effectiveness."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import interventions as svc

router = APIRouter(prefix="/interventions", tags=["interventions"])


class InterventionCreate(BaseModel):
    student_id: str
    type: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    course_id: Optional[str] = None
    description: Optional[str] = None
    expected_outcome: Optional[str] = None
    scheduled_date: Optional[date] = None


class OutcomeCreate(BaseModel):
    metric: str = "avg_score"
    before_value: float
    after_value: float
    notes: Optional[str] = None


@router.get("")
def list_interventions(
    student_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    return svc.list_interventions(db, student_id=student_id)


@router.get("/effectiveness")
def effectiveness(db: Session = Depends(get_db)) -> dict:
    return svc.effectiveness(db)


@router.post("", status_code=201)
def create_intervention(body: InterventionCreate, db: Session = Depends(get_db)) -> dict:
    iv = svc.create_intervention(
        db, student_id=body.student_id, type=body.type, reason=body.reason,
        course_id=body.course_id, description=body.description,
        expected_outcome=body.expected_outcome, scheduled_date=body.scheduled_date)
    return {"id": iv.id, "status": iv.status}


@router.post("/{intervention_id}/outcome")
def record_outcome(intervention_id: int, body: OutcomeCreate,
                   db: Session = Depends(get_db)) -> dict:
    outcome = svc.record_outcome(
        db, intervention_id=intervention_id, metric=body.metric,
        before_value=body.before_value, after_value=body.after_value, notes=body.notes)
    if outcome is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return {"intervention_id": intervention_id, "delta": outcome.delta,
            "before": outcome.before_value, "after": outcome.after_value}
