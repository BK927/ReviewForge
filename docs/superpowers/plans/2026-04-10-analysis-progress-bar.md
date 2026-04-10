# Analysis Progress Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the text-only analysis progress with a step-based pipeline indicator, progress bar, and ETA for the embedding stage.

**Architecture:** Python sidecar sends `stage` and `elapsed_ms` fields with progress messages. React renders an `AnalysisProgress` component with three-step indicator, progress bar (embedding only), and computed ETA.

**Tech Stack:** Python (protocol/analyzer/embeddings), React/TypeScript, CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `python/protocol.py` | Add `stage` and `elapsed_ms` to `format_progress` |
| Modify | `python/analyzer.py` | Pass `stage` with each progress call |
| Modify | `python/embeddings.py` | Track elapsed time, pass `stage` + `elapsed_ms` |
| Create | `src/renderer/src/components/AnalysisProgress.tsx` | Step indicator + progress bar + ETA display |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx` | Structured progress state, use `AnalysisProgress` |
| Modify | `src/renderer/src/assets/styles.css` | Progress bar and step indicator styles |

---

### Task 1: Extend Python protocol with `stage` and `elapsed_ms`

**Files:**
- Modify: `python/protocol.py:21-22`

- [ ] **Step 1: Update `format_progress` signature and body**

Replace the current `format_progress` function in `python/protocol.py`:

```python
def format_progress(msg_id: str, percent: int, message: str, stage: str | None = None, elapsed_ms: int | None = None) -> str:
    data: dict = {"percent": percent, "message": message}
    if stage is not None:
        data["stage"] = stage
    if elapsed_ms is not None:
        data["elapsed_ms"] = elapsed_ms
    return json.dumps({"id": msg_id, "type": "progress", "data": data}, ensure_ascii=False)
```

- [ ] **Step 2: Verify protocol still works**

Run from project root:
```bash
python -c "from protocol import format_progress; print(format_progress('test', 50, 'hello')); print(format_progress('test', 50, 'hello', stage='embedding', elapsed_ms=1234))"
```
Expected: Two JSON lines — first without stage/elapsed_ms, second with them.

- [ ] **Step 3: Commit**

```bash
git add python/protocol.py
git commit -m "feat(protocol): add stage and elapsed_ms to format_progress"
```

---

### Task 2: Add stage info to `analyzer.py` progress calls

**Files:**
- Modify: `python/analyzer.py:19-21,27,40,49,56`

- [ ] **Step 1: Update the progress helper to accept stage**

Replace the `progress` inner function and all calls in `run_analysis` in `python/analyzer.py`:

```python
def progress(pct, msg, stage=None, elapsed_ms=None):
    sys.stdout.write(format_progress(msg_id, pct, msg, stage=stage, elapsed_ms=elapsed_ms) + "\n")
    sys.stdout.flush()
```

- [ ] **Step 2: Update each progress call with its stage**

In `run_analysis`, update the four progress calls:

```python
progress(5, "Generating embeddings...", stage="embedding")
```
(line ~27, before `generate_embeddings` call)

```python
progress(60, "Clustering reviews...", stage="clustering")
```
(line ~40, after embeddings complete)

```python
progress(80, "Extracting keywords...", stage="keywords")
```
(line ~49, before negative topics)

```python
progress(100, "Analysis complete", stage="complete")
```
(line ~56, at the end)

- [ ] **Step 3: Update `generate_embeddings` callback signature**

In `analyzer.py`, the `generate_embeddings` call at line ~30 uses `msg_id` directly — embeddings.py writes progress to stdout itself. No change needed here since embeddings.py will handle its own stage/elapsed_ms in Task 3.

- [ ] **Step 4: Commit**

```bash
git add python/analyzer.py
git commit -m "feat(analyzer): pass stage field with progress messages"
```

---

### Task 3: Track elapsed time in `embeddings.py`

**Files:**
- Modify: `python/embeddings.py:1,18-19,22,35-49`

- [ ] **Step 1: Add `time` import and update `on_progress` to pass stage/elapsed_ms**

At the top of `python/embeddings.py`, add `import time` after `import sys`.

- [ ] **Step 2: Update `generate_embeddings` progress calls**

In `generate_embeddings`, update the first progress call:

```python
on_progress(5, f"Loading model {model_name}...", stage="embedding", elapsed_ms=0)
```

And the final one:

```python
on_progress(100, "Embeddings complete", stage="embedding", elapsed_ms=0)
```

- [ ] **Step 3: Update `on_progress` inner function to accept and forward kwargs**

In `generate_embeddings`, change the `on_progress` function:

```python
def on_progress(percent, message, stage=None, elapsed_ms=None):
    sys.stdout.write(format_progress(msg_id, percent, message, stage=stage, elapsed_ms=elapsed_ms) + "\n")
    sys.stdout.flush()
```

- [ ] **Step 4: Track elapsed time in `_embed_with_sentence_transformers`**

Update the function signature and body in `python/embeddings.py`:

```python
def _embed_with_sentence_transformers(model_path: str, texts: list[str], on_progress: Callable) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_path)
    batch_size = 64
    all_embeddings = []
    t_start = time.time()

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        emb = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        all_embeddings.append(emb)
        processed = min(i + len(batch), len(texts))
        percent = min(95, int(10 + 85 * processed / len(texts)))
        elapsed_ms = int((time.time() - t_start) * 1000)
        on_progress(percent, f"Embedded {processed}/{len(texts)} reviews", stage="embedding", elapsed_ms=elapsed_ms)

    return np.vstack(all_embeddings)
```

- [ ] **Step 5: Test end-to-end with a small analysis**

Run from project root (using the project's Python venv):

```bash
echo '{"id":"t","method":"analyze","params":{"reviews":[{"id":"1","text":"good","voted_up":true,"language":"en","playtime":100},{"id":"2","text":"bad","voted_up":false,"language":"en","playtime":50}],"config":{"n_topics":2,"tier":0}}}' | python/.venv/Scripts/python.exe python/main.py 2>/dev/null | head -20
```

Expected: JSON lines with `"stage"` and `"elapsed_ms"` fields in progress messages. Final result should have `positive_topics` and `negative_topics`.

- [ ] **Step 6: Commit**

```bash
git add python/embeddings.py
git commit -m "feat(embeddings): track elapsed time and send stage with progress"
```

---

### Task 4: Create `AnalysisProgress` React component

**Files:**
- Create: `src/renderer/src/components/AnalysisProgress.tsx`

- [ ] **Step 1: Create the component file**

Create `src/renderer/src/components/AnalysisProgress.tsx`:

```tsx
const STAGES = ['embedding', 'clustering', 'keywords'] as const
type Stage = typeof STAGES[number]

const STAGE_LABELS: Record<Stage, string> = {
  embedding: 'Embedding',
  clustering: 'Clustering',
  keywords: 'Keywords'
}

export interface ProgressData {
  stage: 'idle' | Stage | 'complete'
  percent: number
  message: string
  elapsed_ms: number
}

function getStageState(stage: Stage, current: ProgressData['stage']): 'pending' | 'active' | 'completed' {
  if (current === 'complete') return 'completed'
  const currentIdx = STAGES.indexOf(current as Stage)
  const stageIdx = STAGES.indexOf(stage)
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
  // Skip first 3 batches (192 reviews at batch_size=64) for warmup
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

export function AnalysisProgress({ data }: { data: ProgressData }) {
  const counts = data.stage === 'embedding' ? parseEmbeddingCounts(data.message) : null
  const eta = counts ? computeEta(data.elapsed_ms, counts.processed, counts.total) : null

  return (
    <div className="analysis-progress">
      <div className="progress-steps">
        {STAGES.map((stage, i) => {
          const state = getStageState(stage, data.stage)
          return (
            <div key={stage} className={`progress-step ${state}`}>
              <span className="step-icon">
                {state === 'completed' ? '\u2713' : state === 'active' ? '\u25CF' : '\u25CB'}
              </span>
              <span className="step-label">{STAGE_LABELS[stage]}</span>
              {i < STAGES.length - 1 && <span className="step-arrow">\u2192</span>}
            </div>
          )
        })}
      </div>

      {data.stage === 'embedding' && counts && (
        <>
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.min(data.percent, 100)}%` }}
            />
          </div>
          <div className="progress-detail">
            <span>Embedded {counts.processed.toLocaleString()} / {counts.total.toLocaleString()} reviews</span>
            {eta && <span className="progress-eta">{eta}</span>}
          </div>
        </>
      )}

      {(data.stage === 'clustering' || data.stage === 'keywords') && (
        <div className="progress-detail">
          <span className="progress-spinner" />
          <span>{data.message}</span>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/renderer/src/components/AnalysisProgress.tsx
git commit -m "feat: add AnalysisProgress step indicator component"
```

---

### Task 5: Integrate `AnalysisProgress` into `TopicAnalysis`

**Files:**
- Modify: `src/renderer/src/components/TopicAnalysis.tsx:1-2,27-29,45-52,60,101-103,118`

- [ ] **Step 1: Replace string progress state with structured state**

In `TopicAnalysis.tsx`, replace the `progress` state and add the import:

At the top, add the import:
```tsx
import { AnalysisProgress, ProgressData } from './AnalysisProgress'
```

Replace `const [progress, setProgress] = useState('')` with:
```tsx
const [progress, setProgress] = useState<ProgressData>({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
```

- [ ] **Step 2: Update `onProgress` listener to parse structured data**

Replace the `onProgress` effect:

```tsx
useEffect(() => {
  const cleanup = api.onProgress((data: any) => {
    if (data.type === 'analysis' && data.appId === appId) {
      setProgress({
        stage: data.stage ?? 'embedding',
        percent: data.percent ?? 0,
        message: data.message ?? '',
        elapsed_ms: data.elapsed_ms ?? 0
      })
    }
  })
  return () => { cleanup() }
}, [appId])
```

- [ ] **Step 3: Update `runAnalysis` to use structured progress**

In `runAnalysis`, update the initial progress set and the reset in `appId` effect:

```tsx
setProgress({ stage: 'idle', percent: 0, message: 'Starting analysis...', elapsed_ms: 0 })
```

In the `finally` block:
```tsx
setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
```

In the `appId` useEffect reset:
```tsx
setProgress({ stage: 'idle', percent: 0, message: '', elapsed_ms: 0 })
```

- [ ] **Step 4: Replace button progress text and skeleton with `AnalysisProgress`**

For the button, change the loading text:
```tsx
<button onClick={runAnalysis} disabled={loading}>
  {loading ? 'Analyzing...' : 'Run Analysis'}
</button>
```

Replace `{loading && <TopicsSkeleton />}` with:
```tsx
{loading && <AnalysisProgress data={progress} />}
```

- [ ] **Step 5: Type check**

Run:
```bash
npx tsc --noEmit -p tsconfig.web.json --composite false
```
Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add src/renderer/src/components/TopicAnalysis.tsx
git commit -m "feat(topics): integrate AnalysisProgress with structured progress state"
```

---

### Task 6: Add CSS styles for progress bar and step indicator

**Files:**
- Modify: `src/renderer/src/assets/styles.css` (insert after `.analysis-error` block, before `.analysis-meta`)

- [ ] **Step 1: Add all progress bar styles**

Insert after the `.analysis-error { ... }` block (after line ~468) in `styles.css`:

```css
/* ── Analysis Progress ── */
.analysis-progress {
  margin-bottom: 20px;
}

.progress-steps {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}

.progress-step {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #9ca3af;
}

.progress-step.active {
  color: #6d28d9;
  font-weight: 600;
}

.progress-step.completed {
  color: #16a34a;
}

.step-icon {
  font-size: 12px;
}

.step-arrow {
  margin: 0 8px;
  color: #d1d5db;
}

.progress-bar-track {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar-fill {
  height: 100%;
  background: #6d28d9;
  border-radius: 4px;
  transition: width 300ms ease-out;
}

.progress-detail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
}

.progress-eta {
  font-weight: 500;
  color: #6d28d9;
}

.progress-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #e5e7eb;
  border-top-color: #6d28d9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 8px;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/renderer/src/assets/styles.css
git commit -m "feat: add CSS styles for analysis progress bar and step indicator"
```

---

### Task 7: Final verification

- [ ] **Step 1: Type check all**

```bash
npx tsc --noEmit -p tsconfig.node.json --composite false
npx tsc --noEmit -p tsconfig.web.json --composite false
```
Expected: No errors for both.

- [ ] **Step 2: Test Python sidecar end-to-end**

```bash
echo '{"id":"t","method":"analyze","params":{"reviews":[{"id":"1","text":"great game","voted_up":true,"language":"en","playtime":100},{"id":"2","text":"terrible","voted_up":false,"language":"en","playtime":50}],"config":{"n_topics":2,"tier":0}}}' | python/.venv/Scripts/python.exe python/main.py 2>/dev/null
```

Expected: JSON output includes progress lines with `"stage"` and `"elapsed_ms"` fields, followed by a result line.

- [ ] **Step 3: Visual check**

Run `pnpm dev`, navigate to Topics tab, click Run Analysis. Verify:
- Three-step indicator shows with correct stage highlighting
- Progress bar fills during embedding stage
- ETA appears after a few seconds of embedding
- Clustering/Keywords show spinner
- After completion, progress bar disappears and results display

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address progress bar integration issues"
```
