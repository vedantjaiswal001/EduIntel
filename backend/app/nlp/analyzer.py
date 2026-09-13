"""Feedback analysis with three interchangeable methods.

  * rule        - lexicon-based sentiment + keyword issue/topic/urgency extraction
  * transformer - a pretrained DistilBERT SST-2 sentiment model (lazy-loaded),
                  with rule-based issue/topic extraction layered on top
  * llm         - a single-shot JSON classification via the LLM abstraction,
                  falling back to the rule method when no LLM is available

All three return the same schema, so they can be compared directly.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.nlp.lexicon import (
    ISSUE_LEXICON,
    ISSUE_TO_ASPECT,
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    URGENCY_TERMS,
)

logger = get_logger(__name__)

_TRANSFORMER = None  # lazy singleton
_TRANSFORMER_FAILED = False

SCHEMA_KEYS = ("sentiment", "sentiment_score", "topics", "issues", "severity", "aspect")


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z'-]+", (text or "").lower())


def _extract_issues(low: str) -> List[str]:
    return [issue for issue, kws in ISSUE_LEXICON.items() if any(k in low for k in kws)]


def _extract_topics(low: str, topic_vocab: List[str]) -> List[str]:
    return [t for t in topic_vocab if t.lower() in low]


def _severity(sentiment: str, low: str) -> str:
    urgency = sum(1 for u in URGENCY_TERMS if u in low)
    if sentiment == "negative" and urgency >= 2:
        return "high"
    if sentiment == "negative" and urgency >= 1:
        return "medium"
    if sentiment == "negative":
        return "medium"
    return "low"


def _aspect(issues: List[str]) -> Optional[str]:
    for issue in issues:
        if issue in ISSUE_TO_ASPECT:
            return ISSUE_TO_ASPECT[issue]
    return None


class FeedbackAnalyzer:
    def __init__(self, topic_vocab: Optional[List[str]] = None, llm=None) -> None:
        self.topic_vocab = topic_vocab or []
        self._llm = llm  # optional pre-created provider

    # ---------------------------------------------------------------- rule
    def analyze_rule(self, text: str) -> Dict:
        low = (text or "").lower()
        tokens = _tokenize(text)
        pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
        neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)
        score = (pos - neg) / (pos + neg + 1)
        sentiment = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
        issues = _extract_issues(low)
        return {
            "sentiment": sentiment,
            "sentiment_score": round(score, 3),
            "topics": _extract_topics(low, self.topic_vocab),
            "issues": issues,
            "severity": _severity(sentiment, low),
            "aspect": _aspect(issues),
            "method": "rule",
        }

    # --------------------------------------------------------- transformer
    def analyze_transformer(self, text: str) -> Dict:
        pipe = _get_transformer()
        base = self.analyze_rule(text)  # reuse issue/topic/aspect extraction
        base["method"] = "transformer"
        if pipe is None:
            base["method"] = "transformer(fallback:rule)"
            return base
        try:
            out = pipe(text[:512])[0]
            label, sc = out["label"].upper(), float(out["score"])
            if sc < 0.6:
                sentiment = "neutral"
                signed = 0.0
            elif label.startswith("POS"):
                sentiment, signed = "positive", sc
            else:
                sentiment, signed = "negative", -sc
            base["sentiment"] = sentiment
            base["sentiment_score"] = round(signed, 3)
            base["severity"] = _severity(sentiment, (text or "").lower())
        except Exception as exc:  # pragma: no cover
            logger.warning("transformer inference failed: %s", exc)
            base["method"] = "transformer(fallback:rule)"
        return base

    # ---------------------------------------------------------------- llm
    def analyze_llm(self, text: str) -> Dict:
        llm = self._llm
        if llm is None:
            from app.llm.provider import get_llm

            llm = get_llm()
        if not getattr(llm, "available", False):
            base = self.analyze_rule(text)
            base["method"] = "llm(fallback:rule)"
            return base
        try:
            return self._llm_classify(llm, text)
        except Exception:
            base = self.analyze_rule(text)
            base["method"] = "llm(fallback:rule)"
            return base

    def _llm_classify(self, llm, text: str) -> Dict:
        system = (
            "You are an education feedback classifier. Return ONLY a JSON object "
            "with keys: sentiment (positive|neutral|negative), topics (array of "
            "strings), issues (array from: assignment difficulty, lecture pace, "
            "lack of examples, course material, workload, grading, clarity), "
            "severity (low|medium|high), aspect (assignments|lectures|materials|grading|null)."
        )
        data = llm.generate_json(f"Feedback: \"{text}\"", system=system)
        if not data:
            base = self.analyze_rule(text)
            base["method"] = "llm(parse-failed:rule)"
            return base
        return {
            "sentiment": data.get("sentiment", "neutral"),
            "sentiment_score": data.get("sentiment_score"),
            "topics": data.get("topics", []) or [],
            "issues": data.get("issues", []) or [],
            "severity": data.get("severity", "low"),
            "aspect": data.get("aspect"),
            "method": "llm",
        }

    def analyze(self, text: str, method: str = "rule") -> Dict:
        if method == "transformer":
            return self.analyze_transformer(text)
        if method == "llm":
            return self.analyze_llm(text)
        return self.analyze_rule(text)


def _get_transformer():
    global _TRANSFORMER, _TRANSFORMER_FAILED
    if _TRANSFORMER is not None or _TRANSFORMER_FAILED:
        return _TRANSFORMER
    try:
        from transformers import pipeline

        _TRANSFORMER = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
        )
    except Exception as exc:  # pragma: no cover - offline / no weights
        logger.warning("Transformer model unavailable (%s); using rule fallback.", exc)
        _TRANSFORMER_FAILED = True
    return _TRANSFORMER
