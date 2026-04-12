# Feature 2: Key Review Surfacing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface the most helpful (community-voted) and most representative (centroid-closest) reviews so users can quickly see the most important opinions.

**Architecture:** Two independent data paths. Most Helpful = simple DB query on `weighted_vote_score` (no ML). Most Representative = computed inside existing Python analysis pipeline by finding each topic's centroid-closest review. Frontend displays both in their appropriate locations.

**Tech Stack:** TypeScript (Electron main/renderer), Python (NumPy), better-sqlite3, React, Vitest, pytest

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/main/db.ts` | Add `getTopHelpfulReviews()` DB query function |
| Modify | `tests/main/db.test.ts` | Test for `getTopHelpfulReviews()` |
| Modify | `src/main/ipc-handlers.ts` | Add `reviews:top-helpful` IPC handler |
| Modify | `src/preload/index.ts` | Expose `getTopHelpful` API method |
| Modify | `python/analyzer.py` | Add `representative_review` field to each topic in `_analyze_group()` |
| Modify | `tests/python/test_analyzer.py` | Test representative review selection |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx` | Add `representative_review` to Topic interface + TopicCard display |
| Create | `src/renderer/src/components/HelpfulReviews.tsx` | Component that fetches and displays top helpful reviews |
| Modify | `src/renderer/src/components/Dashboard.tsx` | Integrate HelpfulReviews component |

---

### Task 1: DB helper — `getTopHelpfulReviews()`

**Files:**
- Modify: `src/main/db.ts:193` (after `getReviews()`)
- Test: `tests/main/db.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `tests/main/db.test.ts`, inside the existing `describe('Database', ...)` block, after the last `it(...)`:

```typescript
it('getTopHelpfulReviews returns top reviews by weighted_vote_score per sentiment', () => {
  insertGame(db, { app_id: 730, app_name: 'CS2', review_score: 8, review_score_desc: 'Very Positive', total_positive: 100, total_negative: 20, total_reviews: 120 })

  upsertReviews(db, [
    { recommendation_id: 'r1', app_id: 730, language: 'english', review_text: 'Amazing', voted_up: 1, timestamp_created: 1000, timestamp_updated: 1000, playtime_at_review: 600, playtime_forever: 1200, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 100, votes_funny: 0, weighted_vote_score: 0.95, comment_count: 5 },
    { recommendation_id: 'r2', app_id: 730, language: 'english', review_text: 'Good', voted_up: 1, timestamp_created: 1001, timestamp_updated: 1001, playtime_at_review: 300, playtime_forever: 500, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 50, votes_funny: 0, weighted_vote_score: 0.80, comment_count: 2 },
    { recommendation_id: 'r3', app_id: 730, language: 'english', review_text: 'Okay', voted_up: 1, timestamp_created: 1002, timestamp_updated: 1002, playtime_at_review: 100, playtime_forever: 200, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 5, votes_funny: 0, weighted_vote_score: 0.30, comment_count: 0 },
    { recommendation_id: 'r4', app_id: 730, language: 'english', review_text: 'Terrible', voted_up: 0, timestamp_created: 1003, timestamp_updated: 1003, playtime_at_review: 60, playtime_forever: 60, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 80, votes_funny: 0, weighted_vote_score: 0.90, comment_count: 3 },
    { recommendation_id: 'r5', app_id: 730, language: 'english', review_text: 'Bad', voted_up: 0, timestamp_created: 1004, timestamp_updated: 1004, playtime_at_review: 30, playtime_forever: 30, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 10, votes_funny: 0, weighted_vote_score: 0.40, comment_count: 0 },
  ])

  const topPositive = getTopHelpfulReviews(db, 730, true, 2)
  expect(topPositive).toHaveLength(2)
  expect(topPositive[0].recommendation_id).toBe('r1') // highest weighted_vote_score
  expect(topPositive[1].recommendation_id).toBe('r2')

  const topNegative = getTopHelpfulReviews(db, 730, false, 1)
  expect(topNegative).toHaveLength(1)
  expect(topNegative[0].recommendation_id).toBe('r4')
})
```

Update the import line at the top of the file to include the new function:

```typescript
import { createDb, insertGame, getGame, getAllGames, upsertReviews, getReviews, getGameStats, deleteGame, saveAnalysisCache, getAnalysisCache, getTopHelpfulReviews } from '../../src/main/db'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/main/db.test.ts`
Expected: FAIL — `getTopHelpfulReviews` is not exported from `../../src/main/db`

- [ ] **Step 3: Write minimal implementation**

Add to `src/main/db.ts` after the `getReviews()` function (after line 193):

```typescript
export function getTopHelpfulReviews(db: Database.Database, appId: number, votedUp: boolean, limit: number = 5): ReviewRecord[] {
  return db.prepare(
    'SELECT * FROM reviews WHERE app_id = ? AND voted_up = ? ORDER BY weighted_vote_score DESC LIMIT ?'
  ).all(appId, votedUp ? 1 : 0, limit) as ReviewRecord[]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/main/db.test.ts`
Expected: PASS — all tests including the new one

- [ ] **Step 5: Commit**

```bash
git add src/main/db.ts tests/main/db.test.ts
git commit -m "feat(db): add getTopHelpfulReviews query function"
```

---

### Task 2: IPC handler + preload API for `reviews:top-helpful`

**Files:**
- Modify: `src/main/ipc-handlers.ts:70` (after `reviews:get` handler)
- Modify: `src/preload/index.ts:14` (after `getReviews`)

- [ ] **Step 1: Add IPC handler**

In `src/main/ipc-handlers.ts`, add the import for `getTopHelpfulReviews`:

Change the import line:
```typescript
import { insertGame, getGame, getAllGames, deleteGame, getGameStats, upsertReviews, getReviews, getTopHelpfulReviews } from './db'
```

Add handler after the `reviews:get` handler (after line 70):

```typescript
  ipcMain.handle('reviews:top-helpful', (_event, appId: number, votedUp: boolean, limit?: number) => {
    return getTopHelpfulReviews(db, appId, votedUp, limit ?? 5)
  })
```

- [ ] **Step 2: Add preload API method**

In `src/preload/index.ts`, add after line 14 (`getReviews`):

```typescript
  getTopHelpful: (appId: number, votedUp: boolean, limit?: number) => ipcRenderer.invoke('reviews:top-helpful', appId, votedUp, limit),
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/main/ipc-handlers.ts src/preload/index.ts
git commit -m "feat(ipc): add reviews:top-helpful handler and preload API"
```

---

### Task 3: Representative review in Python analyzer

**Files:**
- Modify: `python/analyzer.py:167-204` (`_analyze_group()` function)
- Test: `tests/python/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/python/test_analyzer.py`:

```python
def test_analyze_group_includes_representative_review(monkeypatch):
    """Each topic should include a representative_review field — the review closest to the centroid."""
    reviews = _make_reviews(6, 0)
    # Two clusters: reviews 0-2 near origin, reviews 3-5 far away
    embeddings = np.array([
        [0.0, 0.1],
        [0.1, 0.0],
        [0.05, 0.05],  # closest to centroid of cluster 0
        [5.0, 5.1],
        [5.1, 5.0],
        [5.05, 5.05],  # closest to centroid of cluster 1
    ])
    progress_calls = []
    cluster_calls = []

    _install_common_mocks(monkeypatch, progress_calls, cluster_calls)
    monkeypatch.setattr(
        analyzer,
        "generate_embeddings",
        lambda params, msg_id: {"embeddings": embeddings[:len(params["texts"])].tolist(), "model": "test-model"},
    )
    # Override cluster to return two clusters
    monkeypatch.setattr(
        analyzer,
        "cluster_reviews",
        lambda vectors, method="kmeans", n_clusters=8, min_cluster_size=5, random_state=42: (
            [0, 0, 0, 1, 1, 1]
        ),
    )
    monkeypatch.setattr(
        analyzer,
        "extract_topic_keywords",
        lambda texts, labels, tier=0, embeddings=None: {
            0: [("topic_a", 0.9)],
            1: [("topic_b", 0.8)],
        },
    )

    result = analyzer.run_analysis(
        {"reviews": reviews, "config": {"tier": 0, "topicCountMode": "manual", "n_topics": 2}},
        "msg-rep",
    )

    for topic in result["positive_topics"]:
        assert "representative_review" in topic, f"Topic {topic['id']} missing representative_review"
        assert isinstance(topic["representative_review"], str)
        assert len(topic["representative_review"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py::test_analyze_group_includes_representative_review -v`
Expected: FAIL — `representative_review` not in topic dict

- [ ] **Step 3: Write minimal implementation**

In `python/analyzer.py`, modify the `_analyze_group()` function. Add import at top of file (line 2, after `import numpy as np`):

```python
from topic_merge import merge_similar_topics, compute_centroids, _cosine_similarity
```

Wait — `compute_centroids` and `_cosine_similarity` are already in `topic_merge.py` but not imported in `analyzer.py`. The current import is just `from topic_merge import merge_similar_topics`. Update to:

Change the import line from:
```python
from topic_merge import merge_similar_topics
```
to:
```python
from topic_merge import merge_similar_topics, compute_centroids
```

Also need cosine similarity — but `_cosine_similarity` is private. Rather than importing a private function, inline the centroid-closest logic using numpy directly in `_analyze_group()`.

Modify the `_analyze_group()` function (starts at line 167). Replace the current function body with:

```python
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
    return topics, merge_info
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py -v`
Expected: PASS — all tests including the new one

- [ ] **Step 5: Commit**

```bash
git add python/analyzer.py tests/python/test_analyzer.py
git commit -m "feat(analysis): add representative_review to each topic via centroid proximity"
```

---

### Task 4: Frontend — Topic interface + TopicCard update

**Files:**
- Modify: `src/renderer/src/components/TopicAnalysis.tsx:7-13` (Topic interface)
- Modify: `src/renderer/src/components/TopicAnalysis.tsx:304-330` (TopicCard component)

- [ ] **Step 1: Update Topic interface**

In `src/renderer/src/components/TopicAnalysis.tsx`, add `representative_review` to the `Topic` interface (line 7-13):

```typescript
export interface Topic {
  id: number
  label: string
  keywords: { word: string; score: number }[]
  review_count: number
  representative_review?: string
  sample_reviews: string[]
}
```

- [ ] **Step 2: Update TopicCard to display representative review**

In `src/renderer/src/components/TopicAnalysis.tsx`, modify the `TopicCard` component (line 304-330). Add representative review display between the keywords and the expanded samples section:

```typescript
function TopicCard({ topic, type, expanded, onToggle }: {
  topic: Topic; type: string; expanded: boolean; onToggle: () => void
}) {
  return (
    <div className={`topic-card ${type}`}>
      <div className="topic-header" onClick={onToggle}>
        <span className="topic-label">{topic.label}</span>
        <span className="topic-count">{topic.review_count} reviews</span>
      </div>
      <div className="topic-keywords">
        {topic.keywords.map(kw => (
          <span key={kw.word} className="keyword-tag" style={{ opacity: 0.5 + kw.score * 0.5 }}>
            {kw.word}
          </span>
        ))}
      </div>
      {topic.representative_review && (
        <div className="representative-review">
          <span className="representative-label">Representative:</span>
          <p className="representative-text">{topic.representative_review}</p>
        </div>
      )}
      {expanded && (
        <div className="topic-samples">
          <h4>Sample Reviews</h4>
          {topic.sample_reviews.map((review, i) => (
            <div key={i} className="sample-review">{review}</div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/components/TopicAnalysis.tsx
git commit -m "feat(ui): display representative review in topic cards"
```

---

### Task 5: Frontend — HelpfulReviews component + Dashboard integration

**Files:**
- Create: `src/renderer/src/components/HelpfulReviews.tsx`
- Modify: `src/renderer/src/components/Dashboard.tsx`

- [ ] **Step 1: Create HelpfulReviews component**

Create `src/renderer/src/components/HelpfulReviews.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { useApi } from '../hooks/useApi'

interface HelpfulReview {
  recommendation_id: string
  review_text: string
  voted_up: number
  votes_up: number
  weighted_vote_score: number
  playtime_at_review: number
}

export function HelpfulReviews({ appId }: { appId: number }) {
  const api = useApi()
  const [positive, setPositive] = useState<HelpfulReview[]>([])
  const [negative, setNegative] = useState<HelpfulReview[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.getTopHelpful(appId, true, 5) as Promise<HelpfulReview[]>,
      api.getTopHelpful(appId, false, 5) as Promise<HelpfulReview[]>,
    ]).then(([pos, neg]) => {
      setPositive(pos)
      setNegative(neg)
      setLoading(false)
    })
  }, [appId])

  if (loading) return <div className="helpful-reviews-loading">Loading helpful reviews...</div>
  if (positive.length === 0 && negative.length === 0) return null

  return (
    <div className="helpful-reviews">
      <h3>Community Top Reviews</h3>
      <div className="helpful-grid">
        <div className="helpful-column">
          <h4 className="helpful-positive-header">Most Helpful Positive</h4>
          {positive.map(r => (
            <div key={r.recommendation_id} className="helpful-card positive">
              <div className="helpful-meta">
                <span>{Math.round(r.playtime_at_review / 60)}h played</span>
                <span>{r.votes_up} helpful</span>
              </div>
              <p className="helpful-text">{r.review_text}</p>
            </div>
          ))}
        </div>
        <div className="helpful-column">
          <h4 className="helpful-negative-header">Most Helpful Negative</h4>
          {negative.map(r => (
            <div key={r.recommendation_id} className="helpful-card negative">
              <div className="helpful-meta">
                <span>{Math.round(r.playtime_at_review / 60)}h played</span>
                <span>{r.votes_up} helpful</span>
              </div>
              <p className="helpful-text">{r.review_text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Integrate into Dashboard**

In `src/renderer/src/components/Dashboard.tsx`, add the import at the top (after the existing imports):

```typescript
import { HelpfulReviews } from './HelpfulReviews'
```

Add the component inside the return JSX, after the `charts-grid` div (before the closing `</div>` of the dashboard, after line 168):

```tsx
      <HelpfulReviews appId={appId} />
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/components/HelpfulReviews.tsx src/renderer/src/components/Dashboard.tsx
git commit -m "feat(ui): add community top reviews section to dashboard"
```
