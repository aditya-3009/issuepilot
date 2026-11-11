"""Evaluation metrics for ranked issue-retrieval results.

The functions in this module are deliberately model-agnostic. They can be
used to evaluate FAISS results, another retriever, or a manually supplied
ranking without loading an embedding model.
"""

from collections.abc import Iterable, Sequence
from typing import TypeVar

T = TypeVar("T")


def _validate_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer.")


def _relevant_set(relevant: Iterable[T]) -> set[T]:
    relevant_set = set(relevant)
    if not relevant_set:
        raise ValueError("relevant must contain at least one item.")
    return relevant_set


def precision_at_k(retrieved: Sequence[T], relevant: Iterable[T], k: int) -> float:
    """Return the fraction of the first k ranked results that are relevant."""
    _validate_k(k)
    relevant_items = _relevant_set(relevant)
    hits = sum(item in relevant_items for item in retrieved[:k])
    return hits / k


def recall_at_k(retrieved: Sequence[T], relevant: Iterable[T], k: int) -> float:
    """Return the fraction of known relevant items found in the first k results."""
    _validate_k(k)
    relevant_items = _relevant_set(relevant)
    hits = len(set(retrieved[:k]) & relevant_items)
    return hits / len(relevant_items)


def mean_reciprocal_rank(rankings: Sequence[Sequence[T]], relevant: Sequence[Iterable[T]]) -> float:
    """Calculate MRR across queries with one or more relevant items each."""
    if len(rankings) != len(relevant):
        raise ValueError("rankings and relevant must have the same length.")
    if not rankings:
        raise ValueError("At least one query ranking is required.")

    reciprocal_ranks = []
    for ranking, relevant_items in zip(rankings, relevant):
        relevant_set = _relevant_set(relevant_items)
        first_relevant_rank = next(
            (rank for rank, item in enumerate(ranking, start=1) if item in relevant_set),
            None,
        )
        reciprocal_ranks.append(
            0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank
        )

    return sum(reciprocal_ranks) / len(reciprocal_ranks)
