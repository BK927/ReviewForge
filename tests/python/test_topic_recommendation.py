import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd() / "python"))

from topic_recommendation import recommend_topic_count


def _make_cluster(center_x: float, center_y: float, count: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = np.array([center_x, center_y], dtype=float)
    return base + rng.normal(0.0, 0.18, size=(count, 2))


def test_recommend_topic_count_prefers_stable_two_cluster_solution():
    positive = np.vstack([
        _make_cluster(0.0, 0.0, 25, 1),
        _make_cluster(4.5, 4.5, 25, 2),
    ])
    negative = np.vstack([
        _make_cluster(0.0, 4.5, 26, 3),
        _make_cluster(4.5, 0.0, 26, 4),
    ])

    result = recommend_topic_count(positive, negative)

    assert result["effective_k"] == 2
    assert result["confidence"] in {"high", "medium"}
    assert result["reason"] == "Best balance of separation and stability across tested k values"
    assert result["details"]["tested_candidates"] == [2, 3, 4]
    assert result["details"]["per_group_sample_counts"] == {"positive": 50, "negative": 52}
    assert result["details"]["used_fallback"] is False
    assert result["details"]["winning_summary"]["k"] == 2


def test_recommend_topic_count_falls_back_when_groups_are_too_small():
    positive = _make_cluster(0.0, 0.0, 10, 5)
    negative = _make_cluster(4.0, 4.0, 8, 6)

    result = recommend_topic_count(positive, negative)

    assert result["effective_k"] == 2
    assert result["confidence"] == "low"
    assert result["reason"] == "Insufficient stable signal; using conservative heuristic"
    assert result["details"]["tested_candidates"] == []
    assert result["details"]["per_group_sample_counts"] == {"positive": 0, "negative": 0}
    assert result["details"]["used_fallback"] is True
