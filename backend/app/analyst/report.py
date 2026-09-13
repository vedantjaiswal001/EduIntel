"""Automated Education Intelligence Report.

Every numeric statement is computed from the analytics layer; the LLM (when
available) only writes the executive-summary prose from those numbers and is
told not to introduce new figures. Offline, the summary is templated.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.analytics import topics as topic_analytics
from app.analytics.course_health import compute_course_health
from app.analytics.dashboard import dashboard_overview
from app.analytics.feedback_agg import feedback_insights
from app.analytics.insights import business_insights
from app.llm.provider import get_llm
from app.ml import serving
from app.models.academic import Course, Student


def generate_report(db: Session, engine: Engine) -> Dict:
    overview = dashboard_overview(db)
    insights = business_insights(db)
    weakest = topic_analytics.weakest_topics(db, limit=5)
    at_risk = serving.get_at_risk_students(db, limit=8)
    fb = feedback_insights(db)

    course_rows = []
    for cid in db.execute(select(Course.id)).scalars().all():
        h = compute_course_health(db, cid)
        if h and h["score"] is not None:
            course_rows.append({"course_id": cid, "title": h["course_title"],
                                "health": h["score"], "pass_rate": h["pass_rate"]})
    course_rows.sort(key=lambda r: r["health"])

    at_risk_list = []
    for p in at_risk:
        s = db.get(Student, p.student_id)
        at_risk_list.append({"student_id": p.student_id, "name": s.name if s else None,
                             "risk_probability": round(p.risk_probability, 3)})

    data = {
        "generated_at": datetime.utcnow().isoformat(),
        "totals": overview["totals"],
        "risk_distribution": overview["risk_distribution"],
        "avg_performance": overview["avg_performance"],
        "attendance_avg": overview["attendance_avg"],
        "avg_course_health": overview["avg_course_health"],
        "course_health": course_rows,
        "weakest_topics": weakest,
        "at_risk_students": at_risk_list,
        "feedback_sentiment": fb.get("sentiment"),
        "top_issues": fb.get("top_issues", [])[:5],
        "insights": [i["text"] for i in insights],
    }
    data["executive_summary"] = _summary(data)
    data["markdown"] = _markdown(data)
    return data


def _summary(d: Dict) -> str:
    rd = d.get("risk_distribution") or {}
    high = rd.get("HIGH_RISK", 0)
    facts = (
        f"{d['totals']['students']} students across {d['totals']['courses']} courses; "
        f"{high} currently modelled HIGH risk; average performance "
        f"{d['avg_performance']}%, attendance {d['attendance_avg']}%, mean course "
        f"health {d['avg_course_health']}/100. Weakest topics: "
        + ", ".join(f"{t['name']} ({t['mastery_pct']:.0f}%)" for t in d['weakest_topics'][:3])
        + "."
    )
    llm = get_llm()
    if getattr(llm, "available", False):
        try:
            return llm.generate(
                f"Write a 3-sentence executive summary for a weekly education "
                f"intelligence report using ONLY these facts (do not add numbers): {facts}",
                system="You summarise education analytics precisely and never invent numbers.")
        except Exception:
            pass
    return facts


def _markdown(d: Dict) -> str:
    lines: List[str] = ["# Education Intelligence Report",
                        f"_Generated {d['generated_at']} · synthetic data_\n",
                        "## Executive Summary", d["executive_summary"], ""]
    lines.append("## Top Risks")
    if d["at_risk_students"]:
        for s in d["at_risk_students"]:
            lines.append(f"- {s['student_id']} ({s['name']}) — high-risk probability "
                         f"{s['risk_probability']*100:.0f}%")
    else:
        lines.append("- No predictions available (train the model).")
    lines += ["", "## Course Performance"]
    lines.append("| Course | Health | Pass rate |")
    lines.append("|---|---|---|")
    for c in d["course_health"]:
        pr = f"{c['pass_rate']*100:.0f}%" if c["pass_rate"] is not None else "—"
        lines.append(f"| {c['title']} | {c['health']:.0f}/100 | {pr} |")
    lines += ["", "## Topic-Level Problems"]
    for t in d["weakest_topics"]:
        lines.append(f"- {t['name']} — {t['mastery_pct']:.0f}% mastery ({t['course_id']})")
    lines += ["", "## Student Risk Distribution", f"{d['risk_distribution']}"]
    lines += ["", "## Feedback Trends", f"Sentiment: {d['feedback_sentiment']}"]
    for i in d["top_issues"]:
        lines.append(f"- {i['issue']}: {i['count']} mentions ({i['share']*100:.0f}%)")
    lines += ["", "## Recommended Actions"]
    for i in d["insights"]:
        lines.append(f"- {i}")
    lines += ["", "## Evidence",
              "All figures are computed from the platform database (synthetic dataset). "
              "Risk figures come from the active model version; topic and course figures "
              "from the analytics layer."]
    return "\n".join(lines)
