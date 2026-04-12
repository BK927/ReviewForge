# Feature 4: Topic Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show how topic distributions change over time so users can see when complaints emerged and whether updates improved them.

**Architecture:** Reuses the existing `cross_reviews` list (reviews annotated with `sentiment` + `topic_id` + `timestamp`) built in `run_analysis()`. A new `topic_timeline.py` module groups these reviews by weekly/monthly periods and computes per-period topic distributions. Both granularities are computed in Python; the frontend toggles between them. The visualization is a stacked area chart in the Topics tab.

**Tech Stack:** Python (datetime), TypeScript (React), ECharts stacked area chart, pytest, Vitest

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `python/topic_timeline.py` | `compute_topics_over_time()` — groups by week/month, computes distributions |
| Create | `tests/python/test_topic_timeline.py` | Tests for timeline computation |
| Modify | `python/analyzer.py:10,38,73,159-183` | Import + call `compute_topics_over_time`, add to result |
| Modify | `tests/python/test_analyzer.py` | Test `topics_over_time` in analysis result |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx:31-69` | Add `topics_over_time` to `AnalysisResult` |
| Create | `src/renderer/src/components/TopicTimeline.tsx` | Stacked area chart with granularity toggle |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx:285-322` | Insert TopicTimeline before topics-grid |

---

### Task 1: `topic_timeline.py` module + test

**Files:**
- Create: `python/topic_timeline.py`
- Create: `tests/python/test_topic_timeline.py`

- [ ] **Step 1: Write the test file**

Create `tests/python/test_topic_timeline.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from topic_timeline import compute_topics_over_time


def _make_timeline_reviews():
    """Reviews spanning 3 months with topic assignments."""
    return [
        # January 2025
        {"text": "great", "voted_up": True, "timestamp": 1704067200, "sentiment": "positive", "topic_id": 0},  # 2024-01-01
        {"text": "good",  "voted_up": True, "timestamp": 1704153600, "sentiment": "positive", "topic_id": 1},  # 2024-01-02
        {"text": "bad",   "voted_up": False, "timestamp": 1704240000, "sentiment": "negative", "topic_id": 0}, # 2024-01-03
        # February 2025
        {"text": "nice",  "voted_up": True, "timestamp": 1706745600, "sentiment": "positive", "topic_id": 0},  # 2024-02-01
        {"text": "awful", "voted_up": False, "timestamp": 1706832000, "sentiment": "negative", "topic_id": 0}, # 2024-02-02
        {"text": "terrible", "voted_up": False, "timestamp": 1706918400, "sentiment": "negative", "topic_id": 1}, # 2024-02-03
        # March 2025
        {"text": "wow",   "voted_up": True, "timestamp": 1709251200, "sentiment": "positive", "topic_id": 0},  # 2024-03-01
        {"text": "cool",  "voted_up": True, "timestamp": 1709337600, "sentiment": "positive", "topic_id": 1},  # 2024-03-02
    ]


def test_monthly_periods():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    monthly = result["monthly"]
    assert len(monthly) == 3  # Jan, Feb, Mar

    # Periods should be sorted chronologically
    assert monthly[0]["period"] == "2024-01"
    assert monthly[1]["period"] == "2024-02"
    assert monthly[2]["period"] == "2024-03"

    # January: 3 reviews (2 pos, 1 neg)
    jan = monthly[0]
    assert jan["total_reviews"] == 3
    assert abs(jan["positive_rate"] - 2 / 3) < 0.01


def test_weekly_periods():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    weekly = result["weekly"]
    # All reviews should be assigned to some week
    total = sum(p["total_reviews"] for p in weekly)
    assert total == 8

    # Periods should be sorted
    periods = [p["period"] for p in weekly]
    assert periods == sorted(periods)


def test_topic_distribution_in_period():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    # January: 2 positive reviews (topic 0 and topic 1), 1 negative (topic 0)
    jan = result["monthly"][0]
    assert len(jan["positive_topic_distribution"]) == 2
    assert len(jan["negative_topic_distribution"]) == 1

    # Proportions should sum to 1.0 for each sentiment
    pos_sum = sum(d["proportion"] for d in jan["positive_topic_distribution"])
    assert abs(pos_sum - 1.0) < 0.01


def test_empty_reviews():
    result = compute_topics_over_time([], [], [])
    assert result["weekly"] == []
    assert result["monthly"] == []


def test_periods_have_expected_structure():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    for granularity in ["weekly", "monthly"]:
        for period in result[granularity]:
            assert "period" in period
            assert "total_reviews" in period
            assert "positive_rate" in period
            assert "positive_topic_distribution" in period
            assert "negative_topic_distribution" in period
            for d in period["positive_topic_distribution"]:
                assert "topic_id" in d
                assert "topic_label" in d
                assert "count" in d
                assert "proportion" in d
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_topic_timeline.py -v`
Expected: FAIL — `topic_timeline` module not found

- [ ] **Step 3: Implement `topic_timeline.py`**

Create `python/topic_timeline.py`:

```python
from datetime import datetime, timezone


def _period_key_weekly(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _period_key_monthly(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return f"{dt.year}-{dt.month:02d}"


def _compute_periods(reviews, period_fn, pos_topic_map, neg_topic_map):
    """Group reviews by time period and compute topic distributions."""
    bins = {}
    for r in reviews:
        ts = r.get("timestamp")
        if ts is None:
            continue
        key = period_fn(ts)
        bins.setdefault(key, []).append(r)

    periods = []
    for key in sorted(bins.keys()):
        entries = bins[key]
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

        periods.append({
            "period": key,
            "total_reviews": total,
            "positive_rate": pos_count / total if total > 0 else 0,
            "positive_topic_distribution": pos_topic_dist,
            "negative_topic_distribution": neg_topic_dist,
        })

    return periods


def compute_topics_over_time(reviews, pos_topics, neg_topics):
    """Compute topic distributions over time at both weekly and monthly granularity.

    Args:
        reviews: list of review dicts with keys:
            sentiment ("positive"/"negative"), topic_id (int), timestamp (int, unix epoch)
        pos_topics: list of positive topic dicts with "id" and "label"
        neg_topics: list of negative topic dicts with "id" and "label"

    Returns:
        dict with "weekly" and "monthly" keys, each a list of period dicts.
    """
    if not reviews:
        return {"weekly": [], "monthly": []}

    pos_topic_map = {t["id"]: t for t in pos_topics}
    neg_topic_map = {t["id"]: t for t in neg_topics}

    return {
        "weekly": _compute_periods(reviews, _period_key_weekly, pos_topic_map, neg_topic_map),
        "monthly": _compute_periods(reviews, _period_key_monthly, pos_topic_map, neg_topic_map),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_topic_timeline.py -v`
Expected: PASS — all 5 tests

- [ ] **Step 5: Commit**

```bash
git add python/topic_timeline.py tests/python/test_topic_timeline.py
git commit -m "feat(analysis): add topic_timeline module for time-series topic tracking"
```

---

### Task 2: Integrate `topics_over_time` into `run_analysis()`

**Files:**
- Modify: `python/analyzer.py:10,38,73,159-183`
- Modify: `tests/python/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/python/test_analyzer.py`:

```python
def test_run_analysis_includes_topics_over_time(monkeypatch):
    """Result should include topics_over_time with weekly and monthly periods."""
    reviews = [
        {"text": "great combat system", "voted_up": True, "playtime": 600, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1704067200},
        {"text": "excellent story telling", "voted_up": True, "playtime": 200, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1706745600},
        {"text": "terrible performance issues", "voted_up": False, "playtime": 300, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1709251200},
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
        "msg-time",
    )

    assert "topics_over_time" in result
    tot = result["topics_over_time"]
    assert "weekly" in tot
    assert "monthly" in tot
    assert len(tot["monthly"]) == 3  # Jan, Feb, Mar 2024

    for period in tot["monthly"]:
        assert "period" in period
        assert "total_reviews" in period
        assert "positive_rate" in period
        assert "positive_topic_distribution" in period
        assert "negative_topic_distribution" in period
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/test_analyzer.py::test_run_analysis_includes_topics_over_time -v`
Expected: FAIL — `topics_over_time` not in result

- [ ] **Step 3: Implement the integration**

In `python/analyzer.py`:

**3a. Add import** (after line 10, the `segment_topics` import):

```python
from topic_timeline import compute_topics_over_time
```

**3b. Add timeline computation** — right after the `segment_topic_cross` computation (after line 159), add:

```python
    topics_over_time = compute_topics_over_time(cross_reviews, pos_topic_list, neg_topic_list)
```

**3c. Add to the return dict** — after `"segment_topic_cross": segment_topic_cross,` add:

```python
        "topics_over_time": topics_over_time,
```

**3d. Add empty value to both early-return dicts** — add to both:

```python
            "topics_over_time": {"weekly": [], "monthly": []},
```

The first early return (empty reviews, around line 27-39) and the second (few long reviews, around line 60-74) both need this line.

- [ ] **Step 4: Run ALL Python tests**

Run: `python/.venv/Scripts/python.exe -m pytest tests/python/ -v`
Expected: PASS — all tests

- [ ] **Step 5: Commit**

```bash
git add python/analyzer.py tests/python/test_analyzer.py
git commit -m "feat(analysis): integrate topics_over_time into run_analysis"
```

---

### Task 3: Frontend — types + TopicTimeline component + integration

**Files:**
- Modify: `src/renderer/src/components/TopicAnalysis.tsx:31-69,285-322`
- Create: `src/renderer/src/components/TopicTimeline.tsx`

- [ ] **Step 1: Add `topics_over_time` type to AnalysisResult**

In `src/renderer/src/components/TopicAnalysis.tsx`, add a new interface after `SegmentTopicData` (after line 29):

```typescript
export interface TopicTimelinePeriod {
  period: string
  total_reviews: number
  positive_rate: number
  positive_topic_distribution: TopicDistributionEntry[]
  negative_topic_distribution: TopicDistributionEntry[]
}
```

Add the `topics_over_time` field to `AnalysisResult`, after the `segment_topic_cross` block (after line 68):

```typescript
  // Topic timeline
  topics_over_time?: {
    weekly: TopicTimelinePeriod[]
    monthly: TopicTimelinePeriod[]
  }
```

- [ ] **Step 2: Create TopicTimeline component**

Create `src/renderer/src/components/TopicTimeline.tsx`:

```tsx
import { useState } from 'react'
import ReactECharts from 'echarts-for-react'
import type { AnalysisResult, TopicTimelinePeriod } from './TopicAnalysis'

type Granularity = 'weekly' | 'monthly'

export function TopicTimeline({ analysisResult }: { analysisResult: AnalysisResult }) {
  const [granularity, setGranularity] = useState<Granularity>('monthly')
  const [sentiment, setSentiment] = useState<'positive' | 'negative'>('negative')

  const timeline = analysisResult.topics_over_time
  if (!timeline) return null

  const periods: TopicTimelinePeriod[] = timeline[granularity] ?? []
  if (periods.length === 0) return null

  const distKey = sentiment === 'positive' ? 'positive_topic_distribution' : 'negative_topic_distribution'

  // Collect all topic IDs and labels
  const topicSet = new Map<number, string>()
  for (const p of periods) {
    for (const d of p[distKey]) {
      if (!topicSet.has(d.topic_id)) {
        topicSet.set(d.topic_id, d.topic_label)
      }
    }
  }

  const topicIds = [...topicSet.keys()].sort((a, b) => a - b)
  const periodLabels = periods.map(p => p.period)

  // Build series: one per topic
  const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6']
  const series = topicIds.map((tid, i) => ({
    name: topicSet.get(tid)!,
    type: 'line' as const,
    stack: 'total',
    areaStyle: { opacity: 0.4 },
    emphasis: { focus: 'series' as const },
    data: periods.map(p => {
      const entry = p[distKey].find(d => d.topic_id === tid)
      return entry?.count ?? 0
    }),
    color: colors[i % colors.length],
  }))

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const },
    },
    legend: {
      data: topicIds.map(tid => topicSet.get(tid)!),
      bottom: 0,
    },
    grid: { top: 10, right: 20, bottom: 60, left: 50 },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: periodLabels,
      axisLabel: { rotate: periodLabels.length > 12 ? 45 : 0 },
    },
    yAxis: {
      type: 'value' as const,
      name: 'Reviews',
    },
    series,
  }

  return (
    <div className="topic-timeline">
      <h3>Topic Trend Over Time</h3>
      <div className="timeline-controls">
        <label>
          Granularity:
          <select value={granularity} onChange={e => setGranularity(e.target.value as Granularity)}>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
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
      <ReactECharts option={option} style={{ height: 350 }} />
    </div>
  )
}
```

- [ ] **Step 3: Integrate into TopicAnalysis**

In `src/renderer/src/components/TopicAnalysis.tsx`, add the import at the top:

```typescript
import { TopicTimeline } from './TopicTimeline'
```

Insert the TopicTimeline component BEFORE the `topics-grid` div. Find the line `{result && (` followed by `<div className="topics-grid">` (around line 285-286). Add the timeline between `{result && (` and the topics-grid:

```tsx
      {result && (
        <>
          {result.topics_over_time && (result.topics_over_time.weekly.length > 0 || result.topics_over_time.monthly.length > 0) && (
            <TopicTimeline analysisResult={result} />
          )}
          <div className="topics-grid">
```

And close the fragment after the topics-grid closing `</div>`:

```tsx
          </div>
        </>
      )}
```

The result is that the `{result && (` block wraps a fragment `<>` containing both `TopicTimeline` and the existing `topics-grid`.

- [ ] **Step 4: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add src/renderer/src/components/TopicTimeline.tsx src/renderer/src/components/TopicAnalysis.tsx
git commit -m "feat(ui): add topic trend over time stacked area chart"
```
