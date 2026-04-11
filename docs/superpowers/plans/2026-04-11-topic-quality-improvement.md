# Topic Quality Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 토픽 분석 품질을 개선한다 — 짧은 리뷰 분리, 유사 토픽 자동 병합, 자동 k 추천 수정, 토픽 라벨 개선.

**Architecture:** 기존 Python 파이프라인(Sentence Transformers → K-Means/HDBSCAN → YAKE/KeyBERT)을 유지하면서, 전처리(짧은 리뷰 필터링)와 후처리(토픽 병합) 단계를 추가한다. 자동 k 추천은 긍정/부정 독립 추천으로 리팩터링하고, 라벨링은 키프레이즈 우선 배치로 개선한다.

**Tech Stack:** Python 3, NumPy, scikit-learn, pytest / TypeScript, Vitest, Electron IPC

**Spec:** `docs/superpowers/specs/2026-04-11-single-game-analysis-enhancement-design.md` — Feature 1 (Section 2)

---

## File Structure

### Python (신규)
- `python/short_review.py` — 짧은 리뷰 판별 + 초단문 요약 생성
- `python/topic_merge.py` — centroid 기반 유사 토픽 병합

### Python (수정)
- `python/analyzer.py` — 짧은 리뷰 분리, 토픽 병합, separate k 적용, 라벨 개선 통합
- `python/topic_recommendation.py` — 긍정/부정 별도 k 추천, 절대 품질 임계값, 편향 완화

### TypeScript (수정)
- `src/main/analysis-settings.ts` — `min_review_words`, `merge_threshold` 설정 추가
- `src/main/analysis-cache.ts` — 캐시 해시에 새 설정 포함
- `src/main/ipc-handlers.ts` — 새 설정 전달
- `src/renderer/src/components/TopicAnalysis.tsx` — 초단문 요약, 병합 정보, separate k 표시

### Tests (신규)
- `tests/python/test_short_review.py`
- `tests/python/test_topic_merge.py`

### Tests (수정)
- `tests/python/test_topic_recommendation.py` — separate k 테스트 추가
- `tests/python/test_analyzer.py` — 통합 흐름 테스트 업데이트
- `tests/main/analysis-cache.test.ts` — 새 설정 포함 캐시 해시 테스트
- `tests/main/analysis-settings.test.ts` — 새 설정 파싱 테스트

---

## Task 1: Short Review Module

**Files:**
- Create: `python/short_review.py`
- Create: `tests/python/test_short_review.py`

- [ ] **Step 1: Write failing tests for short review filtering**

```python
# tests/python/test_short_review.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from short_review import is_short_review, build_short_review_summary


def test_is_short_review_english_below_threshold():
    assert is_short_review("good game", language="english", min_words=5) is True


def test_is_short_review_english_above_threshold():
    assert is_short_review("this game is really fun and amazing", language="english", min_words=5) is False


def test_is_short_review_english_exact_threshold():
    assert is_short_review("one two three four five", language="english", min_words=5) is False


def test_is_short_review_cjk_below_threshold():
    assert is_short_review("좋은게임", language="korean", min_words=5) is True


def test_is_short_review_cjk_above_threshold():
    assert is_short_review("이 게임은 정말 재미있고 강력 추천합니다", language="korean", min_words=5) is False


def test_is_short_review_chinese_below_threshold():
    assert is_short_review("好游戏", language="schinese", min_words=5) is True


def test_is_short_review_japanese_below_threshold():
    assert is_short_review("良いゲーム", language="japanese", min_words=5) is True


def test_is_short_review_empty():
    assert is_short_review("", language="english", min_words=5) is True


def test_build_short_review_summary_basic():
    reviews = [
        {"text": "good", "voted_up": True},
        {"text": "good", "voted_up": True},
        {"text": "bad", "voted_up": False},
        {"text": "10/10", "voted_up": True},
    ]
    result = build_short_review_summary(reviews)
    assert result["count"] == 4
    assert result["positive_rate"] == 0.75
    assert result["frequent_phrases"][0]["phrase"] == "good"
    assert result["frequent_phrases"][0]["count"] == 2
    assert len(result["frequent_phrases"]) <= 10


def test_build_short_review_summary_empty():
    result = build_short_review_summary([])
    assert result["count"] == 0
    assert result["positive_rate"] == 0.0
    assert result["frequent_phrases"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_short_review.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'short_review'`

- [ ] **Step 3: Implement short_review module**

```python
# python/short_review.py
from collections import Counter

CJK_LANGUAGES = {
    "schinese", "tchinese", "japanese", "korean",
    "koreana",  # Steam uses 'koreana' for Korean
}
CJK_CHAR_THRESHOLD_RATIO = 2  # CJK uses char count / this ratio vs word threshold


def is_short_review(text: str, language: str = "english", min_words: int = 5) -> bool:
    """Check if a review is too short for meaningful clustering."""
    stripped = text.strip()
    if not stripped:
        return True

    if language.lower() in CJK_LANGUAGES:
        min_chars = max(1, min_words * CJK_CHAR_THRESHOLD_RATIO)
        return len(stripped) < min_chars
    else:
        return len(stripped.split()) < min_words


def build_short_review_summary(reviews: list[dict]) -> dict:
    """Build summary stats for short reviews."""
    if not reviews:
        return {"count": 0, "positive_rate": 0.0, "frequent_phrases": []}

    count = len(reviews)
    positive_count = sum(1 for r in reviews if r["voted_up"])
    positive_rate = positive_count / count if count > 0 else 0.0

    phrase_counter = Counter(r["text"].strip().lower() for r in reviews if r["text"].strip())
    frequent = [
        {"phrase": phrase, "count": freq}
        for phrase, freq in phrase_counter.most_common(10)
    ]

    return {
        "count": count,
        "positive_rate": round(positive_rate, 4),
        "frequent_phrases": frequent,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_short_review.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add python/short_review.py tests/python/test_short_review.py
git commit -m "feat(analysis): add short review filtering module"
```

---

## Task 2: Topic Merge Module

**Files:**
- Create: `python/topic_merge.py`
- Create: `tests/python/test_topic_merge.py`

- [ ] **Step 1: Write failing tests for topic merging**

```python
# tests/python/test_topic_merge.py
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
    # Two very similar clusters and one distant
    embeddings = np.array([
        [1.0, 0.0, 0.0],
        [0.98, 0.02, 0.0],
        [0.97, 0.03, 0.0],  # cluster 1 — very close to cluster 0
        [0.0, 0.0, 1.0],
        [0.0, 0.02, 0.98],
    ])
    labels = [0, 0, 1, 2, 2]

    new_labels, merge_info = merge_similar_topics(embeddings, labels, threshold=0.95)

    # Clusters 0 and 1 should be merged (cosine similarity > 0.95)
    assert new_labels[0] == new_labels[1] == new_labels[2]
    # Cluster 2 stays separate
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
    # A -> B (sim 0.96), B -> C (sim 0.96), but A -> C (sim 0.88)
    # Single pass: merge A into B, but don't re-merge the result with C
    embeddings = np.array([
        [1.0, 0.0, 0.0],   # cluster 0
        [0.97, 0.05, 0.0],  # cluster 1 — close to 0
        [0.90, 0.10, 0.3],  # cluster 2 — close to 1 but not to 0
    ])
    labels = [0, 1, 2]

    new_labels, merge_info = merge_similar_topics(embeddings, labels, threshold=0.95)

    # Only the most similar pair should merge; third stays separate
    assert merge_info["merged_topic_count"] <= merge_info["original_topic_count"]
    # At most 1 merge in single pass
    assert len(merge_info["merges"]) <= 1


def test_merge_preserves_label_contiguity():
    """After merge, labels should be renumbered 0..N-1."""
    embeddings = np.array([
        [1.0, 0.0],
        [0.99, 0.01],
        [0.0, 1.0],
    ])
    labels = [0, 1, 2]

    new_labels, _ = merge_similar_topics(embeddings, labels, threshold=0.95)

    unique = sorted(set(new_labels))
    assert unique == list(range(len(unique)))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_topic_merge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'topic_merge'`

- [ ] **Step 3: Implement topic_merge module**

```python
# python/topic_merge.py
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

    # Compute all pairwise similarities
    pairs = []
    for i, lid_a in enumerate(unique_labels):
        for lid_b in unique_labels[i + 1:]:
            sim = _cosine_similarity(centroids[lid_a], centroids[lid_b])
            if sim >= threshold:
                pairs.append((sim, lid_a, lid_b))

    pairs.sort(key=lambda x: -x[0])

    # Single-pass merge
    merged_into = {}  # maps absorbed label -> target label
    merges_log = []

    for sim, lid_a, lid_b in pairs:
        if lid_a in merged_into or lid_b in merged_into:
            continue

        # Absorb smaller into larger
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

    # Apply merges to labels
    new_labels = []
    for l in labels:
        new_labels.append(merged_into.get(l, l))

    # Renumber labels to 0..N-1
    remaining = sorted(set(l for l in new_labels if l >= 0))
    remap = {old: new for new, old in enumerate(remaining)}
    remap[-1] = -1  # preserve noise label
    new_labels = [remap.get(l, l) for l in new_labels]

    # Remap merge log IDs
    for merge in merges_log:
        merge["to_id"] = remap.get(merge["to_id"], merge["to_id"])

    return new_labels, {
        "original_topic_count": original_count,
        "merged_topic_count": len(remaining),
        "merges": merges_log,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_topic_merge.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add python/topic_merge.py tests/python/test_topic_merge.py
git commit -m "feat(analysis): add topic merge module with centroid-based similarity"
```

---

## Task 3: Auto-K Recommendation Fix

**Files:**
- Modify: `python/topic_recommendation.py`
- Modify: `tests/python/test_topic_recommendation.py`

- [ ] **Step 1: Write failing tests for separate k recommendation**

Append to `tests/python/test_topic_recommendation.py`:

```python
def test_recommend_topic_count_returns_separate_k_per_group():
    """positive and negative groups should get independent k values."""
    # Positive: clear 2 clusters
    positive = np.vstack([
        _make_cluster(0.0, 0.0, 30, 10),
        _make_cluster(5.0, 5.0, 30, 11),
    ])
    # Negative: clear 3 clusters
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
    # Old fields should not exist
    assert "effective_k" not in result
    assert "confidence" not in result


def test_recommend_topic_count_uses_fallback_on_low_separation():
    """When silhouette scores are all below threshold, use fallback."""
    # Random noise — no clear cluster structure
    rng = np.random.default_rng(42)
    positive = rng.normal(0, 1, size=(60, 2))
    negative = rng.normal(0, 1, size=(60, 2))

    result = recommend_topic_count(positive, negative)

    assert "positive_k" in result
    assert "negative_k" in result
    # With pure noise, confidence should be low
    assert result["positive_confidence"] in {"low", "medium"}
    assert result["negative_confidence"] in {"low", "medium"}


def test_recommend_topic_count_fallback_when_one_group_too_small():
    """When one group is too small, that group gets fallback k."""
    positive = np.vstack([
        _make_cluster(0.0, 0.0, 30, 20),
        _make_cluster(5.0, 5.0, 30, 21),
    ])
    negative = _make_cluster(0.0, 0.0, 5, 22)  # too small

    result = recommend_topic_count(positive, negative)

    assert result["positive_k"] >= 2
    assert result["negative_k"] >= 2  # fallback
    assert result["negative_confidence"] == "low"
```

- [ ] **Step 2: Run tests to verify the new tests fail**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_topic_recommendation.py -v`
Expected: New 3 tests FAIL (old tests still PASS — will be removed in Step 5)

- [ ] **Step 3: Refactor topic_recommendation.py**

Replace `python/topic_recommendation.py` with:

```python
# python/topic_recommendation.py
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
            "used_fallback": pos_result["used_fallback"] and neg_result["used_fallback"],
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

    # Absolute quality check: if all separations are below threshold, fallback
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
```

- [ ] **Step 4: Update old tests to match new API**

Replace the existing two tests in `tests/python/test_topic_recommendation.py`:

```python
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
```

- [ ] **Step 5: Run all topic recommendation tests**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_topic_recommendation.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add python/topic_recommendation.py tests/python/test_topic_recommendation.py
git commit -m "refactor(analysis): separate k recommendation per sentiment group

Positive and negative review groups now get independent topic counts.
Adds absolute quality threshold (silhouette < 0.05 = fallback).
Reduces tie-breaking bias (0.03 -> 0.01 contender range)."
```

---

## Task 4: Integrate Into Analyzer Pipeline

**Files:**
- Modify: `python/analyzer.py`
- Modify: `tests/python/test_analyzer.py`

- [ ] **Step 1: Update test for auto-mode to expect separate k**

Replace `test_run_analysis_uses_recommendation_for_tier0_auto` in `tests/python/test_analyzer.py`:

```python
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
            "positive_k": 3,
            "negative_k": 4,
            "positive_confidence": "high",
            "negative_confidence": "medium",
            "positive_reason": "Best balance of separation and stability across tested k values",
            "negative_reason": "Best balance of separation and stability across tested k values",
            "details": {
                "tested_candidates": {"positive": [2, 3, 4], "negative": [2, 3, 4]},
                "per_group_sample_counts": {"positive": 3, "negative": 3},
                "positive_summary": {"k": 3, "score": 0.71, "margin": 0.1},
                "negative_summary": {"k": 4, "score": 0.65, "margin": 0.08},
                "used_fallback": False,
            },
        },
    )
    # Mock short review + merge to pass through
    monkeypatch.setattr(analyzer, "is_short_review", lambda text, language="english", min_words=5: False)
    monkeypatch.setattr(analyzer, "build_short_review_summary", lambda reviews: {"count": 0, "positive_rate": 0.0, "frequent_phrases": []})
    monkeypatch.setattr(analyzer, "merge_similar_topics", lambda emb, labels, threshold=0.80: (labels, {"original_topic_count": len(set(labels)), "merged_topic_count": len(set(labels)), "merges": []}))

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
    # Positive group clustered with k=3, negative with k=4
    assert cluster_calls[0]["n_clusters"] == 3
    assert cluster_calls[1]["n_clusters"] == 4
```

- [ ] **Step 2: Add test for short review filtering in analyzer**

Append to `tests/python/test_analyzer.py`:

```python
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

    result = analyzer.run_analysis(
        {"reviews": reviews, "config": {"tier": 0, "topicCountMode": "manual", "n_topics": 2, "min_review_words": 5}},
        "msg-4",
    )

    assert "short_review_summary" in result
    assert result["short_review_summary"]["count"] == 2  # "good" and "bad"
    assert result["total_reviews"] == 4
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_analyzer.py -v`
Expected: Updated/new tests FAIL

- [ ] **Step 4: Update analyzer.py**

Replace `python/analyzer.py` with:

```python
import sys
import numpy as np
from protocol import format_progress
from embeddings import generate_embeddings
from clustering import cluster_reviews
from keywords import extract_topic_keywords
from topic_recommendation import recommend_topic_count
from short_review import is_short_review, build_short_review_summary
from topic_merge import merge_similar_topics


def run_analysis(params: dict, msg_id: str) -> dict:
    """Full analysis pipeline: filter short → embed → recommend k → cluster → merge → extract keywords."""
    reviews = params.get("reviews", [])
    config = params.get("config", {})
    tier = config.get("tier", 0)
    n_topics = config.get("n_topics", 8)
    topic_count_mode = str(
        config.get("topicCountMode", config.get("topic_count_mode", "manual"))
    ).lower()
    min_review_words = config.get("min_review_words", 5)
    merge_threshold = config.get("merge_threshold", 0.80)

    if not reviews:
        return {"positive_topics": [], "negative_topics": [],
                "short_review_summary": {"count": 0, "positive_rate": 0.0, "frequent_phrases": []}}

    if tier >= 1:
        topic_count_mode = "auto"

    def progress(pct, msg, stage=None, elapsed_ms=None):
        sys.stdout.write(format_progress(msg_id, pct, msg, stage=stage, elapsed_ms=elapsed_ms) + "\n")
        sys.stdout.flush()

    # --- Step 1: Filter short reviews ---
    long_reviews = []
    short_reviews = []
    for r in reviews:
        lang = r.get("language", "english")
        if is_short_review(r["text"], language=lang, min_words=min_review_words):
            short_reviews.append({"text": r["text"], "voted_up": r["voted_up"]})
        else:
            long_reviews.append(r)

    short_review_summary = build_short_review_summary(short_reviews)

    if len(long_reviews) < 2:
        return {
            "positive_topics": [], "negative_topics": [],
            "short_review_summary": short_review_summary,
            "total_reviews": len(reviews),
            "positive_count": sum(1 for r in reviews if r["voted_up"]),
            "negative_count": sum(1 for r in reviews if not r["voted_up"]),
        }

    # --- Step 2: Split by sentiment ---
    positive = [r for r in long_reviews if r["voted_up"]]
    negative = [r for r in long_reviews if not r["voted_up"]]

    progress(5, "Generating embeddings...", stage="embedding")

    all_texts = [r["text"] for r in long_reviews]
    emb_result = generate_embeddings({"texts": all_texts, "tier": tier}, msg_id)
    all_embeddings = np.array(emb_result["embeddings"])

    # Map back to positive/negative
    pos_indices = [i for i, r in enumerate(long_reviews) if r["voted_up"]]
    neg_indices = [i for i, r in enumerate(long_reviews) if not r["voted_up"]]

    pos_embeddings = all_embeddings[pos_indices] if pos_indices else np.array([])
    neg_embeddings = all_embeddings[neg_indices] if neg_indices else np.array([])

    method = "hdbscan" if tier >= 1 else "kmeans"
    requested_k = int(n_topics) if tier == 0 and topic_count_mode == "manual" else None
    positive_k = requested_k
    negative_k = requested_k
    positive_confidence = None
    negative_confidence = None
    positive_reason = None
    negative_reason = None
    recommendation_details = None

    if tier == 0 and topic_count_mode == "auto":
        progress(60, "Calculating recommended topic count...", stage="recommendation")
        recommendation = recommend_topic_count(pos_embeddings, neg_embeddings)
        positive_k = recommendation["positive_k"]
        negative_k = recommendation["negative_k"]
        positive_confidence = recommendation["positive_confidence"]
        negative_confidence = recommendation["negative_confidence"]
        positive_reason = recommendation["positive_reason"]
        negative_reason = recommendation["negative_reason"]
        recommendation_details = recommendation["details"]
        progress(72, "Clustering reviews...", stage="clustering")
    else:
        progress(60, "Clustering reviews...", stage="clustering")

    if tier == 0 and topic_count_mode == "manual":
        positive_reason = "Using requested topic count"
        negative_reason = "Using requested topic count"
        positive_k = requested_k
        negative_k = requested_k
    elif tier >= 1:
        positive_reason = "Auto by HDBSCAN"
        negative_reason = "Auto by HDBSCAN"

    pos_topics = _analyze_group(
        [r["text"] for r in positive], pos_embeddings,
        method, positive_k if positive_k is not None else n_topics, tier,
        merge_threshold
    ) if positive else ([], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []})

    progress(80, "Extracting keywords...", stage="keywords")

    neg_topics = _analyze_group(
        [r["text"] for r in negative], neg_embeddings,
        method, negative_k if negative_k is not None else n_topics, tier,
        merge_threshold
    ) if negative else ([], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []})

    progress(100, "Analysis complete", stage="complete")

    pos_topic_list, pos_merge_info = pos_topics
    neg_topic_list, neg_merge_info = neg_topics

    return {
        "model": emb_result["model"],
        "tier": tier,
        "total_reviews": len(reviews),
        "positive_count": len(positive) + sum(1 for r in short_reviews if r["voted_up"]),
        "negative_count": len(negative) + sum(1 for r in short_reviews if not r["voted_up"]),
        "topic_count_mode": topic_count_mode,
        "requested_k": requested_k,
        "positive_k": positive_k if tier == 0 else None,
        "negative_k": negative_k if tier == 0 else None,
        "positive_confidence": positive_confidence,
        "negative_confidence": negative_confidence,
        "positive_reason": positive_reason,
        "negative_reason": negative_reason,
        "recommendation_details": recommendation_details,
        "short_review_summary": short_review_summary,
        "merge_info": {
            "positive": pos_merge_info,
            "negative": neg_merge_info,
        },
        "positive_topics": pos_topic_list,
        "negative_topics": neg_topic_list,
    }


def _analyze_group(texts, embeddings, method, n_topics, tier, merge_threshold=0.80):
    if len(texts) < 2:
        return [], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []}

    labels = cluster_reviews(
        embeddings,
        method=method,
        n_clusters=min(n_topics, len(texts)),
        min_cluster_size=3
    )

    # Merge similar topics
    labels, merge_info = merge_similar_topics(embeddings, labels, threshold=merge_threshold)

    topic_keywords = extract_topic_keywords(
        texts, labels, tier=tier,
        embeddings=embeddings if tier >= 1 else None
    )

    topics = []
    for topic_id, keywords in sorted(topic_keywords.items()):
        topic_texts = [t for t, l in zip(texts, labels) if l == topic_id]
        # Prefer bigram+ keyphrases for label
        bigram_kws = [kw for kw, _ in keywords if " " in kw]
        unigram_kws = [kw for kw, _ in keywords if " " not in kw]
        label_parts = (bigram_kws + unigram_kws)[:3]
        label = ", ".join(label_parts) if label_parts else f"Topic {topic_id}"

        topics.append({
            "id": topic_id,
            "keywords": [{"word": kw, "score": round(sc, 3)} for kw, sc in keywords],
            "label": label,
            "review_count": len(topic_texts),
            "sample_reviews": topic_texts[:5]
        })

    topics.sort(key=lambda t: t["review_count"], reverse=True)
    return topics, merge_info
```

- [ ] **Step 5: Update remaining analyzer tests for new return shape**

Update `test_run_analysis_uses_requested_k_for_tier0_manual` and `test_run_analysis_skips_recommendation_for_tier1` in `tests/python/test_analyzer.py` — add mock imports and update assertions:

For `_install_common_mocks`, add merge mock:

```python
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
```

Update `test_run_analysis_uses_requested_k_for_tier0_manual` assertions:

```python
    assert result["topic_count_mode"] == "manual"
    assert result["requested_k"] == 5
    assert result["positive_k"] == 5
    assert result["negative_k"] == 5
    assert result["positive_confidence"] is None
    assert result["positive_reason"] == "Using requested topic count"
    assert [call["n_clusters"] for call in cluster_calls] == [5, 5]
```

Update `test_run_analysis_skips_recommendation_for_tier1` assertions:

```python
    assert result["topic_count_mode"] == "auto"
    assert result["requested_k"] is None
    assert result["positive_k"] is None
    assert result["negative_k"] is None
    assert result["positive_confidence"] is None
    assert result["positive_reason"] == "Auto by HDBSCAN"
    assert all(call["method"] == "hdbscan" for call in cluster_calls)
```

- [ ] **Step 6: Run all analyzer tests**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/test_analyzer.py -v`
Expected: All tests PASS

- [ ] **Step 7: Run full Python test suite**

Run: `cd C:\Users\BK927\repo\ReviewForge && python -m pytest tests/python/ -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add python/analyzer.py tests/python/test_analyzer.py
git commit -m "feat(analysis): integrate short review filter, topic merge, separate k into pipeline"
```

---

## Task 5: Settings and Cache Updates (TypeScript)

**Files:**
- Modify: `src/main/analysis-settings.ts`
- Modify: `src/main/analysis-cache.ts`
- Modify: `tests/main/analysis-settings.test.ts`
- Modify: `tests/main/analysis-cache.test.ts`

- [ ] **Step 1: Read existing TypeScript tests**

Read `tests/main/analysis-settings.test.ts` and `tests/main/analysis-cache.test.ts` to understand current test patterns before modifying.

- [ ] **Step 2: Add min_review_words and merge_threshold to NormalizedAnalysisConfig**

In `src/main/analysis-settings.ts`, update the interface and `resolveAnalysisConfig`:

```typescript
// Add to NormalizedAnalysisConfig interface:
export interface NormalizedAnalysisConfig extends Record<string, unknown> {
  tier: number
  topicCountMode: TopicCountMode
  n_topics?: number
  maxReviews?: number
  filter?: Record<string, unknown>
  min_review_words: number
  merge_threshold: number
}
```

In `resolveAnalysisConfig`, add after `filter` resolution:

```typescript
  const minReviewWords = parsePositiveInteger(config.min_review_words, 1) ?? 5
  const mergeThreshold = typeof config.merge_threshold === 'number'
    && Number.isFinite(config.merge_threshold)
    && config.merge_threshold >= 0 && config.merge_threshold <= 1.0
    ? config.merge_threshold
    : 0.80

  // ... in normalizedConfig:
  normalizedConfig.min_review_words = minReviewWords
  normalizedConfig.merge_threshold = mergeThreshold
```

- [ ] **Step 3: Update cache hash to include new fields**

In `src/main/analysis-cache.ts`, update `buildAnalysisCacheIdentity`:

```typescript
  const cacheDescriptor: Record<string, unknown> = {
    tier: config.tier,
    topicCountMode: config.topicCountMode,
    maxReviews: config.maxReviews ?? null,
    filter: activeFilters,
    min_review_words: config.min_review_words,
    merge_threshold: config.merge_threshold,
  }
```

- [ ] **Step 4: Add tests for new settings**

Append to `tests/main/analysis-settings.test.ts`:

```typescript
test('resolveAnalysisConfig sets default min_review_words and merge_threshold', () => {
  const config = resolveAnalysisConfig({ topicCountMode: 'manual', n_topics: 5 })
  expect(config.min_review_words).toBe(5)
  expect(config.merge_threshold).toBe(0.80)
})

test('resolveAnalysisConfig respects custom min_review_words and merge_threshold', () => {
  const config = resolveAnalysisConfig({
    topicCountMode: 'manual',
    n_topics: 5,
    min_review_words: 3,
    merge_threshold: 0.90
  })
  expect(config.min_review_words).toBe(3)
  expect(config.merge_threshold).toBe(0.90)
})
```

Append to `tests/main/analysis-cache.test.ts`:

```typescript
test('cache hash changes when min_review_words changes', () => {
  const base = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 5, merge_threshold: 0.80 } as NormalizedAnalysisConfig)
  const changed = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 3, merge_threshold: 0.80 } as NormalizedAnalysisConfig)
  expect(base.configHash).not.toBe(changed.configHash)
})

test('cache hash changes when merge_threshold changes', () => {
  const base = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 5, merge_threshold: 0.80 } as NormalizedAnalysisConfig)
  const changed = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 5, merge_threshold: 0.90 } as NormalizedAnalysisConfig)
  expect(base.configHash).not.toBe(changed.configHash)
})
```

- [ ] **Step 5: Run TypeScript tests**

Run: `cd C:\Users\BK927\repo\ReviewForge && pnpm test`
Expected: All tests PASS (including new ones)

- [ ] **Step 6: Commit**

```bash
git add src/main/analysis-settings.ts src/main/analysis-cache.ts tests/main/analysis-settings.test.ts tests/main/analysis-cache.test.ts
git commit -m "feat(settings): add min_review_words and merge_threshold to analysis config"
```

---

## Task 6: IPC Handler Update

**Files:**
- Modify: `src/main/ipc-handlers.ts`

- [ ] **Step 1: Update review data sent to Python sidecar**

In `src/main/ipc-handlers.ts`, update `analysis:run` handler (line 124-130). Change the `reviewData` mapping to include `language` (already present) and pass new config fields:

```typescript
    const reviewData = reviews.map(r => ({
      id: r.recommendation_id,
      text: r.review_text,
      voted_up: r.voted_up === 1,
      language: r.language,
      playtime: r.playtime_at_review
    }))
```

No change needed here — `language` is already included. The `analysisConfig` already passes through to sidecar via `config`, and the new `min_review_words`/`merge_threshold` fields are included by `resolveAnalysisConfig`.

Verify: the sidecar call at line 134 passes `analysisConfig`:
```typescript
    const result = await sidecar.send('analyze', { reviews: reviewData, config: analysisConfig }, ...)
```

The new fields (`min_review_words`, `merge_threshold`) are already part of `analysisConfig` after Task 5 changes. Python `analyzer.py` reads them with `config.get("min_review_words", 5)` and `config.get("merge_threshold", 0.80)`.

- [ ] **Step 2: Verify end-to-end by running full test suite**

Run: `cd C:\Users\BK927\repo\ReviewForge && pnpm test && python -m pytest tests/python/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit (if any changes were needed)**

```bash
git add src/main/ipc-handlers.ts
git commit -m "chore: verify IPC handler passes new analysis config fields"
```

---

## Task 7: Frontend — TopicAnalysis Component Update

**Files:**
- Modify: `src/renderer/src/components/TopicAnalysis.tsx`

- [ ] **Step 1: Read current TopicAnalysis.tsx fully**

Read the file to understand the current UI structure before modifying.

- [ ] **Step 2: Update AnalysisResult interface**

Replace old fields with new ones:

```typescript
interface AnalysisResult {
  positive_topics: Topic[]
  negative_topics: Topic[]
  total_reviews: number
  total_available?: number
  sampled?: boolean
  positive_count: number
  negative_count: number
  tier: number
  model: string
  topic_count_mode?: 'auto' | 'manual'
  requested_k?: number | null
  // New: separate k per group
  positive_k?: number | null
  negative_k?: number | null
  positive_confidence?: 'high' | 'medium' | 'low' | null
  negative_confidence?: 'high' | 'medium' | 'low' | null
  positive_reason?: string | null
  negative_reason?: string | null
  recommendation_details?: Record<string, unknown> | null
  // New: short review summary
  short_review_summary?: {
    count: number
    positive_rate: number
    frequent_phrases: { phrase: string; count: number }[]
  }
  // New: merge info
  merge_info?: {
    positive: { original_topic_count: number; merged_topic_count: number; merges: unknown[] }
    negative: { original_topic_count: number; merged_topic_count: number; merges: unknown[] }
  }
}
```

- [ ] **Step 3: Update metadata display section**

Replace the existing metadata badges (effective_k, confidence) with separate positive/negative displays. Find the metadata section (around line 196-211) and update:

```tsx
{result.topic_count_mode === 'auto' && result.positive_k != null && (
  <span className="badge">
    Positive topics: {result.positive_k}
    {result.positive_confidence && (
      <span className={`confidence-${result.positive_confidence}`}>
        ({result.positive_confidence})
      </span>
    )}
  </span>
)}
{result.topic_count_mode === 'auto' && result.negative_k != null && (
  <span className="badge">
    Negative topics: {result.negative_k}
    {result.negative_confidence && (
      <span className={`confidence-${result.negative_confidence}`}>
        ({result.negative_confidence})
      </span>
    )}
  </span>
)}
```

- [ ] **Step 4: Add short review summary section**

Add before the topic columns:

```tsx
{result.short_review_summary && result.short_review_summary.count > 0 && (
  <div className="short-review-summary">
    <h4>Short Reviews ({result.short_review_summary.count} filtered)</h4>
    <p>Positive rate: {(result.short_review_summary.positive_rate * 100).toFixed(1)}%</p>
    {result.short_review_summary.frequent_phrases.length > 0 && (
      <div className="frequent-phrases">
        {result.short_review_summary.frequent_phrases.map((fp, i) => (
          <span key={i} className="phrase-tag">
            {fp.phrase} ({fp.count})
          </span>
        ))}
      </div>
    )}
  </div>
)}
```

- [ ] **Step 5: Add merge info display (optional, collapsed by default)**

Add a small info line near each topic group header:

```tsx
{result.merge_info?.positive && result.merge_info.positive.merges.length > 0 && (
  <p className="merge-info">
    {result.merge_info.positive.original_topic_count} topics merged to {result.merge_info.positive.merged_topic_count}
  </p>
)}
```

Same pattern for negative merge info.

- [ ] **Step 6: Verify the app builds**

Run: `cd C:\Users\BK927\repo\ReviewForge && pnpm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 7: Commit**

```bash
git add src/renderer/src/components/TopicAnalysis.tsx
git commit -m "feat(ui): display separate k, short review summary, merge info in topic analysis"
```

---

## Task 8: Final Integration Test

- [ ] **Step 1: Run full test suite**

Run: `cd C:\Users\BK927\repo\ReviewForge && pnpm test && python -m pytest tests/python/ -v`
Expected: All tests PASS

- [ ] **Step 2: Manual smoke test (optional)**

Run: `cd C:\Users\BK927\repo\ReviewForge && pnpm dev`
- Open a game with reviews already fetched
- Run topic analysis in auto mode
- Verify: separate positive/negative topic counts displayed
- Verify: short review summary appears (if short reviews exist)
- Verify: merge info appears (if topics were merged)

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address integration issues from topic quality improvement"
```
