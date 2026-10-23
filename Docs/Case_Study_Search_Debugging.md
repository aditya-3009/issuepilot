## Debugging Case Study: API Search Returned Zero Results

**Date:** 14 October 2026  
**Component:** FastAPI `/issues` endpoint  
**Technologies:** Python, FastAPI, SQLAlchemy, SQLite, Swagger UI

### 1. Problem Statement

After implementing a search parameter for the `/issues` endpoint, searches returned an HTTP `200 OK` response but contained no matching records:

```json
{
  "count": 0,
  "items": []
}
```

Initially, searches for `update` and `error` both returned empty results. This raised an important question: was the search implementation broken, or was the database missing issues containing those terms?

The HTTP status code alone could not answer that question.

### 2. Investigation Process

Instead of immediately changing the search implementation, we tested the endpoint in stages.

#### Step 1: Test common search terms

The following search terms were tried through Swagger UI:

| Search term | Result | Initial interpretation |
|---|---|---|
| `update` | Zero results | No matching issue was found |
| `error` | Zero results | No matching issue was found |

At this stage, we did not have enough evidence to conclude that the search functionality was broken. A search can execute successfully and still return no matches.

#### Step 2: Remove the search filter

We cleared the search parameter and executed `GET /issues` with:

- `limit = 20`
- `offset = 0`
- No repository, state, label, or search filters

This request returned one issue, confirming that the API could retrieve stored data.

The returned record was:

- **Repository:** `fastapi/fastapi`
- **Issue number:** `16451`
- **Title:** `Docs: note that native OpenTelemetry works on AWS Lambda (Mangum)`
- **State:** `closed`
- **Author:** `igormcsouza`

This was the key diagnostic step. It showed that the database was not completely empty and that the endpoint could return an existing issue.

#### Step 3: Choose a search term from actual data

Rather than guessing more keywords, we selected `OpenTelemetry`, a term visibly present in the returned issue's title and description.

We executed:

`GET /issues?search=OpenTelemetry&limit=20&offset=0`

The response was:

```json
{
  "count": 1,
  "items": [
    {
      "repo": "fastapi/fastapi",
      "number": 16451,
      "title": "Docs: note that native OpenTelemetry works on AWS Lambda (Mangum)",
      "state": "closed"
    }
  ]
}
```

The actual response also contained additional issue fields, including the body, URL, author, labels, comment count, and update timestamp.

The search returned the expected issue.

### 3. Root Cause

The evidence showed that the initial zero-result responses were consistent with the contents of the local database.

At the time of testing, the endpoint returned only one stored issue. The terms `update` and `error` did not match that issue's title or description, whereas `OpenTelemetry` did.

Therefore, the initial zero-result responses did **not** establish that the search code was defective. The dataset was too small to make common search terms useful test cases.

This distinction matters:

- **No matching records:** The query executes, but no stored records satisfy the search condition.
- **Broken search implementation:** The query fails to apply the intended search condition or behaves incorrectly when matching data exists.
- **Empty database:** The endpoint has no stored records to return, even without filters.

Our investigation ruled out a completely empty database and demonstrated a successful search against a known matching record.

### 4. Implementation Used for Search

The `/issues` endpoint accepts an optional `search` query parameter. The search condition is applied to the issue title and description before pagination.

The relevant SQLAlchemy implementation is:

```python
if search:
    term = f"%{search.strip()}%"
    stmt = stmt.where(
        or_(
            Issue.title.ilike(term),
            Issue.body.ilike(term),
        )
    )
```

The required imports are:

```python
from sqlalchemy import func, or_, select
```

How it works:

1. `search.strip()` removes leading and trailing whitespace from the search term.
2. The `%` characters are SQL `LIKE` wildcards. They allow the term to appear anywhere within the field.
3. `Issue.title.ilike(term)` checks the title using a case-insensitive pattern match on supported database dialects.
4. `Issue.body.ilike(term)` performs the corresponding check against the issue description.
5. `or_(...)` means a record qualifies if either its title or its description matches.
6. `stmt.where(...)` adds the condition to the SQLAlchemy query. Repository and state filters can be applied to the same query.

For example, `search=OpenTelemetry` can match a title containing `OpenTelemetry`, even if the complete title contains many other words.

### 5. A Coding Error Encountered During Implementation

While adding the search condition, an indentation error occurred:

```text
IndentationError: expected an indented block after 'if' statement
```

The cause was that the statements intended to run inside `if search:` were not indented beneath it.

The problem was resolved by replacing the entire `main.py` file with a consistently formatted version rather than trying to patch individual lines.

This reinforced two practical lessons:

- Python indentation is part of the program's syntax, not merely a formatting preference.
- After modifying an endpoint, run the automated test suite to catch syntax errors before testing the API manually.

### 6. Verification Results

| Check | Observed result | Conclusion |
|---|---|---|
| Search for `update` | `200 OK`, zero matches | No matching stored record was returned |
| Search for `error` | `200 OK`, zero matches | No matching stored record was returned |
| List issues without search | `200 OK`, one issue | The API could retrieve stored data |
| Search for `OpenTelemetry` | `200 OK`, one match | Search worked for a known matching record |

These were manual tests performed through Swagger UI. They verified the observed API behavior against the available local data. They did not, by themselves, establish correctness across a large dataset or replace automated regression tests.

### 7. Lessons Learned

**Lesson 1: Debug with evidence, not assumptions.**

A zero-result response is not automatically a software bug. Inspect the underlying data before changing the query.

**Lesson 2: Separate API success from business results.**

HTTP `200 OK` means the request was processed successfully. It does not mean that the search found any records.

**Lesson 3: Use known-positive test cases.**

A reliable manual search test uses a keyword already known to exist in a stored record. This makes the expected result clear.

**Lesson 4: Understand dataset limitations.**

A database containing only one issue is sufficient for a basic smoke test, but not for meaningful evaluation of search behavior across different issue titles, descriptions, repositories, states, and labels.

**Lesson 5: Combine manual and automated testing.**

Swagger UI helps inspect real responses. Automated tests make the behavior repeatable and help prevent regressions when the implementation changes.

### 8. Future Improvements

- Ingest more issues from public GitHub repositories to test search against a broader dataset.
- Add automated tests using an isolated test database and known issue records.
- Test title matches, description-only matches, case variations, no-match searches, and searches combined with repository or state filters.
- Test how the endpoint handles empty or whitespace-only search values.
- Review label filtering and pagination together to ensure the endpoint returns predictable results.
- Track the number of ingested records and expose useful ingestion statistics so an empty or undersized dataset is easier to diagnose.

### Interview Explanation

During manual API testing, searches for `update` and `error` returned empty results. Rather than assuming the query was defective, I removed the search filter and confirmed that the endpoint returned a stored FastAPI issue. I then searched for `OpenTelemetry`, a keyword present in that issue's title and description, and received the expected result. This demonstrated the importance of distinguishing a query that returns no matches from a query that is incorrectly implemented. I also corrected an indentation error encountered during implementation and used Swagger UI to validate the endpoint against real stored data.
