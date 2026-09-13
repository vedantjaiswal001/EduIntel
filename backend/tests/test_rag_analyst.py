"""RAG retrieval and AI-analyst integration tests (require seeded DB + documents)."""
from __future__ import annotations

from tests.conftest import requires_db


@requires_db
def test_rag_relevant_query_returns_cited_results(client):
    r = client.post("/api/rag/query", json={"query": "recursion and memoization dynamic programming", "top_k": 3})
    body = r.json()
    assert r.status_code == 200
    if body["count"] == 0:
        import pytest
        pytest.skip("no documents ingested")
    assert body["results"][0]["citation"].startswith("[")


@requires_db
def test_rag_irrelevant_query_is_insufficient(client):
    body = client.post("/api/rag/query", json={"query": "the price of bitcoin tomorrow"}).json()
    # either no results, or flagged insufficient
    assert body["sufficient"] is False or body["count"] == 0


@requires_db
def test_analyst_grounded_answer_has_evidence(client):
    body = client.post("/api/analyst/query", json={"question": "Why are students performing poorly in Dynamic Programming?"}).json()
    assert body["sufficient"] is True
    assert len(body["evidence"]) >= 1
    # numbers come from the analytics layer, surfaced as evidence
    assert any(e["kind"] in ("statistic", "fact") for e in body["evidence"])


@requires_db
def test_analyst_out_of_scope_declines(client):
    body = client.post("/api/analyst/query", json={"question": "What is the price of bitcoin?"}).json()
    assert body["sufficient"] is False
    assert body["mode"] == "insufficient"


@requires_db
def test_student_risk_and_recommendations(client):
    # find an at-risk student if predictions exist
    at = client.get("/api/students/at-risk?limit=1").json()
    if not at:
        import pytest
        pytest.skip("no predictions (model not trained)")
    sid = at[0]["student_id"]
    risk = client.get(f"/api/students/{sid}/risk").json()
    assert risk["risk_label"] in ("LOW_RISK", "MEDIUM_RISK", "HIGH_RISK")
    recs = client.get(f"/api/students/{sid}/recommendations").json()
    assert "recommendations" in recs
