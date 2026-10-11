from fastapi.testclient import TestClient
from issuepilot.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_issues_shape():
    response = client.get("/issues")
    assert response.status_code == 200
    payload = response.json()
    assert "count" in payload
    assert "items" in payload
    assert isinstance(payload["items"], list)


def test_summary_shape():
    response = client.get("/metrics/summary")
    assert response.status_code == 200
    payload = response.json()
    assert {"total_issues", "open_issues", "closed_issues"} <= set(payload)
