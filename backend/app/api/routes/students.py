"""Student CRUD-style read/write endpoints.

Analytics-heavy student endpoints (risk, trajectory, recommendations) are
added in later phases; this module provides the core record access.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.trajectory import student_trajectory
from app.api.deps import PaginationParams, get_db, pagination
from app.db.session import engine
from app.ml import serving
from app.models.academic import Student
from app.services import interventions as interventions_svc
from app.schemas.common import Page
from app.schemas.student import StudentCreate, StudentRead

router = APIRouter(prefix="/students", tags=["students"])


def _prediction_dict(p) -> dict:
    return {
        "student_id": p.student_id,
        "risk_label": p.risk_label,
        "risk_probability": round(p.risk_probability, 4),
        "probabilities": p.probabilities,
        "features": p.features,
        "model_version_id": p.model_version_id,
        "predicted_at": p.predicted_at,
        "explanation": p.explanation,          # populated in Phase 5 (SHAP)
        "shap_values": p.shap_values,          # populated in Phase 5
    }


@router.get("", response_model=Page[StudentRead])
def list_students(
    db: Session = Depends(get_db),
    page: PaginationParams = Depends(pagination),
    program: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Match name or id"),
) -> Page[StudentRead]:
    stmt = select(Student)
    count_stmt = select(func.count(Student.id))
    if program:
        stmt = stmt.where(Student.program == program)
        count_stmt = count_stmt.where(Student.program == program)
    if search:
        like = f"%{search}%"
        stmt = stmt.where((Student.name.ilike(like)) | (Student.id.ilike(like)))
        count_stmt = count_stmt.where(
            (Student.name.ilike(like)) | (Student.id.ilike(like))
        )
    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(stmt.order_by(Student.id).limit(page.limit).offset(page.offset))
        .scalars()
        .all()
    )
    return Page(items=rows, total=total, limit=page.limit, offset=page.offset)


@router.get("/at-risk")
def at_risk_students(
    limit: int = Query(50, ge=1, le=500),
    label: str = Query("HIGH_RISK"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Students ranked by risk (requires a trained model — see scripts/train.py)."""
    preds = serving.get_at_risk_students(db, limit=limit, label=label)
    out = []
    for p in preds:
        student = db.get(Student, p.student_id)
        out.append({
            "student_id": p.student_id,
            "name": student.name if student else None,
            "program": student.program if student else None,
            "risk_label": p.risk_label,
            "risk_probability": round(p.risk_probability, 4),
        })
    return out


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: str, db: Session = Depends(get_db)) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/{student_id}/risk")
def get_student_risk(student_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    pred = serving.get_student_prediction(db, student_id)
    if pred is None:
        raise HTTPException(
            status_code=404,
            detail="No prediction available. Train the model (scripts/train.py) first.",
        )
    return _prediction_dict(pred)


@router.get("/{student_id}/trajectory")
def get_student_trajectory(student_id: str, db: Session = Depends(get_db)) -> dict:
    result = student_trajectory(db, engine, student_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return result


@router.get("/{student_id}/recommendations")
def get_student_recommendations(student_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return interventions_svc.recommend_for_student(db, student_id)


@router.post("", response_model=StudentRead, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)) -> Student:
    if db.get(Student, payload.id) is not None:
        raise HTTPException(status_code=409, detail="Student id already exists")
    student = Student(
        id=payload.id,
        name=payload.name,
        email=payload.email,
        program=payload.program,
        enrollment_year=payload.enrollment_year,
        prev_gpa=payload.prev_gpa,
        is_synthetic=False,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student
