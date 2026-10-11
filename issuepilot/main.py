from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
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
    return {"status": "ok", "service": "issuepilot-api", "version": "0.1.0"}


@app.get("/issues", tags=["issues"])
def list_issues(
    repo: str | None = Query(default=None, description="Filter by full repository name, e.g. fastapi/fastapi"),
    state: str | None = Query(default=None, pattern="^(open|closed)$"),
    label: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Issue)
    if repo:
        stmt = stmt.where(Issue.repo_full_name == repo)
    if state:
        stmt = stmt.where(Issue.state == state)
    if label:
        # Labels are stored as JSON. This portable starter filters after fetching a bounded result set.
        # We'll replace this with database-specific JSON querying if needed.
        pass

    rows = db.scalars(stmt.order_by(Issue.updated_at.desc()).offset(offset).limit(limit)).all()
    if label:
        rows = [row for row in rows if label.lower() in [str(x).lower() for x in (row.labels or [])]]

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
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
    }


@app.get("/metrics/summary", tags=["analytics"])
def metrics_summary(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Issue)) or 0
    open_count = db.scalar(select(func.count()).select_from(Issue).where(Issue.state == "open")) or 0
    closed_count = db.scalar(select(func.count()).select_from(Issue).where(Issue.state == "closed")) or 0
    return {
        "total_issues": total,
        "open_issues": open_count,
        "closed_issues": closed_count,
    }
