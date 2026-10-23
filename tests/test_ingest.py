
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import issuepilot.ingest as ingest
from issuepilot.db import Base
from issuepilot.models import Issue


@pytest.fixture
def test_db(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    TestSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    monkeypatch.setattr(ingest, "engine", engine)
    monkeypatch.setattr(ingest, "SessionLocal", TestSessionLocal)

    yield TestSessionLocal

    Base.metadata.drop_all(engine)
    engine.dispose()


def make_issue(
    github_id=101,
    number=1,
    title="Original title",
    state="open",
    labels=None,
    updated_at="2026-10-14T10:00:00Z",
):
    return {
        "id": github_id,
        "number": number,
        "title": title,
        "body": "Example issue body",
        "state": state,
        "html_url": f"https://github.com/owner/repo/issues/{number}",
        "user": {"login": "test-user"},
        "labels": [
            {"name": label}
            for label in (labels if labels is not None else ["bug"])
        ],
        "comments": 2,
        "created_at": "2026-10-13T10:00:00Z",
        "updated_at": updated_at,
    }


def read_issues(TestSessionLocal):
    with TestSessionLocal() as session:
        return session.scalars(select(Issue)).all()


def test_upsert_inserts_new_issue(test_db):
    inserted, updated = ingest.upsert_issues(
        "owner", "repo", [make_issue()]
    )

    assert (inserted, updated) == (1, 0)

    issues = read_issues(test_db)
    assert len(issues) == 1
    assert issues[0].github_id == 101
    assert issues[0].title == "Original title"
    assert issues[0].labels == ["bug"]


def test_upsert_updates_existing_issue_without_duplicate(test_db):
    ingest.upsert_issues("owner", "repo", [make_issue()])

    changed_issue = make_issue(
        title="Updated title",
        state="closed",
        labels=["bug", "fixed"],
        updated_at="2026-10-14T12:00:00Z",
    )

    inserted, updated = ingest.upsert_issues(
        "owner", "repo", [changed_issue]
    )

    assert (inserted, updated) == (0, 1)

    issues = read_issues(test_db)
    assert len(issues) == 1
    assert issues[0].title == "Updated title"
    assert issues[0].state == "closed"
    assert issues[0].labels == ["bug", "fixed"]


def test_upsert_handles_multiple_distinct_issues(test_db):
    items = [
        make_issue(github_id=101, number=1, title="Issue one"),
        make_issue(github_id=102, number=2, title="Issue two"),
        make_issue(github_id=103, number=3, title="Issue three"),
    ]

    inserted, updated = ingest.upsert_issues("owner", "repo", items)

    assert (inserted, updated) == (3, 0)
    assert len(read_issues(test_db)) == 3


def test_upsert_handles_duplicate_id_within_one_batch(test_db):
    first = make_issue(title="First version")
    second = make_issue(title="Second version", state="closed")

    inserted, updated = ingest.upsert_issues(
        "owner", "repo", [first, second]
    )

    assert (inserted, updated) == (1, 1)

    issues = read_issues(test_db)
    assert len(issues) == 1
    assert issues[0].title == "Second version"
    assert issues[0].state == "closed"


def test_parse_datetime_normalizes_timezone_to_utc():
    parsed = ingest.parse_datetime("2026-10-14T15:30:00+05:30")

    assert parsed.isoformat() == "2026-10-14T10:00:00"
    assert parsed.tzinfo is None


def test_parse_datetime_handles_missing_value():
    assert ingest.parse_datetime(None) is None
