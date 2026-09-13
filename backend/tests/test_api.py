"""API integration tests (require a seeded database)."""
from __future__ import annotations

from tests.conftest import requires_db


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["service"] == "EduIntel"


@requires_db
def test_students_list_and_get(client):
    r = client.get("/api/students?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1 and len(body["items"]) >= 1
    sid = body["items"][0]["id"]
    assert client.get(f"/api/students/{sid}").status_code == 200


@requires_db
def test_invalid_student_returns_404(client):
    assert client.get("/api/students/NOPE999").status_code == 404


@requires_db
def test_courses_and_health(client):
    courses = client.get("/api/courses").json()
    assert len(courses) >= 1
    h = client.get(f"/api/courses/{courses[0]['id']}/health").json()
    assert set(h["weights"]) and h["score"] is not None
    assert abs(sum(h["weights"].values()) - 1.0) < 1e-9


@requires_db
def test_dashboard_overview_shape(client):
    d = client.get("/api/dashboard/overview").json()
    assert "totals" in d and "performance_trend" in d
    assert isinstance(d["ai_insights"], list)


@requires_db
def test_weak_topics_and_feedback(client):
    weak = client.get("/api/topics/weak?limit=5").json()
    assert len(weak) >= 1
    fb = client.get("/api/feedback/insights").json()
    assert fb["total"] >= 1
    assert set(fb["sentiment"]) == {"positive", "neutral", "negative"}


@requires_db
def test_data_quality_scans_rows(client):
    dq = client.get("/api/analytics/data-quality").json()
    assert dq["rows_processed"] > 0
    assert "checks" in dq


@requires_db
def test_anomaly_detection_finds_planted(client):
    an = client.get("/api/analytics/anomalies").json()
    ids = [a["entity_id"] for a in an["assessment"]]
    assert "C03-A06" in ids  # the planted anomaly
