import numpy as np
from sklearn.cluster import KMeans


def cluster_reviews(
    vectors: np.ndarray,
    method: str = "kmeans",
    n_clusters: int = 8,
    min_cluster_size: int = 5
) -> list[int]:
    """Cluster review embeddings. Returns list of cluster labels."""
    if len(vectors) < 2:
        return [0] * len(vectors)

    if method == "hdbscan":
        import hdbscan as hdb
        clusterer = hdb.HDBSCAN(
            min_cluster_size=max(2, min_cluster_size),
            min_samples=1,
            metric="euclidean"
        )
        labels = clusterer.fit_predict(vectors)
        return labels.tolist()

    else:  # kmeans
        actual_k = min(n_clusters, len(vectors))
        km = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
        labels = km.fit_predict(vectors)
        return labels.tolist()
