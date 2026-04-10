import numpy as np
import pytest
import python.clustering as clustering
from python.clustering import cluster_reviews


def test_kmeans_returns_labels():
    # 3 clear clusters in 2D space
    vecs = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.05, 0.05],
        [5.0, 5.0], [5.1, 5.1], [4.9, 4.9],
        [10.0, 0.0], [10.1, 0.1], [9.9, 0.05],
    ])
    labels = cluster_reviews(vecs, method="kmeans", n_clusters=3)
    assert len(labels) == 9
    # Points 0-2 should share a label, 3-5 another, 6-8 another
    assert labels[0] == labels[1] == labels[2]
    assert labels[3] == labels[4] == labels[5]
    assert labels[6] == labels[7] == labels[8]
    assert len(set(labels)) == 3


def test_hdbscan_returns_labels():
    vecs = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.05, 0.05], [0.02, 0.08],
        [5.0, 5.0], [5.1, 5.1], [4.9, 4.9], [5.05, 5.02],
    ])
    labels = cluster_reviews(vecs, method="hdbscan", min_cluster_size=2)
    assert len(labels) == 8
    # HDBSCAN may assign -1 (noise), but should find at least 2 clusters
    unique = set(l for l in labels if l >= 0)
    assert len(unique) >= 2


def test_kmeans_forwards_seeded_random_state(monkeypatch):
    captured = {}

    class FakeKMeans:
        def __init__(self, n_clusters, random_state, n_init):
            captured["n_clusters"] = n_clusters
            captured["random_state"] = random_state
            captured["n_init"] = n_init

        def fit_predict(self, vectors):
            return np.zeros(len(vectors), dtype=int)

    monkeypatch.setattr(clustering, "KMeans", FakeKMeans)

    vecs = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    labels = cluster_reviews(vecs, method="kmeans", n_clusters=3, random_state=17)

    assert labels == [0, 0, 0]
    assert captured == {"n_clusters": 3, "random_state": 17, "n_init": 10}
