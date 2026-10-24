
from functools import lru_cache
from threading import Lock

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .db import SessionLocal
from .models import Issue


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_index_lock = Lock()


def issue_to_text(issue: Issue) -> str:
    """Convert a GitHub issue into searchable text."""
    parts = [
        f"Repository: {issue.repo_full_name}",
        f"Title: {issue.title}",
        f"State: {issue.state}",
        f"Labels: {', '.join(issue.labels or [])}",
        f"Description: {issue.body or ''}",
    ]
    return "\n".join(parts)


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load and cache the embedding model once per process."""
    return SentenceTransformer(MODEL_NAME)


def build_index():
    """Build an in-memory FAISS index from stored GitHub issues."""
    with SessionLocal() as session:
        issues = session.query(Issue).order_by(Issue.id).all()

        if not issues:
            raise ValueError(
                "No issues found. Run the ingestion command first."
            )

        records = [
            {
                "id": issue.id,
                "repo": issue.repo_full_name,
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "url": issue.html_url,
                "text": issue_to_text(issue),
            }
            for issue in issues
        ]

    model = get_model()
    texts = [record["text"] for record in records]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return model, index, records


@lru_cache(maxsize=1)
def get_search_index():
    """Build and cache the index once per process."""
    return build_index()


def rebuild_search_index():
    """Rebuild the index after new issues have been ingested."""
    with _index_lock:
        get_search_index.cache_clear()
        return get_search_index()


def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """Return issues ranked by semantic similarity to a query."""
    query = query.strip()
    if not query:
        return []

    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20.")

    with _index_lock:
        model, index, records = get_search_index()

        query_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        k = min(top_k, len(records))
        scores, indices = index.search(query_embedding, k)

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue

        record = records[int(idx)].copy()
        record.pop("text")
        record["similarity"] = round(float(score), 4)
        results.append(record)

    return results
