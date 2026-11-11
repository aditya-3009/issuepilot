# IssuePilot

**Developer-operations intelligence for GitHub issues.**

IssuePilot ingests public GitHub issues, stores normalized records in a relational database, and exposes keyword search, analytics, and semantic retrieval through a REST API.

[![Tests](https://github.com/aditya-3009/issuepilot/actions/workflows/tests.yml/badge.svg)](https://github.com/aditya-3009/issuepilot/actions/workflows/tests.yml)

## What it does

- Ingests public GitHub issues through the GitHub REST API.
- Handles pagination, network failures, API errors, and pull-request exclusion.
- Normalizes issue metadata and performs idempotent database upserts.
- Stores records with SQLAlchemy using SQLite by default, with PostgreSQL configurable through `DATABASE_URL`.
- Exposes FastAPI endpoints for health checks, issue listing, filtering, summary metrics, and semantic search.
- Creates embeddings with Sentence Transformers (`all-MiniLM-L6-v2`).
- Uses normalized embeddings and FAISS inner-product search to rank semantically related issues.
- Includes model-agnostic Precision@k, Recall@k, and Mean Reciprocal Rank (MRR) metrics for retrieval evaluation.
- Uses automated tests and GitHub Actions CI.

## Architecture

```text
GitHub Issues REST API
        |
        v
GitHub client (pagination, HTTP errors, rate limits)
        |
        v
Ingestion and normalization
        |
        v
SQLAlchemy database (SQLite / PostgreSQL)
        |
        +------------------------------+
        |                              |
        v                              v
FastAPI issue and metrics API     Issue text construction
                                       |
                                       v
                              Sentence Transformers
                                       |
                                       v
                                  FAISS index
                                       |
                                       v
                              Semantic retrieval API
                                       |
                                       v
                          Ranked issues + source URLs
```

## Tech stack

| Area | Technologies |
|---|---|
| Language | Python 3.10+ |
| API | FastAPI, Uvicorn |
| Data access | SQLAlchemy |
| Databases | SQLite, PostgreSQL |
| External integration | GitHub REST API, Requests |
| Embeddings | Sentence Transformers |
| Vector search | FAISS, NumPy |
| Testing | Pytest, FastAPI TestClient |
| CI | GitHub Actions |

## Setup

Create and activate a virtual environment from the repository root.

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux / WSL

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you want to configure a database URL or GitHub token. A token is optional for small-scale public-repository ingestion. Never commit real credentials.

## Ingest GitHub issues

Start with a small sample:

```bash
python -m issuepilot.ingest --owner fastapi --repo fastapi --pages 1 --per-page 50
```

Ingest another repository:

```bash
python -m issuepilot.ingest --owner pallets --repo flask --pages 3 --per-page 100
```

The GitHub Issues API can return pull requests as well as issues. IssuePilot excludes pull requests from the stored issue records.

## Run the API

```bash
python -m uvicorn issuepilot.main:app --reload
```

- Interactive API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health |
| `GET` | `/issues` | List, search, filter, and paginate stored issues |
| `GET` | `/issues/semantic-search?q=API%20validation&top_k=5` | Semantic retrieval |
| `GET` | `/metrics/summary` | Total, open, and closed issue counts |

### Issue filters

The `GET /issues` endpoint supports:

- `search`: case-insensitive search across issue titles and descriptions.
- `repo`: filter by full repository name, e.g. `fastapi/fastapi`.
- `state`: `open` or `closed`.
- `label`: case-insensitive label filter.
- `limit`: page size from 1 to 100.
- `offset`: number of records to skip.

### Semantic retrieval

Example:

```text
GET /issues/semantic-search?q=API%20returns%20an%20incorrect%20validation%20error&top_k=5
```

The response contains ranked issue metadata, similarity scores, and GitHub source URLs. Similarity scores are ranking signals, not calibrated probabilities.

The embedding model and FAISS index are cached in process memory. The index is a snapshot of the database when first built; restart the API process after ingesting new issues to rebuild the snapshot.

## Retrieval evaluation

The module `issuepilot/evaluation.py` provides:

- `precision_at_k(retrieved, relevant, k)`
- `recall_at_k(retrieved, relevant, k)`
- `mean_reciprocal_rank(rankings, relevant)`

These functions are independent of the embedding model and can compare different retrieval approaches using a fixed, human-labelled query set.

See [Retrieval Evaluation](docs/RETRIEVAL_EVALUATION.md) for definitions, examples, and a recommended evaluation protocol.

**Evaluation status:** metric implementations and unit tests are included. A representative human-labelled benchmark has not yet been assembled, so this repository does not claim a measured retrieval-quality score.

## Run tests

```bash
python -m pytest -q
```

GitHub Actions runs the test suite on pushes and pull requests targeting `main`, using Python 3.10 and 3.11.

## Current scope and limitations

Implemented:
1. GitHub issue ingestion, normalization, pagination, and database upserts.
2. FastAPI endpoints for issue listing, filters, semantic retrieval, and summary metrics.
3. Sentence Transformer embeddings and FAISS similarity search.
4. Retrieval ranking metrics and unit tests.
5. Automated tests for API behavior, GitHub client handling, ingestion edge cases, and evaluation metrics.

Not implemented:
- LLM-generated answers or summaries.
- Agent-driven GitHub actions or automated issue modifications.
- Persistent vector-index storage or automatic index refresh.
- A production deployment or a human-labelled retrieval benchmark.

## Security

- Keep `.env` out of version control.
- Never commit GitHub tokens, database credentials, or private issue data.
- Semantic search is read-only. No GitHub write actions are performed.

## Future work

1. Build a human-labelled retrieval benchmark and report Precision@k, Recall@k, and MRR.
2. Add index refresh and persistence strategies.
3. Add evidence-grounded issue summaries with source references.
4. Add structured logging, database migrations, and deployment automation.
5. Consider controlled workflows only after defining approval, audit, and failure-handling requirements.
