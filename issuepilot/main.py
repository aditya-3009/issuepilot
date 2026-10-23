
from fastapi import Depends, FastAPI, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Issue


Base.metadata.create_all(engine)

app = FastAPI(
    title="IssuePilot API",
    description="Developer-operations intelligence: GitHub issue ingestion and analytics.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "service": "issuepilot-api",
        "version": "0.1.0",
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

    # Search issue titles and descriptions.
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Issue.title.ilike(term),
                Issue.body.ilike(term),
            )
        )

    # Filter by repository.
    if repo:
        stmt = stmt.where(Issue.repo_full_name == repo)

    # Filter by issue state.
    if state:
        stmt = stmt.where(Issue.state == state)

    # Retrieve the requested page of results.
    rows = db.scalars(
        stmt.order_by(Issue.updated_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    # Filter labels after retrieving the bounded result set.
    if label:
        rows = [
            row
            for row in rows
            if label.lower()
            in [str(item).lower() for item in (row.labels or [])]
        ]

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
