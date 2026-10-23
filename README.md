
# IssuePilot

IssuePilot is a developer-operations intelligence project that ingests public GitHub issues, stores them in a relational database, and exposes them through a REST API. The current MVP establishes the data ingestion and API foundation for future retrieval-augmented generation (RAG), agent workflows, and human-approved actions.

## Current MVP

- Fetches issues from public GitHub repositories through the GitHub REST API.
- Handles pagination and filters out pull requests returned by the Issues API.
- Normalizes issue data and upserts records to avoid duplicate rows during repeated ingestion.
- Stores issues in SQLite by default, with PostgreSQL support through `DATABASE_URL`.
- Exposes health, issue listing, search, filtering, and summary endpoints through FastAPI.
- Includes automated tests for API behavior, GitHub client handling, and ingestion safeguards.
- Handles empty and whitespace-only search queries and trims unnecessary whitespace from search terms.

## Requirements

- Python 3.10+
- Internet access for GitHub ingestion.
- A GitHub token is optional for a small number of public API requests. A token can be configured for higher API rate limits.

## Setup (Windows PowerShell)

Run these commands from the project root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks virtual environment activation, use the Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Alternatively, select the project's `.venv` interpreter in VS Code.

## Ingest a Small Public Sample

Start with one page to keep the initial run small. This example ingests issues from `fastapi/fastapi`:

```powershell
python -m issuepilot.ingest --owner fastapi --repo fastapi --pages 1
```

The GitHub Issues API can return both issues and pull requests. IssuePilot filters out pull requests.

See the [GitHub Issues API documentation](https://docs.github.com/en/rest/issues/issues).

## Run the API

Start the development server:

```powershell
uvicorn issuepilot.main:app --reload
```

Open these endpoints in your browser:

- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- List and search issues: [http://127.0.0.1:8000/issues](http://127.0.0.1:8000/issues)
- Summary metrics: [http://127.0.0.1:8000/metrics/summary](http://127.0.0.1:8000/metrics/summary)

### Search, Filter, and Paginate Issues

The `GET /issues` endpoint supports the following query parameters:

| Parameter | Purpose | Example |
|---|---|---|
| `search` | Search issue titles and descriptions using a case-insensitive text match | `?search=OpenTelemetry` |
| `repo` | Filter by full repository name | `?repo=fastapi/fastapi` |
| `state` | Filter by issue state: `open` or `closed` | `?state=open` |
| `label` | Keep issues with the specified label | `?label=bug` |
| `limit` | Number of records requested, from 1 to 100; default is 20 | `?limit=10` |
| `offset` | Number of records to skip for pagination; default is 0 | `?offset=20` |

Parameters can be combined. For example:

```text
http://127.0.0.1:8000/issues?search=OpenTelemetry&state=closed&limit=10
```

Search uses SQL text matching. It does not currently use semantic search or embeddings.

**Known limitation:** Label filtering is applied after the database page is retrieved. Consequently, a response may contain fewer items than the requested `limit` when a label filter is used.

## Run Tests

Run the test suite from the project root with the active virtual environment:

```powershell
python -m pytest -q
```

The current test suite contains **16 tests** covering API behavior, GitHub client handling, and ingestion/upsert safeguards.

## Suggested Acceptance Checks

1. Ingest one page of issues from a public GitHub repository.
2. Confirm that the ingestion command reports fetched, inserted, and updated counts.
3. Start the API server and open `/docs`.
4. Verify that `/issues` returns structured JSON and test the `search`, `repo`, and `state` parameters.
5. Run `python -m pytest -q` and confirm that all tests pass.
6. Rerun ingestion and verify that existing GitHub issues are updated rather than duplicated.

## Architecture Roadmap

1. **Foundation (current MVP):** GitHub API → normalization → relational database → FastAPI.
2. **Retrieval (future):** Embeddings and semantic search for similar issues and documentation.
3. **LLM layer (future):** Structured issue summaries and classification supported by evidence.
4. **Agent workflow (future):** SQL analytics and retrieval tools orchestrated with LangGraph.
5. **Safety (future):** Human approval before any write action to GitHub.
6. **Evaluation (future):** A labeled test set, retrieval and classification metrics, API tests, and latency/cost measurements.

## Security and Honest Scope

- Never commit `.env` files or real API tokens.
- Do not enable write actions until review, approval, and audit logging are implemented.
- RAG, embeddings, LLM generation, and agent workflows are roadmap items, not part of the current MVP.
- Do not claim evaluation improvements until they have been measured.
