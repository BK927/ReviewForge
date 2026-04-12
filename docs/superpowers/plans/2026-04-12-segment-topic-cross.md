# Feature 3: Segment × Topic Cross-Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show how topic distributions vary across player segments (playtime, language, platform, purchase type) so users can answer questions like "what do 50h+ players complain about?"

**Architecture:** The existing pipeline clusters positive and negative reviews separately. Rather than re-clustering globally, we reuse the per-sentiment cluster labels and compute per-segment topic distributions. This requires (1) extending the review data sent to Python with segment metadata, (2) returning cluster labels from `_analyze_group()`, (3) a new `segment_topics.py` module that computes the cross-analysis matrix, and (4) a frontend heatmap component on the Segments tab.

**Tech Stack:** Python (NumPy), TypeScript (Electron IPC), React, ECharts heatmap, Vitest, pytest

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/main/ipc-handlers.ts:128-134` | Add `steam_deck`, `steam_purchase`, `timestamp` to reviewData |
| Modify | `python/analyzer.py:167-221` | Return labels from `_analyze_group()`, call cross-analysis |
| Create | `python/segment_topics.py` | `compute_segment_topic_cross()` pure function |
| Create | `tests/python/test_segment_topics.py` | Tests for segment × topic cross-analysis |
| Modify | `tests/python/test_analyzer.py` | Update for 3-tuple return + cross-analysis in result |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx:16-47` | Add `segment_topic_cross` to `AnalysisResult` |
| Modify | `src/renderer/src/App.tsx:26` | Pass `analysisResult` prop to SegmentAnalysis |
| Modify | `src/renderer/src/components/SegmentAnalysis.tsx` | Accept `analysisResult` prop, render cross-analysis |
| Create | `src/renderer/src/components/SegmentTopicHeatmap.tsx` | ECharts heatmap for segment × topic matrix |

---

### Task 1: Extend review data sent to Python sidecar

**Files:**
- Modify: `src/main/ipc-handlers.ts:128-134`

- [ ] **Step 1: Add segment metadata fields to reviewData**

In `src/main/ipc-handlers.ts`, find the `reviewData` mapping (line 128-134):

```typescript
    const reviewData = reviews.map(r => ({
      id: r.recommendation_id,
      text: r.review_text,
      voted_up: r.voted_up === 1,
      language: r.language,
      playtime: r.playtime_at_review
    }))
```

Replace with:

```typescript
    const reviewData = reviews.map(r => ({
      id: r.recommendation_id,
      text: r.review_text,
      voted_up: r.voted_up === 1,
      language: r.language,
      playtime: r.playtime_at_review,
      steam_deck: r.primarily_steam_deck === 1,
      steam_purchase: r.steam_purchase === 1,
      timestamp: r.timestamp_created
    }))
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/main/ipc-handlers.ts
git commit -m "feat(ipc): pass segment metadata fields to Python sidecar"
```

---

### Task 2: Return labels from `_analyze_group()`

**Files:**
- Modify: `python/analyzer.py:123-140,167-221`
- Modify: `tests/python/test_analyzer.py`

- [ ] **Step 1: Update `_analyze_group()` to return labels**

In `python/analyzer.py`, modify `_analyze_group()` (line 167). Change the early return and the final return to include `labels`:

Replace the function:

```python
def _analyze_group(texts, embeddings, method, n_topics, tier, merge_threshold=0.80):
    if len(texts) < 2:
        return [], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []}, []

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

    # Compute centroids for representative review selection
    centroids = compute_centroids(embeddings, labels)

    topics = []
    for topic_id, keywords in sorted(topic_keywords.items()):
        indices = [i for i, l in enumerate(labels) if l == topic_id]
        topic_texts = [texts[i] for i in indices]
        # Prefer bigram+ keyphrases for label
        bigram_kws = [kw for kw, _ in keywords if " " in kw]
        unigram_kws = [kw for kw, _ in keywords if " " not in kw]
        label_parts = (bigram_kws + unigram_kws)[:3]
        label = ", ".join(label_parts) if label_parts else f"Topic {topic_id}"

        # Find representative review: closest to centroid by cosine similarity
        representative_review = topic_texts[0]  # fallback
        if topic_id in centroids and len(indices) > 0:
            centroid = centroids[topic_id]
            topic_embeddings = embeddings[indices]
            # Cosine similarity: dot(a, b) / (||a|| * ||b||)
            norms = np.linalg.norm(topic_embeddings, axis=1) * np.linalg.norm(centroid)
            norms = np.where(norms < 1e-12, 1.0, norms)
            similarities = topic_embeddings @ centroid / norms
            best_idx = int(np.argmax(similarities))
            representative_review = topic_texts[best_idx]

        topics.append({
            "id": topic_id,
            "keywords": [{"word": kw, "score": round(sc, 3)} for kw, sc in keywords],
            "label": label,
            "review_count": len(topic_texts),
            "representative_review": representative_review,
            "sample_reviews": topic_texts[:5]
        })

    topics.sort(key=lambda t: t["review_count"], reverse=True)
    return topics, merge_info, labels
```

- [ ] **Step 2: Update callers in `run_analysis()`**

In `python/analyzer.py`, update the empty-case fallbacks (lines 123-127 and 131-135):

Replace the positive call (line 123-127):

```python
    pos_topics = _analyze_group(
        [r["text"] for r in positive], pos_embeddings,
        method, positive_k if positive_k is not None else n_topics, tier,
        merge_threshold
    ) if positive else ([], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []}, [])
```

Replace the negative call (line 131-135):

```python
    neg_topics = _analyze_group(
        [r["text"] for r in negative], neg_embeddings,
        method, negative_k if negative_k is not None else n_topics, tier,
        merge_threshold
    ) if negative else ([], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []}, [])
```

Update the destructuring (line 139-140):

```python
    pos_topic_list, pos_merge_info, pos_labels = pos_topics
    neg_topic_list, neg_merge_info, neg_labels = neg_topics
```

- [ ] **Step 3: Run tests to verify existing tests still pass**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py -v`
Expected: PASS — all 5 existing tests (the 3rd tuple element is just ignored in destructuring)

- [ ] **Step 4: Commit**

```bash
git add python/analyzer.py
git commit -m "refactor(analysis): return cluster labels from _analyze_group"
```

---

### Task 3: New `segment_topics.py` module + test

**Files:**
- Create: `python/segment_topics.py`
- Create: `tests/python/test_segment_topics.py`

- [ ] **Step 1: Write the test**

Create `tests/python/test_segment_topics.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from segment_topics import compute_segment_topic_cross


def _make_cross_reviews():
    """Build 8 reviews spanning different segments and topic assignments."""
    return [
        # Positive reviews with topic assignments
        {"text": "great combat", "voted_up": True, "playtime": 6000, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1000, "sentiment": "positive", "topic_id": 0},
        {"text": "good story", "voted_up": True, "playtime": 200, "language": "english", "steam_deck": True, "steam_purchase": True, "timestamp": 2000, "sentiment": "positive", "topic_id": 1},
        {"text": "fun gameplay", "voted_up": True, "playtime": 6000, "language": "koreana", "steam_deck": False, "steam_purchase": False, "timestamp": 3000, "sentiment": "positive", "topic_id": 0},
        {"text": "nice graphics", "voted_up": True, "playtime": 300, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 4000, "sentiment": "positive", "topic_id": 1},
        # Negative reviews with topic assignments
        {"text": "bad performance", "voted_up": False, "playtime": 6000, "language": "english", "steam_deck": True, "steam_purchase": True, "timestamp": 5000, "sentiment": "negative", "topic_id": 0},
        {"text": "buggy game", "voted_up": False, "playtime": 60, "language": "koreana", "steam_deck": False, "steam_purchase": True, "timestamp": 6000, "sentiment": "negative", "topic_id": 1},
        {"text": "crashes often", "voted_up": False, "playtime": 6000, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 7000, "sentiment": "negative", "topic_id": 0},
        {"text": "too expensive", "voted_up": False, "playtime": 200, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 8000, "sentiment": "negative", "topic_id": 1},
    ]


def test_compute_playtime_axis():
    reviews = _make_cross_reviews()
    pos_topics = [
        {"id": 0, "label": "combat"},
        {"id": 1, "label": "story"},
    ]
    neg_topics = [
        {"id": 0, "label": "performance"},
        {"id": 1, "label": "bugs"},
    ]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "playtime" in result
    playtime = result["playtime"]

    # Find the 50h+ segment (playtime >= 3000 min)
    seg_50h = next(s for s in playtime if s["segment_label"] == "50h+")
    # Reviews: great combat (pos, t0), fun gameplay (pos, t0), bad performance (neg, t0), crashes often (neg, t0)
    assert seg_50h["total_reviews"] == 4
    assert seg_50h["positive_rate"] == 0.5  # 2 pos / 4 total

    # Positive topics in 50h+: topic 0 has 2 reviews
    pos_dist = seg_50h["positive_topic_distribution"]
    assert len(pos_dist) == 1  # only topic 0 in this segment
    assert pos_dist[0]["topic_id"] == 0
    assert pos_dist[0]["count"] == 2

    # Negative topics in 50h+: topic 0 has 2 reviews
    neg_dist = seg_50h["negative_topic_distribution"]
    assert len(neg_dist) == 1
    assert neg_dist[0]["topic_id"] == 0
    assert neg_dist[0]["count"] == 2


def test_compute_language_axis():
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "language" in result
    lang = result["language"]
    # english: 6 reviews, koreana: 2 reviews
    eng = next(s for s in lang if s["segment_label"] == "english")
    assert eng["total_reviews"] == 6
    kor = next(s for s in lang if s["segment_label"] == "koreana")
    assert kor["total_reviews"] == 2


def test_compute_steam_deck_axis():
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "steam_deck" in result
    deck_segs = result["steam_deck"]
    deck = next(s for s in deck_segs if s["segment_label"] == "Deck")
    # Deck reviews: good story (pos), bad performance (neg)
    assert deck["total_reviews"] == 2
    assert deck["positive_rate"] == 0.5


def test_compute_purchase_type_axis():
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "purchase_type" in result
    pt = result["purchase_type"]
    purchase = next(s for s in pt if s["segment_label"] == "Purchase")
    free = next(s for s in pt if s["segment_label"] == "Free")
    # Only 1 review is free (fun gameplay, pos)
    assert free["total_reviews"] == 1
    assert free["positive_rate"] == 1.0
    assert purchase["total_reviews"] == 7


def test_empty_reviews():
    result = compute_segment_topic_cross([], [], [])
    assert result["playtime"] == []
    assert result["language"] == []
    assert result["steam_deck"] == []
    assert result["purchase_type"] == []


def test_proportion_sums_to_one():
    """Within a segment, positive topic proportions should sum to ~1.0."""
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    for axis_name, segments in result.items():
        for seg in segments:
            pos_dist = seg["positive_topic_distribution"]
            if pos_dist:
                total_prop = sum(d["proportion"] for d in pos_dist)
                assert abs(total_prop - 1.0) < 0.01, f"{axis_name}/{seg['segment_label']} pos proportions sum to {total_prop}"
            neg_dist = seg["negative_topic_distribution"]
            if neg_dist:
                total_prop = sum(d["proportion"] for d in neg_dist)
                assert abs(total_prop - 1.0) < 0.01, f"{axis_name}/{seg['segment_label']} neg proportions sum to {total_prop}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_segment_topics.py -v`
Expected: FAIL — `segment_topics` module does not exist

- [ ] **Step 3: Implement `segment_topics.py`**

Create `python/segment_topics.py`:

```python
PLAYTIME_BINS = [
    {"label": "0-2h", "min": 0, "max": 120},
    {"label": "2-10h", "min": 120, "max": 600},
    {"label": "10-50h", "min": 600, "max": 3000},
    {"label": "50h+", "min": 3000, "max": float("inf")},
]


def _bin_playtime(minutes):
    for b in PLAYTIME_BINS:
        if b["min"] <= minutes < b["max"]:
            return b["label"]
    return "50h+"


def _compute_axis(reviews, bin_fn, pos_topic_map, neg_topic_map):
    """Compute per-segment topic distribution for a single segment axis."""
    bins = {}
    for r in reviews:
        label = bin_fn(r)
        if label is None:
            continue
        bins.setdefault(label, []).append(r)

    segments = []
    for label, entries in sorted(bins.items(), key=lambda x: x[0]):
        total = len(entries)
        pos_reviews = [r for r in entries if r["sentiment"] == "positive"]
        neg_reviews = [r for r in entries if r["sentiment"] == "negative"]
        pos_count = len(pos_reviews)
        neg_count = len(neg_reviews)

        # Positive topic distribution
        pos_dist = {}
        for r in pos_reviews:
            tid = r["topic_id"]
            if tid >= 0:
                pos_dist[tid] = pos_dist.get(tid, 0) + 1

        pos_topic_dist = []
        for tid, count in sorted(pos_dist.items(), key=lambda x: -x[1]):
            topic = pos_topic_map.get(tid, {})
            pos_topic_dist.append({
                "topic_id": tid,
                "topic_label": topic.get("label", f"Topic {tid}"),
                "count": count,
                "proportion": count / pos_count if pos_count > 0 else 0,
            })

        # Negative topic distribution
        neg_dist = {}
        for r in neg_reviews:
            tid = r["topic_id"]
            if tid >= 0:
                neg_dist[tid] = neg_dist.get(tid, 0) + 1

        neg_topic_dist = []
        for tid, count in sorted(neg_dist.items(), key=lambda x: -x[1]):
            topic = neg_topic_map.get(tid, {})
            neg_topic_dist.append({
                "topic_id": tid,
                "topic_label": topic.get("label", f"Topic {tid}"),
                "count": count,
                "proportion": count / neg_count if neg_count > 0 else 0,
            })

        segments.append({
            "segment_label": label,
            "total_reviews": total,
            "positive_rate": pos_count / total if total > 0 else 0,
            "positive_topic_distribution": pos_topic_dist,
            "negative_topic_distribution": neg_topic_dist,
        })

    return segments


def compute_segment_topic_cross(reviews, pos_topics, neg_topics):
    """Compute segment × topic cross-analysis across all segment axes.

    Args:
        reviews: list of review dicts, each with keys:
            sentiment ("positive"/"negative"), topic_id (int),
            playtime (int, minutes), language (str),
            steam_deck (bool), steam_purchase (bool), timestamp (int)
        pos_topics: list of positive topic dicts with "id" and "label"
        neg_topics: list of negative topic dicts with "id" and "label"

    Returns:
        dict with keys "playtime", "language", "steam_deck", "purchase_type",
        each mapping to a list of segment dicts.
    """
    if not reviews:
        return {"playtime": [], "language": [], "steam_deck": [], "purchase_type": []}

    pos_topic_map = {t["id"]: t for t in pos_topics}
    neg_topic_map = {t["id"]: t for t in neg_topics}

    result = {}

    # Playtime axis
    result["playtime"] = _compute_axis(
        reviews,
        lambda r: _bin_playtime(r.get("playtime", 0)),
        pos_topic_map, neg_topic_map,
    )

    # Language axis (top 10 by review count)
    lang_counts = {}
    for r in reviews:
        lang = r.get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_langs = set(sorted(lang_counts, key=lang_counts.get, reverse=True)[:10])

    result["language"] = _compute_axis(
        reviews,
        lambda r: r.get("language", "unknown") if r.get("language", "unknown") in top_langs else None,
        pos_topic_map, neg_topic_map,
    )

    # Steam Deck axis
    result["steam_deck"] = _compute_axis(
        reviews,
        lambda r: "Deck" if r.get("steam_deck") else "Non-Deck",
        pos_topic_map, neg_topic_map,
    )

    # Purchase type axis
    result["purchase_type"] = _compute_axis(
        reviews,
        lambda r: "Purchase" if r.get("steam_purchase") else "Free",
        pos_topic_map, neg_topic_map,
    )

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_segment_topics.py -v`
Expected: PASS — all 6 tests

- [ ] **Step 5: Commit**

```bash
git add python/segment_topics.py tests/python/test_segment_topics.py
git commit -m "feat(analysis): add segment_topics module for cross-analysis"
```

---

### Task 4: Integrate segment cross-analysis into `run_analysis()`

**Files:**
- Modify: `python/analyzer.py:1-10,139-164`
- Modify: `tests/python/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/python/test_analyzer.py`:

```python
def test_run_analysis_includes_segment_topic_cross(monkeypatch):
    """Result should include segment_topic_cross when reviews have segment metadata."""
    reviews = [
        {"text": "great combat system", "voted_up": True, "playtime": 6000, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1000},
        {"text": "excellent story", "voted_up": True, "playtime": 200, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 2000},
        {"text": "bad performance", "voted_up": False, "playtime": 6000, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 3000},
        {"text": "terrible bugs everywhere", "voted_up": False, "playtime": 60, "language": "koreana", "steam_deck": True, "steam_purchase": False, "timestamp": 4000},
    ]
    embeddings = np.array([[0.0, 0.0], [0.1, 0.1], [5.0, 5.0], [5.1, 5.1]])
    progress_calls = []
    cluster_calls = []

    _install_common_mocks(monkeypatch, progress_calls, cluster_calls)
    monkeypatch.setattr(
        analyzer,
        "generate_embeddings",
        lambda params, msg_id: {"embeddings": embeddings[:len(params["texts"])].tolist(), "model": "test-model"},
    )

    result = analyzer.run_analysis(
        {"reviews": reviews, "config": {"tier": 0, "topicCountMode": "manual", "n_topics": 2}},
        "msg-seg",
    )

    assert "segment_topic_cross" in result
    cross = result["segment_topic_cross"]
    assert "playtime" in cross
    assert "language" in cross
    assert "steam_deck" in cross
    assert "purchase_type" in cross

    # Verify playtime segments have expected structure
    for seg in cross["playtime"]:
        assert "segment_label" in seg
        assert "total_reviews" in seg
        assert "positive_rate" in seg
        assert "positive_topic_distribution" in seg
        assert "negative_topic_distribution" in seg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py::test_run_analysis_includes_segment_topic_cross -v`
Expected: FAIL — `segment_topic_cross` not in result

- [ ] **Step 3: Implement integration**

In `python/analyzer.py`, add the import (line 9, after the existing topic_merge import):

```python
from segment_topics import compute_segment_topic_cross
```

In `run_analysis()`, after the destructuring of pos/neg topics (after the line `neg_topic_list, neg_merge_info, neg_labels = neg_topics`), add:

```python
    # Build segment × topic cross-analysis
    cross_reviews = []
    for i, r in enumerate(positive):
        cross_reviews.append({
            **r,
            "sentiment": "positive",
            "topic_id": pos_labels[i] if i < len(pos_labels) else -1,
        })
    for i, r in enumerate(negative):
        cross_reviews.append({
            **r,
            "sentiment": "negative",
            "topic_id": neg_labels[i] if i < len(neg_labels) else -1,
        })
    segment_topic_cross = compute_segment_topic_cross(cross_reviews, pos_topic_list, neg_topic_list)
```

Add `"segment_topic_cross": segment_topic_cross,` to the return dict (after `"negative_topics": neg_topic_list,`).

Also add `"segment_topic_cross": {"playtime": [], "language": [], "steam_deck": [], "purchase_type": []},` to both early-return dicts (the empty-reviews return near line 26 and the few-long-reviews return near line 58).

- [ ] **Step 4: Run ALL tests to verify they pass**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/ -v`
Expected: PASS — all tests (5 existing analyzer + 1 new analyzer + 6 segment_topics)

- [ ] **Step 5: Commit**

```bash
git add python/analyzer.py tests/python/test_analyzer.py
git commit -m "feat(analysis): integrate segment_topic_cross into run_analysis"
```

---

### Task 5: Frontend types + pass analysisResult to SegmentAnalysis

**Files:**
- Modify: `src/renderer/src/components/TopicAnalysis.tsx:16-47`
- Modify: `src/renderer/src/App.tsx:26`
- Modify: `src/renderer/src/components/SegmentAnalysis.tsx:14`

- [ ] **Step 1: Add segment_topic_cross type to AnalysisResult**

In `src/renderer/src/components/TopicAnalysis.tsx`, add after the `merge_info` field (before the closing `}` of `AnalysisResult` interface):

```typescript
  // Segment × topic cross-analysis
  segment_topic_cross?: {
    playtime: SegmentTopicData[]
    language: SegmentTopicData[]
    steam_deck: SegmentTopicData[]
    purchase_type: SegmentTopicData[]
  }
```

Add the `SegmentTopicData` interface before `AnalysisResult` (after the `Topic` interface):

```typescript
export interface TopicDistributionEntry {
  topic_id: number
  topic_label: string
  count: number
  proportion: number
}

export interface SegmentTopicData {
  segment_label: string
  total_reviews: number
  positive_rate: number
  positive_topic_distribution: TopicDistributionEntry[]
  negative_topic_distribution: TopicDistributionEntry[]
}
```

- [ ] **Step 2: Pass analysisResult to SegmentAnalysis**

In `src/renderer/src/App.tsx`, change line 26 from:

```tsx
              <SegmentAnalysis appId={appId} />
```

to:

```tsx
              <SegmentAnalysis appId={appId} analysisResult={analysisResult} />
```

- [ ] **Step 3: Update SegmentAnalysis to accept the prop**

In `src/renderer/src/components/SegmentAnalysis.tsx`, add the import at top:

```typescript
import type { AnalysisResult } from './TopicAnalysis'
```

Change the function signature (line 14) from:

```typescript
export function SegmentAnalysis({ appId }: { appId: number }) {
```

to:

```typescript
export function SegmentAnalysis({ appId, analysisResult }: { appId: number; analysisResult: AnalysisResult | null }) {
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add src/renderer/src/components/TopicAnalysis.tsx src/renderer/src/App.tsx src/renderer/src/components/SegmentAnalysis.tsx
git commit -m "feat(ui): add segment_topic_cross types and pass analysisResult to SegmentAnalysis"
```

---

### Task 6: SegmentTopicHeatmap component + integration

**Files:**
- Create: `src/renderer/src/components/SegmentTopicHeatmap.tsx`
- Modify: `src/renderer/src/components/SegmentAnalysis.tsx`

- [ ] **Step 1: Create SegmentTopicHeatmap component**

Create `src/renderer/src/components/SegmentTopicHeatmap.tsx`:

```tsx
import { useState } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResult, SegmentTopicData } from './TopicAnalysis'

type SegmentAxis = 'playtime' | 'language' | 'steam_deck' | 'purchase_type'

const AXIS_LABELS: Record<SegmentAxis, string> = {
  playtime: 'Playtime',
  language: 'Language',
  steam_deck: 'Steam Deck',
  purchase_type: 'Purchase Type',
}

export function SegmentTopicHeatmap({ analysisResult }: { analysisResult: AnalysisResult }) {
  const [axis, setAxis] = useState<SegmentAxis>('playtime')
  const [sentiment, setSentiment] = useState<'positive' | 'negative'>('negative')

  const cross = analysisResult.segment_topic_cross
  if (!cross) return null

  const segments: SegmentTopicData[] = cross[axis] ?? []
  if (segments.length === 0) return <p>No segment data available for this axis.</p>

  // Collect all topic labels for the selected sentiment
  const distKey = sentiment === 'positive' ? 'positive_topic_distribution' : 'negative_topic_distribution'
  const topicSet = new Map<number, string>()
  for (const seg of segments) {
    for (const d of seg[distKey]) {
      if (!topicSet.has(d.topic_id)) {
        topicSet.set(d.topic_id, d.topic_label)
      }
    }
  }

  const topicIds = [...topicSet.keys()].sort((a, b) => a - b)
  const topicLabels = topicIds.map(id => topicSet.get(id)!)
  const segmentLabels = segments.map(s => s.segment_label)

  // Build heatmap data: [xIndex, yIndex, value]
  const data: [number, number, number][] = []
  let maxVal = 0
  for (let xi = 0; xi < segments.length; xi++) {
    const dist = segments[xi][distKey]
    const distMap = new Map(dist.map(d => [d.topic_id, d.count]))
    for (let yi = 0; yi < topicIds.length; yi++) {
      const val = distMap.get(topicIds[yi]) ?? 0
      data.push([xi, yi, val])
      if (val > maxVal) maxVal = val
    }
  }

  const option = {
    tooltip: {
      position: 'top' as const,
      formatter: (p: { value: [number, number, number] }) => {
        const seg = segmentLabels[p.value[0]]
        const topic = topicLabels[p.value[1]]
        return `${seg} × ${topic}<br/>Reviews: ${p.value[2]}`
      },
    },
    grid: { top: 10, right: 20, bottom: 60, left: 140 },
    xAxis: {
      type: 'category' as const,
      data: segmentLabels,
      axisLabel: { rotate: segmentLabels.length > 6 ? 30 : 0 },
    },
    yAxis: {
      type: 'category' as const,
      data: topicLabels,
    },
    visualMap: {
      min: 0,
      max: maxVal || 1,
      calculable: true,
      orient: 'horizontal' as const,
      left: 'center',
      bottom: 0,
      inRange: {
        color: sentiment === 'positive'
          ? ['#f0fdf4', '#22c55e']
          : ['#fef2f2', '#ef4444'],
      },
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: true,
        formatter: (p: { value: [number, number, number] }) => p.value[2] > 0 ? String(p.value[2]) : '',
      },
    }],
  }

  return (
    <div className="segment-topic-heatmap">
      <div className="heatmap-controls">
        <label>
          Segment axis:
          <select value={axis} onChange={e => setAxis(e.target.value as SegmentAxis)}>
            {(Object.keys(AXIS_LABELS) as SegmentAxis[]).map(a => (
              <option key={a} value={a}>{AXIS_LABELS[a]}</option>
            ))}
          </select>
        </label>
        <label>
          Sentiment:
          <select value={sentiment} onChange={e => setSentiment(e.target.value as 'positive' | 'negative')}>
            <option value="negative">Negative Topics</option>
            <option value="positive">Positive Topics</option>
          </select>
        </label>
      </div>
      <ReactECharts option={option} style={{ height: Math.max(200, topicLabels.length * 40 + 80) }} />
    </div>
  )
}
```

- [ ] **Step 2: Integrate into SegmentAnalysis**

In `src/renderer/src/components/SegmentAnalysis.tsx`, add import:

```typescript
import { SegmentTopicHeatmap } from './SegmentTopicHeatmap'
```

Add the cross-analysis section inside the return JSX. After the `charts-grid` closing `</div>` (line 189) and before the closing of the non-loading branch, add:

```tsx
          {analysisResult?.segment_topic_cross ? (
            <div className="chart-card" style={{ marginTop: '1rem' }}>
              <h3>Topic × Segment Cross-Analysis</h3>
              <SegmentTopicHeatmap analysisResult={analysisResult} />
            </div>
          ) : (
            <div className="cross-analysis-placeholder" style={{ marginTop: '1rem', padding: '1rem', opacity: 0.6 }}>
              Run topic analysis first to see segment × topic cross-analysis.
            </div>
          )}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/components/SegmentTopicHeatmap.tsx src/renderer/src/components/SegmentAnalysis.tsx
git commit -m "feat(ui): add segment × topic heatmap visualization"
```
