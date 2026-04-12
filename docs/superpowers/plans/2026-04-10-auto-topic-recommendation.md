# Auto Topic Recommendation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `Auto (recommended)` and `Manual` topic-count modes, compute a stability-aware recommended topic count during Tier 0 analysis, and surface the recommendation stage plus result metadata in the UI.

**Architecture:** Keep the recommendation engine inside the Python analysis pipeline so it can reuse the same embeddings and filtered review set as the real clustering pass. Normalize mode/tier decisions in the main process, reuse config-specific cache entries, and keep the renderer focused on mode selection, progress display, and post-run metadata.

**Tech Stack:** Electron main process, React + TypeScript renderer, Python + NumPy + scikit-learn, Vitest, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/main/analysis-settings.ts` | Normalize `topicCountMode`, clamp manual topic counts, force Tier 1 to auto mode |
| Create | `src/main/analysis-cache.ts` | Build stable cache-hash payloads for auto/manual analysis requests |
| Modify | `src/main/ipc-handlers.ts` | Use normalized config, short-circuit exact cache hits, persist new result metadata |
| Modify | `tests/main/analysis-settings.test.ts` | Verify mode normalization and Tier 1 override behavior |
| Create | `tests/main/analysis-cache.test.ts` | Verify cache payload and hash differences across mode/filter combinations |
| Modify | `python/clustering.py` | Accept explicit random seeds for repeated KMeans evaluation |
| Create | `python/topic_recommendation.py` | Evaluate candidate `k` values with separation, stability, fragmentation penalty, and fallback logic |
| Modify | `python/analyzer.py` | Run recommender for `Tier 0 + Auto`, emit recommendation progress, attach recommendation metadata |
| Create | `tests/python/test_topic_recommendation.py` | Verify candidate ranges, fallback, and stable-cluster recommendation output |
| Create | `tests/python/test_analyzer.py` | Verify auto/manual/Tier 1 analyzer behavior and metadata wiring |
| Modify | `tests/python/test_clustering.py` | Verify seeded KMeans behavior stays controllable |
| Create | `src/renderer/src/components/TopicCountModeControl.tsx` | Render mode selector and manual-input affordance |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx` | Track selected mode, load effective tier, send normalized config, render recommendation metadata |
| Modify | `src/renderer/src/components/AnalysisProgress.tsx` | Add optional recommendation stage to the step pipeline |
| Modify | `src/renderer/src/assets/styles.css` | Style the new mode controls, recommendation hint, and result metadata |
| Create | `tests/main/topic-count-mode-control.test.tsx` | Verify manual input visibility and Tier 1 lockout copy |
| Create | `tests/main/analysis-progress.test.tsx` | Verify recommendation step renders only for auto Tier 0 runs |

---

### Task 1: Normalize analysis mode and cache-key inputs in the main process

**Files:**
- Modify: `src/main/analysis-settings.ts`
- Create: `src/main/analysis-cache.ts`
- Modify: `tests/main/analysis-settings.test.ts`
- Create: `tests/main/analysis-cache.test.ts`

- [ ] **Step 1: Write the failing main-process tests**

Create `tests/main/analysis-cache.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { buildAnalysisCacheHash, buildAnalysisCachePayload } from '../../src/main/analysis-cache'

describe('buildAnalysisCachePayload', () => {
  it('includes manual topic counts in the cache payload', () => {
    expect(buildAnalysisCachePayload({
      tier: 0,
      topicCountMode: 'manual',
      n_topics: 7,
      maxReviews: 3000,
      filter: { language: 'koreana' }
    })).toEqual({
      tier: 0,
      topicCountMode: 'manual',
      n_topics: 7,
      maxReviews: 3000,
      filter: {
        language: 'koreana',
        period_start: null,
        period_end: null,
        playtime_min: null,
        playtime_max: null,
        steam_purchase: null,
        received_for_free: null
      }
    })
  })

  it('omits manual topic counts for auto runs', () => {
    expect(buildAnalysisCachePayload({
      tier: 0,
      topicCountMode: 'auto',
      n_topics: 7,
      maxReviews: 3000
    })).toEqual({
      tier: 0,
      topicCountMode: 'auto',
      maxReviews: 3000,
      filter: {
        language: null,
        period_start: null,
        period_end: null,
        playtime_min: null,
        playtime_max: null,
        steam_purchase: null,
        received_for_free: null
      }
    })
  })

  it('changes the hash when mode or filters change', () => {
    const manualHash = buildAnalysisCacheHash({ tier: 0, topicCountMode: 'manual', n_topics: 6 })
    const autoHash = buildAnalysisCacheHash({ tier: 0, topicCountMode: 'auto', n_topics: 6 })
    const filteredHash = buildAnalysisCacheHash({
      tier: 0,
      topicCountMode: 'auto',
      filter: { language: 'english' }
    })

    expect(manualHash).not.toBe(autoHash)
    expect(autoHash).not.toBe(filteredHash)
  })
})
```

Replace `tests/main/analysis-settings.test.ts` with:

```ts
import { describe, expect, it } from 'vitest'
import { resolveAnalysisConfig } from '../../src/main/analysis-settings'

describe('resolveAnalysisConfig', () => {
  it('keeps manual mode on Tier 0 and clamps the requested topic count', () => {
    expect(resolveAnalysisConfig({ topicCountMode: 'manual', n_topics: 50 }, { tier: '0' }, 0)).toMatchObject({
      tier: 0,
      topicCountMode: 'manual',
      n_topics: 20
    })
  })

  it('defaults unknown modes back to manual on Tier 0 for backward compatibility', () => {
    expect(resolveAnalysisConfig({ n_topics: 8 }, { tier: '0' }, 0)).toMatchObject({
      tier: 0,
      topicCountMode: 'manual',
      n_topics: 8
    })
  })

  it('forces Tier 1 requests to auto mode even when manual was requested', () => {
    expect(resolveAnalysisConfig({ topicCountMode: 'manual', n_topics: 5 }, { tier: '1' }, 0)).toMatchObject({
      tier: 1,
      topicCountMode: 'auto',
      n_topics: 5
    })
  })

  it('uses the detected tier when settings are auto', () => {
    expect(resolveAnalysisConfig({ topicCountMode: 'auto' }, { tier: 'auto' }, 1)).toMatchObject({
      tier: 1,
      topicCountMode: 'auto'
    })
  })
})
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
npx vitest run tests/main/analysis-settings.test.ts tests/main/analysis-cache.test.ts
```

Expected: FAIL because `analysis-cache.ts` does not exist and `resolveAnalysisConfig` does not return `topicCountMode`.

- [ ] **Step 3: Implement config normalization helpers**

Replace `src/main/analysis-settings.ts` with:

```ts
export interface SavedSettings {
  tier?: 'auto' | '0' | '1'
}

export type TopicCountMode = 'auto' | 'manual'

function parseTier(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
    return Math.trunc(value)
  }

  if (value === '0' || value === '1') {
    return Number(value)
  }

  return null
}

function parseTopicCountMode(value: unknown): TopicCountMode | null {
  if (value === 'auto' || value === 'manual') return value
  return null
}

function normalizeTopicCount(value: unknown, fallback = 8): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.min(20, Math.max(2, Math.trunc(value)))
  }
  return fallback
}

export function resolveAnalysisTier(requestedTier: unknown, settings?: SavedSettings, detectedTier = 0): number {
  const explicitTier = parseTier(requestedTier)
  if (explicitTier !== null) return explicitTier

  if (settings?.tier === 'auto') {
    return detectedTier
  }

  const savedTier = parseTier(settings?.tier)
  return savedTier ?? 0
}

export function resolveAnalysisConfig(
  config: Record<string, unknown>,
  settings?: SavedSettings,
  detectedTier = 0
): Record<string, unknown> {
  const tier = resolveAnalysisTier(config.tier, settings, detectedTier)
  const requestedMode = parseTopicCountMode(config.topicCountMode) ?? 'manual'
  const topicCountMode: TopicCountMode = tier >= 1 ? 'auto' : requestedMode

  return {
    ...config,
    tier,
    topicCountMode,
    n_topics: normalizeTopicCount(config.n_topics, 8)
  }
}
```

- [ ] **Step 4: Add cache-hash helpers**

Create `src/main/analysis-cache.ts`:

```ts
import crypto from 'crypto'

function normalizeFilter(filter: unknown): Record<string, unknown> {
  const value = (filter ?? {}) as Record<string, unknown>
  return {
    language: value.language ?? null,
    period_start: value.period_start ?? null,
    period_end: value.period_end ?? null,
    playtime_min: value.playtime_min ?? null,
    playtime_max: value.playtime_max ?? null,
    steam_purchase: value.steam_purchase ?? null,
    received_for_free: value.received_for_free ?? null
  }
}

export function buildAnalysisCachePayload(config: Record<string, unknown>): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    tier: config.tier ?? 0,
    topicCountMode: config.topicCountMode ?? 'manual',
    maxReviews: config.maxReviews ?? null,
    filter: normalizeFilter(config.filter)
  }

  if (config.topicCountMode === 'manual') {
    payload.n_topics = config.n_topics ?? 8
  }

  return payload
}

export function buildAnalysisCacheHash(config: Record<string, unknown>): string {
  return crypto
    .createHash('md5')
    .update(JSON.stringify(buildAnalysisCachePayload(config)))
    .digest('hex')
}
```

- [ ] **Step 5: Re-run the tests**

Run:

```bash
npx vitest run tests/main/analysis-settings.test.ts tests/main/analysis-cache.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/main/analysis-settings.ts src/main/analysis-cache.ts tests/main/analysis-settings.test.ts tests/main/analysis-cache.test.ts
git commit -m "feat(main): normalize topic count modes and cache inputs"
```

---

### Task 2: Add a stability-aware topic recommendation engine in Python

**Files:**
- Modify: `python/clustering.py`
- Create: `python/topic_recommendation.py`
- Modify: `tests/python/test_clustering.py`
- Create: `tests/python/test_topic_recommendation.py`

- [ ] **Step 1: Write the failing Python tests**

Append this test to `tests/python/test_clustering.py`:

```python
def test_kmeans_honors_random_state():
    vecs = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.05, 0.05],
        [5.0, 5.0], [5.1, 5.1], [4.9, 4.9],
        [10.0, 0.0], [10.1, 0.1], [9.9, 0.05],
    ])

    labels_a = cluster_reviews(vecs, method="kmeans", n_clusters=3, random_state=7)
    labels_b = cluster_reviews(vecs, method="kmeans", n_clusters=3, random_state=7)

    assert labels_a == labels_b
```

Create `tests/python/test_topic_recommendation.py`:

```python
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd() / "python"))

from topic_recommendation import candidate_range_for_size, recommend_topic_count


def make_three_cluster_vectors() -> np.ndarray:
    rng = np.random.default_rng(42)
    cluster_a = rng.normal(loc=[0.0, 0.0], scale=0.12, size=(30, 2))
    cluster_b = rng.normal(loc=[4.0, 4.0], scale=0.12, size=(30, 2))
    cluster_c = rng.normal(loc=[8.0, 0.0], scale=0.12, size=(30, 2))
    return np.vstack([cluster_a, cluster_b, cluster_c])


def test_candidate_range_scales_with_sample_size():
    assert list(candidate_range_for_size(25)) == [2, 3, 4]
    assert list(candidate_range_for_size(90)) == [3, 4, 5, 6]
    assert list(candidate_range_for_size(220)) == [4, 5, 6, 7, 8]
    assert list(candidate_range_for_size(400)) == [5, 6, 7, 8, 9, 10]


def test_recommend_topic_count_prefers_the_stable_cluster_count():
    vectors = make_three_cluster_vectors()
    result = recommend_topic_count({
        "positive": vectors,
        "negative": vectors.copy()
    }, total_selected_reviews=180)

    assert result["effective_k"] == 3
    assert result["confidence"] in {"medium", "high"}
    assert result["used_fallback"] is False


def test_recommend_topic_count_falls_back_for_tiny_groups():
    tiny = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    result = recommend_topic_count({
        "positive": tiny,
        "negative": tiny
    }, total_selected_reviews=6)

    assert result["used_fallback"] is True
    assert result["confidence"] == "low"
    assert result["effective_k"] == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python/.venv/Scripts/python.exe -m pytest tests/python/test_clustering.py tests/python/test_topic_recommendation.py -v
```

Expected: FAIL because `cluster_reviews()` does not accept `random_state` and `topic_recommendation.py` does not exist.

- [ ] **Step 3: Add seeded KMeans support**

Replace `python/clustering.py` with:

```python
import numpy as np
from sklearn.cluster import KMeans


def cluster_reviews(
    vectors: np.ndarray,
    method: str = "kmeans",
    n_clusters: int = 8,
    min_cluster_size: int = 5,
    random_state: int = 42
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

    actual_k = min(n_clusters, len(vectors))
    km = KMeans(n_clusters=actual_k, random_state=random_state, n_init=10)
    labels = km.fit_predict(vectors)
    return labels.tolist()
```

- [ ] **Step 4: Implement the recommendation module**

Create `python/topic_recommendation.py`:

```python
from __future__ import annotations

import math
from itertools import combinations
from typing import Any

import numpy as np
from sklearn.metrics import adjusted_rand_score, silhouette_score

from clustering import cluster_reviews

MAX_SAMPLE_PER_GROUP = 600
RUN_CONFIGS = (
    (1.00, 11),
    (1.00, 23),
    (0.85, 101),
    (0.85, 202),
)


def candidate_range_for_size(sample_size: int) -> range:
    if sample_size < 60:
        return range(2, 5)
    if sample_size < 150:
        return range(3, 7)
    if sample_size < 300:
        return range(4, 9)
    return range(5, 11)


def _sample_vectors(vectors: np.ndarray, ratio: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    if ratio >= 0.999:
        indices = np.arange(len(vectors))
        return vectors, indices

    sample_size = max(2, int(math.ceil(len(vectors) * ratio)))
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(len(vectors), size=sample_size, replace=False))
    return vectors[indices], indices


def _fragmentation_penalty(labels: list[int], sample_size: int) -> float:
    if sample_size <= 0:
        return 1.0

    tiny_threshold = max(8, int(math.ceil(sample_size * 0.05)))
    counts: dict[int, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1

    tiny_points = sum(count for count in counts.values() if count < tiny_threshold)
    return tiny_points / sample_size


def _evaluate_candidate(vectors: np.ndarray, k: int) -> dict[str, Any] | None:
    runs: list[dict[str, Any]] = []

    for ratio, seed in RUN_CONFIGS:
        sample_vectors, indices = _sample_vectors(vectors, ratio, seed)
        if len(sample_vectors) <= k:
            continue

        labels = cluster_reviews(
            sample_vectors,
            method="kmeans",
            n_clusters=k,
            random_state=seed
        )

        if len(set(labels)) < 2:
            continue

        separation = float(silhouette_score(sample_vectors, labels))
        fragmentation = _fragmentation_penalty(labels, len(sample_vectors))
        runs.append({
            "indices": indices,
            "labels": labels,
            "separation": separation,
            "fragmentation": fragmentation
        })

    if len(runs) < 2:
        return None

    ari_scores: list[float] = []
    for left, right in combinations(runs, 2):
        shared = np.intersect1d(left["indices"], right["indices"])
        if len(shared) < max(2, k):
            continue

        left_map = {idx: label for idx, label in zip(left["indices"], left["labels"])}
        right_map = {idx: label for idx, label in zip(right["indices"], right["labels"])}

        left_labels = [left_map[idx] for idx in shared]
        right_labels = [right_map[idx] for idx in shared]
        ari_scores.append(float(adjusted_rand_score(left_labels, right_labels)))

    if not ari_scores:
        return None

    separation_values = [run["separation"] for run in runs]
    fragmentation_values = [run["fragmentation"] for run in runs]
    score = (
        0.55 * float(np.median(separation_values))
        + 0.35 * float(np.mean(ari_scores))
        - 0.10 * float(np.mean(fragmentation_values))
    )

    return {
        "k": k,
        "score": score,
        "median_separation": float(np.median(separation_values)),
        "mean_stability": float(np.mean(ari_scores)),
        "mean_fragmentation": float(np.mean(fragmentation_values))
    }
```

Append the rest of `python/topic_recommendation.py`:

```python
def _normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}

    lo = min(scores.values())
    hi = max(scores.values())
    if math.isclose(lo, hi):
        return {k: 1.0 for k in scores}

    return {k: (value - lo) / (hi - lo) for k, value in scores.items()}


def _fallback(total_selected_reviews: int) -> dict[str, Any]:
    effective_k = max(2, min(8, round(math.sqrt(max(total_selected_reviews, 1)) / 2)))
    return {
        "effective_k": effective_k,
        "confidence": "low",
        "reason": "Insufficient stable signal; using conservative heuristic",
        "details": {
            "candidate_range": [],
            "group_sample_counts": {},
            "scores": {},
            "used_fallback": True
        },
        "used_fallback": True
    }


def recommend_topic_count(group_vectors: dict[str, np.ndarray], total_selected_reviews: int) -> dict[str, Any]:
    eligible: dict[str, np.ndarray] = {}
    sampled_counts: dict[str, int] = {}

    for group_name, vectors in group_vectors.items():
        if len(vectors) < 20:
            continue

        if len(vectors) > MAX_SAMPLE_PER_GROUP:
            rng = np.random.default_rng(42)
            indices = np.sort(rng.choice(len(vectors), size=MAX_SAMPLE_PER_GROUP, replace=False))
            sampled = vectors[indices]
        else:
            sampled = vectors

        eligible[group_name] = sampled
        sampled_counts[group_name] = len(sampled)

    if not eligible:
        return _fallback(total_selected_reviews)

    group_scores: dict[str, dict[int, float]] = {}
    score_details: dict[str, dict[int, dict[str, float]]] = {}
    candidate_values: set[int] = set()

    for group_name, vectors in eligible.items():
        evaluations = {}
        group_detail = {}
        for k in candidate_range_for_size(len(vectors)):
            result = _evaluate_candidate(vectors, k)
            if result is None:
                continue
            evaluations[k] = result["score"]
            group_detail[k] = {
                "score": result["score"],
                "median_separation": result["median_separation"],
                "mean_stability": result["mean_stability"],
                "mean_fragmentation": result["mean_fragmentation"]
            }
            candidate_values.add(k)

        if evaluations:
            group_scores[group_name] = _normalize_scores(evaluations)
            score_details[group_name] = group_detail

    if not group_scores:
        return _fallback(total_selected_reviews)

    weighted_scores: dict[int, float] = {}
    total_weight = sum(len(vectors) for vectors in eligible.values())
    for group_name, normalized_scores in group_scores.items():
        weight = len(eligible[group_name]) / total_weight
        for k, score in normalized_scores.items():
            weighted_scores[k] = weighted_scores.get(k, 0.0) + (weight * score)

    ordered = sorted(weighted_scores.items(), key=lambda item: (-item[1], item[0]))
    best_k, best_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else best_score
    margin = best_score - second_score

    if len(ordered) > 1 and margin < 0.03:
        top_score = ordered[0][1]
        tied = [k for k, score in ordered if (top_score - score) < 0.03]
        best_k = min(tied)

    if margin >= 0.12:
        confidence = "high"
    elif margin >= 0.05:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "effective_k": best_k,
        "confidence": confidence,
        "reason": "Best balance of separation and stability across tested k values",
        "details": {
            "candidate_range": sorted(candidate_values),
            "group_sample_counts": sampled_counts,
            "scores": score_details,
            "used_fallback": False
        },
        "used_fallback": False
    }
```

- [ ] **Step 5: Re-run the Python tests**

Run:

```bash
python/.venv/Scripts/python.exe -m pytest tests/python/test_clustering.py tests/python/test_topic_recommendation.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add python/clustering.py python/topic_recommendation.py tests/python/test_clustering.py tests/python/test_topic_recommendation.py
git commit -m "feat(python): add stability-based topic count recommendation"
```

---

### Task 3: Wire the recommendation engine into the analyzer and return metadata

**Files:**
- Modify: `python/analyzer.py`
- Create: `tests/python/test_analyzer.py`

- [ ] **Step 1: Write the failing analyzer tests**

Create `tests/python/test_analyzer.py`:

```python
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd() / "python"))

import analyzer


def make_reviews(count: int, voted_up: bool) -> list[dict]:
    return [
        {
            "id": f"{'p' if voted_up else 'n'}-{idx}",
            "text": f"{'good' if voted_up else 'bad'} review {idx}",
            "voted_up": voted_up,
            "language": "en",
            "playtime": 100
        }
        for idx in range(count)
    ]


def test_run_analysis_uses_recommended_k_in_auto_mode(monkeypatch):
    reviews = make_reviews(6, True) + make_reviews(6, False)
    recorded = []

    monkeypatch.setattr(analyzer, "generate_embeddings", lambda params, msg_id: {
        "embeddings": np.tile(np.array([[0.0, 0.0]]), (len(params["texts"]), 1)).tolist(),
        "model": "stub-model"
    })
    monkeypatch.setattr(analyzer, "recommend_topic_count", lambda groups, total_selected_reviews: {
        "effective_k": 4,
        "confidence": "medium",
        "reason": "stub reason",
        "details": {"candidate_range": [3, 4, 5], "used_fallback": False},
        "used_fallback": False
    })
    monkeypatch.setattr(analyzer, "_analyze_group", lambda texts, embeddings, method, n_topics, tier: recorded.append((method, n_topics, tier, len(texts))) or [{
        "id": 0,
        "keywords": [{"word": "stub", "score": 1.0}],
        "label": "stub",
        "review_count": len(texts),
        "sample_reviews": texts[:2]
    }])

    result = analyzer.run_analysis({
        "reviews": reviews,
        "config": {"tier": 0, "topicCountMode": "auto", "n_topics": 8}
    }, "msg-auto")

    assert recorded == [("kmeans", 4, 0, 6), ("kmeans", 4, 0, 6)]
    assert result["effective_k"] == 4
    assert result["topic_count_mode"] == "auto"
    assert result["recommendation_confidence"] == "medium"
```

Append this second test to `tests/python/test_analyzer.py`:

```python
def test_run_analysis_uses_manual_topic_count_without_recommender(monkeypatch):
    reviews = make_reviews(6, True) + make_reviews(6, False)
    recorded = []

    monkeypatch.setattr(analyzer, "generate_embeddings", lambda params, msg_id: {
        "embeddings": np.tile(np.array([[0.0, 0.0]]), (len(params["texts"]), 1)).tolist(),
        "model": "stub-model"
    })
    monkeypatch.setattr(analyzer, "recommend_topic_count", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("recommender should not run")))
    monkeypatch.setattr(analyzer, "_analyze_group", lambda texts, embeddings, method, n_topics, tier: recorded.append((method, n_topics, tier, len(texts))) or [])

    result = analyzer.run_analysis({
        "reviews": reviews,
        "config": {"tier": 0, "topicCountMode": "manual", "n_topics": 5}
    }, "msg-manual")

    assert recorded == [("kmeans", 5, 0, 6), ("kmeans", 5, 0, 6)]
    assert result["requested_k"] == 5
    assert result["effective_k"] == 5
    assert result["recommendation_reason"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py -v
```

Expected: FAIL because `analyzer.py` does not call the recommender or return the new metadata fields.

- [ ] **Step 3: Implement analyzer wiring**

Replace `python/analyzer.py` with:

```python
import sys
import numpy as np

from protocol import format_progress
from embeddings import generate_embeddings
from clustering import cluster_reviews
from keywords import extract_topic_keywords
from topic_recommendation import recommend_topic_count


def run_analysis(params: dict, msg_id: str) -> dict:
    """Full analysis pipeline: embed -> recommend topic count (optional) -> cluster -> extract keywords."""
    reviews = params.get("reviews", [])
    config = params.get("config", {})
    tier = config.get("tier", 0)
    topic_count_mode = config.get("topicCountMode", "manual")
    requested_k = config.get("n_topics") if topic_count_mode == "manual" else None
    default_topics = config.get("n_topics", 8)

    if not reviews:
        return {
            "positive_topics": [],
            "negative_topics": [],
            "topic_count_mode": topic_count_mode,
            "requested_k": requested_k,
            "effective_k": None,
            "recommendation_confidence": None,
            "recommendation_reason": None,
            "recommendation_details": None
        }

    def progress(pct, msg, stage=None, elapsed_ms=None):
        sys.stdout.write(format_progress(msg_id, pct, msg, stage=stage, elapsed_ms=elapsed_ms) + "\n")
        sys.stdout.flush()

    positive = [r for r in reviews if r["voted_up"]]
    negative = [r for r in reviews if not r["voted_up"]]

    progress(5, "Generating embeddings...", stage="embedding")

    all_texts = [r["text"] for r in reviews]
    emb_result = generate_embeddings({"texts": all_texts, "tier": tier}, msg_id)
    all_embeddings = np.array(emb_result["embeddings"])

    pos_indices = [i for i, r in enumerate(reviews) if r["voted_up"]]
    neg_indices = [i for i, r in enumerate(reviews) if not r["voted_up"]]

    pos_embeddings = all_embeddings[pos_indices] if pos_indices else np.array([])
    neg_embeddings = all_embeddings[neg_indices] if neg_indices else np.array([])

    recommendation = None
    effective_k = None

    if tier == 0 and topic_count_mode == "auto":
        progress(65, "Calculating recommended topic count...", stage="recommendation")
        recommendation = recommend_topic_count({
            "positive": pos_embeddings,
            "negative": neg_embeddings
        }, total_selected_reviews=len(reviews))
        effective_k = recommendation["effective_k"]
    elif tier == 0:
        effective_k = default_topics

    progress(75, "Clustering reviews...", stage="clustering")

    method = "hdbscan" if tier >= 1 else "kmeans"
    topic_count = effective_k if effective_k is not None else default_topics

    pos_topics = _analyze_group(
        [r["text"] for r in positive],
        pos_embeddings,
        method,
        topic_count,
        tier
    ) if positive else []

    progress(90, "Extracting keywords...", stage="keywords")

    neg_topics = _analyze_group(
        [r["text"] for r in negative],
        neg_embeddings,
        method,
        topic_count,
        tier
    ) if negative else []

    progress(100, "Analysis complete", stage="complete")

    return {
        "model": emb_result["model"],
        "tier": tier,
        "total_reviews": len(reviews),
        "positive_count": len(positive),
        "negative_count": len(negative),
        "positive_topics": pos_topics,
        "negative_topics": neg_topics,
        "topic_count_mode": topic_count_mode,
        "requested_k": requested_k,
        "effective_k": effective_k if tier == 0 else None,
        "recommendation_confidence": recommendation["confidence"] if recommendation else None,
        "recommendation_reason": recommendation["reason"] if recommendation else None,
        "recommendation_details": recommendation["details"] if recommendation else None
    }


def _analyze_group(texts, embeddings, method, n_topics, tier):
    if len(texts) < 2:
        return []

    labels = cluster_reviews(
        embeddings,
        method=method,
        n_clusters=min(n_topics, len(texts)),
        min_cluster_size=3
    )

    topic_keywords = extract_topic_keywords(
        texts, labels, tier=tier,
        embeddings=embeddings if tier >= 1 else None
    )

    topics = []
    for topic_id, keywords in sorted(topic_keywords.items()):
        topic_texts = [t for t, l in zip(texts, labels) if l == topic_id]
        topics.append({
            "id": topic_id,
            "keywords": [{"word": kw, "score": round(sc, 3)} for kw, sc in keywords],
            "label": ", ".join(kw for kw, _ in keywords[:3]),
            "review_count": len(topic_texts),
            "sample_reviews": topic_texts[:5]
        })

    topics.sort(key=lambda t: t["review_count"], reverse=True)
    return topics
```

- [ ] **Step 4: Re-run the analyzer tests**

Run:

```bash
python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/analyzer.py tests/python/test_analyzer.py
git commit -m "feat(analyzer): compute recommended topic counts in auto mode"
```

---

### Task 4: Use normalized configs and exact cache hits in the main IPC handler

**Files:**
- Modify: `src/main/ipc-handlers.ts`

- [ ] **Step 1: Add a cache-hit fast path before invoking the sidecar**

Update the imports at the top of `src/main/ipc-handlers.ts`:

```ts
import { insertGame, getGame, getAllGames, deleteGame, getGameStats, upsertReviews, getReviews, saveAnalysisCache, getAnalysisCache } from './db'
import { buildAnalysisCacheHash } from './analysis-cache'
```

Then replace the `analysis:run` handler body with this version:

```ts
  ipcMain.handle('analysis:run', async (_event, appId: number, config: Record<string, unknown>) => {
    const win = getMainWindow()
    const sendProgress = async (message: string): Promise<void> => {
      win?.webContents.send('progress', { type: 'analysis', appId, stage: 'idle', percent: 0, message })
      await new Promise(resolve => setImmediate(resolve))
    }

    const settings = loadSettings()
    const detectedTier = settings.tier === 'auto'
      ? Number(((await sidecar.send('detect_gpu')) as { recommended_tier?: unknown })?.recommended_tier ?? 0)
      : 0
    const analysisConfig = resolveAnalysisConfig(config, settings, detectedTier)
    const configHash = buildAnalysisCacheHash(analysisConfig)

    const cached = getAnalysisCache(db, appId, 'topics', configHash)
    if (cached) {
      return JSON.parse(cached)
    }

    await sendProgress('Loading reviews from database...')

    let reviews = getReviews(db, appId, analysisConfig.filter as Parameters<typeof getReviews>[2])
    const totalAvailable = reviews.length
    const maxReviews = analysisConfig.maxReviews as number | undefined
    if (maxReviews && reviews.length > maxReviews) {
      reviews = reviews.slice(0, maxReviews)
    }

    const reviewData = reviews.map(r => ({
      id: r.recommendation_id,
      text: r.review_text,
      voted_up: r.voted_up === 1,
      language: r.language,
      playtime: r.playtime_at_review
    }))

    await sendProgress(`Sending ${reviewData.length.toLocaleString()} reviews to analysis engine...`)

    const result = await sidecar.send('analyze', { reviews: reviewData, config: analysisConfig }, (progress) => {
      win?.webContents.send('progress', { type: 'analysis', appId, ...progress })
    }) as Record<string, unknown>

    const finalResult = {
      ...result,
      total_available: totalAvailable,
      sampled: reviews.length < totalAvailable
    }

    const langFilter = (analysisConfig.filter as Record<string, unknown> | undefined)?.language as string ?? 'all'
    saveAnalysisCache(db, appId, 'topics', langFilter, configHash, JSON.stringify(finalResult))

    return finalResult
  })
```

- [ ] **Step 2: Run the main-process tests again**

Run:

```bash
npx vitest run tests/main/analysis-settings.test.ts tests/main/analysis-cache.test.ts
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/main/ipc-handlers.ts
git commit -m "feat(main): reuse exact cached analysis results by mode and filter"
```

---

### Task 5: Add renderer controls for auto/manual topic counts and recommendation progress

**Files:**
- Create: `src/renderer/src/components/TopicCountModeControl.tsx`
- Modify: `src/renderer/src/components/AnalysisProgress.tsx`
- Modify: `src/renderer/src/components/TopicAnalysis.tsx`
- Modify: `src/renderer/src/assets/styles.css`
- Create: `tests/main/topic-count-mode-control.test.tsx`
- Create: `tests/main/analysis-progress.test.tsx`

- [ ] **Step 1: Write the failing renderer tests**

Create `tests/main/topic-count-mode-control.test.tsx`:

```tsx
import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { TopicCountModeControl } from '../../src/renderer/src/components/TopicCountModeControl'

describe('TopicCountModeControl', () => {
  it('shows the numeric input only in Tier 0 manual mode', () => {
    const html = renderToStaticMarkup(
      <TopicCountModeControl
        tier={0}
        mode="manual"
        nTopics={7}
        disabled={false}
        onModeChange={vi.fn()}
        onTopicCountChange={vi.fn()}
      />
    )

    expect(html).toContain('Auto (recommended)')
    expect(html).toContain('Manual')
    expect(html).toContain('type="number"')
  })

  it('locks the control to auto mode on Tier 1', () => {
    const html = renderToStaticMarkup(
      <TopicCountModeControl
        tier={1}
        mode="auto"
        nTopics={7}
        disabled={false}
        onModeChange={vi.fn()}
        onTopicCountChange={vi.fn()}
      />
    )

    expect(html).toContain('Auto by HDBSCAN on Tier 1')
    expect(html).not.toContain('type="number"')
  })
})
```

Create `tests/main/analysis-progress.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { AnalysisProgress } from '../../src/renderer/src/components/AnalysisProgress'

describe('AnalysisProgress', () => {
  it('renders the recommendation stage for auto Tier 0 runs', () => {
    const html = renderToStaticMarkup(
      <AnalysisProgress
        data={{ stage: 'recommendation', percent: 68, message: 'Calculating recommended topic count...', elapsed_ms: 0 }}
        includeRecommendationStage={true}
      />
    )

    expect(html).toContain('Recommendation')
    expect(html).toContain('Calculating recommended topic count...')
  })

  it('omits the recommendation stage when it is not part of the run', () => {
    const html = renderToStaticMarkup(
      <AnalysisProgress
        data={{ stage: 'clustering', percent: 75, message: 'Clustering reviews...', elapsed_ms: 0 }}
        includeRecommendationStage={false}
      />
    )

    expect(html).not.toContain('Recommendation')
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
npx vitest run tests/main/topic-count-mode-control.test.tsx tests/main/analysis-progress.test.tsx
```

Expected: FAIL because `TopicCountModeControl.tsx` does not exist and `AnalysisProgress` does not accept `includeRecommendationStage`.

- [ ] **Step 3: Create the mode-control component**

Create `src/renderer/src/components/TopicCountModeControl.tsx`:

```tsx
type TopicCountMode = 'auto' | 'manual'

interface TopicCountModeControlProps {
  tier: number | null
  mode: TopicCountMode
  nTopics: number
  disabled: boolean
  onModeChange: (mode: TopicCountMode) => void
  onTopicCountChange: (value: number) => void
}

export function TopicCountModeControl({
  tier,
  mode,
  nTopics,
  disabled,
  onModeChange,
  onTopicCountChange
}: TopicCountModeControlProps) {
  if (tier === null) {
    return <div className="topic-count-hint">Checking analysis tier...</div>
  }

  if (tier >= 1) {
    return <div className="topic-count-hint">Auto by HDBSCAN on Tier 1</div>
  }

  return (
    <>
      <label>
        Topic count mode:
        <select
          value={mode}
          disabled={disabled}
          onChange={e => onModeChange(e.target.value as TopicCountMode)}
        >
          <option value="auto">Auto (recommended)</option>
          <option value="manual">Manual</option>
        </select>
      </label>

      {mode === 'manual' ? (
        <label>
          Topics per group:
          <input
            type="number"
            min={2}
            max={20}
            value={nTopics}
            disabled={disabled}
            onChange={e => onTopicCountChange(Number(e.target.value))}
          />
        </label>
      ) : (
        <div className="topic-count-hint">
          Recommended during analysis using separation and stability scoring.
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 4: Update the progress component**

Replace `src/renderer/src/components/AnalysisProgress.tsx` with:

```tsx
const BASE_STAGES = ['embedding', 'clustering', 'keywords'] as const
const AUTO_STAGES = ['embedding', 'recommendation', 'clustering', 'keywords'] as const
type Stage = typeof AUTO_STAGES[number]

const STAGE_LABELS: Record<Stage, string> = {
  embedding: 'Embedding',
  recommendation: 'Recommendation',
  clustering: 'Clustering',
  keywords: 'Keywords'
}

export interface ProgressData {
  stage: 'idle' | Stage | 'complete'
  percent: number
  message: string
  elapsed_ms: number
}

function getStageState(stages: readonly Stage[], stage: Stage, current: ProgressData['stage']): 'pending' | 'active' | 'completed' {
  if (current === 'complete') return 'completed'
  const currentIdx = stages.indexOf(current as Stage)
  const stageIdx = stages.indexOf(stage)
  if (currentIdx < 0) return 'pending'
  if (stageIdx < currentIdx) return 'completed'
  if (stageIdx === currentIdx) return 'active'
  return 'pending'
}

function parseEmbeddingCounts(message: string): { processed: number; total: number } | null {
  const match = message.match(/Embedded (\d[\d,]*)\s*\/\s*(\d[\d,]*)/)
  if (!match) return null
  return {
    processed: parseInt(match[1].replace(/,/g, ''), 10),
    total: parseInt(match[2].replace(/,/g, ''), 10)
  }
}

function computeEta(elapsed_ms: number, processed: number, total: number): string | null {
  if (processed < 192 || elapsed_ms <= 0) return null
  const remaining = total - processed
  if (remaining <= 0) return null
  const etaMs = (elapsed_ms / processed) * remaining
  if (etaMs < 5000) return 'Almost done...'
  const etaSec = Math.round(etaMs / 1000)
  if (etaSec >= 60) {
    const min = Math.floor(etaSec / 60)
    const sec = etaSec % 60
    return `ETA ${min}m ${sec}s`
  }
  return `ETA ${etaSec}s`
}

export function AnalysisProgress({
  data,
  includeRecommendationStage
}: {
  data: ProgressData
  includeRecommendationStage: boolean
}) {
  const stages = includeRecommendationStage ? AUTO_STAGES : BASE_STAGES
  const counts = data.stage === 'embedding' ? parseEmbeddingCounts(data.message) : null
  const eta = counts ? computeEta(data.elapsed_ms, counts.processed, counts.total) : null

  return (
    <div className="analysis-progress">
      <div className="progress-steps">
        {stages.map((stage, i) => {
          const state = getStageState(stages, stage, data.stage)
          return (
            <div key={stage} className={`progress-step ${state}`}>
              <span className="step-icon">
                {state === 'completed' ? '✓' : state === 'active' ? '●' : '○'}
              </span>
              <span className="step-label">{STAGE_LABELS[stage]}</span>
              {i < stages.length - 1 && <span className="step-arrow">→</span>}
            </div>
          )
        })}
      </div>

      {data.stage === 'embedding' && counts ? (
        <>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${Math.min(data.percent, 100)}%` }} />
          </div>
          <div className="progress-detail">
            <span>Embedded {counts.processed.toLocaleString()} / {counts.total.toLocaleString()} reviews</span>
            {eta && <span className="progress-eta">{eta}</span>}
          </div>
        </>
      ) : (
        data.message && (
          <div className="progress-detail">
            <span className="progress-spinner" />
            <span>{data.message}</span>
          </div>
        )
      )}
    </div>
  )
}
```

- [ ] **Step 5: Update `TopicAnalysis.tsx`**

Replace the local interfaces and state setup in `src/renderer/src/components/TopicAnalysis.tsx` with:

```tsx
import { useEffect, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { AnalysisProgress, ProgressData } from './AnalysisProgress'
import { TopicCountModeControl } from './TopicCountModeControl'
import { estimateLocalAnalysisMinutes } from '../lib/analysis-timing'

export interface Topic {
  id: number
  label: string
  keywords: { word: string; score: number }[]
  review_count: number
  sample_reviews: string[]
}

export interface AnalysisResult {
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
  effective_k?: number | null
  recommendation_confidence?: 'high' | 'medium' | 'low' | null
  recommendation_reason?: string | null
  recommendation_details?: Record<string, unknown> | null
}

export function TopicAnalysis({ appId, onAnalysisComplete }: TopicAnalysisProps) {
  const api = useApi()
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<ProgressData>({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
  const [error, setError] = useState<string | null>(null)
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [topicCountMode, setTopicCountMode] = useState<'auto' | 'manual'>('auto')
  const [nTopics, setNTopics] = useState(8)
  const [reviewLimit, setReviewLimit] = useState<'all' | number>('all')
  const [totalReviews, setTotalReviews] = useState(0)
  const [resolvedTier, setResolvedTier] = useState<number | null>(null)
}
```

Replace the `useEffect` that resets state on app change with:

```tsx
  useEffect(() => {
    let cancelled = false

    async function loadTier() {
      const settings = await api.getSettings() as { tier?: 'auto' | '0' | '1' }
      if (settings?.tier === '0') {
        if (!cancelled) setResolvedTier(0)
        return
      }
      if (settings?.tier === '1') {
        if (!cancelled) {
          setResolvedTier(1)
          setTopicCountMode('auto')
        }
        return
      }

      const gpuInfo = await api.detectGpu().catch(() => ({ recommended_tier: 0 })) as { recommended_tier?: number }
      const tier = Number(gpuInfo?.recommended_tier ?? 0)
      if (!cancelled) {
        setResolvedTier(tier)
        if (tier >= 1) setTopicCountMode('auto')
      }
    }

    setResult(null)
    setError(null)
    setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
    setResolvedTier(null)
    onAnalysisComplete(null)
    api.getGameStats(appId).then((stats: any) => {
      if (!cancelled) setTotalReviews(stats.total_collected ?? 0)
    })
    api.getCachedAnalysis(appId).then((cached: any) => {
      if (!cancelled && cached) {
        setResult(cached)
        onAnalysisComplete(cached)
      }
    })
    loadTier()

    return () => { cancelled = true }
  }, [appId])
```

Replace `runAnalysis` with:

```tsx
  const effectiveCount = reviewLimit === 'all' ? totalReviews : Math.min(reviewLimit, totalReviews)
  const effectiveMinutes = estimateLocalAnalysisMinutes(effectiveCount)
  const includeRecommendationStage = resolvedTier === 0 && topicCountMode === 'auto'

  const runAnalysis = async () => {
    if (resolvedTier === null) return

    setLoading(true)
    setError(null)
    setProgress({ stage: 'idle', percent: 0, message: 'Starting analysis...', elapsed_ms: 0 })

    try {
      const config: Record<string, unknown> = { topicCountMode }
      if (topicCountMode === 'manual') {
        config.n_topics = nTopics
      }
      if (reviewLimit !== 'all') {
        config.maxReviews = reviewLimit
      }
      const res = await api.runAnalysis(appId, config) as AnalysisResult
      setResult(res)
      onAnalysisComplete(res)
    } catch (e) {
      console.error(e)
      setError(e instanceof Error ? e.message : 'Analysis failed. Check the developer console for details.')
    } finally {
      setLoading(false)
      setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
    }
  }
```

Replace the controls, progress area, and metadata JSX with:

```tsx
      <div className="analysis-controls">
        <TopicCountModeControl
          tier={resolvedTier}
          mode={topicCountMode}
          nTopics={nTopics}
          disabled={loading}
          onModeChange={mode => setTopicCountMode(mode)}
          onTopicCountChange={value => setNTopics(value)}
        />
        <label>
          Reviews to analyze:
          <select
            value={reviewLimit === 'all' ? 'all' : String(reviewLimit)}
            onChange={e => setReviewLimit(e.target.value === 'all' ? 'all' : Number(e.target.value))}
          >
            <option value="all">All ({totalReviews.toLocaleString()})</option>
            <option value="1000">1,000</option>
            <option value="3000">3,000</option>
            <option value="5000">5,000</option>
            <option value="10000">10,000</option>
          </select>
        </label>
        <button onClick={runAnalysis} disabled={loading || resolvedTier === null}>
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>

      {!loading && effectiveCount > 3000 && (
        <div className="analysis-warning">
          Analyzing {effectiveCount.toLocaleString()} reviews may take approximately <strong>{effectiveMinutes} min</strong> on CPU. You can reduce the count above for faster results.
        </div>
      )}

      {error && (
        <div className="analysis-error">
          <strong>Analysis Error:</strong> {error}
        </div>
      )}

      {loading && <AnalysisProgress data={progress} includeRecommendationStage={includeRecommendationStage} />}

      {result && (
        <div className="analysis-meta">
          <span>Model: {result.model}</span>
          <span>Tier: {result.tier}</span>
          <span>Mode: {result.topic_count_mode ?? 'manual'}</span>
          <span>Topic count: {result.effective_k ?? 'Auto by HDBSCAN'}</span>
          {result.recommendation_confidence && <span>Confidence: {result.recommendation_confidence}</span>}
          {result.recommendation_reason && <span>{result.recommendation_reason}</span>}
          <span>
            Reviews: {result.total_reviews.toLocaleString()}
            {result.sampled ? ` (sampled from ${result.total_available?.toLocaleString()})` : ''}
          </span>
        </div>
      )}
```

- [ ] **Step 6: Add matching CSS**

Append these rules near the existing `.analysis-controls` block in `src/renderer/src/assets/styles.css`:

```css
.analysis-controls select {
  min-width: 160px;
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: white;
}

.topic-count-hint {
  font-size: 12px;
  color: #6b7280;
  max-width: 260px;
  line-height: 1.4;
}

.analysis-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.analysis-meta span {
  background: #f5f3ff;
  color: #5b21b6;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
}
```

- [ ] **Step 7: Run the renderer tests and typecheck**

Run:

```bash
npx vitest run tests/main/topic-count-mode-control.test.tsx tests/main/analysis-progress.test.tsx
npx tsc --noEmit -p tsconfig.web.json --composite false
```

Expected: PASS for both test files and no TypeScript errors.

- [ ] **Step 8: Commit**

```bash
git add src/renderer/src/components/TopicCountModeControl.tsx src/renderer/src/components/AnalysisProgress.tsx src/renderer/src/components/TopicAnalysis.tsx src/renderer/src/assets/styles.css tests/main/topic-count-mode-control.test.tsx tests/main/analysis-progress.test.tsx
git commit -m "feat(renderer): add auto topic-count controls and recommendation progress"
```

---

### Task 6: Run full verification and manual QA

- [ ] **Step 1: Run all focused automated checks**

Run:

```bash
npx vitest run tests/main/analysis-settings.test.ts tests/main/analysis-cache.test.ts tests/main/topic-count-mode-control.test.tsx tests/main/analysis-progress.test.tsx
python/.venv/Scripts/python.exe -m pytest tests/python/test_clustering.py tests/python/test_topic_recommendation.py tests/python/test_analyzer.py -v
npx tsc --noEmit -p tsconfig.node.json --composite false
npx tsc --noEmit -p tsconfig.web.json --composite false
```

Expected: PASS across all commands.

- [ ] **Step 2: Smoke-test the Python analyzer from the command line**

Run:

```bash
echo '{"id":"t","method":"analyze","params":{"reviews":[{"id":"1","text":"great performance","voted_up":true,"language":"en","playtime":100},{"id":"2","text":"great controls","voted_up":true,"language":"en","playtime":120},{"id":"3","text":"bad matchmaking","voted_up":false,"language":"en","playtime":40},{"id":"4","text":"bad servers","voted_up":false,"language":"en","playtime":35}],"config":{"tier":0,"topicCountMode":"auto"}}}' | python/.venv/Scripts/python.exe python/main.py
```

Expected: Progress JSON includes `"stage":"recommendation"` after embedding, and the final result includes `topic_count_mode`, `effective_k`, and `recommendation_reason`.

- [ ] **Step 3: Perform manual UI verification in development mode**

Run:

```bash
pnpm dev
```

Verify in the app:

- Tier 0 shows `Auto (recommended)` and `Manual`
- Switching to `Manual` reveals the numeric input
- Auto runs show the `Recommendation` step in the progress pipeline
- Manual runs skip the `Recommendation` step
- Tier 1 shows `Auto by HDBSCAN on Tier 1` and does not offer the numeric input
- Completed Tier 0 auto results show `Topic count`, `Confidence`, and the recommendation reason

- [ ] **Step 4: Verify cache reuse manually**

In the running app:

- Run the same Tier 0 auto analysis twice without changing game, review limit, or mode
- Confirm the second run returns immediately from cache
- Change mode to `Manual` or change review count and confirm the analysis runs again instead of reusing the old result

- [ ] **Step 5: Final commit for any verification fixes**

```bash
git add -A
git commit -m "fix: address auto topic recommendation follow-up issues"
```
```
