# IssuePilot

IssuePilot is a developer-operations intelligence project that ingests public GitHub issues, stores them in a relational database, and exposes them through a small API. This version establishes the data and API foundation before adding retrieval-augmented generation (RAG), an agent workflow, and human-approved actions.

## Current MVP

- Fetches issues from a public GitHub repository through the GitHub REST API.
- Handles pagination and filters pull requests returned by the Issues endpoint.
- Normalizes issue data and upserts records to avoid duplicate rows during repeated ingestion.
- Stores issues in SQLite by default; can use PostgreSQL through `DATABASE_URL`.
- Exposes health, issue listing/search, and summary endpoints through FastAPI.
- Includes automated API, GitHub client, and ingestion tests.

## Requirements

- Python 3.10+
- Internet access for GitHub ingestion
- A GitHub token is optional for a small number of public API requests. A token can be added later for higher rate limits.

## Setup (Windows PowerShell)

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, you can run `.venv\Scripts\python.exe` directly or use the VS Code interpreter selector.

## Ingest a small public sample

Start with one page to keep the first run small. This example ingests issues from `fastapi/fastapi`:

```powershell
python -m issuepilot.ingest --owner fastapi --repo fastapi --pages 1
```

The GitHub Issues API can return pull requests as well as issues; this project filters pull requests out. See the [GitHub Issues API documentation](https://docs.github.com/en/rest/issues/issues).

## Run the API

```powershell
uvicorn issuepilot.main:app --reload
```

Open these endpoints in your browser:

- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs
- List and search issues: http://127.0.0.1:8000/issues
- Summary metrics: http://127.0.0.1:8000/metrics/summary

### Search, filter, and paginate issues

The `GET /issues` endpoint supports these query parameters:

| Parameter | Purpose | Example |
|---|---|---|
| `search` | Search issue titles and descriptions using a case-insensitive text match | `?search=OpenTelemetry` |
| `repo` | Filter by full repository name | `?repo=fastapi/fastapi` |
| `state` | Filter by issue state: `open` or `closed` | `?state=open` |
| `label` | Keep issues with the specified label | `?label=bug` |
| `limit` | Number of records requested, from 1 to 100 (default 20) | `?limit=10` |
| `offset` | Number of records to skip for pagination (default 0) | `?offset=20` |

Parameters can be combined, for example:

```text
http://127.0.0.1:8000/issues?search=OpenTelemetry&state=closed&limit=10
```

The search is SQL text matching, not semantic or embedding-based search. Label filtering is currently applied after the database page is retrieved, so a page can contain fewer results than the requested limit when a label filter is used.

## Run tests

Run pytest through the active Python interpreter from the project root:

```powershell
python -m pytest -q
```

The current test suite contains 14 tests covering API behavior, GitHub client handling, and ingestion/upsert safeguards.

## Suggested acceptance checks

1. Ingest one page of issues.
2. Confirm the ingestion command reports fetched, inserted, and updated counts.
3. Start the API and open `/docs`.
4. Verify `/issues` returns structured JSON and test the `search`, `repo`, and `state` parameters.
5. Run `python -m pytest -q`.
6. Rerun ingestion and verify that existing GitHub issues are updated rather than duplicated.

## Architecture roadmap

1. **Foundation (current MVP):** GitHub API → normalization → relational database → FastAPI.
2. **Retrieval (future):** embeddings and semantic search for similar issues and documentation.
3. **LLM layer (future):** structured issue summaries and classification with evidence.
4. **Agent workflow (future):** SQL analytics and retrieval tools orchestrated with LangGraph.
5. **Safety (future):** human approval before any write action to GitHub.
6. **Evaluation (future):** a labeled test set, retrieval and classification metrics, API tests, and latency/cost measurements.

## Security and honest scope

- Never commit `.env` or real tokens.
- Do not enable write actions until review/approval and audit logging exist.
- RAG, embeddings, LLM generation, and agent workflows are roadmap items, not part of the current MVP.
- Do not claim evaluation improvements until they have been measured.
