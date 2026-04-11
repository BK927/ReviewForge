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
    monkeypatch.setattr(analyzer, "is_short_review", lambda text, language="english", min_words=5: False)
    monkeypatch.setattr(analyzer, "build_short_review_summary", lambda reviews: {"count": 0, "positive_rate": 0.0, "frequent_phrases": []})
    monkeypatch.setattr(analyzer, "merge_similar_topics", lambda emb, labels, threshold=0.80: (labels, {"original_topic_count": len(set(labels)), "merged_topic_count": len(set(labels)), "merges": []}))


def test_run_analysis_uses_recommendation_for_tier0_auto(monkeypatch):
    # 3 positive + 5 negative so negative_k=4 doesn't get capped by min()
    reviews = _make_reviews(3, 5)
    embeddings = np.array([
        [0.0, 0.0],
        [0.1, 0.1],
        [0.2, 0.2],
        [5.0, 5.0],
        [5.1, 5.1],
        [5.2, 5.2],
        [5.3, 5.3],
        [5.4, 5.4],
    ])
    progress_calls = []
    cluster_calls = []

    _install_common_mocks(monkeypatch, progress_calls, cluster_calls)
    monkeypatch.setattr(
        analyzer,
        "generate_embeddings",
        lambda params, msg_id: {"embeddings": embeddings[:len(params["texts"])].tolist(), "model": "test-model"},
    )
    monkeypatch.setattr(
        analyzer,
        "recommend_topic_count",
        lambda positive_embeddings, negative_embeddings: {
            "positive_k": 3,
            "negative_k": 4,
            "positive_confidence": "high",
            "negative_confidence": "medium",
            "positive_reason": "Best balance of separation and stability across tested k values",
            "negative_reason": "Best balance of separation and stability across tested k values",
            "details": {
                "tested_candidates": [2, 3, 4],
                "per_group_sample_counts": {"positive": 3, "negative": 3},
                "winning_summary": {"k": 3, "score": 0.71},
                "positive_used_fallback": False,
                "negative_used_fallback": False,
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
    assert result["positive_k"] == 3
    assert result["negative_k"] == 4
    assert result["positive_confidence"] == "high"
    assert result["negative_confidence"] == "medium"
    assert result["positive_reason"] == "Best balance of separation and stability across tested k values"
    assert result["recommendation_details"]["used_fallback"] is False
    assert [call["n_clusters"] for call in cluster_calls] == [3, 4]
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
    assert result["positive_k"] == 5
    assert result["negative_k"] == 5
    assert result["positive_confidence"] is None
    assert result["positive_reason"] == "Using requested topic count"
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
    assert result["positive_k"] is None
    assert result["negative_k"] is None
    assert result["positive_confidence"] is None
    assert result["positive_reason"] == "Auto by HDBSCAN"
    assert all(call["method"] == "hdbscan" for call in cluster_calls)
    assert [stage for _, _, stage in progress_calls] == [
        "embedding",
        "clustering",
        "keywords",
        "complete",
    ]


def test_run_analysis_filters_short_reviews(monkeypatch):
    reviews = [
        {"text": "good", "voted_up": True, "language": "english"},
        {"text": "this game has an amazing combat system", "voted_up": True, "language": "english"},
        {"text": "bad", "voted_up": False, "language": "english"},
        {"text": "the controls are terrible and unresponsive", "voted_up": False, "language": "english"},
    ]
    embeddings = np.array([[0.0, 0.0], [0.1, 0.1], [5.0, 5.0], [5.1, 5.1]])
    progress_calls = []
    cluster_calls = []

    _install_common_mocks(monkeypatch, progress_calls, cluster_calls)
    monkeypatch.setattr(
        analyzer,
        "generate_embeddings",
        lambda params, msg_id: {
            "embeddings": embeddings[:len(params["texts"])].tolist(),
            "model": "test-model",
        },
    )
    monkeypatch.setattr(analyzer, "merge_similar_topics", lambda emb, labels, threshold=0.80: (labels, {"original_topic_count": 1, "merged_topic_count": 1, "merges": []}))

    # Override is_short_review to treat single-word texts as short
    monkeypatch.setattr(
        analyzer,
        "is_short_review",
        lambda text, language="english", min_words=5: len(text.split()) < min_words,
    )
    monkeypatch.setattr(
        analyzer,
        "build_short_review_summary",
        lambda reviews: {"count": len(reviews), "positive_rate": 0.0, "frequent_phrases": []},
    )

    result = analyzer.run_analysis(
        {"reviews": reviews, "config": {"tier": 0, "topicCountMode": "manual", "n_topics": 2, "min_review_words": 5}},
        "msg-4",
    )

    assert "short_review_summary" in result
    assert result["short_review_summary"]["count"] == 2  # "good" and "bad"
    assert result["total_reviews"] == 4
