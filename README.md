# IssuePilot

IssuePilot is a developer-operations intelligence project that ingests public GitHub issues, stores them in a relational database, and exposes them through a small API. This starter version establishes the data and API foundation before adding retrieval-augmented generation (RAG), an agent workflow, and human-approved actions.

## Current MVP

- Fetches issues from a public GitHub repository through the GitHub REST API.
- Follows pagination and filters pull requests returned by the Issues endpoint.
- Stores issues in SQLite by default; can use PostgreSQL through `DATABASE_URL`.
- Exposes health, issue listing, and simple summary endpoints.
- Includes starter tests.

## Requirements

- Python 3.10+
- Internet access for GitHub ingestion
- No GitHub token is required for a small number of public API requests. A token can be added later for higher rate limits.

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

The default repository is `fastapi/fastapi`. Start with one page to keep the first run small:

```powershell
python -m issuepilot.ingest --owner fastapi --repo fastapi --pages 1
```

The GitHub Issues API can return pull requests as well as issues; this starter filters pull requests out. GitHub API docs: https://docs.github.com/en/rest/issues/issues

## Run the API

```powershell
uvicorn issuepilot.main:app --reload
```

Open:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/issues
- http://127.0.0.1:8000/metrics/summary

## Run tests

```powershell
pytest -q
```

## Suggested first acceptance checks

1. Ingest one page of issues.
2. Confirm the number inserted/updated is printed.
3. Start the API and open `/docs`.
4. Verify `/issues` returns structured JSON.
5. Run the test suite.
6. Inspect the database and confirm rerunning ingestion does not create duplicate rows.

## Architecture roadmap

1. **Foundation (this starter):** GitHub API → normalization → relational database → FastAPI.
2. **Retrieval:** keyword search and embeddings for similar issues and documentation.
3. **LLM layer:** structured issue summaries and classification with evidence.
4. **Agent workflow:** SQL analytics and retrieval tools orchestrated with LangGraph.
5. **Safety:** human approval before any write action to GitHub.
6. **Evaluation:** labeled test set, retrieval metrics, classification metrics, API tests, latency and cost measurements.

## Security and honesty

- Never commit `.env` or real tokens.
- Do not enable write actions until review/approval and audit logging exist.
- Do not claim evaluation improvements until you have measured them.
