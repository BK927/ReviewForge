import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd() / "python"))

import analyzer


def _make_reviews(positive_count: int, negative_count: int) -> list[dict]:
    reviews = []
    for index in range(positive_count):
        reviews.append({"text": f"positive review {index}", "voted_up": True})
    for index in range(negative_count):
        reviews.append({"text": f"negative review {index}", "voted_up": False})
    return reviews


def _install_common_mocks(monkeypatch, progress_calls, cluster_calls):
    def fake_format_progress(msg_id, percent, message, stage=None, elapsed_ms=None):
        progress_calls.append((percent, message, stage))
        return f"{stage}:{message}"

    def fake_cluster_reviews(vectors, method="kmeans", n_clusters=8, min_cluster_size=5, random_state=42):
        cluster_calls.append({
            "method": method,
            "n_clusters": n_clusters,
            "min_cluster_size": min_cluster_size,
            "random_state": random_state,
            "size": len(vectors),
        })
        return [0] * len(vectors)

    monkeypatch.setattr(analyzer, "format_progress", fake_format_progress)
    monkeypatch.setattr(analyzer, "cluster_reviews", fake_cluster_reviews)
    monkeypatch.setattr(
        analyzer,
        "extract_topic_keywords",
        lambda texts, labels, tier=0, embeddings=None: {0: [("topic", 0.95)]} if texts else {},
    )


def test_run_analysis_uses_recommendation_for_tier0_auto(monkeypatch):
    reviews = _make_reviews(3, 3)
    embeddings = np.array([
        [0.0, 0.0],
        [0.1, 0.1],
        [0.2, 0.2],
        [5.0, 5.0],
        [5.1, 5.1],
        [5.2, 5.2],
    ])
    progress_calls = []
    cluster_calls = []

    _install_common_mocks(monkeypatch, progress_calls, cluster_calls)
    monkeypatch.setattr(
        analyzer,
        "generate_embeddings",
        lambda params, msg_id: {"embeddings": embeddings.tolist(), "model": "test-model"},
    )
    monkeypatch.setattr(
        analyzer,
        "recommend_topic_count",
        lambda positive_embeddings, negative_embeddings: {
            "effective_k": 3,
            "confidence": "high",
                "reason": "Best balance of separation and stability across tested k values",
                "details": {
                    "tested_candidates": [2, 3, 4],
                    "per_group_sample_counts": {"positive": 3, "negative": 3},
                    "winning_summary": {"k": 3, "score": 0.71},
                    "used_fallback": False,
                },
            },
    )

    result = analyzer.run_analysis(
        {"reviews": reviews, "config": {"tier": 0, "topicCountMode": "auto", "n_topics": 8}},
        "msg-1",
    )

    assert result["topic_count_mode"] == "auto"
    assert result["requested_k"] is None
    assert result["effective_k"] == 3
    assert result["recommendation_confidence"] == "high"
    assert result["recommendation_reason"] == "Best balance of separation and stability across tested k values"
    assert result["recommendation_details"]["used_fallback"] is False
    assert [call["n_clusters"] for call in cluster_calls] == [3, 3]
    assert all(call["method"] == "kmeans" for call in cluster_calls)
    assert [stage for _, _, stage in progress_calls] == [
        "embedding",
        "recommendation",
        "clustering",
        "keywords",
        "complete",
    ]


def test_run_analysis_uses_requested_k_for_tier0_manual(monkeypatch):
    reviews = _make_reviews(5, 5)
    embeddings = np.array([[float(index), float(index)] for index in range(10)])
    progress_calls = []
    cluster_calls = []

    _install_common_mocks(monkeypatch, progress_calls, cluster_calls)
    monkeypatch.setattr(
        analyzer,
        "generate_embeddings",
        lambda params, msg_id: {"embeddings": embeddings.tolist(), "model": "test-model"},
    )

    def fail_recommendation(*args, **kwargs):
        raise AssertionError("recommend_topic_count should not run for manual Tier 0")

    monkeypatch.setattr(analyzer, "recommend_topic_count", fail_recommendation)

    result = analyzer.run_analysis(
        {"reviews": reviews, "config": {"tier": 0, "topicCountMode": "manual", "n_topics": 5}},
        "msg-2",
    )

    assert result["topic_count_mode"] == "manual"
    assert result["requested_k"] == 5
    assert result["effective_k"] == 5
    assert result["recommendation_confidence"] is None
    assert result["recommendation_reason"] == "Using requested topic count"
    assert [call["n_clusters"] for call in cluster_calls] == [5, 5]
    assert [stage for _, _, stage in progress_calls] == [
        "embedding",
        "clustering",
        "keywords",
        "complete",
    ]


def test_run_analysis_skips_recommendation_for_tier1(monkeypatch):
    reviews = _make_reviews(2, 2)
    embeddings = np.array([
        [0.0, 0.0],
        [0.1, 0.1],
        [5.0, 5.0],
        [5.1, 5.1],
    ])
    progress_calls = []
    cluster_calls = []

    _install_common_mocks(monkeypatch, progress_calls, cluster_calls)
    monkeypatch.setattr(
        analyzer,
        "generate_embeddings",
        lambda params, msg_id: {"embeddings": embeddings.tolist(), "model": "tier1-model"},
    )

    def fail_recommendation(*args, **kwargs):
        raise AssertionError("recommend_topic_count should not run for Tier 1")

    monkeypatch.setattr(analyzer, "recommend_topic_count", fail_recommendation)

    result = analyzer.run_analysis(
        {"reviews": reviews, "config": {"tier": 1, "topicCountMode": "manual", "n_topics": 6}},
        "msg-3",
    )

    assert result["topic_count_mode"] == "auto"
    assert result["requested_k"] is None
    assert result["effective_k"] is None
    assert result["recommendation_confidence"] is None
    assert result["recommendation_reason"] == "Auto by HDBSCAN"
    assert all(call["method"] == "hdbscan" for call in cluster_calls)
    assert [stage for _, _, stage in progress_calls] == [
        "embedding",
        "clustering",
        "keywords",
        "complete",
    ]
