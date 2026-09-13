"""Import all ORM models so `Base.metadata` is fully populated.

Importing this package (or `app.models`) guarantees every table is
registered before `Base.metadata.create_all` or Alembic autogeneration runs.
"""
from app.models.academic import Course, Enrollment, Student, Topic
from app.models.assessment import (
    Assessment,
    AssessmentResult,
    Attendance,
    Question,
    QuestionResult,
    StudentTopicMastery,
)
from app.models.documents import Document, DocumentChunk
from app.models.feedback import Feedback
from app.models.intervention import Intervention, InterventionOutcome
from app.models.ml import Experiment, ModelVersion, Prediction
from app.models.ops import Alert, AuditLog

__all__ = [
    "Student",
    "Course",
    "Topic",
    "Enrollment",
    "Assessment",
    "Question",
    "AssessmentResult",
    "QuestionResult",
    "Attendance",
    "StudentTopicMastery",
    "Feedback",
    "Document",
    "DocumentChunk",
    "ModelVersion",
    "Experiment",
    "Prediction",
    "Intervention",
    "InterventionOutcome",
    "Alert",
    "AuditLog",
]
