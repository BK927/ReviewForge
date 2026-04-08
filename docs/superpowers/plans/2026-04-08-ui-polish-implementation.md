# UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ReviewForge UI compact, responsive, and juicy — reduce excessive padding, add responsive breakpoints with collapsible sidebar, and layer in micro-interactions (hover/press, tab transitions, count-up animations, loading skeletons).

**Architecture:** Pure CSS changes for layout/hover/transitions (no new dependencies). One new React hook (`useCountUp`) for number animations. One new component (`Skeleton.tsx`) for loading states. Sidebar collapse managed via React state in `Layout.tsx` + CSS classes. ECharts built-in animation options for chart effects.

**Tech Stack:** React 18, CSS (no preprocessor), ECharts (echarts-for-react), Electron renderer process.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/renderer/src/assets/styles.css` | Modify | CSS variables, compact layout, media queries, sidebar collapse, hover/press, tab indicator, skeleton styles, transitions |
| `src/renderer/src/components/Layout.tsx` | Modify | Sidebar collapse state + toggle, tab indicator element + ref, content transition wrapper |
| `src/renderer/src/components/GameSidebar.tsx` | Modify | Accept `collapsed` prop, render condensed mode |
| `src/renderer/src/hooks/useCountUp.ts` | Create | Animated number hook |
| `src/renderer/src/components/Dashboard.tsx` | Modify | Apply count-up to stats, add ECharts animation options, use skeleton loading |
| `src/renderer/src/components/Skeleton.tsx` | Create | SkeletonCard, SkeletonText, SkeletonCircle components |
| `src/renderer/src/components/TopicAnalysis.tsx` | Modify | Use skeleton loading state |
| `src/renderer/src/components/SegmentAnalysis.tsx` | Modify | Use skeleton loading state |

---

### Task 1: CSS Custom Properties & Compact Layout

**Files:**
- Modify: `src/renderer/src/assets/styles.css`

- [ ] **Step 1: Add CSS custom properties at root**

At the top of `styles.css`, after the `body` rule, add a `:root` block with layout variables:

```css
:root {
  --content-padding: 12px;
  --grid-gap: 12px;
  --sidebar-width: 260px;
  --sidebar-collapsed-width: 48px;
}
```

- [ ] **Step 2: Update `.tab-content` to use CSS variable**

Change `.tab-content` from:
```css
.tab-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
```
To:
```css
.tab-content {
  flex: 1;
  padding: var(--content-padding);
  overflow-y: auto;
}
```

- [ ] **Step 3: Update `.charts-grid` to use CSS variable and auto-fill**

Change `.charts-grid` from:
```css
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
}
```
To:
```css
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--grid-gap);
}
```

- [ ] **Step 4: Update `.tab-nav` padding**

Change `.tab-nav` padding from `0 24px` to `0 var(--content-padding)`.

- [ ] **Step 5: Update `.sidebar` to use CSS variable**

Change `.sidebar` width from `260px` to `var(--sidebar-width)`.

- [ ] **Step 6: Verify — run `pnpm dev` and check layout**

Run: `cd C:/Users/BK927/repo/ReviewForge && pnpm dev`

Expected: Content area has tighter padding (12px instead of 24px), chart cards fill width better. No visual breakage.

- [ ] **Step 7: Commit**

```bash
git add src/renderer/src/assets/styles.css
git commit -m "feat(ui): compact layout with CSS custom properties"
```

---

### Task 2: Responsive Media Queries

**Files:**
- Modify: `src/renderer/src/assets/styles.css`

- [ ] **Step 1: Add responsive breakpoints at end of `styles.css`**

Append the following media queries:

```css
/* ── Responsive ── */
@media (max-width: 800px) {
  :root {
    --content-padding: 8px;
    --grid-gap: 8px;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }

  .topics-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 1201px) {
  :root {
    --content-padding: 16px;
    --grid-gap: 16px;
  }
}
```

- [ ] **Step 2: Verify — resize window to narrow (<800px), medium, and wide (>1200px)**

Expected:
- Narrow: 1-column grid, 8px padding
- Medium: 2-column grid, 12px padding
- Wide: 3-column grid, 16px padding

- [ ] **Step 3: Commit**

```bash
git add src/renderer/src/assets/styles.css
git commit -m "feat(ui): responsive breakpoints for narrow/medium/wide"
```

---

### Task 3: Collapsible Sidebar — CSS

**Files:**
- Modify: `src/renderer/src/assets/styles.css`

- [ ] **Step 1: Add sidebar collapsed styles**

Add these rules after the existing sidebar section in `styles.css`:

```css
/* ── Sidebar Collapse ── */
.sidebar {
  transition: width 250ms ease-out;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar.collapsed .sidebar-header {
  padding: 12px 8px;
  text-align: center;
}

.sidebar.collapsed .app-title {
  font-size: 14px;
  overflow: hidden;
  white-space: nowrap;
}

.sidebar.collapsed .app-title::after {
  content: 'RF';
}

.sidebar.collapsed .app-title span {
  display: none;
}

.sidebar.collapsed .game-input {
  display: none;
}

.sidebar.collapsed .game-list li {
  padding: 8px;
  justify-content: center;
}

.sidebar.collapsed .game-info .game-name {
  display: none;
}

.sidebar.collapsed .game-info .game-score {
  display: none;
}

.sidebar.collapsed .game-info {
  width: 24px;
  height: 24px;
  min-width: 24px;
  background: #313244;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #cdd6f4;
}

.sidebar.collapsed .delete-btn {
  display: none;
}

.sidebar-toggle {
  background: none;
  border: none;
  color: #6c7086;
  cursor: pointer;
  padding: 8px;
  font-size: 16px;
  border-top: 1px solid #313244;
  text-align: center;
  width: 100%;
}

.sidebar-toggle:hover {
  color: #cdd6f4;
  background: #313244;
}
```

- [ ] **Step 2: Commit**

```bash
git add src/renderer/src/assets/styles.css
git commit -m "feat(ui): sidebar collapsed CSS styles"
```

---

### Task 4: Collapsible Sidebar — React Logic

**Files:**
- Modify: `src/renderer/src/components/Layout.tsx`
- Modify: `src/renderer/src/components/GameSidebar.tsx`

- [ ] **Step 1: Add collapse state and toggle to Layout.tsx**

In `Layout.tsx`, add state and pass to `GameSidebar`:

```tsx
const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
```

Update the `GameSidebar` usage:

```tsx
<GameSidebar
  selectedAppId={selectedAppId}
  onSelectGame={setSelectedAppId}
  compareMode={compareMode}
  compareIds={compareIds}
  onToggleCompare={handleToggleCompare}
  collapsed={sidebarCollapsed}
  onToggleCollapse={() => setSidebarCollapsed(prev => !prev)}
/>
```

- [ ] **Step 2: Update GameSidebar.tsx to accept collapse props**

Add `collapsed` and `onToggleCollapse` to the Props interface:

```tsx
interface Props {
  selectedAppId: number | null
  onSelectGame: (appId: number) => void
  compareMode?: boolean
  compareIds?: number[]
  onToggleCompare?: (appId: number) => void
  collapsed?: boolean
  onToggleCollapse?: () => void
}
```

Update the component to use the `collapsed` class and render toggle button:

```tsx
export function GameSidebar({ selectedAppId, onSelectGame, compareMode, compareIds, onToggleCompare, collapsed, onToggleCollapse }: Props) {
```

Change `<aside className="sidebar">` to:

```tsx
<aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
```

Change the `<h1 className="app-title">` to:

```tsx
<h1 className="app-title">
  <span>ReviewForge</span>
</h1>
```

In collapsed mode, each game list `<li>` should show only an initial. Update the game-info div inside the map to show an initial when collapsed:

```tsx
<div className="game-info">
  {collapsed ? (
    game.app_name.charAt(0).toUpperCase()
  ) : (
    <>
      <span className="game-name">{game.app_name}</span>
      <span className="game-score">{game.review_score_desc}</span>
    </>
  )}
</div>
```

Add the toggle button at the bottom of the sidebar, before the closing `</aside>`:

```tsx
<button className="sidebar-toggle" onClick={onToggleCollapse} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
  {collapsed ? '»' : '«'}
</button>
```

- [ ] **Step 3: Add auto-collapse on narrow windows in Layout.tsx**

Add a `useEffect` that listens to window resize and auto-collapses below 800px:

```tsx
useEffect(() => {
  const handleResize = () => {
    if (window.innerWidth < 800) {
      setSidebarCollapsed(true)
    }
  }
  handleResize() // check on mount
  window.addEventListener('resize', handleResize)
  return () => window.removeEventListener('resize', handleResize)
}, [])
```

- [ ] **Step 4: Verify — click toggle button, resize window below 800px**

Expected: Sidebar smoothly collapses to 48px with game initials. Auto-collapses on narrow windows. Toggle button works both ways.

- [ ] **Step 5: Commit**

```bash
git add src/renderer/src/components/Layout.tsx src/renderer/src/components/GameSidebar.tsx
git commit -m "feat(ui): collapsible sidebar with auto-collapse on narrow windows"
```

---

### Task 5: Hover & Press Feedback

**Files:**
- Modify: `src/renderer/src/assets/styles.css`

- [ ] **Step 1: Add card hover transitions**

Update `.chart-card` to add transition and hover:

```css
.chart-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  transition: transform 200ms ease-out, box-shadow 200ms ease-out;
}

.chart-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(109, 40, 217, 0.12);
}
```

Do the same for `.topic-card`:

```css
.topic-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  background: white;
  cursor: pointer;
  transition: transform 200ms ease-out, box-shadow 200ms ease-out;
}

.topic-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(109, 40, 217, 0.12);
}
```

And `.game-info-card`:

```css
.game-info-card {
  background: white;
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  transition: transform 200ms ease-out, box-shadow 200ms ease-out;
}

.game-info-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(109, 40, 217, 0.12);
}
```

- [ ] **Step 2: Add button hover/active effects**

Add generic button interaction styles. For the primary action buttons (`.collection-progress button`, `.analysis-controls button`, `.game-input button`):

```css
.collection-progress button,
.analysis-controls button,
.game-input button {
  transition: transform 150ms ease-out, background-color 150ms ease-out;
}

.collection-progress button:hover:not(:disabled),
.analysis-controls button:hover:not(:disabled),
.game-input button:hover:not(:disabled) {
  transform: scale(1.02);
}

.collection-progress button:active:not(:disabled),
.analysis-controls button:active:not(:disabled),
.game-input button:active:not(:disabled) {
  transform: scale(0.97);
}
```

For secondary buttons (`.export-actions button`, `.trend-toggle button`, `.dialog-actions button`):

```css
.export-actions button,
.dialog-actions button {
  transition: transform 150ms ease-out, background-color 150ms ease-out;
}

.export-actions button:hover,
.dialog-actions button:hover {
  transform: scale(1.02);
}

.export-actions button:active,
.dialog-actions button:active {
  transform: scale(0.97);
}
```

- [ ] **Step 3: Enhance sidebar game item hover**

Update `.game-list li:hover` to have a smoother transition:

```css
.game-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background-color 150ms ease-out;
}
```

- [ ] **Step 4: Verify — hover over cards, click buttons, hover sidebar items**

Expected: Cards lift on hover with purple-tinted shadow. Buttons scale up on hover, scale down on click. Sidebar items have smooth background transition.

- [ ] **Step 5: Commit**

```bash
git add src/renderer/src/assets/styles.css
git commit -m "feat(ui): hover and press feedback for cards, buttons, sidebar"
```

---

### Task 6: Tab Sliding Indicator

**Files:**
- Modify: `src/renderer/src/assets/styles.css`
- Modify: `src/renderer/src/components/Layout.tsx`

- [ ] **Step 1: Add tab indicator CSS**

Add these styles after the existing tab-nav section:

```css
.tab-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 var(--content-padding);
  background: white;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
  position: relative;
}

.tab-indicator {
  position: absolute;
  bottom: 0;
  height: 2px;
  background: #6d28d9;
  transition: left 300ms cubic-bezier(0.4, 0, 0.2, 1), width 300ms cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 1px 1px 0 0;
}

.tab-nav button.active {
  border-bottom-color: transparent;
  color: #6d28d9;
}
```

Note: We override `.tab-nav button.active` to remove the static border-bottom since the sliding indicator replaces it.

- [ ] **Step 2: Add indicator element and ref logic in Layout.tsx**

Add imports and refs at the top of `Layout`:

```tsx
import { useState, useRef, useEffect, useCallback } from 'react'
```

Add refs inside the component:

```tsx
const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map())
const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 })
```

Add a function to update indicator position:

```tsx
const updateIndicator = useCallback(() => {
  const currentId = compareMode ? '__compare__' : activeTab
  const el = tabRefs.current.get(currentId)
  if (el) {
    setIndicatorStyle({ left: el.offsetLeft, width: el.offsetWidth })
  }
}, [activeTab, compareMode])

useEffect(() => {
  updateIndicator()
}, [updateIndicator])

useEffect(() => {
  window.addEventListener('resize', updateIndicator)
  return () => window.removeEventListener('resize', updateIndicator)
}, [updateIndicator])
```

Update the tab buttons to store refs:

```tsx
{TABS.map(tab => (
  <button
    key={tab.id}
    ref={el => { if (el) tabRefs.current.set(tab.id, el) }}
    className={activeTab === tab.id && !compareMode ? 'active' : ''}
    onClick={() => { setActiveTab(tab.id); setCompareMode(false) }}
  >
    {tab.label}
  </button>
))}
```

Also add ref to the compare button:

```tsx
<button
  ref={el => { if (el) tabRefs.current.set('__compare__', el) }}
  className={compareMode ? 'active compare-btn' : 'compare-btn'}
  onClick={() => compareMode ? exitCompare() : setCompareMode(true)}
>
  {compareMode ? 'Exit Compare' : 'Compare'}
</button>
```

Add the indicator element inside `.tab-nav`, after the settings button:

```tsx
<div className="tab-indicator" style={{ left: indicatorStyle.left, width: indicatorStyle.width }} />
```

- [ ] **Step 3: Verify — click through tabs, observe indicator sliding**

Expected: Purple indicator bar smoothly slides between tabs. Also slides to Compare when compare mode is activated.

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/assets/styles.css src/renderer/src/components/Layout.tsx
git commit -m "feat(ui): sliding tab indicator with smooth transitions"
```

---

### Task 7: Tab Content Transition

**Files:**
- Modify: `src/renderer/src/assets/styles.css`
- Modify: `src/renderer/src/components/Layout.tsx`

- [ ] **Step 1: Add content transition CSS**

```css
/* ── Tab Content Transition ── */
.tab-content-inner {
  animation: tabFadeIn 250ms ease-out;
}

@keyframes tabFadeIn {
  from {
    opacity: 0;
    transform: translateX(12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

- [ ] **Step 2: Add key-based re-mount in Layout.tsx**

Wrap the content in a keyed div so React re-mounts it on tab change, triggering the animation. In `Layout.tsx`, replace the content inside `.tab-content`:

Change:
```tsx
<div className="tab-content">
  {compareMode && compareIds.length === 2 ? (
    <CompareView appIds={compareIds as [number, number]} />
  ) : compareMode ? (
    <div className="empty-state">Select 2 games from the sidebar to compare</div>
  ) : (
    children(selectedAppId, activeTab)
  )}
</div>
```

To:
```tsx
<div className="tab-content">
  <div className="tab-content-inner" key={compareMode ? 'compare' : activeTab}>
    {compareMode && compareIds.length === 2 ? (
      <CompareView appIds={compareIds as [number, number]} />
    ) : compareMode ? (
      <div className="empty-state">Select 2 games from the sidebar to compare</div>
    ) : (
      children(selectedAppId, activeTab)
    )}
  </div>
</div>
```

- [ ] **Step 3: Verify — switch tabs, observe fade+slide animation**

Expected: Each tab switch shows a subtle fade-in from the right (12px slide + opacity).

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/assets/styles.css src/renderer/src/components/Layout.tsx
git commit -m "feat(ui): tab content fade-slide transition on switch"
```

---

### Task 8: useCountUp Hook

**Files:**
- Create: `src/renderer/src/hooks/useCountUp.ts`

- [ ] **Step 1: Create the hook**

```ts
import { useState, useEffect, useRef } from 'react'

export function useCountUp(target: number, duration = 600): number {
  const [current, setCurrent] = useState(0)
  const prevTarget = useRef(0)

  useEffect(() => {
    const start = prevTarget.current
    prevTarget.current = target
    if (target === 0) {
      setCurrent(0)
      return
    }

    const startTime = performance.now()

    let rafId: number
    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // ease-out: 1 - (1 - t)^3
      const eased = 1 - Math.pow(1 - progress, 3)
      setCurrent(Math.round(start + (target - start) * eased))

      if (progress < 1) {
        rafId = requestAnimationFrame(animate)
      }
    }

    rafId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafId)
  }, [target, duration])

  return current
}
```

- [ ] **Step 2: Commit**

```bash
git add src/renderer/src/hooks/useCountUp.ts
git commit -m "feat(ui): useCountUp hook for animated number transitions"
```

---

### Task 9: Dashboard Count-Up & ECharts Animations

**Files:**
- Modify: `src/renderer/src/components/Dashboard.tsx`

- [ ] **Step 1: Import useCountUp and apply to stats**

Add import:
```tsx
import { useCountUp } from '../hooks/useCountUp'
```

Inside the component, after the `if (!game || !stats)` guard, add count-up values:

```tsx
const animatedCollected = useCountUp(stats.total_collected)
const animatedPositiveRate = useCountUp(Math.round(stats.positive_rate * 1000)) // x10 for 1 decimal
const recentPosRateRaw = recentPosRate !== null ? Math.round(recentPosRate * 1000) : 0
const animatedRecentRate = useCountUp(recentPosRateRaw)
```

Update the stats-row to use animated values:

```tsx
<div className="stats-row">
  <span>Total on Steam: {game.total_reviews.toLocaleString()}</span>
  <span>Collected: {animatedCollected.toLocaleString()}</span>
  <span>All-time positive: {(animatedPositiveRate / 10).toFixed(1)}%</span>
  {recentPosRate !== null && (
    <span>Last 30d positive: {(animatedRecentRate / 10).toFixed(1)}%</span>
  )}
</div>
```

- [ ] **Step 2: Add ECharts animation options to all charts**

Add animation properties to `donutOption`:

```tsx
const donutOption = {
  tooltip: { trigger: 'item' },
  animationDuration: 400,
  animationEasing: 'cubicOut',
  series: [{ /* existing */ }]
}
```

Add to `trendOption`:

```tsx
const trendOption = {
  tooltip: { trigger: 'axis' },
  animationDuration: 400,
  animationEasing: 'cubicOut',
  animationDelay: (idx: number) => idx * 100,
  xAxis: { /* existing */ },
  yAxis: { /* existing */ },
  series: [/* existing */]
}
```

Add to `langOption`:

```tsx
const langOption = {
  tooltip: { trigger: 'axis' },
  animationDuration: 400,
  animationEasing: 'cubicOut',
  animationDelay: (idx: number) => idx * 100,
  xAxis: { /* existing */ },
  yAxis: { /* existing */ },
  series: [/* existing */]
}
```

- [ ] **Step 3: Verify — select a game, observe numbers counting up and charts animating**

Expected: Stats numbers animate from 0 to their values. Charts bars/donut grow in with staggered delay.

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/components/Dashboard.tsx
git commit -m "feat(ui): count-up stats and ECharts animations on Dashboard"
```

---

### Task 10: Add ECharts Animations to Segments

**Files:**
- Modify: `src/renderer/src/components/SegmentAnalysis.tsx`

- [ ] **Step 1: Add animation options to all chart options**

Add to `playtimeOption`:
```tsx
animationDuration: 400,
animationEasing: 'cubicOut' as const,
```

Add to `langOption`:
```tsx
animationDuration: 400,
animationEasing: 'cubicOut' as const,
animationDelay: (idx: number) => idx * 100,
```

Add to `purchaseOption`:
```tsx
animationDuration: 400,
animationEasing: 'cubicOut' as const,
```

- [ ] **Step 2: Commit**

```bash
git add src/renderer/src/components/SegmentAnalysis.tsx
git commit -m "feat(ui): ECharts animations for Segment charts"
```

---

### Task 11: Skeleton Components

**Files:**
- Create: `src/renderer/src/components/Skeleton.tsx`
- Modify: `src/renderer/src/assets/styles.css`

- [ ] **Step 1: Add skeleton CSS styles**

Append to `styles.css`:

```css
/* ── Skeleton Loading ── */
@keyframes shimmer {
  0% { background-position: -200px 0; }
  100% { background-position: 200px 0; }
}

.skeleton {
  background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
  background-size: 200px 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

.skeleton-text {
  height: 14px;
  margin-bottom: 8px;
}

.skeleton-text.short { width: 40%; }
.skeleton-text.medium { width: 65%; }
.skeleton-text.long { width: 90%; }

.skeleton-circle {
  border-radius: 50%;
}

.skeleton-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.skeleton-chart {
  height: 300px;
  border-radius: 6px;
}
```

- [ ] **Step 2: Create Skeleton.tsx component**

```tsx
export function SkeletonText({ width }: { width?: 'short' | 'medium' | 'long' | string }) {
  const cls = width === 'short' || width === 'medium' || width === 'long'
    ? `skeleton skeleton-text ${width}`
    : 'skeleton skeleton-text'
  const style = width && !['short', 'medium', 'long'].includes(width)
    ? { width }
    : undefined
  return <div className={cls} style={style} />
}

export function SkeletonCircle({ size = 50 }: { size?: number }) {
  return <div className="skeleton skeleton-circle" style={{ width: size, height: size }} />
}

export function SkeletonChart() {
  return <div className="skeleton skeleton-chart" />
}

export function DashboardSkeleton() {
  return (
    <div className="dashboard">
      <div className="skeleton-card" style={{ marginBottom: 16 }}>
        <SkeletonText width="medium" />
        <SkeletonText width="short" />
        <div style={{ display: 'flex', gap: 20, marginTop: 12 }}>
          <SkeletonText width="120px" />
          <SkeletonText width="100px" />
          <SkeletonText width="140px" />
        </div>
      </div>
      <div className="charts-grid">
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
      </div>
    </div>
  )
}

export function TopicsSkeleton() {
  return (
    <div className="topic-analysis">
      <div className="skeleton-card" style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
        <SkeletonText width="120px" />
        <SkeletonText width="100px" />
      </div>
      <div className="topics-grid">
        <div>
          <SkeletonText width="medium" />
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton-card" style={{ marginBottom: 8 }}>
              <SkeletonText width="long" />
              <SkeletonText width="medium" />
            </div>
          ))}
        </div>
        <div>
          <SkeletonText width="medium" />
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton-card" style={{ marginBottom: 8 }}>
              <SkeletonText width="long" />
              <SkeletonText width="medium" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function SegmentsSkeleton() {
  return (
    <div className="segment-analysis">
      <div className="skeleton-card" style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
        <SkeletonText width="100px" />
        <SkeletonText width="80px" />
        <SkeletonText width="80px" />
        <SkeletonText width="80px" />
      </div>
      <div className="charts-grid">
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
        <div className="skeleton-card"><SkeletonText width="short" /><SkeletonChart /></div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add src/renderer/src/components/Skeleton.tsx src/renderer/src/assets/styles.css
git commit -m "feat(ui): skeleton loading components with shimmer animation"
```

---

### Task 12: Apply Skeletons to Dashboard

**Files:**
- Modify: `src/renderer/src/components/Dashboard.tsx`

- [ ] **Step 1: Import and use DashboardSkeleton**

Add import:
```tsx
import { DashboardSkeleton } from './Skeleton'
```

Replace the loading guard:

Change:
```tsx
if (!game || !stats) return <div className="loading">Loading...</div>
```

To:
```tsx
if (!game || !stats) return <DashboardSkeleton />
```

- [ ] **Step 2: Verify — select a game, observe skeleton while data loads**

Expected: Shimmer skeleton cards appear while data loads, then smoothly replaced by real content.

- [ ] **Step 3: Commit**

```bash
git add src/renderer/src/components/Dashboard.tsx
git commit -m "feat(ui): skeleton loading state for Dashboard"
```

---

### Task 13: Apply Skeletons to Topics & Segments

**Files:**
- Modify: `src/renderer/src/components/TopicAnalysis.tsx`
- Modify: `src/renderer/src/components/SegmentAnalysis.tsx`

- [ ] **Step 1: Add skeleton to TopicAnalysis loading state**

Import:
```tsx
import { TopicsSkeleton } from './Skeleton'
```

In `TopicAnalysis`, the loading state is shown when `loading` is true. Wrap the area below `analysis-controls` to show skeleton while loading:

After the `analysis-controls` div, add:
```tsx
{loading && <TopicsSkeleton />}
```

This shows the skeleton while analysis is running. The existing `{result && ...}` block already handles showing results when done.

- [ ] **Step 2: Add skeleton to SegmentAnalysis initial load**

Import:
```tsx
import { SegmentsSkeleton } from './Skeleton'
```

Add a loading state to track initial load. Add state:
```tsx
const [loading, setLoading] = useState(true)
```

Wrap the existing load function:
```tsx
useEffect(() => {
  const load = async () => {
    setLoading(true)
    // ... existing filter/fetch logic ...
    setLoading(false)
  }
  load()
}, [appId, langFilter, periodFilter, playtimeFilter, purchaseFilter])
```

Replace the `<div className="charts-grid">` section with a conditional:

```tsx
{loading ? (
  <SegmentsSkeleton />
) : (
  <div className="charts-grid">
    {/* existing chart cards */}
  </div>
)}
```

- [ ] **Step 3: Verify — run analysis on Topics tab (observe skeleton), switch to Segments (observe skeleton during load)**

Expected: Shimmer skeletons appear during data loading on both tabs.

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/components/TopicAnalysis.tsx src/renderer/src/components/SegmentAnalysis.tsx
git commit -m "feat(ui): skeleton loading states for Topics and Segments tabs"
```

---

### Task 14: Final Polish & Verification

**Files:**
- Modify: `src/renderer/src/assets/styles.css` (if needed)

- [ ] **Step 1: Full visual regression check**

Run: `cd C:/Users/BK927/repo/ReviewForge && pnpm dev`

Test checklist:
1. ✅ Compact layout — padding is reduced, cards fill width
2. ✅ Responsive — resize window through narrow (<800px), medium, wide (>1200px)
3. ✅ Sidebar collapse — auto-collapses on narrow, manual toggle works
4. ✅ Hover/press — cards lift on hover, buttons scale on click
5. ✅ Tab indicator — slides between tabs smoothly
6. ✅ Tab content — fades in on switch
7. ✅ Count-up — dashboard stats animate on load
8. ✅ Chart animations — bars/donut animate in
9. ✅ Skeletons — shimmer loading on Dashboard, Topics (during analysis), Segments

- [ ] **Step 2: Fix any visual issues found**

Address any spacing, overflow, or animation glitches discovered during testing.

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix(ui): polish visual regression fixes"
```
