# IssuePilot

IssuePilot is a developer-operations intelligence project that ingests public GitHub issues, stores them in a relational database, and exposes them through a REST API. It supports keyword-based search, semantic retrieval over issue content, and optional RAG answers grounded in retrieved issues.

The implementation retrieves relevant issues and can optionally generate evidence-grounded answers with an LLM. It does not execute agent-driven write actions.

## Features

- Fetches issues from public GitHub repositories using the GitHub REST API.
- Supports pagination and excludes pull requests returned by the Issues API.
- Normalizes issue data and upserts records to prevent duplicates during repeated ingestion.
- Stores data in SQLite by default, with PostgreSQL support through `DATABASE_URL`.
- Exposes FastAPI endpoints for health checks, issue listing/search/filtering, summary metrics, semantic search, and RAG question answering.
- Uses Sentence Transformers (`sentence-transformers/all-MiniLM-L6-v2`) to create 384-dimensional embeddings.
- Uses FAISS inner-product search over normalized embeddings to rank semantically similar issues.
- Supports optional LLM answer generation through an OpenAI-compatible chat-completions API.
- Returns source issue metadata and GitHub URLs alongside generated answers.
- Caches the embedding model and in-memory FAISS index within a running process.
- Includes automated tests for API behavior, GitHub client handling, ingestion safeguards, and semantic-search endpoint behavior.

## Architecture

```text
GitHub REST API
      |
      v
Issue ingestion and normalization
      |
      v
SQLAlchemy database (SQLite by default / PostgreSQL configurable)
      |
      v
Issue text construction
      |
      v
Sentence Transformers embeddings
      |
      v
FAISS vector similarity search
      |
      v
FastAPI semantic-search endpoint
      |
      v
Ranked issue metadata, similarity scores, and GitHub source URLs
```

## Requirements

- Python 3.10 or newer.
- Internet access to ingest public GitHub issues and download the embedding model on first use.
- A GitHub token is optional for a small number of public API requests. A token can be configured for higher API rate limits.

## Setup (Windows PowerShell)

Run these commands from the project root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, use the environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Alternatively, select the project's `.venv` interpreter in VS Code. Ensure that `requirements.txt` includes the project's runtime and RAG dependencies before installing.

## Ingest Issues

Start with a small public sample from `fastapi/fastapi`:

```powershell
python -m issuepilot.ingest --owner fastapi --repo fastapi --pages 1 --per-page 50
```

You can ingest another repository too:

```powershell
python -m issuepilot.ingest --owner pallets --repo flask --pages 3 --per-page 100
```

GitHub's Issues API can return pull requests as well as issues. IssuePilot filters pull requests out. The number returned may be lower than the requested page size.

Documentation: [GitHub Issues API](https://docs.github.com/en/rest/issues/issues).

## Run the API

Start the development server from the project root:

```powershell
python -m uvicorn issuepilot.main:app --reload
```

Open the interactive documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Available endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/issues` | List, keyword-search, filter, and paginate issues |
| `GET` | `/issues/semantic-search?q=API%20validation%20errors&top_k=5` | Retrieve issues ranked by semantic similarity |
| `POST` | `/issues/ask` | Generate an answer grounded in retrieved issues, with source links |
| `GET` | `/metrics/summary` | Counts of total, open, and closed issues |

### Keyword search, filtering, and pagination

The `GET /issues` endpoint supports these query parameters:

| Parameter | Purpose | Example |
|---|---|---|
| `search` | Case-insensitive text match in issue titles and descriptions | `?search=OpenTelemetry` |
| `repo` | Filter by full repository name | `?repo=fastapi/fastapi` |
| `state` | Filter by issue state: `open` or `closed` | `?state=open` |
| `label` | Keep issues with the specified label | `?label=bug` |
| `limit` | Page size from 1 to 100; default 20 | `?limit=10` |
| `offset` | Number of records to skip; default 0 | `?offset=20` |

Example:

```text
http://127.0.0.1:8000/issues?search=OpenTelemetry&state=closed&limit=10
```

Keyword search uses SQL text matching; it is separate from semantic retrieval.

**Known limitation:** label filtering is currently applied after the database page is retrieved. A page may therefore contain fewer items than the requested `limit` when a label filter is used.

### Semantic search

Use natural language to find conceptually related issues, even when the query does not use the same wording as an issue title.

Example request:

```text
GET /issues/semantic-search?q=API%20returns%20an%20incorrect%20validation%20error&top_k=5
```

Example PowerShell command:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/issues/semantic-search?q=API%20validation%20errors&top_k=5"
```

The JSON response includes the query, result count, and ranked issue records with repository, issue number, title, state, source URL, and similarity score. Scores are ranking signals, not probabilities that a result is correct.

The first semantic search in a server process may take longer while the embedding model and FAISS index are loaded/built. They are cached for subsequent searches in that process.

**Refreshing the index:** the current index is an in-memory snapshot. If new issues are ingested while the API process is running, restart the process to clear the cache and build a new index. A persistent vector store and automatic index refresh are future improvements.

## Tests

Run the full test suite from the project root with the virtual environment activated:

```powershell
python -m pytest -q
```

Tests cover API behavior, GitHub client handling, ingestion/upsert behavior, semantic search, and the LLM provider adapter. Run the suite locally before relying on a test count. Endpoint tests mock the retrieval function, so they do not need to download the model or contact GitHub. Manual semantic retrieval has also been checked against the local sample dataset.

## Current scope and next steps

Implemented:
1. GitHub issue ingestion, normalization, and relational storage.
2. FastAPI endpoints for issue access and summary metrics.
3. Sentence Transformer embeddings and FAISS semantic retrieval.
4. Optional LLM answer generation with source issue links.
5. Automated endpoint, ingestion, and provider-adapter tests.

Potential next steps:
1. Add retrieval-level evaluation with a labeled query set and metrics such as Recall@k or MRR.
2. Refresh the vector index automatically after ingestion and consider persistent index storage.
3. Add retrieval and answer-quality evaluation with a labeled benchmark.
4. Explore tool-using workflows or LangGraph only after defining a clear use case.
5. Add human approval, audit logging, and safeguards before any GitHub write actions.

## Security and honest scope

- Never commit `.env` files or API tokens.
- LLM answer generation is optional and requires a configured OpenAI-compatible provider.
- Agent workflows and GitHub write actions are not implemented.
- Do not claim retrieval or classification improvements until they have been measured with a defined evaluation set.


## RAG question answering

IssuePilot can answer engineering questions using the indexed GitHub issues as evidence. The endpoint first retrieves the top-k semantically relevant issues, passes their descriptions to an LLM, and returns the answer with source links for inspection.

Configure an OpenAI-compatible provider in your local `.env` file:

```dotenv
LLM_API_KEY=your-provider-api-key
LLM_MODEL=your-chat-model
LLM_BASE_URL=https://api.openai.com/v1
```

The provider must expose `POST /chat/completions`. Compatible hosted or local inference servers can be used by changing `LLM_BASE_URL`. No API key is required for the existing ingestion, search, or analytics endpoints.

Example PowerShell request:

```powershell
$body = @{
  question = "What recurring causes of validation errors are reported?"
  top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/issues/ask" -ContentType "application/json" -Body $body
```

The response contains `question`, `answer`, and `sources` (repository, issue number, title, URL, and retrieval similarity). If retrieval returns no results, the API returns an explicit no-evidence response without calling the LLM. If the provider is not configured, the endpoint returns HTTP 503; provider failures return HTTP 502.

Tests mock the provider, so they do not require a paid API key or make network requests.

**Limitations:** answer quality depends on retrieval quality and the configured model. Retrieved issue text is untrusted input; prompt instructions reduce instruction-following risk but are not a complete security boundary. No answer-quality benchmark has been run yet, so do not claim measured accuracy or quality improvements.
