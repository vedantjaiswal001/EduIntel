"""Cross-cutting analytics endpoints: anomalies, data quality, BI insights."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.anomaly import detect_assessment_anomalies, detect_attendance_anomalies
from app.analytics.data_quality import run_data_quality
from app.analytics.insights import business_insights
from app.api.deps import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/anomalies")
def anomalies(db: Session = Depends(get_db)) -> dict:
    assess = detect_assessment_anomalies(db)
    attend = detect_attendance_anomalies(db)
    return {"assessment": assess, "attendance": attend,
            "total": len(assess) + len(attend)}


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db)) -> dict:
    return run_data_quality(db)


@router.get("/business-insights")
def bi(db: Session = Depends(get_db)) -> list[dict]:
    return business_insights(db)
