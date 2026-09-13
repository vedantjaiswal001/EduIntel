"""AI Education Analyst and automated report endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analyst.analyst import answer_question
from app.analyst.report import generate_report
from app.api.deps import get_db
from app.db.session import engine

router = APIRouter(tags=["analyst"])


class AnalystQuery(BaseModel):
    question: str = Field(min_length=1)


@router.post("/analyst/query")
def analyst_query(body: AnalystQuery, db: Session = Depends(get_db)) -> dict:
    return answer_question(db, engine, body.question)


@router.get("/reports/weekly")
def weekly_report(db: Session = Depends(get_db)) -> dict:
    return generate_report(db, engine)
