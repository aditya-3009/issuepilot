import pytest

from issuepilot.evaluation import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


def test_precision_at_k_counts_relevant_results_in_top_k():
    assert precision_at_k(["a", "x", "b", "c"], {"a", "b"}, 3) == pytest.approx(2 / 3)


def test_precision_at_k_uses_k_as_denominator_when_fewer_results_exist():
    assert precision_at_k(["a"], {"a", "b"}, 3) == pytest.approx(1 / 3)


def test_recall_at_k_measures_relevant_items_retrieved():
    assert recall_at_k(["x", "a", "b"], {"a", "b", "c"}, 3) == pytest.approx(2 / 3)


def test_recall_at_k_does_not_double_count_duplicate_results():
    assert recall_at_k(["a", "a", "x"], {"a", "b"}, 3) == pytest.approx(1 / 2)


def test_mrr_uses_first_relevant_rank_for_each_query():
    rankings = [["x", "a", "b"], ["c", "y"], ["z"]]
    relevant = [{"a", "b"}, {"c"}, {"a"}]
    assert mean_reciprocal_rank(rankings, relevant) == pytest.approx((1 / 2 + 1 + 0) / 3)


def test_mrr_rejects_mismatched_query_counts():
    with pytest.raises(ValueError, match="same length"):
        mean_reciprocal_rank([["a"]], [])


@pytest.mark.parametrize("k", [0, -1, 1.5, True])
def test_precision_rejects_invalid_k(k):
    with pytest.raises(ValueError, match="positive integer"):
        precision_at_k(["a"], {"a"}, k)


def test_recall_rejects_empty_relevance_set():
    with pytest.raises(ValueError, match="at least one item"):
        recall_at_k(["a"], set(), 1)
