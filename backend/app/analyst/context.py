"""Evidence assembly for the AI Education Analyst.

Every number the analyst uses is computed here by the analytics layer and
attached to a typed evidence item with an explicit source. The LLM is later
given ONLY this grounding and is instructed never to invent figures — so the
analyst's numbers are always traceable to the database.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.analytics import topics as topic_analytics
from app.analytics.course_health import compute_course_health
from app.analytics.feedback_agg import feedback_insights
from app.models.academic import Course, Student, Topic
from app.models.feedback import Feedback
from app.ml import serving
from app.rag.retrieval import semantic_search

_STUDENT_RE = re.compile(r"\bS\d{3,5}\b", re.IGNORECASE)


@dataclass
class Evidence:
    kind: str          # fact | statistic | prediction | document | feedback
    statement: str
    source: str
    value: Optional[float] = None


@dataclass
class AnalystContext:
    question: str
    entities: dict = field(default_factory=dict)
    evidence: List[Evidence] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    rag_sufficient: bool = False
    recommendations: List[str] = field(default_factory=list)

    def add(self, kind, statement, source, value=None):
        self.evidence.append(Evidence(kind, statement, source, value))

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "entities": self.entities,
            "evidence": [asdict(e) for e in self.evidence],
            "citations": self.citations,
            "rag_sufficient": self.rag_sufficient,
            "recommendations": self.recommendations,
        }


def _resolve_entities(db: Session, question: str) -> dict:
    q = question.lower()
    ent: dict = {}
    m = _STUDENT_RE.search(question)
    if m:
        sid = m.group(0).upper()
        if db.get(Student, sid):
            ent["student_id"] = sid
    # course by title or code
    for c in db.execute(select(Course)).scalars():
        if c.title.lower() in q or c.code.lower() in q:
            ent["course_id"] = c.id
            break
    # topic by name (longest match first for specificity)
    topic_rows = db.execute(select(Topic)).scalars().all()
    for t in sorted(topic_rows, key=lambda t: -len(t.name)):
        if t.name.lower() in q:
            ent["topic_id"] = t.id
            ent["topic_name"] = t.name
            if "course_id" not in ent:
                ent["course_id"] = t.course_id
            break
    return ent


def gather_context(db: Session, engine: Engine, question: str) -> AnalystContext:
    ctx = AnalystContext(question=question)
    ctx.entities = _resolve_entities(db, question)
    ent = ctx.entities

    # ---- topic-focused evidence ----
    if ent.get("topic_id"):
        tp = topic_analytics.topic_performance(db, ent["topic_id"])
        if tp and tp["mean_mastery_pct"] is not None:
            ctx.add("statistic",
                    f"Average mastery of {tp['name']} is {tp['mean_mastery_pct']:.0f}% "
                    f"across {tp['students']} students.",
                    "student_topic_mastery", tp["mean_mastery_pct"])
            # compare with siblings in the same course
            siblings = topic_analytics.course_topics_performance(db, tp["course_id"])
            ranked = [s for s in siblings if s["mastery_pct"] is not None]
            ranked.sort(key=lambda s: s["mastery_pct"])
            if ranked:
                best = ranked[-1]
                if best["topic_id"] != ent["topic_id"]:
                    ctx.add("statistic",
                            f"By comparison, {best['name']} averages {best['mastery_pct']:.0f}%.",
                            "student_topic_mastery", best["mastery_pct"])
                rank = next((i for i, s in enumerate(ranked) if s["topic_id"] == ent["topic_id"]), None)
                if rank is not None:
                    ctx.add("fact",
                            f"{tp['name']} ranks {rank + 1} of {len(ranked)} topics by mastery "
                            f"in {db.get(Course, tp['course_id']).title} (1 = weakest).",
                            "analytics")
            if tp["is_weak"]:
                ctx.add("fact", f"{tp['name']} is flagged as a weak topic (mastery below 60%).",
                        "analytics")

        # feedback mentioning this topic
        name = ent.get("topic_name", "")
        n_mentions = db.execute(
            select(func.count(Feedback.id)).where(Feedback.text.ilike(f"%{name}%"))
        ).scalar() or 0
        if n_mentions:
            fb = feedback_insights(db, course_id=ent.get("course_id"))
            ts = next((t for t in fb.get("topic_sentiment", []) if t["topic"] == name), None)
            neg = f" ({ts['negative']*100:.0f}% negative)" if ts else ""
            ctx.add("feedback",
                    f"{n_mentions} feedback responses mention {name}{neg}.",
                    "feedback", float(n_mentions))

    # ---- course-focused evidence ----
    if ent.get("course_id") and not ent.get("topic_id"):
        health = compute_course_health(db, ent["course_id"])
        if health and health["score"] is not None:
            ctx.add("statistic",
                    f"{health['course_title']} health score is {health['score']:.0f}/100 "
                    f"(performance {health['components']['performance']}, attendance "
                    f"{health['components']['attendance']}, mastery "
                    f"{health['components']['topic_mastery']}).",
                    "course_health", health["score"])
            if health["pass_rate"] is not None:
                ctx.add("statistic",
                        f"Pass rate is {health['pass_rate']*100:.0f}%.",
                        "enrollments", health["pass_rate"] * 100)

    # ---- student-focused evidence (observed + PREDICTION, kept distinct) ----
    if ent.get("student_id"):
        pred = serving.get_student_prediction(db, ent["student_id"])
        if pred:
            ctx.add("prediction",
                    f"The model estimates {ent['student_id']}'s risk as {pred.risk_label} "
                    f"(modelled high-risk probability {pred.risk_probability*100:.0f}%).",
                    f"model_version:{pred.model_version_id}", pred.risk_probability)
            if pred.explanation:
                ctx.add("prediction", pred.explanation, "shap")

    # ---- retrieved documents (RAG) ----
    rag = semantic_search(db, question, course_id=ent.get("course_id"),
                          top_k=4)
    ctx.rag_sufficient = rag["sufficient"]
    for r in rag["results"][:3]:
        snippet = r["content"][:160].rsplit(" ", 1)[0]
        ctx.add("document", f"{r['citation']} {r['section'] or ''}: {snippet}…".strip(),
                r["citation"])
        if r["citation"] not in ctx.citations:
            ctx.citations.append(r["citation"])

    # ---- recommendations (weakness-driven, non-prescriptive) ----
    ctx.recommendations = _recommend(ctx)
    return ctx


def _recommend(ctx: AnalystContext) -> List[str]:
    recs: List[str] = []
    ent = ctx.entities
    if ent.get("topic_id"):
        name = ent.get("topic_name", "this topic")
        recs.append(f"Add a worked-example session on {name} before the next assessment.")
        recs.append(f"Provide prerequisite revision material for {name}.")
        recs.append(f"Share targeted practice questions on {name} and track completion.")
    elif ent.get("course_id"):
        recs.append("Review the lowest-scoring topics and schedule focused revision.")
        recs.append("Follow up with students whose attendance is declining.")
    return recs
