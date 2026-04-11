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

    assert result["positive_k"] == 2
    assert result["positive_confidence"] in {"high", "medium"}
    assert result["negative_k"] == 2
    assert result["negative_confidence"] in {"high", "medium"}
    assert result["details"]["used_fallback"] is False


def test_recommend_topic_count_falls_back_when_groups_are_too_small():
    positive = _make_cluster(0.0, 0.0, 10, 5)
    negative = _make_cluster(4.0, 4.0, 8, 6)

    result = recommend_topic_count(positive, negative)

    assert result["positive_k"] >= 2
    assert result["negative_k"] >= 2
    assert result["positive_confidence"] == "low"
    assert result["negative_confidence"] == "low"
    assert result["details"]["used_fallback"] is True


def test_recommend_topic_count_returns_separate_k_per_group():
    """positive and negative groups should get independent k values."""
    positive = np.vstack([
        _make_cluster(0.0, 0.0, 30, 10),
        _make_cluster(5.0, 5.0, 30, 11),
    ])
    negative = np.vstack([
        _make_cluster(0.0, 0.0, 25, 12),
        _make_cluster(5.0, 0.0, 25, 13),
        _make_cluster(2.5, 5.0, 25, 14),
    ])

    result = recommend_topic_count(positive, negative)

    assert "positive_k" in result
    assert "negative_k" in result
    assert "positive_confidence" in result
    assert "negative_confidence" in result
    assert result["positive_k"] >= 2
    assert result["negative_k"] >= 2
    assert result["details"]["used_fallback"] is False
    assert "effective_k" not in result
    assert "confidence" not in result


def test_recommend_topic_count_uses_fallback_on_low_separation():
    """When silhouette scores are all below threshold, use fallback."""
    rng = np.random.default_rng(42)
    positive = rng.normal(0, 1, size=(60, 2))
    negative = rng.normal(0, 1, size=(60, 2))

    result = recommend_topic_count(positive, negative)

    assert "positive_k" in result
    assert "negative_k" in result
    assert result["positive_confidence"] in {"low", "medium"}
    assert result["negative_confidence"] in {"low", "medium"}


def test_recommend_topic_count_fallback_when_one_group_too_small():
    """When one group is too small, that group gets fallback k."""
    positive = np.vstack([
        _make_cluster(0.0, 0.0, 30, 20),
        _make_cluster(5.0, 5.0, 30, 21),
    ])
    negative = _make_cluster(0.0, 0.0, 5, 22)

    result = recommend_topic_count(positive, negative)

    assert result["positive_k"] >= 2
    assert result["negative_k"] >= 2
    assert result["negative_confidence"] == "low"
    assert result["details"]["used_fallback"] is True
    assert result["details"]["negative_used_fallback"] is True
