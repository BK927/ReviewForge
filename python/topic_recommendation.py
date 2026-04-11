import math
from itertools import combinations

import numpy as np
from sklearn.metrics import adjusted_rand_score, silhouette_score

from clustering import cluster_reviews

MAX_SAMPLES_PER_GROUP = 600
ELIGIBLE_GROUP_MIN_SIZE = 20
MIN_SEPARATION_THRESHOLD = 0.05
RUN_CONFIGS = (
    {"seed": 11, "sample_ratio": 1.0},
    {"seed": 23, "sample_ratio": 1.0},
    {"seed": 101, "sample_ratio": 0.85},
    {"seed": 202, "sample_ratio": 0.85},
)
DEFAULT_REASON = "Best balance of separation and stability across tested k values"
FALLBACK_REASON = "Insufficient stable signal; using conservative heuristic"


def recommend_topic_count(
    positive_embeddings: np.ndarray,
    negative_embeddings: np.ndarray,
) -> dict:
    """Recommend topic count independently for positive and negative groups."""
    positive_embeddings = np.asarray(positive_embeddings)
    negative_embeddings = np.asarray(negative_embeddings)

    pos_result = _recommend_for_group(positive_embeddings, seed=17)
    neg_result = _recommend_for_group(negative_embeddings, seed=29)

    return {
        "positive_k": pos_result["k"],
        "negative_k": neg_result["k"],
        "positive_confidence": pos_result["confidence"],
        "negative_confidence": neg_result["confidence"],
        "positive_reason": pos_result["reason"],
        "negative_reason": neg_result["reason"],
        "details": {
            "tested_candidates": {
                "positive": pos_result["tested_candidates"],
                "negative": neg_result["tested_candidates"],
            },
            "per_group_sample_counts": {
                "positive": pos_result["sample_count"],
                "negative": neg_result["sample_count"],
            },
            "positive_summary": pos_result["winning_summary"],
            "negative_summary": neg_result["winning_summary"],
            "positive_used_fallback": pos_result["used_fallback"],
            "negative_used_fallback": neg_result["used_fallback"],
            "used_fallback": pos_result["used_fallback"] or neg_result["used_fallback"],
        },
    }


def _recommend_for_group(embeddings: np.ndarray, seed: int) -> dict:
    """Recommend k for a single sentiment group."""
    if len(embeddings) < ELIGIBLE_GROUP_MIN_SIZE:
        k = _fallback_k(len(embeddings))
        return {
            "k": k,
            "confidence": "low",
            "reason": FALLBACK_REASON,
            "tested_candidates": [],
            "sample_count": 0,
            "winning_summary": {"k": k, "score": 0.0, "margin": 0.0},
            "used_fallback": True,
        }

    sampled = _sample_group_embeddings(embeddings, seed)
    if sampled is None:
        k = _fallback_k(len(embeddings))
        return {
            "k": k,
            "confidence": "low",
            "reason": FALLBACK_REASON,
            "tested_candidates": [],
            "sample_count": 0,
            "winning_summary": {"k": k, "score": 0.0, "margin": 0.0},
            "used_fallback": True,
        }

    sample_vectors, sample_indices = sampled
    candidate_scores = _evaluate_group_candidates(sample_vectors, sample_indices)

    if not candidate_scores:
        k = _fallback_k(len(embeddings))
        return {
            "k": k,
            "confidence": "low",
            "reason": FALLBACK_REASON,
            "tested_candidates": [],
            "sample_count": len(sample_vectors),
            "winning_summary": {"k": k, "score": 0.0, "margin": 0.0},
            "used_fallback": True,
        }

    max_separation = max(m["separation_median"] for m in candidate_scores.values())
    if max_separation < MIN_SEPARATION_THRESHOLD:
        k = _fallback_k(len(embeddings))
        return {
            "k": k,
            "confidence": "low",
            "reason": FALLBACK_REASON,
            "tested_candidates": sorted(candidate_scores),
            "sample_count": len(sample_vectors),
            "winning_summary": {"k": k, "score": 0.0, "margin": 0.0},
            "used_fallback": True,
        }

    raw_scores = {k_val: m["group_score"] for k_val, m in candidate_scores.items()}
    normalized = _normalize_scores(raw_scores)
    k, score, margin = _pick_winning_k(normalized)
    confidence = _confidence_from_scores(score, margin)

    return {
        "k": k,
        "confidence": confidence,
        "reason": DEFAULT_REASON,
        "tested_candidates": sorted(candidate_scores),
        "sample_count": len(sample_vectors),
        "winning_summary": {"k": k, "score": round(score, 4), "margin": round(margin, 4)},
        "used_fallback": False,
    }


def _fallback_k(total: int) -> int:
    return max(2, min(8, int(round(math.sqrt(max(total, 1)) / 2))))


def _sample_group_embeddings(embeddings: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray] | None:
    if len(embeddings) < ELIGIBLE_GROUP_MIN_SIZE:
        return None

    rng = np.random.default_rng(seed)
    sample_size = min(len(embeddings), MAX_SAMPLES_PER_GROUP)
    if sample_size == len(embeddings):
        indices = np.arange(len(embeddings))
    else:
        indices = np.sort(rng.choice(len(embeddings), size=sample_size, replace=False))

    return embeddings[indices], indices


def _candidate_ks(sample_size: int) -> list[int]:
    if sample_size < 20:
        return []
    if sample_size < 60:
        return list(range(2, 5))
    if sample_size < 150:
        return list(range(3, 7))
    if sample_size < 300:
        return list(range(4, 9))
    return list(range(5, 11))


def _evaluate_group_candidates(vectors: np.ndarray, indices: np.ndarray) -> dict[int, dict]:
    candidate_scores = {}
    for candidate_k in _candidate_ks(len(vectors)):
        metrics = _evaluate_candidate_k(vectors, indices, candidate_k)
        if metrics is None:
            continue
        candidate_scores[candidate_k] = metrics
    return candidate_scores


def _evaluate_candidate_k(vectors: np.ndarray, base_indices: np.ndarray, candidate_k: int) -> dict | None:
    run_results = []
    for config in RUN_CONFIGS:
        sampled_vectors, sampled_indices = _subsample_vectors(
            vectors,
            base_indices,
            seed=config["seed"],
            sample_ratio=config["sample_ratio"],
        )
        labels = np.array(
            cluster_reviews(
                sampled_vectors,
                method="kmeans",
                n_clusters=candidate_k,
                random_state=config["seed"],
            )
        )
        unique_labels = set(labels.tolist())
        if len(unique_labels) < 2 or len(unique_labels) >= len(sampled_vectors):
            continue

        try:
            separation = silhouette_score(sampled_vectors, labels)
        except ValueError:
            continue

        run_results.append({
            "indices": sampled_indices,
            "labels": labels,
            "separation": float(separation),
            "fragmentation": float(_fragmentation_penalty(labels)),
        })

    if not run_results:
        return None

    stability_scores = _pairwise_stability_scores(run_results)
    stability_mean = float(np.mean(stability_scores)) if stability_scores else 0.0
    separation_median = float(np.median([run["separation"] for run in run_results]))
    fragmentation_mean = float(np.mean([run["fragmentation"] for run in run_results]))
    group_score = (
        0.55 * separation_median
        + 0.35 * stability_mean
        - 0.10 * fragmentation_mean
    )

    return {
        "group_score": group_score,
        "separation_median": separation_median,
        "stability_mean": stability_mean,
        "fragmentation_mean": fragmentation_mean,
    }


def _subsample_vectors(
    vectors: np.ndarray,
    base_indices: np.ndarray,
    seed: int,
    sample_ratio: float,
) -> tuple[np.ndarray, np.ndarray]:
    if sample_ratio >= 1.0:
        return vectors, base_indices

    rng = np.random.default_rng(seed)
    sample_size = max(2, int(round(len(vectors) * sample_ratio)))
    selected_positions = np.sort(rng.choice(len(vectors), size=sample_size, replace=False))
    return vectors[selected_positions], base_indices[selected_positions]


def _fragmentation_penalty(labels: np.ndarray) -> float:
    sample_size = len(labels)
    if sample_size == 0:
        return 0.0

    tiny_threshold = max(8, int(math.ceil(sample_size * 0.05)))
    _, counts = np.unique(labels, return_counts=True)
    tiny_cluster_points = int(sum(count for count in counts if count < tiny_threshold))
    return tiny_cluster_points / sample_size


def _pairwise_stability_scores(run_results: list[dict]) -> list[float]:
    stability_scores = []
    for left_run, right_run in combinations(run_results, 2):
        shared_indices, left_positions, right_positions = np.intersect1d(
            left_run["indices"],
            right_run["indices"],
            assume_unique=True,
            return_indices=True,
        )
        if len(shared_indices) < 2:
            continue

        left_labels = left_run["labels"][left_positions]
        right_labels = right_run["labels"][right_positions]
        if len(set(left_labels.tolist())) < 2 or len(set(right_labels.tolist())) < 2:
            continue

        stability_scores.append(float(adjusted_rand_score(left_labels, right_labels)))
    return stability_scores


def _normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}

    minimum = min(scores.values())
    maximum = max(scores.values())
    if math.isclose(minimum, maximum):
        return {candidate_k: 1.0 for candidate_k in scores}

    span = maximum - minimum
    return {
        candidate_k: (score - minimum) / span
        for candidate_k, score in scores.items()
    }


def _pick_winning_k(scores: dict[int, float]) -> tuple[int, float, float]:
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_k, top_score = ranked[0]
    contenders = [item for item in ranked if (top_score - item[1]) < 0.01]
    winning_k, winning_score = min(contenders, key=lambda item: item[0])
    next_best_score = max(
        (score for candidate_k, score in ranked if candidate_k != winning_k),
        default=winning_score,
    )
    return winning_k, winning_score, max(0.0, winning_score - next_best_score)


def _confidence_from_scores(winning_score: float, margin: float) -> str:
    if winning_score >= 0.75 and margin >= 0.12:
        return "high"
    if winning_score >= 0.45 or margin >= 0.05:
        return "medium"
    return "low"
