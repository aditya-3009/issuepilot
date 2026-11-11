# Retrieval Evaluation

IssuePilot now includes model-agnostic ranking metrics in
`issuepilot/evaluation.py`. These functions make it possible to compare
retrieval approaches using a small, human-labelled query set instead of
judging search quality from a few hand-picked examples.

## Metrics

- **Precision@k:** relevant results in the first `k`, divided by `k`.
- **Recall@k:** known relevant items found in the first `k`, divided by the
  total number of known relevant items.
- **Mean Reciprocal Rank (MRR):** average reciprocal rank of the first
  relevant result for each query.

The metric functions accept identifiers and rankings, not model objects.
For IssuePilot, use a stable identifier such as `(repo, issue_number)` so
results remain comparable if the local database primary keys change.

## Example

```python
from issuepilot.evaluation import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)

ranking = [
    ("fastapi/fastapi", 101),
    ("pallets/flask", 55),
    ("fastapi/fastapi", 204),
]
relevant = {
    ("fastapi/fastapi", 101),
    ("fastapi/fastapi", 204),
}

print(precision_at_k(ranking, relevant, k=3))
print(recall_at_k(ranking, relevant, k=3))
print(mean_reciprocal_rank([ranking], [relevant]))
```

## Evaluation protocol

1. Write representative natural-language queries from realistic developer
   support tasks.
2. Have a human identify all relevant issue identifiers for each query.
3. Keep the labelled query set fixed while comparing retrieval changes.
4. Record Precision@k, Recall@k, and MRR for each experiment.
5. Inspect failures, especially queries with no relevant result in the top k.
6. Do not tune and report on the same tiny query set as if it were an
   independent test set.

No retrieval-quality score is published by this repository yet. The metric
implementation is available; a sufficiently broad, human-labelled benchmark
still needs to be assembled before making quality claims.
