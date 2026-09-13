"""Feedback aggregation.

Phase 3 provides rating-based sentiment plus a transparent rule-based issue
extractor and topic-mention sentiment. Phase 7 upgrades the sentiment/issue
signal with transformer + LLM methods; the aggregation API stays the same.
"""
from __future__ import annotations

import re
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Topic
from app.models.feedback import Feedback

# Rule-based issue lexicon: issue label -> keywords/patterns.
ISSUE_LEXICON: Dict[str, List[str]] = {
    "assignment difficulty": ["difficult", "hard", "tough", "challenging", "unreasonable"],
    "lecture pace": ["pace", "fast", "quickly", "rushed", "slow"],
    "lack of examples": ["example", "examples", "worked example", "practice"],
    "course material": ["material", "notes", "resources", "textbook"],
    "workload": ["workload", "too much", "long", "time-consuming", "crammed"],
    "grading": ["grading", "harsh", "marks", "unfair"],
    "clarity": ["confusing", "unclear", "explained clearly", "hard to follow"],
}


def _sentiment_from_rating(rating) -> str:
    if rating is None:
        return "neutral"
    if rating >= 4:
        return "positive"
    if rating <= 2:
        return "negative"
    return "neutral"


def feedback_insights(db: Session, course_id: str | None = None) -> dict:
    q = select(Feedback.text, Feedback.rating, Feedback.course_id, Feedback.sentiment)
    if course_id:
        q = q.where(Feedback.course_id == course_id)
    rows = db.execute(q).all()
    n = len(rows)
    if n == 0:
        return {"total": 0, "sentiment": {}, "top_issues": [], "topic_sentiment": []}

    # Prefer stored NLP sentiment (Phase 7) when present; else derive from rating.
    used_nlp = any(r[3] for r in rows)

    def sentiment_of(rating, stored) -> str:
        return stored if stored else _sentiment_from_rating(rating)

    sent = {"positive": 0, "neutral": 0, "negative": 0}
    issue_counts = {k: 0 for k in ISSUE_LEXICON}
    for text_, rating, _, stored in rows:
        sent[sentiment_of(rating, stored)] += 1
        low = (text_ or "").lower()
        for issue, kws in ISSUE_LEXICON.items():
            if any(kw in low for kw in kws):
                issue_counts[issue] += 1

    top_issues = sorted(
        ({"issue": k, "count": v, "share": round(v / n, 3)} for k, v in issue_counts.items() if v),
        key=lambda d: d["count"], reverse=True,
    )

    # ---- topic-mention sentiment: match topic names appearing in feedback text
    topics = db.execute(select(Topic.name).distinct()).scalars().all()
    topic_sent: Dict[str, Dict[str, int]] = {}
    for t in topics:
        pat = re.compile(re.escape(t.lower()))
        for text_, rating, _, stored in rows:
            if pat.search((text_ or "").lower()):
                d = topic_sent.setdefault(t, {"positive": 0, "neutral": 0, "negative": 0})
                d[sentiment_of(rating, stored)] += 1
    topic_sentiment = []
    for t, d in topic_sent.items():
        tot = sum(d.values())
        if tot < 5:  # ignore rarely-mentioned topics
            continue
        topic_sentiment.append({
            "topic": t, "total": tot,
            "positive": round(d["positive"] / tot, 3),
            "neutral": round(d["neutral"] / tot, 3),
            "negative": round(d["negative"] / tot, 3),
        })
    topic_sentiment.sort(key=lambda d: d["negative"], reverse=True)

    return {
        "total": n,
        "sentiment": {k: round(v / n, 3) for k, v in sent.items()},
        "sentiment_counts": sent,
        "top_issues": top_issues,
        "topic_sentiment": topic_sentiment[:15],
        "sentiment_source": "nlp" if used_nlp else "rating-based",
        "method": "stored NLP sentiment when available; rule-based issue extraction",
    }
