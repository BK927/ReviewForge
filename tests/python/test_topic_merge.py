import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd() / "python"))

from topic_merge import compute_centroids, merge_similar_topics


def test_compute_centroids():
    embeddings = np.array([
        [1.0, 0.0],
        [1.0, 0.2],
        [0.0, 1.0],
        [0.2, 1.0],
        [0.1, 1.0],
    ])
    labels = [0, 0, 1, 1, 1]
    centroids = compute_centroids(embeddings, labels)
    assert set(centroids.keys()) == {0, 1}
    np.testing.assert_allclose(centroids[0], [1.0, 0.1], atol=0.01)
    np.testing.assert_allclose(centroids[1], [0.1, 1.0], atol=0.01)


def test_merge_similar_topics_merges_close_clusters():
    embeddings = np.array([
        [1.0, 0.0, 0.0],
        [0.98, 0.02, 0.0],
        [0.97, 0.03, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, 0.02, 0.98],
    ])
    labels = [0, 0, 1, 2, 2]

    new_labels, merge_info = merge_similar_topics(embeddings, labels, threshold=0.95)

    assert new_labels[0] == new_labels[1] == new_labels[2]
    assert new_labels[3] == new_labels[4]
    assert new_labels[0] != new_labels[3]
    assert merge_info["original_topic_count"] == 3
    assert merge_info["merged_topic_count"] == 2
    assert len(merge_info["merges"]) == 1


def test_merge_similar_topics_no_merge_when_distant():
    embeddings = np.array([
        [1.0, 0.0],
        [1.0, 0.1],
        [0.0, 1.0],
        [0.1, 1.0],
    ])
    labels = [0, 0, 1, 1]

    new_labels, merge_info = merge_similar_topics(embeddings, labels, threshold=0.95)

    assert len(set(new_labels)) == 2
    assert merge_info["original_topic_count"] == 2
    assert merge_info["merged_topic_count"] == 2
    assert merge_info["merges"] == []


def test_merge_similar_topics_single_pass_only():
    embeddings = np.array([
        [1.0, 0.0, 0.0],
        [0.97, 0.05, 0.0],
        [0.90, 0.10, 0.3],
    ])
    labels = [0, 1, 2]

    new_labels, merge_info = merge_similar_topics(embeddings, labels, threshold=0.95)

    assert merge_info["merged_topic_count"] <= merge_info["original_topic_count"]
    assert len(merge_info["merges"]) <= 1


def test_merge_preserves_label_contiguity():
    embeddings = np.array([
        [1.0, 0.0],
        [0.99, 0.01],
        [0.0, 1.0],
    ])
    labels = [0, 1, 2]

    new_labels, _ = merge_similar_topics(embeddings, labels, threshold=0.95)

    unique = sorted(set(new_labels))
    assert unique == list(range(len(unique)))
