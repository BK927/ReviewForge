import math
from itertools import combinations

import numpy as np
from sklearn.metrics import adjusted_rand_score, silhouette_score

from clustering import cluster_reviews

MAX_SAMPLES_PER_GROUP = 600
ELIGIBLE_GROUP_MIN_SIZE = 20
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
    positive_embeddings = np.asarray(positive_embeddings)
    negative_embeddings = np.asarray(negative_embeddings)
    total_reviews = int(len(positive_embeddings) + len(negative_embeddings))

    group_inputs = {
        "positive": positive_embeddings,
        "negative": negative_embeddings,
    }
    group_evaluations = {}
    for group_name, embeddings in group_inputs.items():
        sampled = _sample_group_embeddings(embeddings, seed=17 if group_name == "positive" else 29)
        if sampled is None:
            group_evaluations[group_name] = {
                "sample_count": 0,
                "weight": len(embeddings),
                "candidate_scores": {},
            }
            continue

        sample_vectors, sample_indices = sampled
        candidate_scores = _evaluate_group_candidates(sample_vectors, sample_indices)
        group_evaluations[group_name] = {
            "sample_count": len(sample_vectors),
            "weight": len(embeddings),
            "candidate_scores": candidate_scores,
        }

    aggregate_scores = _aggregate_group_scores(group_evaluations)
    tested_candidates = sorted(aggregate_scores)
    if not tested_candidates:
        return _fallback_result(total_reviews)

    effective_k, winning_score, margin = _pick_winning_k(aggregate_scores)
    confidence = _confidence_from_scores(winning_score, margin)

    return {
        "effective_k": effective_k,
        "confidence": confidence,
        "reason": DEFAULT_REASON,
        "details": {
            "tested_candidates": tested_candidates,
            "per_group_sample_counts": {
                name: values["sample_count"] for name, values in group_evaluations.items()
            },
            "winning_summary": {
                "k": effective_k,
                "score": round(winning_score, 4),
                "margin": round(margin, 4),
            },
            "used_fallback": False,
        },
    }


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


def _aggregate_group_scores(group_evaluations: dict[str, dict]) -> dict[int, float]:
    aggregate_scores = {}
    total_weight = sum(
        values["weight"]
        for values in group_evaluations.values()
        if values["candidate_scores"]
    )
    if total_weight == 0:
        return aggregate_scores

    for values in group_evaluations.values():
        candidate_scores = values["candidate_scores"]
        if not candidate_scores:
            continue

        normalized_scores = _normalize_scores({
            k: metrics["group_score"] for k, metrics in candidate_scores.items()
        })
        weight = values["weight"] / total_weight
        for candidate_k, score in normalized_scores.items():
            aggregate_scores[candidate_k] = aggregate_scores.get(candidate_k, 0.0) + (score * weight)

    return aggregate_scores


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
    contenders = [item for item in ranked if (top_score - item[1]) < 0.03]
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


def _fallback_result(total_reviews: int) -> dict:
    effective_k = max(2, min(8, int(round(math.sqrt(max(total_reviews, 1)) / 2))))
    return {
        "effective_k": effective_k,
        "confidence": "low",
        "reason": FALLBACK_REASON,
        "details": {
            "tested_candidates": [],
            "per_group_sample_counts": {"positive": 0, "negative": 0},
            "winning_summary": {
                "k": effective_k,
                "score": 0.0,
                "margin": 0.0,
            },
            "used_fallback": True,
        },
    }
