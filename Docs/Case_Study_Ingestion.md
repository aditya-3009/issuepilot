Case study: Why did duplicate GitHub issues crash ingestion?
Based on the bug we encountered in IssuePilot
The problem
When the same GitHub issue ID appeared twice in one batch, SQLAlchemy attempted to insert it twice. The database rejected the second insert because github_id has a unique constraint.
The underlying concept
Our session factory uses autoflush=False. Calling session.add(issue) puts the new object into the session, but it doesn't immediately write the row to the database. A subsequent database query may therefore fail to find that pending object.
The fix
We added a dictionary named seen_by_github_id that remembers issue objects already encountered in the current batch. If an ID appears again, we reuse the existing object and update its fields instead of scheduling another insert.
Why not just remove the unique constraint?
Because that would weaken database integrity. The constraint protects the database; our application logic must correctly handle duplicate inputs.
What you should be able to explain
- What does session.add() do?
- What is the difference between a pending object and a persisted database row?
- What does autoflush=False change?
- Why is a unique constraint still necessary?
- How does our regression test prove the fix works?