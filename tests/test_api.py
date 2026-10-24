
from fastapi.testclient import TestClient

from issuepilot.main import app
import issuepilot.main as main_module


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


def test_semantic_search_returns_ranked_issues(monkeypatch):
    fake_results = [
        {
            "id": 1,
            "repo": "fastapi/fastapi",
            "number": 16601,
            "title": "Incorrect validation error response",
            "state": "closed",
            "url": "https://github.com/fastapi/fastapi/issues/16601",
            "similarity": 0.5233,
        }
    ]

    def fake_search(query, top_k=5):
        assert query == "API validation errors"
        assert top_k == 3
        return fake_results[:top_k]

    monkeypatch.setattr(main_module, "semantic_search", fake_search)

    response = client.get(
        "/issues/semantic-search",
        params={"q": "API validation errors", "top_k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "API validation errors"
    assert payload["count"] == 1
    assert payload["items"][0]["number"] == 16601
    assert payload["items"][0]["similarity"] == 0.5233
    assert payload["items"][0]["url"].startswith("https://github.com/")


def test_semantic_search_respects_top_k(monkeypatch):
    def fake_search(query, top_k=5):
        return [
            {
                "id": i,
                "repo": "fastapi/fastapi",
                "number": i,
                "title": f"Issue {i}",
                "state": "open",
                "url": f"https://github.com/fastapi/fastapi/issues/{i}",
                "similarity": 0.9 - i * 0.01,
            }
            for i in range(1, top_k + 1)
        ]

    monkeypatch.setattr(main_module, "semantic_search", fake_search)

    response = client.get(
        "/issues/semantic-search",
        params={"q": "validation", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert len(response.json()["items"]) == 3


def test_semantic_search_rejects_whitespace_query():
    response = client.get(
        "/issues/semantic-search",
        params={"q": "   "},
    )

    assert response.status_code == 422


def test_semantic_search_rejects_invalid_top_k():
    response = client.get(
        "/issues/semantic-search",
        params={"q": "validation", "top_k": 21},
    )

    assert response.status_code == 422
