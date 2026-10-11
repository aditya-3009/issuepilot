import argparse
from datetime import datetime, timezone
from sqlalchemy import select
from .db import Base, SessionLocal, engine
from .github_client import fetch_issues
from .models import Issue


def parse_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Store naive UTC for portability across SQLite and PostgreSQL in this starter.
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


def upsert_issues(owner: str, repo: str, items: list[dict]) -> tuple[int, int]:
    Base.metadata.create_all(engine)
    inserted = updated = 0
    with SessionLocal() as session:
        for item in items:
            labels = [label.get("name", "") for label in item.get("labels", [])]
            values = {
                "repo_full_name": f"{owner}/{repo}",
                "number": item["number"],
                "title": item.get("title") or "(untitled)",
                "body": item.get("body"),
                "state": item.get("state", "unknown"),
                "html_url": item.get("html_url", ""),
                "author_login": (item.get("user") or {}).get("login"),
                "labels": labels,
                "comments_count": item.get("comments", 0),
                "created_at": parse_datetime(item.get("created_at")),
                "updated_at": parse_datetime(item.get("updated_at")),
            }
            existing = session.scalar(select(Issue).where(Issue.github_id == item["id"]))
            if existing is None:
                session.add(Issue(github_id=item["id"], **values))
                inserted += 1
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
                updated += 1
        session.commit()
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description="Ingest public GitHub issues into IssuePilot.")
    parser.add_argument("--owner", default="fastapi")
    parser.add_argument("--repo", default="fastapi")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=50)
    args = parser.parse_args()

    items = fetch_issues(args.owner, args.repo, pages=args.pages, per_page=args.per_page)
    inserted, updated = upsert_issues(args.owner, args.repo, items)
    print(
        f"Repository: {args.owner}/{args.repo}\n"
        f"Fetched: {len(items)} real issues (pull requests excluded)\n"
        f"Inserted: {inserted}\nUpdated: {updated}"
    )


if __name__ == "__main__":
    main()
