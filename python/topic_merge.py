import numpy as np
from numpy.linalg import norm


def compute_centroids(embeddings: np.ndarray, labels: list[int]) -> dict[int, np.ndarray]:
    """Compute mean embedding (centroid) for each cluster label."""
    centroids = {}
    labels_arr = np.array(labels)
    for label_id in set(labels):
        if label_id < 0:
            continue
        mask = labels_arr == label_id
        centroids[label_id] = embeddings[mask].mean(axis=0)
    return centroids


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = norm(a) * norm(b)
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def merge_similar_topics(
    embeddings: np.ndarray,
    labels: list[int],
    threshold: float = 0.80,
) -> tuple[list[int], dict]:
    """Merge clusters with centroid cosine similarity above threshold.

    Single-pass greedy: process most similar pair first, absorb smaller
    cluster into larger one. Already-merged clusters are not re-merged.
    """
    unique_labels = sorted(set(l for l in labels if l >= 0))
    original_count = len(unique_labels)

    if original_count < 2:
        return list(labels), {
            "original_topic_count": original_count,
            "merged_topic_count": original_count,
            "merges": [],
        }

    centroids = compute_centroids(embeddings, labels)
    labels_arr = np.array(labels)
    label_counts = {lid: int(np.sum(labels_arr == lid)) for lid in unique_labels}

    pairs = []
    for i, lid_a in enumerate(unique_labels):
        for lid_b in unique_labels[i + 1:]:
            sim = _cosine_similarity(centroids[lid_a], centroids[lid_b])
            if sim >= threshold:
                pairs.append((sim, lid_a, lid_b))

    pairs.sort(key=lambda x: -x[0])

    merged_into = {}
    merges_log = []

    for sim, lid_a, lid_b in pairs:
        if lid_a in merged_into or lid_b in merged_into:
            continue

        if label_counts.get(lid_a, 0) >= label_counts.get(lid_b, 0):
            target, source = lid_a, lid_b
        else:
            target, source = lid_b, lid_a

        merged_into[source] = target
        label_counts[target] = label_counts.get(target, 0) + label_counts.get(source, 0)
        label_counts.pop(source, None)
        merges_log.append({
            "from_id": int(source),
            "to_id": int(target),
            "similarity": round(sim, 4),
        })

    new_labels = []
    for l in labels:
        new_labels.append(merged_into.get(l, l))

    remaining = sorted(set(l for l in new_labels if l >= 0))
    remap = {old: new for new, old in enumerate(remaining)}
    remap[-1] = -1
    new_labels = [remap.get(l, l) for l in new_labels]

    for merge in merges_log:
        merge["to_id"] = remap.get(merge["to_id"], merge["to_id"])

    return new_labels, {
        "original_topic_count": original_count,
        "merged_topic_count": len(remaining),
        "merges": merges_log,
    }
