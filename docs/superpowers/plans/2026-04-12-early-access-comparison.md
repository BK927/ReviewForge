# Feature 5: Early Access Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare negative topic distributions between Early Access and Post-Launch periods, classifying each topic's lifecycle status (persistent/resolved/new).

**Architecture:** Reuses the `cross_reviews` list (reviews annotated with `sentiment` + `topic_id`). A new `early_access.py` module segments negative reviews by the `written_during_early_access` flag, computes per-topic proportions in each period, and classifies lifecycle status based on a 5% presence threshold. The IPC layer must pass the `written_during_early_access` field to Python. The frontend renders lifecycle cards with color-coded status and proportion comparison bars, conditionally shown in the Segments tab.

**Tech Stack:** Python, TypeScript (React), CSS inline styles, pytest

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `python/early_access.py` | `compute_early_access_comparison()` — lifecycle classification |
| Create | `tests/python/test_early_access.py` | Tests for EA comparison logic |
| Modify | `src/main/ipc-handlers.ts:128-137` | Add `early_access` to reviewData mapping |
| Modify | `python/analyzer.py:11,40,76,163-188` | Import + call + add to result |
| Modify | `tests/python/test_analyzer.py` | Integration test |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx:30-82` | Add EA types to AnalysisResult |
| Create | `src/renderer/src/components/EarlyAccessComparison.tsx` | Lifecycle cards with comparison bars |
| Modify | `src/renderer/src/components/SegmentAnalysis.tsx:193-202` | Conditional EA section |

---

### Task 1: `early_access.py` module + test

**Files:**
- Create: `python/early_access.py`
- Create: `tests/python/test_early_access.py`

- [ ] **Step 1: Write the test file**

Create `tests/python/test_early_access.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from early_access import compute_early_access_comparison


def _make_lifecycle_reviews():
    """Create cross_reviews for lifecycle classification testing.

    200 total: 100 EA (50 pos + 50 neg), 100 Post (50 pos + 50 neg).
    Negative topic distributions:
      Topic 0: 15/50 EA (30%), 15/50 Post (30%) -> persistent
      Topic 1: 15/50 EA (30%), 1/50 Post (2%)   -> resolved
      Topic 2: 1/50 EA (2%),  15/50 Post (30%)  -> new
      Topic 3: 19/50 EA (38%), 19/50 Post (38%) -> persistent
    """
    reviews = []

    # EA positive (50)
    for _ in range(50):
        reviews.append({"early_access": True, "sentiment": "positive", "topic_id": 0, "timestamp": 1000})

    # EA negative (50): topic 0 x15, topic 1 x15, topic 2 x1, topic 3 x19
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 0, "timestamp": 1000})
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 1, "timestamp": 1000})
    reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 2, "timestamp": 1000})
    for _ in range(19):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 3, "timestamp": 1000})

    # Post positive (50)
    for _ in range(50):
        reviews.append({"early_access": False, "sentiment": "positive", "topic_id": 0, "timestamp": 2000})

    # Post negative (50): topic 0 x15, topic 1 x1, topic 2 x15, topic 3 x19
    for _ in range(15):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 0, "timestamp": 2000})
    reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 1, "timestamp": 2000})
    for _ in range(15):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 2, "timestamp": 2000})
    for _ in range(19):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 3, "timestamp": 2000})

    return reviews


def test_returns_none_when_ea_count_below_50():
    """Activation requires at least 50 EA reviews."""
    reviews = []
    # 30 EA + 30 Post = 60 total, EA ratio = 50% (ok), but EA count = 30 (< 50)
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "positive", "topic_id": 0})
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 0})
    for _ in range(30):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 0})

    result = compute_early_access_comparison(reviews, [{"id": 0, "label": "t0"}])
    assert result is None


def test_returns_none_when_ea_ratio_below_10_percent():
    """Activation requires EA >= 10% of total."""
    reviews = []
    # 5 EA + 95 Post = 100 total, EA ratio = 5% (< 10%), EA count = 5 (< 50 too)
    for _ in range(5):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 0})
    for _ in range(95):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 0})

    result = compute_early_access_comparison(reviews, [{"id": 0, "label": "t0"}])
    assert result is None


def test_returns_none_for_empty_reviews():
    result = compute_early_access_comparison([], [])
    assert result is None


def test_lifecycle_classification():
    reviews = _make_lifecycle_reviews()
    neg_topics = [
        {"id": 0, "label": "performance"},
        {"id": 1, "label": "bugs"},
        {"id": 2, "label": "crashes"},
        {"id": 3, "label": "balance"},
    ]

    result = compute_early_access_comparison(reviews, neg_topics)
    assert result is not None
    assert result["ea_review_count"] == 100
    assert result["post_launch_review_count"] == 100

    lifecycle = result["lifecycle"]
    status_map = {entry["topic_id"]: entry["status"] for entry in lifecycle}

    # Topic 0: 30% EA, 30% Post -> persistent
    assert status_map[0] == "persistent"
    # Topic 1: 30% EA, 2% Post -> resolved
    assert status_map[1] == "resolved"
    # Topic 2: 2% EA, 30% Post -> new
    assert status_map[2] == "new"
    # Topic 3: 38% EA, 38% Post -> persistent
    assert status_map[3] == "persistent"


def test_lifecycle_entry_structure():
    reviews = _make_lifecycle_reviews()
    neg_topics = [
        {"id": 0, "label": "performance"},
        {"id": 1, "label": "bugs"},
        {"id": 2, "label": "crashes"},
        {"id": 3, "label": "balance"},
    ]

    result = compute_early_access_comparison(reviews, neg_topics)
    assert "ea_review_count" in result
    assert "post_launch_review_count" in result
    assert "lifecycle" in result

    for entry in result["lifecycle"]:
        assert "topic_id" in entry
        assert "topic_label" in entry
        assert entry["status"] in ("persistent", "resolved", "new")
        assert "ea_proportion" in entry
        assert "post_launch_proportion" in entry
        assert "ea_positive_rate" in entry
        assert "post_launch_positive_rate" in entry
        assert 0 <= entry["ea_proportion"] <= 1
        assert 0 <= entry["post_launch_proportion"] <= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_early_access.py -v`
Expected: FAIL — `early_access` module not found

- [ ] **Step 3: Implement `early_access.py`**

Create `python/early_access.py`:

```python
PRESENCE_THRESHOLD = 0.05


def compute_early_access_comparison(cross_reviews, neg_topics):
    """Compare negative topic distributions between Early Access and Post-Launch.

    Activation: EA reviews >= 50 AND EA ratio >= 10% of total.
    Each negative topic is classified as persistent/resolved/new based on its
    proportion in each period (threshold: 5%).

    Args:
        cross_reviews: list of review dicts with keys:
            early_access (bool), sentiment ("positive"/"negative"), topic_id (int)
        neg_topics: list of negative topic dicts with "id" and "label"

    Returns:
        dict with ea_review_count, post_launch_review_count, lifecycle list.
        None if activation conditions not met or no reviews.
    """
    if not cross_reviews:
        return None

    ea_reviews = [r for r in cross_reviews if r.get("early_access")]
    post_reviews = [r for r in cross_reviews if not r.get("early_access")]

    ea_count = len(ea_reviews)
    total_count = len(cross_reviews)

    # Activation check
    if ea_count < 50 or ea_count / total_count < 0.10:
        return None

    post_count = len(post_reviews)

    # Overall positive rates per period
    ea_pos_rate = sum(1 for r in ea_reviews if r["sentiment"] == "positive") / ea_count
    post_pos_rate = sum(1 for r in post_reviews if r["sentiment"] == "positive") / post_count if post_count > 0 else 0

    # Negative reviews per period
    ea_neg = [r for r in ea_reviews if r["sentiment"] == "negative"]
    post_neg = [r for r in post_reviews if r["sentiment"] == "negative"]
    ea_neg_count = len(ea_neg)
    post_neg_count = len(post_neg)

    neg_topic_map = {t["id"]: t for t in neg_topics}

    # Count per negative topic in each period
    ea_topic_counts = {}
    for r in ea_neg:
        tid = r["topic_id"]
        if tid >= 0:
            ea_topic_counts[tid] = ea_topic_counts.get(tid, 0) + 1

    post_topic_counts = {}
    for r in post_neg:
        tid = r["topic_id"]
        if tid >= 0:
            post_topic_counts[tid] = post_topic_counts.get(tid, 0) + 1

    all_topic_ids = set(ea_topic_counts.keys()) | set(post_topic_counts.keys())

    lifecycle = []
    for tid in sorted(all_topic_ids):
        ea_prop = ea_topic_counts.get(tid, 0) / ea_neg_count if ea_neg_count > 0 else 0
        post_prop = post_topic_counts.get(tid, 0) / post_neg_count if post_neg_count > 0 else 0

        in_ea = ea_prop >= PRESENCE_THRESHOLD
        in_post = post_prop >= PRESENCE_THRESHOLD

        if not in_ea and not in_post:
            continue

        if in_ea and in_post:
            status = "persistent"
        elif in_ea:
            status = "resolved"
        else:
            status = "new"

        topic = neg_topic_map.get(tid, {})
        lifecycle.append({
            "topic_id": tid,
            "topic_label": topic.get("label", f"Topic {tid}"),
            "status": status,
            "ea_proportion": round(ea_prop, 4),
            "post_launch_proportion": round(post_prop, 4),
            "ea_positive_rate": round(ea_pos_rate, 4),
            "post_launch_positive_rate": round(post_pos_rate, 4),
        })

    # Sort: persistent first, then resolved, then new; within group by max proportion desc
    status_order = {"persistent": 0, "resolved": 1, "new": 2}
    lifecycle.sort(key=lambda x: (status_order[x["status"]], -max(x["ea_proportion"], x["post_launch_proportion"])))

    return {
        "ea_review_count": ea_count,
        "post_launch_review_count": post_count,
        "lifecycle": lifecycle,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_early_access.py -v`
Expected: PASS — all 5 tests

- [ ] **Step 5: Commit**

```bash
git add python/early_access.py tests/python/test_early_access.py
git commit -m "feat(analysis): add early_access module for EA vs post-launch lifecycle comparison"
```

---

### Task 2: IPC data mapping + analyzer integration + test

**Files:**
- Modify: `src/main/ipc-handlers.ts:128-137`
- Modify: `python/analyzer.py:11,40,76,163-188`
- Modify: `tests/python/test_analyzer.py`

- [ ] **Step 1: Add `early_access` to IPC reviewData mapping**

In `src/main/ipc-handlers.ts`, the `reviewData` mapping (lines 128-137) currently looks like:

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

Add `early_access` field after `timestamp`:

```typescript
    const reviewData = reviews.map(r => ({
      id: r.recommendation_id,
      text: r.review_text,
      voted_up: r.voted_up === 1,
      language: r.language,
      playtime: r.playtime_at_review,
      steam_deck: r.primarily_steam_deck === 1,
      steam_purchase: r.steam_purchase === 1,
      timestamp: r.timestamp_created,
      early_access: r.written_during_early_access === 1
    }))
```

- [ ] **Step 2: Write the failing integration test**

Add to the END of `tests/python/test_analyzer.py`:

```python
def test_run_analysis_includes_early_access_comparison(monkeypatch):
    """Result should include early_access_comparison field (None when not enough EA reviews)."""
    reviews = [
        {"text": "great combat system", "voted_up": True, "playtime": 600, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1704067200, "early_access": False},
        {"text": "excellent story telling", "voted_up": True, "playtime": 200, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1706745600, "early_access": True},
        {"text": "terrible performance issues", "voted_up": False, "playtime": 300, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1709251200, "early_access": False},
    ]
    embeddings = np.array([[0.0, 0.0], [0.1, 0.1], [5.0, 5.0]])
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
        "msg-ea",
    )

    # With only 3 reviews (1 EA), activation threshold not met -> None
    assert "early_access_comparison" in result
    assert result["early_access_comparison"] is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py::test_run_analysis_includes_early_access_comparison -v`
Expected: FAIL — `early_access_comparison` not in result

- [ ] **Step 4: Implement the analyzer integration**

In `python/analyzer.py`, make 4 edits:

**4a. Add import** — after `from topic_timeline import compute_topics_over_time` (line 11):

```python
from early_access import compute_early_access_comparison
```

**4b. Add to first early return** (empty reviews, around line 40) — after `"topics_over_time": {"weekly": [], "monthly": []},`:

```python
            "early_access_comparison": None,
```

**4c. Add to second early return** (few long reviews, around line 76) — after `"topics_over_time": {"weekly": [], "monthly": []},`:

```python
            "early_access_comparison": None,
```

**4d. Add computation and return value** — after the `topics_over_time` computation (line 163), add:

```python
    early_access_comparison = compute_early_access_comparison(cross_reviews, neg_topic_list)
```

And in the return dict, after `"topics_over_time": topics_over_time,` (line 188), add:

```python
        "early_access_comparison": early_access_comparison,
```

- [ ] **Step 5: Run ALL Python tests**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/ -v`
Expected: PASS — all tests

- [ ] **Step 6: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add src/main/ipc-handlers.ts python/analyzer.py tests/python/test_analyzer.py
git commit -m "feat(analysis): integrate early access comparison into pipeline"
```

---

### Task 3: Frontend — types + EarlyAccessComparison component + integration

**Files:**
- Modify: `src/renderer/src/components/TopicAnalysis.tsx:30-82`
- Create: `src/renderer/src/components/EarlyAccessComparison.tsx`
- Modify: `src/renderer/src/components/SegmentAnalysis.tsx:193-202`

- [ ] **Step 1: Add types to TopicAnalysis.tsx**

In `src/renderer/src/components/TopicAnalysis.tsx`, add two new interfaces after `TopicTimelinePeriod` (around line 38). Find the line `export interface AnalysisResult {` and add these BEFORE it:

```typescript
export interface EarlyAccessLifecycleEntry {
  topic_id: number
  topic_label: string
  status: 'persistent' | 'resolved' | 'new'
  ea_proportion: number
  post_launch_proportion: number
  ea_positive_rate: number
  post_launch_positive_rate: number
}

export interface EarlyAccessComparisonData {
  ea_review_count: number
  post_launch_review_count: number
  lifecycle: EarlyAccessLifecycleEntry[]
}
```

Add a new field to the `AnalysisResult` interface, after the `topics_over_time` block:

```typescript
  // Early access comparison
  early_access_comparison?: EarlyAccessComparisonData | null
```

- [ ] **Step 2: Create EarlyAccessComparison component**

Create `src/renderer/src/components/EarlyAccessComparison.tsx`:

```tsx
import type { AnalysisResult } from './TopicAnalysis'

const STATUS_CONFIG = {
  persistent: { label: 'Persistent', color: '#ef4444', bg: '#fef2f2' },
  resolved: { label: 'Resolved', color: '#22c55e', bg: '#f0fdf4' },
  new: { label: 'New', color: '#eab308', bg: '#fefce8' },
} as const

export function EarlyAccessComparison({ analysisResult }: { analysisResult: AnalysisResult }) {
  const data = analysisResult.early_access_comparison
  if (!data) return null

  return (
    <div className="early-access-comparison">
      <h3>Early Access vs Post-Launch</h3>
      <div className="ea-summary" style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.9rem', opacity: 0.8 }}>
        <span>EA Reviews: {data.ea_review_count.toLocaleString()}</span>
        <span>Post-Launch Reviews: {data.post_launch_review_count.toLocaleString()}</span>
      </div>
      <div className="lifecycle-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {data.lifecycle.map(entry => {
          const config = STATUS_CONFIG[entry.status]
          const maxProp = Math.max(entry.ea_proportion, entry.post_launch_proportion, 0.01)
          return (
            <div
              key={entry.topic_id}
              className="lifecycle-card"
              style={{
                borderLeft: `4px solid ${config.color}`,
                backgroundColor: config.bg,
                padding: '0.75rem 1rem',
                borderRadius: '4px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>{entry.topic_label}</span>
                <span style={{ color: config.color, fontWeight: 600, fontSize: '0.85rem' }}>{config.label}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ width: '3rem', fontSize: '0.8rem', textAlign: 'right' }}>EA</span>
                  <div style={{ flex: 1, height: '12px', backgroundColor: '#e5e7eb', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ width: `${(entry.ea_proportion / maxProp) * 100}%`, height: '100%', backgroundColor: config.color, borderRadius: '6px' }} />
                  </div>
                  <span style={{ width: '3.5rem', fontSize: '0.8rem' }}>{(entry.ea_proportion * 100).toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ width: '3rem', fontSize: '0.8rem', textAlign: 'right' }}>Post</span>
                  <div style={{ flex: 1, height: '12px', backgroundColor: '#e5e7eb', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ width: `${(entry.post_launch_proportion / maxProp) * 100}%`, height: '100%', backgroundColor: config.color, opacity: 0.6, borderRadius: '6px' }} />
                  </div>
                  <span style={{ width: '3.5rem', fontSize: '0.8rem' }}>{(entry.post_launch_proportion * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Integrate into SegmentAnalysis.tsx**

In `src/renderer/src/components/SegmentAnalysis.tsx`, add the import at the top (after the existing imports):

```typescript
import { EarlyAccessComparison } from './EarlyAccessComparison'
```

Find the section that renders the heatmap or placeholder (around lines 193-202). Currently:

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

Add the Early Access section AFTER the heatmap/placeholder block, before the closing `</>`:

```tsx
          {analysisResult?.early_access_comparison && (
            <div className="chart-card" style={{ marginTop: '1rem' }}>
              <EarlyAccessComparison analysisResult={analysisResult} />
            </div>
          )}
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add src/renderer/src/components/EarlyAccessComparison.tsx src/renderer/src/components/TopicAnalysis.tsx src/renderer/src/components/SegmentAnalysis.tsx
git commit -m "feat(ui): add early access vs post-launch lifecycle comparison section"
```
