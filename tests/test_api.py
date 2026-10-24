
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from issuepilot.main import app
from issuepilot.db import Base, get_db
from issuepilot.models import Issue
import issuepilot.main as main_module


client = TestClient(app)


def seed_label_test_issues(session_factory):
    updated_at = datetime(2026, 10, 24)
    issues = [
        Issue(
            github_id=index,
            repo_full_name="owner/repo",
            number=index,
            title=f"Issue {index}",
            body="Test issue",
            state="open",
            html_url=f"https://github.com/owner/repo/issues/{index}",
            labels=labels,
            updated_at=updated_at - timedelta(minutes=index),
        )
        for index, labels in (
            (1, ["docs"]),
            (2, ["enhancement"]),
            (3, ["Bug"]),
            (4, ["bug"]),
            (5, ["bug", "docs"]),
            (6, ["debug"]),
            (7, ['release "candidate"\\win']),
        )
    ]
    with session_factory() as session:
        session.add_all(issues)
        session.commit()


def test_issue_label_filter_applies_before_pagination(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    seed_label_test_issues(session_factory)

    try:
        with TestClient(app) as test_client:
            first_page = test_client.get(
                "/issues", params={"label": "bug", "limit": 2}
            )
            second_page = test_client.get(
                "/issues", params={"label": "BUG", "limit": 2, "offset": 2}
            )

        assert first_page.status_code == 200
        assert first_page.json()["count"] == 2
        assert [item["number"] for item in first_page.json()["items"]] == [3, 4]
        assert second_page.status_code == 200
        assert second_page.json()["count"] == 1
        assert [item["number"] for item in second_page.json()["items"]] == [5]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_issue_label_filter_combines_with_other_filters(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    seed_label_test_issues(session_factory)

    try:
        with TestClient(app) as test_client:
            response = test_client.get(
                "/issues",
                params={
                    "label": "bug",
                    "repo": "owner/repo",
                    "state": "open",
                    "search": "Issue",
                    "limit": 10,
                },
            )

        assert response.status_code == 200
        assert response.json()["count"] == 3
        assert [item["number"] for item in response.json()["items"]] == [3, 4, 5]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_issue_label_filter_matches_json_escaped_label(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        with session_factory() as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    seed_label_test_issues(session_factory)
    special_label = 'release "candidate"\\win'

    with session_factory() as session:
        stored_labels = session.scalar(
            select(Issue.labels).where(Issue.number == 7)
        )
    assert special_label.lower() in [
        str(item).lower() for item in stored_labels
    ]

    try:
        with TestClient(app) as test_client:
            response = test_client.get(
                "/issues",
                params={"label": special_label, "limit": 1},
            )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["items"][0]["labels"] == [special_label]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


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
