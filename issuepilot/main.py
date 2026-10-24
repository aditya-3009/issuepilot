
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Issue
from .retrieval import semantic_search


Base.metadata.create_all(engine)

app = FastAPI(
    title="IssuePilot API",
    description=(
        "Developer-operations intelligence: "
        "GitHub issue ingestion, analytics, and semantic search."
    ),
    version="0.2.0",
)


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "service": "issuepilot-api",
        "version": "0.2.0",
    }


@app.get("/issues", tags=["issues"])
def list_issues(
    search: str | None = Query(
        default=None,
        min_length=1,
        description="Search issue titles and descriptions",
    ),
    repo: str | None = Query(
        default=None,
        description="Filter by full repository name, e.g. fastapi/fastapi",
    ),
    state: str | None = Query(
        default=None,
        pattern="^(open|closed)$",
    ),
    label: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Issue)

    if search is not None:
        search = search.strip()

        if not search:
            return {"count": 0, "items": []}

        term = f"%{search}%"
        stmt = stmt.where(
            or_(
                Issue.title.ilike(term),
                Issue.body.ilike(term),
            )
        )

    if repo:
        stmt = stmt.where(Issue.repo_full_name == repo)

    if state:
        stmt = stmt.where(Issue.state == state)

    if label:
        if db.bind.dialect.name == "sqlite":
            label_values = func.json_each(Issue.labels).table_valued(
                "value"
            ).alias("issue_label")
        elif db.bind.dialect.name == "postgresql":
            label_values = func.json_array_elements_text(
                Issue.labels
            ).table_valued("value").alias("issue_label")
        else:
            raise NotImplementedError(
                "Label filtering requires SQLite or PostgreSQL JSON support."
            )

        matching_label = (
            select(1)
            .select_from(label_values)
            .where(func.lower(label_values.c.value) == label.lower())
            .correlate(Issue)
            .exists()
        )
        stmt = stmt.where(matching_label)

    rows = db.scalars(
        stmt.order_by(Issue.updated_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "count": len(rows),
        "items": [
            {
                "repo": row.repo_full_name,
                "number": row.number,
                "title": row.title,
                "body": row.body,
                "state": row.state,
                "url": row.html_url,
                "author": row.author_login,
                "labels": row.labels or [],
                "comments": row.comments_count,
                "updated_at": (
                    row.updated_at.isoformat()
                    if row.updated_at
                    else None
                ),
            }
            for row in rows
        ],
    }


@app.get("/issues/semantic-search", tags=["semantic search"])
def search_issues_semantically(
    q: str = Query(
        min_length=1,
        description="Natural-language question or issue description",
    ),
    top_k: int = Query(default=5, ge=1, le=20),
):
    """Find GitHub issues by semantic similarity."""
    if not q.strip():
        raise HTTPException(
            status_code=422,
            detail="Query must not be empty.",
        )

    try:
        results = semantic_search(q, top_k=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Semantic search failed. Check the server logs.",
        ) from exc

    return {
        "query": q,
        "count": len(results),
        "items": results,
    }


@app.get("/metrics/summary", tags=["analytics"])
def metrics_summary(db: Session = Depends(get_db)):
    total = (
        db.scalar(select(func.count()).select_from(Issue))
        or 0
    )

    open_count = (
        db.scalar(
            select(func.count())
            .select_from(Issue)
            .where(Issue.state == "open")
        )
        or 0
    )

    closed_count = (
        db.scalar(
            select(func.count())
            .select_from(Issue)
            .where(Issue.state == "closed")
        )
        or 0
    )

    return {
        "total_issues": total,
        "open_issues": open_count,
        "closed_issues": closed_count,
    }
