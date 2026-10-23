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

def test_issue_search_filters_results():
    response = client.get("/issues", params={"search": "authentication"})

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["items"], list)

    for issue in payload["items"]:
        searchable_text = (
            f"{issue['title']} {issue.get('body') or ''}"
        ).lower()
        assert "authentication" in searchable_text

def test_whitespace_only_search_returns_no_results():
    response = client.get("/issues", params={"search": "   "})

    assert response.status_code == 200
    assert response.json() == {"count": 0, "items": []}

def test_search_trims_leading_and_trailing_whitespace():
    response = client.get(
        "/issues",
        params={"search": "  authentication  "},
    )

    assert response.status_code == 200
    payload = response.json()

    for issue in payload["items"]:
        searchable_text = (
            f"{issue['title']} {issue.get('body') or ''}"
        ).lower()
        assert "authentication" in searchable_text
