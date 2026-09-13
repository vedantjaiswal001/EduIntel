"""Batch feedback analysis + method comparison."""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.academic import Topic
from app.models.feedback import Feedback
from app.nlp.analyzer import FeedbackAnalyzer

logger = get_logger(__name__)


def _topic_vocab(db: Session) -> List[str]:
    return db.execute(select(Topic.name).distinct()).scalars().all()


def _rating_label(rating: Optional[float]) -> Optional[str]:
    if rating is None:
        return None
    return "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"


def analyze_and_store(db: Session, method: str = "rule", limit: Optional[int] = None) -> int:
    analyzer = FeedbackAnalyzer(topic_vocab=_topic_vocab(db))
    q = select(Feedback)
    if limit:
        q = q.limit(limit)
    rows = db.execute(q).scalars().all()
    for fb in rows:
        res = analyzer.analyze(fb.text, method=method)
        fb.sentiment = res["sentiment"]
        fb.sentiment_score = res.get("sentiment_score")
        fb.severity = res.get("severity")
        fb.aspect = res.get("aspect")
        fb.topics = res.get("topics")
        fb.issues = res.get("issues")
        fb.analysis_method = res.get("method")
    db.commit()
    logger.info("Analysed %d feedback rows with method=%s", len(rows), method)
    return len(rows)


def compare_methods(db: Session, sample: int = 200) -> Dict:
    """Compare rule vs transformer vs LLM sentiment against rating-derived labels.

    Ratings are a proxy ground truth (the student's own star rating), letting us
    quantify each method rather than merely describe it.
    """
    analyzer = FeedbackAnalyzer(topic_vocab=_topic_vocab(db))
    rows = db.execute(
        select(Feedback.text, Feedback.rating)
        .where(Feedback.rating.isnot(None))
        .limit(sample)
    ).all()

    methods = ["rule", "transformer", "llm"]
    correct = {m: 0 for m in methods}
    preds: Dict[str, List[str]] = {m: [] for m in methods}
    truth: List[str] = []
    n = 0
    for text, rating in rows:
        gold = _rating_label(rating)
        if gold is None:
            continue
        truth.append(gold)
        n += 1
        for m in methods:
            p = analyzer.analyze(text, method=m)["sentiment"]
            preds[m].append(p)
            if p == gold:
                correct[m] += 1

    accuracy = {m: round(correct[m] / n, 3) if n else None for m in methods}
    # pairwise agreement between methods
    agreement = {}
    for i in range(len(methods)):
        for j in range(i + 1, len(methods)):
            a, b = methods[i], methods[j]
            agree = sum(1 for x, y in zip(preds[a], preds[b]) if x == y)
            agreement[f"{a}-vs-{b}"] = round(agree / n, 3) if n else None

    return {
        "sample_size": n,
        "ground_truth": "student star rating (>=4 positive, <=2 negative, else neutral)",
        "accuracy_vs_rating": accuracy,
        "pairwise_agreement": agreement,
        "note": "Transformer/LLM fall back to the rule method when weights/keys "
                "are unavailable; the 'method' field on each result records which ran.",
    }
