"""Chunking and NLP unit tests, including edge cases."""
from __future__ import annotations

from app.nlp.analyzer import FeedbackAnalyzer
from app.rag.chunking import chunk_document, clean


def test_chunking_produces_metadata():
    text = "Recursion\n\n" + ("word " * 400)
    chunks = chunk_document([(1, text)], max_words=100, overlap=20)
    assert len(chunks) >= 3
    assert all(c["page"] == 1 for c in chunks)
    assert chunks[0]["section"] == "Recursion"
    assert all(c["token_count"] <= 100 for c in chunks)


def test_chunking_empty_or_corrupt_text_yields_nothing():
    assert chunk_document([(1, "")]) == []
    assert chunk_document([(1, "   \n  ")]) == []


def test_clean_collapses_whitespace():
    assert clean("a\r\n\n\n\nb   c") == "a\n\nb c"


def test_rule_sentiment_positive_and_negative():
    an = FeedbackAnalyzer(topic_vocab=["Dynamic Programming"])
    pos = an.analyze_rule("The lectures are clear and the examples are excellent.")
    neg = an.analyze_rule("The Dynamic Programming assignments are extremely difficult and confusing.")
    assert pos["sentiment"] == "positive"
    assert neg["sentiment"] == "negative"
    assert "Dynamic Programming" in neg["topics"]
    assert "assignment difficulty" in neg["issues"]


def test_empty_feedback_is_neutral():
    an = FeedbackAnalyzer()
    r = an.analyze_rule("")
    assert r["sentiment"] == "neutral"
    assert r["issues"] == []


def test_analyze_dispatch_falls_back_offline():
    an = FeedbackAnalyzer()
    # transformer/llm are unavailable offline -> method records the fallback
    r = an.analyze("This is very difficult", method="transformer")
    assert r["method"].startswith("transformer")
