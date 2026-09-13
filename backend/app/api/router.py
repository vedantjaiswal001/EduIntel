"""Aggregate API router.

Route modules are included here as each phase adds them.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    analyst,
    analytics,
    courses,
    dashboard,
    documents,
    feedback,
    interventions,
    ml,
    rag,
    students,
    system,
    topics,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(students.router)
api_router.include_router(courses.router)
api_router.include_router(topics.router)
api_router.include_router(feedback.router)
api_router.include_router(analytics.router)
api_router.include_router(dashboard.router)
api_router.include_router(ml.router)
api_router.include_router(documents.router)
api_router.include_router(rag.router)
api_router.include_router(analyst.router)
api_router.include_router(interventions.router)
