# ReviewForge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop app that collects and analyzes Steam game reviews with embedding-based multilingual keyword/topic extraction, helping game planners and marketers objectively understand player sentiment.

**Architecture:** Electron (React + TypeScript) for UI, Python sidecar for ML pipeline. Electron Main handles Steam API calls, SQLite storage, and Python process lifecycle. Communication between Electron and Python uses JSON-line protocol over stdin/stdout. Two-tier analysis: CPU-only (multilingual-e5-small) and GPU-enhanced (BGE-M3).

**Tech Stack:** Electron + electron-vite, React, TypeScript, better-sqlite3, ECharts, Python 3.11+, onnxruntime, scikit-learn, YAKE!, KeyBERT, HDBSCAN

---

## File Structure

```
ReviewForge/
├── package.json
├── electron.vite.config.ts
├── electron/
│   └── main/
│       ├── index.ts                 # Electron main entry, window creation
│       ├── db.ts                    # SQLite schema + CRUD
│       ├── steam-api.ts             # Steam review API client
│       ├── sidecar.ts               # Python sidecar process manager
│       └── ipc-handlers.ts          # All IPC handler registrations
│   └── preload/
│       └── index.ts                 # contextBridge API exposure
├── src/
│   ├── main.tsx                     # React entry
│   ├── App.tsx                      # Root: Layout + tab routing
│   ├── components/
│   │   ├── Layout.tsx               # Sidebar + top bar + content area
│   │   ├── GameInput.tsx            # App ID / URL input component
│   │   ├── GameSidebar.tsx          # Saved games list
│   │   ├── CollectionProgress.tsx   # Review fetch progress bar
│   │   ├── Dashboard.tsx            # Tab 1: overview charts
│   │   ├── TopicAnalysis.tsx        # Tab 2: topics + keywords
│   │   ├── SegmentAnalysis.tsx      # Tab 3: segment comparison
│   │   ├── ExportPanel.tsx          # Tab 4: export + AI
│   │   ├── CompareView.tsx          # Game comparison overlay
│   │   └── SettingsDialog.tsx       # Settings modal
│   ├── hooks/
│   │   └── useApi.ts               # Typed IPC wrapper hook
│   └── lib/
│       ├── export-utils.ts          # CSV/Markdown/Clipboard generation
│       └── steam-languages.ts       # Steam language code to display name map
├── python/
│   ├── requirements.txt
│   ├── main.py                      # Sidecar entry: stdin/stdout loop
│   ├── protocol.py                  # JSON-line message parsing
│   ├── gpu_detect.py                # CUDA/VRAM detection
│   ├── model_manager.py             # Model download + path management
│   ├── embeddings.py                # Embedding generation (Tier 0/1)
│   ├── clustering.py                # KMeans + HDBSCAN
│   ├── keywords.py                  # YAKE! + KeyBERT keyword extraction
│   └── analyzer.py                  # Orchestrator: embed -> cluster -> keywords
├── tests/
│   ├── main/
│   │   ├── db.test.ts
│   │   └── steam-api.test.ts
│   └── python/
│       ├── test_protocol.py
│       ├── test_embeddings.py
│       ├── test_clustering.py
│       └── test_keywords.py
└── resources/                        # Bundled assets (models, icons)
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `package.json`, `electron.vite.config.ts`, `electron/main/index.ts`, `electron/preload/index.ts`, `src/main.tsx`, `src/App.tsx`

- [ ] **Step 1: Scaffold electron-vite project**

```bash
cd C:/Users/BK927/repo/ReviewForge
pnpm create @electron-vite/create@latest . -- --template react-ts
```

Select React + TypeScript template. If the directory is not empty, move `docs/` aside first, scaffold, then move `docs/` back.

- [ ] **Step 2: Install core dependencies**

```bash
pnpm add better-sqlite3 echarts echarts-for-react papaparse uuid
pnpm add -D @types/better-sqlite3 @types/papaparse @types/uuid
```

- [ ] **Step 3: Verify dev server starts**

```bash
pnpmdev
```

Expected: Electron window opens with default React template.

- [ ] **Step 4: Set up Python sidecar directory**

```bash
mkdir python
```

Create `python/requirements.txt`:
```
onnxruntime>=1.18.0
numpy>=1.26.0
scikit-learn>=1.5.0
hdbscan>=0.8.38
yake>=0.4.8
keybert>=0.8.5
sentence-transformers>=3.0.0
huggingface-hub>=0.24.0
```

```bash
cd python && uv venv && uv pip install -r requirements.txt
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: scaffold electron-vite project with dependencies"
```

---

## Task 2: SQLite Database Module

**Files:**
- Create: `electron/main/db.ts`
- Test: `tests/main/db.test.ts`

- [ ] **Step 1: Write failing tests for DB initialization and CRUD**

Create `tests/main/db.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import Database from 'better-sqlite3'
import { createDb, insertGame, getGame, upsertReviews, getReviews, getGameStats } from '../../electron/main/db'
import fs from 'fs'
import path from 'path'

const TEST_DB_PATH = path.join(__dirname, 'test.db')

describe('Database', () => {
  let db: Database.Database

  beforeEach(() => {
    db = createDb(TEST_DB_PATH)
  })

  afterEach(() => {
    db.close()
    if (fs.existsSync(TEST_DB_PATH)) fs.unlinkSync(TEST_DB_PATH)
  })

  it('creates tables on init', () => {
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all() as { name: string }[]
    const names = tables.map(t => t.name)
    expect(names).toContain('games')
    expect(names).toContain('reviews')
    expect(names).toContain('embeddings')
    expect(names).toContain('analysis_cache')
  })

  it('inserts and retrieves a game', () => {
    insertGame(db, {
      app_id: 730,
      app_name: 'Counter-Strike 2',
      review_score: 8,
      review_score_desc: 'Very Positive',
      total_positive: 1000,
      total_negative: 200,
      total_reviews: 1200
    })
    const game = getGame(db, 730)
    expect(game).not.toBeNull()
    expect(game!.app_name).toBe('Counter-Strike 2')
    expect(game!.review_score_desc).toBe('Very Positive')
  })

  it('upserts reviews without duplicates', () => {
    insertGame(db, { app_id: 730, app_name: 'CS2', review_score: 8, review_score_desc: 'Very Positive', total_positive: 100, total_negative: 20, total_reviews: 120 })

    const reviews = [
      { recommendation_id: 'r1', app_id: 730, language: 'english', review_text: 'Great game', voted_up: 1, timestamp_created: 1000, timestamp_updated: 1000, playtime_at_review: 600, playtime_forever: 1200, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 10, votes_funny: 2, weighted_vote_score: 0.8, comment_count: 1 },
      { recommendation_id: 'r2', app_id: 730, language: 'koreana', review_text: '재밌어요', voted_up: 1, timestamp_created: 1001, timestamp_updated: 1001, playtime_at_review: 300, playtime_forever: 500, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 5, votes_funny: 0, weighted_vote_score: 0.6, comment_count: 0 }
    ]

    upsertReviews(db, reviews)
    upsertReviews(db, reviews) // second call should not duplicate

    const result = getReviews(db, 730)
    expect(result).toHaveLength(2)
  })

  it('filters reviews by language', () => {
    insertGame(db, { app_id: 730, app_name: 'CS2', review_score: 8, review_score_desc: 'Very Positive', total_positive: 100, total_negative: 20, total_reviews: 120 })

    upsertReviews(db, [
      { recommendation_id: 'r1', app_id: 730, language: 'english', review_text: 'Good', voted_up: 1, timestamp_created: 1000, timestamp_updated: 1000, playtime_at_review: 600, playtime_forever: 1200, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 10, votes_funny: 0, weighted_vote_score: 0.5, comment_count: 0 },
      { recommendation_id: 'r2', app_id: 730, language: 'koreana', review_text: '좋아요', voted_up: 0, timestamp_created: 1001, timestamp_updated: 1001, playtime_at_review: 300, playtime_forever: 500, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 2, votes_funny: 0, weighted_vote_score: 0.3, comment_count: 0 }
    ])

    const korean = getReviews(db, 730, { language: 'koreana' })
    expect(korean).toHaveLength(1)
    expect(korean[0].language).toBe('koreana')
  })

  it('computes game stats from reviews', () => {
    insertGame(db, { app_id: 730, app_name: 'CS2', review_score: 8, review_score_desc: 'Very Positive', total_positive: 100, total_negative: 20, total_reviews: 120 })

    upsertReviews(db, [
      { recommendation_id: 'r1', app_id: 730, language: 'english', review_text: 'Good', voted_up: 1, timestamp_created: 1000, timestamp_updated: 1000, playtime_at_review: 600, playtime_forever: 1200, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 10, votes_funny: 0, weighted_vote_score: 0.5, comment_count: 0 },
      { recommendation_id: 'r2', app_id: 730, language: 'english', review_text: 'Bad', voted_up: 0, timestamp_created: 1001, timestamp_updated: 1001, playtime_at_review: 60, playtime_forever: 100, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 2, votes_funny: 0, weighted_vote_score: 0.3, comment_count: 0 },
      { recommendation_id: 'r3', app_id: 730, language: 'koreana', review_text: '최고', voted_up: 1, timestamp_created: 1002, timestamp_updated: 1002, playtime_at_review: 900, playtime_forever: 1500, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 8, votes_funny: 0, weighted_vote_score: 0.7, comment_count: 0 }
    ])

    const stats = getGameStats(db, 730)
    expect(stats.total_collected).toBe(3)
    expect(stats.positive_rate).toBeCloseTo(0.6667, 2)
    expect(stats.languages).toEqual(expect.arrayContaining(['english', 'koreana']))
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/main/db.test.ts
```

Expected: FAIL — module `../../electron/main/db` not found.

- [ ] **Step 3: Implement database module**

Create `electron/main/db.ts`:

```typescript
import Database from 'better-sqlite3'
import path from 'path'
import { app } from 'electron'

const SCHEMA = `
CREATE TABLE IF NOT EXISTS games (
    app_id INTEGER PRIMARY KEY,
    app_name TEXT,
    review_score INTEGER,
    review_score_desc TEXT,
    total_positive INTEGER,
    total_negative INTEGER,
    total_reviews INTEGER,
    first_fetched_at INTEGER,
    last_fetched_at INTEGER
);

CREATE TABLE IF NOT EXISTS reviews (
    recommendation_id TEXT PRIMARY KEY,
    app_id INTEGER REFERENCES games(app_id),
    language TEXT,
    review_text TEXT,
    voted_up INTEGER,
    timestamp_created INTEGER,
    timestamp_updated INTEGER,
    playtime_at_review INTEGER,
    playtime_forever INTEGER,
    steam_purchase INTEGER,
    received_for_free INTEGER,
    written_during_early_access INTEGER,
    primarily_steam_deck INTEGER,
    votes_up INTEGER,
    votes_funny INTEGER,
    weighted_vote_score REAL,
    comment_count INTEGER,
    fetched_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_reviews_app_lang ON reviews(app_id, language);
CREATE INDEX IF NOT EXISTS idx_reviews_app_time ON reviews(app_id, timestamp_created);

CREATE TABLE IF NOT EXISTS embeddings (
    recommendation_id TEXT PRIMARY KEY REFERENCES reviews(recommendation_id),
    embedding_model TEXT,
    vector BLOB
);

CREATE TABLE IF NOT EXISTS analysis_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER REFERENCES games(app_id),
    analysis_type TEXT,
    language_filter TEXT,
    config_hash TEXT,
    result_json TEXT,
    created_at INTEGER
);
`

export interface GameRecord {
  app_id: number
  app_name: string
  review_score: number
  review_score_desc: string
  total_positive: number
  total_negative: number
  total_reviews: number
  first_fetched_at?: number
  last_fetched_at?: number
}

export interface ReviewRecord {
  recommendation_id: string
  app_id: number
  language: string
  review_text: string
  voted_up: number
  timestamp_created: number
  timestamp_updated: number
  playtime_at_review: number
  playtime_forever: number
  steam_purchase: number
  received_for_free: number
  written_during_early_access: number
  primarily_steam_deck: number
  votes_up: number
  votes_funny: number
  weighted_vote_score: number
  comment_count: number
  fetched_at?: number
}

export interface ReviewFilter {
  language?: string
  period_start?: number
  period_end?: number
  playtime_min?: number
  playtime_max?: number
  steam_purchase?: number
}

export function createDb(dbPath?: string): Database.Database {
  const resolvedPath = dbPath ?? path.join(app.getPath('userData'), 'reviewforge.db')
  const db = new Database(resolvedPath)
  db.pragma('journal_mode = WAL')
  db.exec(SCHEMA)
  return db
}

export function insertGame(db: Database.Database, game: Omit<GameRecord, 'first_fetched_at' | 'last_fetched_at'>): void {
  const now = Math.floor(Date.now() / 1000)
  db.prepare(`
    INSERT INTO games (app_id, app_name, review_score, review_score_desc, total_positive, total_negative, total_reviews, first_fetched_at, last_fetched_at)
    VALUES (@app_id, @app_name, @review_score, @review_score_desc, @total_positive, @total_negative, @total_reviews, @first_fetched_at, @last_fetched_at)
    ON CONFLICT(app_id) DO UPDATE SET
      app_name = @app_name, review_score = @review_score, review_score_desc = @review_score_desc,
      total_positive = @total_positive, total_negative = @total_negative, total_reviews = @total_reviews,
      last_fetched_at = @last_fetched_at
  `).run({ ...game, first_fetched_at: now, last_fetched_at: now })
}

export function getGame(db: Database.Database, appId: number): GameRecord | null {
  return (db.prepare('SELECT * FROM games WHERE app_id = ?').get(appId) as GameRecord) ?? null
}

export function getAllGames(db: Database.Database): GameRecord[] {
  return db.prepare('SELECT * FROM games ORDER BY last_fetched_at DESC').all() as GameRecord[]
}

export function upsertReviews(db: Database.Database, reviews: Omit<ReviewRecord, 'fetched_at'>[]): void {
  const now = Math.floor(Date.now() / 1000)
  const stmt = db.prepare(`
    INSERT INTO reviews (recommendation_id, app_id, language, review_text, voted_up, timestamp_created, timestamp_updated, playtime_at_review, playtime_forever, steam_purchase, received_for_free, written_during_early_access, primarily_steam_deck, votes_up, votes_funny, weighted_vote_score, comment_count, fetched_at)
    VALUES (@recommendation_id, @app_id, @language, @review_text, @voted_up, @timestamp_created, @timestamp_updated, @playtime_at_review, @playtime_forever, @steam_purchase, @received_for_free, @written_during_early_access, @primarily_steam_deck, @votes_up, @votes_funny, @weighted_vote_score, @comment_count, @fetched_at)
    ON CONFLICT(recommendation_id) DO UPDATE SET
      review_text = @review_text, voted_up = @voted_up, timestamp_updated = @timestamp_updated,
      votes_up = @votes_up, votes_funny = @votes_funny, weighted_vote_score = @weighted_vote_score,
      comment_count = @comment_count, fetched_at = @fetched_at
  `)
  const transaction = db.transaction(() => {
    for (const review of reviews) {
      stmt.run({ ...review, fetched_at: now })
    }
  })
  transaction()
}

export function getReviews(db: Database.Database, appId: number, filter?: ReviewFilter): ReviewRecord[] {
  let sql = 'SELECT * FROM reviews WHERE app_id = ?'
  const params: unknown[] = [appId]

  if (filter?.language) {
    sql += ' AND language = ?'
    params.push(filter.language)
  }
  if (filter?.period_start) {
    sql += ' AND timestamp_created >= ?'
    params.push(filter.period_start)
  }
  if (filter?.period_end) {
    sql += ' AND timestamp_created <= ?'
    params.push(filter.period_end)
  }
  if (filter?.playtime_min !== undefined) {
    sql += ' AND playtime_at_review >= ?'
    params.push(filter.playtime_min)
  }
  if (filter?.playtime_max !== undefined) {
    sql += ' AND playtime_at_review < ?'
    params.push(filter.playtime_max)
  }
  if (filter?.steam_purchase !== undefined) {
    sql += ' AND steam_purchase = ?'
    params.push(filter.steam_purchase)
  }

  sql += ' ORDER BY timestamp_created DESC'
  return db.prepare(sql).all(...params) as ReviewRecord[]
}

export function getGameStats(db: Database.Database, appId: number) {
  const total = db.prepare('SELECT COUNT(*) as count FROM reviews WHERE app_id = ?').get(appId) as { count: number }
  const positive = db.prepare('SELECT COUNT(*) as count FROM reviews WHERE app_id = ? AND voted_up = 1').get(appId) as { count: number }
  const languages = db.prepare('SELECT DISTINCT language FROM reviews WHERE app_id = ?').all(appId) as { language: string }[]

  return {
    total_collected: total.count,
    positive_count: positive.count,
    negative_count: total.count - positive.count,
    positive_rate: total.count > 0 ? positive.count / total.count : 0,
    languages: languages.map(l => l.language)
  }
}

export function deleteGame(db: Database.Database, appId: number): void {
  db.prepare('DELETE FROM analysis_cache WHERE app_id = ?').run(appId)
  db.prepare('DELETE FROM embeddings WHERE recommendation_id IN (SELECT recommendation_id FROM reviews WHERE app_id = ?)').run(appId)
  db.prepare('DELETE FROM reviews WHERE app_id = ?').run(appId)
  db.prepare('DELETE FROM games WHERE app_id = ?').run(appId)
}

export function saveAnalysisCache(db: Database.Database, appId: number, analysisType: string, languageFilter: string, configHash: string, resultJson: string): void {
  const now = Math.floor(Date.now() / 1000)
  db.prepare('DELETE FROM analysis_cache WHERE app_id = ? AND analysis_type = ? AND config_hash = ?').run(appId, analysisType, configHash)
  db.prepare('INSERT INTO analysis_cache (app_id, analysis_type, language_filter, config_hash, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?)').run(appId, analysisType, languageFilter, configHash, resultJson, now)
}

export function getAnalysisCache(db: Database.Database, appId: number, analysisType: string, configHash: string): string | null {
  const row = db.prepare('SELECT result_json FROM analysis_cache WHERE app_id = ? AND analysis_type = ? AND config_hash = ?').get(appId, analysisType, configHash) as { result_json: string } | undefined
  return row?.result_json ?? null
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run tests/main/db.test.ts
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add electron/main/db.ts tests/main/db.test.ts
git commit -m "feat: add SQLite database module with schema and CRUD"
```

---

## Task 3: Steam API Client

**Files:**
- Create: `electron/main/steam-api.ts`
- Test: `tests/main/steam-api.test.ts`

- [ ] **Step 1: Write failing tests for URL parsing and response transformation**

Create `tests/main/steam-api.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { parseAppId, transformReview, transformQuerySummary } from '../../electron/main/steam-api'

describe('parseAppId', () => {
  it('parses plain number', () => {
    expect(parseAppId('730')).toBe(730)
  })

  it('parses store URL', () => {
    expect(parseAppId('https://store.steampowered.com/app/730/CounterStrike_2/')).toBe(730)
  })

  it('parses store URL without trailing slash', () => {
    expect(parseAppId('store.steampowered.com/app/292030')).toBe(292030)
  })

  it('returns null for invalid input', () => {
    expect(parseAppId('not-a-url')).toBeNull()
  })
})

describe('transformReview', () => {
  it('extracts fields and excludes personal info', () => {
    const raw = {
      recommendationid: '12345',
      author: {
        steamid: '76561198000000000',
        personaname: 'Player1',
        playtime_at_review: 600,
        playtime_forever: 1200,
        num_games_owned: 50,
        num_reviews: 3
      },
      language: 'english',
      review: 'Great game!',
      voted_up: true,
      timestamp_created: 1700000000,
      timestamp_updated: 1700000000,
      steam_purchase: true,
      received_for_free: false,
      written_during_early_access: false,
      primarily_steam_deck: false,
      votes_up: 10,
      votes_funny: 2,
      weighted_vote_score: '0.85',
      comment_count: 1
    }

    const result = transformReview(raw, 730)
    expect(result.recommendation_id).toBe('12345')
    expect(result.voted_up).toBe(1)
    expect(result.weighted_vote_score).toBe(0.85)
    expect(result).not.toHaveProperty('steamid')
    expect(result).not.toHaveProperty('personaname')
  })

  it('handles weighted_vote_score as number', () => {
    const raw = {
      recommendationid: '99',
      author: { playtime_at_review: 100, playtime_forever: 200 },
      language: 'koreana',
      review: '좋아요',
      voted_up: false,
      timestamp_created: 1700000000,
      timestamp_updated: 1700000000,
      steam_purchase: true,
      received_for_free: false,
      written_during_early_access: false,
      primarily_steam_deck: false,
      votes_up: 0,
      votes_funny: 0,
      weighted_vote_score: 0.5,
      comment_count: 0
    }

    const result = transformReview(raw, 730)
    expect(result.weighted_vote_score).toBe(0.5)
    expect(result.voted_up).toBe(0)
  })
})

describe('transformQuerySummary', () => {
  it('extracts game metadata', () => {
    const raw = {
      num_reviews: 20,
      review_score: 8,
      review_score_desc: 'Very Positive',
      total_positive: 1000,
      total_negative: 200,
      total_reviews: 1200
    }
    const result = transformQuerySummary(raw, 730)
    expect(result.app_id).toBe(730)
    expect(result.review_score).toBe(8)
    expect(result.total_reviews).toBe(1200)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/main/steam-api.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement Steam API client**

Create `electron/main/steam-api.ts`:

```typescript
import { net } from 'electron'

export function parseAppId(input: string): number | null {
  const trimmed = input.trim()

  // Plain number
  if (/^\d+$/.test(trimmed)) return parseInt(trimmed, 10)

  // URL: extract from /app/<id>
  const match = trimmed.match(/\/app\/(\d+)/)
  if (match) return parseInt(match[1], 10)

  return null
}

export function transformReview(raw: Record<string, unknown>, appId: number) {
  const author = raw.author as Record<string, unknown> | undefined
  const weightedScore = raw.weighted_vote_score
  return {
    recommendation_id: String(raw.recommendationid),
    app_id: appId,
    language: String(raw.language ?? ''),
    review_text: String(raw.review ?? ''),
    voted_up: raw.voted_up ? 1 : 0,
    timestamp_created: Number(raw.timestamp_created ?? 0),
    timestamp_updated: Number(raw.timestamp_updated ?? 0),
    playtime_at_review: Number(author?.playtime_at_review ?? 0),
    playtime_forever: Number(author?.playtime_forever ?? 0),
    steam_purchase: raw.steam_purchase ? 1 : 0,
    received_for_free: raw.received_for_free ? 1 : 0,
    written_during_early_access: raw.written_during_early_access ? 1 : 0,
    primarily_steam_deck: raw.primarily_steam_deck ? 1 : 0,
    votes_up: Number(raw.votes_up ?? 0),
    votes_funny: Number(raw.votes_funny ?? 0),
    weighted_vote_score: typeof weightedScore === 'string' ? parseFloat(weightedScore) : Number(weightedScore ?? 0),
    comment_count: Number(raw.comment_count ?? 0)
  }
}

export function transformQuerySummary(raw: Record<string, unknown>, appId: number) {
  return {
    app_id: appId,
    app_name: '',
    review_score: Number(raw.review_score ?? 0),
    review_score_desc: String(raw.review_score_desc ?? ''),
    total_positive: Number(raw.total_positive ?? 0),
    total_negative: Number(raw.total_negative ?? 0),
    total_reviews: Number(raw.total_reviews ?? 0)
  }
}

interface FetchProgress {
  fetched: number
  total: number
  cursor: string
}

export async function fetchAllReviews(
  appId: number,
  onBatch: (reviews: ReturnType<typeof transformReview>[], summary: ReturnType<typeof transformQuerySummary> | null) => void,
  onProgress: (progress: FetchProgress) => void,
  options: { language?: string; filterOfftopic?: boolean } = {}
): Promise<void> {
  let cursor = '*'
  let totalReviews = 0
  let fetchedCount = 0
  let isFirstPage = true

  const language = options.language ?? 'all'
  const offtopic = options.filterOfftopic !== false ? 1 : 0

  while (true) {
    const url = `https://store.steampowered.com/appreviews/${appId}?json=1&filter=recent&language=${language}&num_per_page=100&cursor=${encodeURIComponent(cursor)}&filter_offtopic_activity=${offtopic}`

    const response = await fetchJson(url)

    if (!response.success) throw new Error(`Steam API returned success=0 for app ${appId}`)

    const reviews = (response.reviews as Record<string, unknown>[]) ?? []

    if (reviews.length === 0) break

    const transformed = reviews.map(r => transformReview(r, appId))
    let summary: ReturnType<typeof transformQuerySummary> | null = null

    if (isFirstPage && response.query_summary) {
      summary = transformQuerySummary(response.query_summary as Record<string, unknown>, appId)
      totalReviews = summary.total_reviews
      isFirstPage = false
    }

    onBatch(transformed, summary)
    fetchedCount += transformed.length
    cursor = String(response.cursor ?? '')

    onProgress({ fetched: fetchedCount, total: totalReviews, cursor })

    // Rate limit: wait 500ms between requests
    await new Promise(resolve => setTimeout(resolve, 500))
  }
}

async function fetchJson(url: string, retries = 3): Promise<Record<string, unknown>> {
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const response = await net.fetch(url)

      if (response.status === 429 || response.status >= 500) {
        const delay = Math.pow(2, attempt) * 1000 + Math.random() * 500
        await new Promise(resolve => setTimeout(resolve, delay))
        continue
      }

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      return await response.json() as Record<string, unknown>
    } catch (err) {
      if (attempt === retries - 1) throw err
      const delay = Math.pow(2, attempt) * 1000
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  throw new Error('Max retries exceeded')
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run tests/main/steam-api.test.ts
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add electron/main/steam-api.ts tests/main/steam-api.test.ts
git commit -m "feat: add Steam review API client with URL parsing and pagination"
```

---

## Task 4: Python Sidecar Infrastructure

**Files:**
- Create: `python/protocol.py`, `python/main.py`, `python/gpu_detect.py`, `electron/main/sidecar.ts`
- Test: `tests/python/test_protocol.py`

- [ ] **Step 1: Write failing test for Python JSON-line protocol**

Create `tests/python/test_protocol.py`:

```python
import json
import pytest
from python.protocol import parse_message, format_result, format_progress, format_error


def test_parse_valid_message():
    line = json.dumps({"id": "abc-123", "method": "detect_gpu", "params": {}})
    msg = parse_message(line)
    assert msg["id"] == "abc-123"
    assert msg["method"] == "detect_gpu"
    assert msg["params"] == {}


def test_parse_invalid_json():
    with pytest.raises(ValueError):
        parse_message("not json")


def test_parse_missing_fields():
    with pytest.raises(ValueError):
        parse_message(json.dumps({"id": "x"}))


def test_format_result():
    out = format_result("abc-123", {"gpu": True, "vram": 16000})
    parsed = json.loads(out)
    assert parsed["id"] == "abc-123"
    assert parsed["type"] == "result"
    assert parsed["data"]["gpu"] is True


def test_format_progress():
    out = format_progress("abc-123", 50, "Embedding...")
    parsed = json.loads(out)
    assert parsed["type"] == "progress"
    assert parsed["data"]["percent"] == 50


def test_format_error():
    out = format_error("abc-123", "Something failed")
    parsed = json.loads(out)
    assert parsed["type"] == "error"
    assert parsed["data"]["message"] == "Something failed"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd python && python -m pytest tests/python/test_protocol.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement protocol module**

Create `python/protocol.py`:

```python
import json
from typing import Any


def parse_message(line: str) -> dict:
    try:
        msg = json.loads(line.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if "id" not in msg or "method" not in msg:
        raise ValueError("Message must have 'id' and 'method' fields")

    return msg


def format_result(msg_id: str, data: Any) -> str:
    return json.dumps({"id": msg_id, "type": "result", "data": data}, ensure_ascii=False)


def format_progress(msg_id: str, percent: int, message: str) -> str:
    return json.dumps({"id": msg_id, "type": "progress", "data": {"percent": percent, "message": message}}, ensure_ascii=False)


def format_error(msg_id: str, message: str) -> str:
    return json.dumps({"id": msg_id, "type": "error", "data": {"message": message}}, ensure_ascii=False)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd python && python -m pytest tests/python/test_protocol.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Implement GPU detection**

Create `python/gpu_detect.py`:

```python
def detect_gpu() -> dict:
    """Detect CUDA GPU and VRAM. Returns tier info."""
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram_mb = props.total_mem // (1024 * 1024)
            return {
                "gpu_available": True,
                "gpu_name": props.name,
                "vram_mb": vram_mb,
                "recommended_tier": 1 if vram_mb >= 8192 else 0
            }
    except ImportError:
        pass

    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if "CUDAExecutionProvider" in providers:
            return {
                "gpu_available": True,
                "gpu_name": "CUDA (via ONNX Runtime)",
                "vram_mb": 0,
                "recommended_tier": 0
            }
    except ImportError:
        pass

    return {
        "gpu_available": False,
        "gpu_name": None,
        "vram_mb": 0,
        "recommended_tier": 0
    }
```

- [ ] **Step 6: Implement Python sidecar entry point**

Create `python/main.py`:

```python
import sys
import traceback
from protocol import parse_message, format_result, format_error
from gpu_detect import detect_gpu


def handle_message(msg: dict) -> str:
    method = msg["method"]
    params = msg.get("params", {})
    msg_id = msg["id"]

    if method == "ping":
        return format_result(msg_id, {"status": "ok"})

    elif method == "detect_gpu":
        result = detect_gpu()
        return format_result(msg_id, result)

    elif method == "analyze":
        # Imported lazily to avoid slow startup
        from analyzer import run_analysis
        result = run_analysis(params, msg_id)
        return format_result(msg_id, result)

    elif method == "generate_embeddings":
        from embeddings import generate_embeddings
        result = generate_embeddings(params, msg_id)
        return format_result(msg_id, result)

    else:
        return format_error(msg_id, f"Unknown method: {method}")


def main():
    # Signal readiness
    sys.stdout.write(format_result("__init__", {"status": "ready"}) + "\n")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = parse_message(line)
            response = handle_message(msg)
        except Exception as e:
            response = format_error(
                "unknown",
                f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
        sys.stdout.write(response + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Implement Electron-side sidecar manager**

Create `electron/main/sidecar.ts`:

```typescript
import { spawn, ChildProcess } from 'child_process'
import { v4 as uuidv4 } from 'uuid'
import path from 'path'
import { app } from 'electron'

type MessageHandler = (data: unknown) => void

interface PendingRequest {
  resolve: (data: unknown) => void
  reject: (error: Error) => void
  onProgress?: (data: { percent: number; message: string }) => void
}

export class SidecarManager {
  private process: ChildProcess | null = null
  private pending = new Map<string, PendingRequest>()
  private buffer = ''
  private ready = false
  private readyPromise: Promise<void> | null = null

  start(): Promise<void> {
    if (this.readyPromise) return this.readyPromise

    this.readyPromise = new Promise((resolve, reject) => {
      const pythonPath = this.getPythonPath()
      const scriptPath = this.getScriptPath()

      this.process = spawn(pythonPath, [scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: path.dirname(scriptPath)
      })

      this.process.stdout!.on('data', (chunk: Buffer) => {
        this.buffer += chunk.toString()
        const lines = this.buffer.split('\n')
        this.buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const msg = JSON.parse(line)
            this.handleMessage(msg)
            if (msg.id === '__init__' && msg.data?.status === 'ready') {
              this.ready = true
              resolve()
            }
          } catch {
            console.error('Sidecar: invalid JSON from Python:', line)
          }
        }
      })

      this.process.stderr!.on('data', (chunk: Buffer) => {
        console.error('Sidecar stderr:', chunk.toString())
      })

      this.process.on('exit', (code) => {
        this.ready = false
        this.process = null
        if (!this.ready) reject(new Error(`Sidecar exited with code ${code}`))
      })

      setTimeout(() => {
        if (!this.ready) reject(new Error('Sidecar startup timeout'))
      }, 30000)
    })

    return this.readyPromise
  }

  async send(method: string, params: Record<string, unknown> = {}, onProgress?: (data: { percent: number; message: string }) => void): Promise<unknown> {
    if (!this.process || !this.ready) {
      await this.start()
    }

    const id = uuidv4()
    const message = JSON.stringify({ id, method, params }) + '\n'

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, onProgress })
      this.process!.stdin!.write(message)
    })
  }

  stop(): void {
    if (this.process) {
      this.process.kill()
      this.process = null
      this.ready = false
      this.readyPromise = null
    }
  }

  private handleMessage(msg: { id: string; type: string; data: unknown }): void {
    const pending = this.pending.get(msg.id)
    if (!pending) return

    if (msg.type === 'result') {
      this.pending.delete(msg.id)
      pending.resolve(msg.data)
    } else if (msg.type === 'error') {
      this.pending.delete(msg.id)
      pending.reject(new Error((msg.data as { message: string }).message))
    } else if (msg.type === 'progress') {
      pending.onProgress?.(msg.data as { percent: number; message: string })
    }
  }

  private getPythonPath(): string {
    const isWin = process.platform === 'win32'
    const venvBin = isWin ? 'Scripts/python.exe' : 'bin/python'
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'python', 'venv', venvBin)
    }
    return path.join(__dirname, '..', '..', 'python', 'venv', venvBin)
  }

  private getScriptPath(): string {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'python', 'main.py')
    }
    return path.join(__dirname, '..', '..', 'python', 'main.py')
  }
}
```

- [ ] **Step 8: Commit**

```bash
git add python/protocol.py python/main.py python/gpu_detect.py python/requirements.txt electron/main/sidecar.ts tests/python/test_protocol.py
git commit -m "feat: add Python sidecar with JSON-line protocol and GPU detection"
```

---

## Task 5: IPC Bridge (Electron Main <-> Renderer)

**Files:**
- Create: `electron/main/ipc-handlers.ts`, `electron/preload/index.ts`, `src/hooks/useApi.ts`

- [ ] **Step 1: Implement preload script with typed API**

Replace `electron/preload/index.ts`:

```typescript
import { contextBridge, ipcRenderer } from 'electron'

const api = {
  // Games
  addGame: (input: string) => ipcRenderer.invoke('game:add', input),
  getGames: () => ipcRenderer.invoke('game:list'),
  getGame: (appId: number) => ipcRenderer.invoke('game:get', appId),
  deleteGame: (appId: number) => ipcRenderer.invoke('game:delete', appId),
  getGameStats: (appId: number) => ipcRenderer.invoke('game:stats', appId),

  // Reviews
  fetchReviews: (appId: number) => ipcRenderer.invoke('reviews:fetch', appId),
  getReviews: (appId: number, filter?: Record<string, unknown>) => ipcRenderer.invoke('reviews:get', appId, filter),

  // Analysis
  detectGpu: () => ipcRenderer.invoke('analysis:detect-gpu'),
  runAnalysis: (appId: number, config: Record<string, unknown>) => ipcRenderer.invoke('analysis:run', appId, config),

  // Export
  exportCsv: (appId: number, filter: Record<string, unknown>) => ipcRenderer.invoke('export:csv', appId, filter),
  exportMarkdown: (appId: number, filter: Record<string, unknown>) => ipcRenderer.invoke('export:markdown', appId, filter),

  // Events
  onProgress: (callback: (data: unknown) => void) => {
    ipcRenderer.on('progress', (_event, data) => callback(data))
    return () => ipcRenderer.removeAllListeners('progress')
  },

  // Settings
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (settings: Record<string, unknown>) => ipcRenderer.invoke('settings:save', settings)
}

contextBridge.exposeInMainWorld('api', api)

export type ElectronAPI = typeof api
```

- [ ] **Step 2: Implement IPC handlers**

Create `electron/main/ipc-handlers.ts`:

```typescript
import { ipcMain, BrowserWindow, dialog } from 'electron'
import Database from 'better-sqlite3'
import { insertGame, getGame, getAllGames, deleteGame, getGameStats, upsertReviews, getReviews } from './db'
import { parseAppId, fetchAllReviews, transformQuerySummary } from './steam-api'
import { SidecarManager } from './sidecar'
import path from 'path'
import fs from 'fs'

export function registerIpcHandlers(db: Database.Database, sidecar: SidecarManager, getMainWindow: () => BrowserWindow | null): void {

  ipcMain.handle('game:add', async (_event, input: string) => {
    const appId = parseAppId(input)
    if (!appId) throw new Error('Invalid App ID or URL')

    const existing = getGame(db, appId)
    if (existing) return existing

    // Fetch ONLY first page to get query_summary (not all reviews)
    const url = `https://store.steampowered.com/appreviews/${appId}?json=1&language=all&num_per_page=1`
    const response = await net.fetch(url)
    const data = await response.json() as Record<string, unknown>
    if (!data.success) throw new Error('Failed to fetch game info')

    const summary = transformQuerySummary(data.query_summary as Record<string, unknown>, appId)

    // Fetch game name from Steam store page
    try {
      const storeRes = await net.fetch(`https://store.steampowered.com/api/appdetails?appids=${appId}`)
      const storeData = await storeRes.json() as Record<string, any>
      summary.app_name = storeData[String(appId)]?.data?.name ?? `App ${appId}`
    } catch {
      summary.app_name = `App ${appId}`
    }

    insertGame(db, summary)
    return getGame(db, appId)
  })

  ipcMain.handle('game:list', () => getAllGames(db))
  ipcMain.handle('game:get', (_event, appId: number) => getGame(db, appId))
  ipcMain.handle('game:delete', (_event, appId: number) => deleteGame(db, appId))
  ipcMain.handle('game:stats', (_event, appId: number) => getGameStats(db, appId))

  ipcMain.handle('reviews:fetch', async (_event, appId: number) => {
    const win = getMainWindow()
    await fetchAllReviews(
      appId,
      (reviews, summary) => {
        if (summary) insertGame(db, summary)
        upsertReviews(db, reviews)
      },
      (progress) => {
        win?.webContents.send('progress', { type: 'fetch', appId, ...progress })
      }
    )
    return getGameStats(db, appId)
  })

  ipcMain.handle('reviews:get', (_event, appId: number, filter?: Record<string, unknown>) => {
    return getReviews(db, appId, filter as Parameters<typeof getReviews>[2])
  })

  ipcMain.handle('analysis:detect-gpu', async () => {
    return sidecar.send('detect_gpu')
  })

  ipcMain.handle('analysis:run', async (_event, appId: number, config: Record<string, unknown>) => {
    const reviews = getReviews(db, appId, config.filter as Parameters<typeof getReviews>[2])
    const reviewData = reviews.map(r => ({
      id: r.recommendation_id,
      text: r.review_text,
      voted_up: r.voted_up === 1,
      language: r.language,
      playtime: r.playtime_at_review
    }))
    const win = getMainWindow()
    return sidecar.send('analyze', { reviews: reviewData, config }, (progress) => {
      win?.webContents.send('progress', { type: 'analysis', appId, ...progress })
    })
  })

  ipcMain.handle('export:csv', async (_event, appId: number, filter: Record<string, unknown>) => {
    const reviews = getReviews(db, appId, filter as Parameters<typeof getReviews>[2])
    const result = await dialog.showSaveDialog({ defaultPath: `reviews_${appId}.csv`, filters: [{ name: 'CSV', extensions: ['csv'] }] })
    if (result.canceled || !result.filePath) return null

    const BOM = '\uFEFF'
    const header = 'recommendation_id,language,review_text,voted_up,timestamp_created,playtime_at_review,steam_purchase,votes_up,weighted_vote_score\n'
    const rows = reviews.map(r => {
      const text = `"${r.review_text.replace(/"/g, '""')}"`
      return `${r.recommendation_id},${r.language},${text},${r.voted_up},${r.timestamp_created},${r.playtime_at_review},${r.steam_purchase},${r.votes_up},${r.weighted_vote_score}`
    }).join('\n')

    fs.writeFileSync(result.filePath, BOM + header + rows, 'utf-8')
    return result.filePath
  })

  ipcMain.handle('export:markdown', async (_event, appId: number, filter: Record<string, unknown>) => {
    const reviews = getReviews(db, appId, filter as Parameters<typeof getReviews>[2])
    const game = getGame(db, appId)
    const stats = getGameStats(db, appId)

    let md = `# ${game?.app_name ?? `App ${appId}`} Review Analysis\n\n`
    md += `- Total Reviews: ${stats.total_collected}\n`
    md += `- Positive Rate: ${(stats.positive_rate * 100).toFixed(1)}%\n`
    md += `- Languages: ${stats.languages.join(', ')}\n\n`
    md += `## Reviews\n\n`

    for (const r of reviews.slice(0, 200)) {
      md += `### ${r.voted_up ? '+' : '-'} [${r.language}] (${Math.round(r.playtime_at_review / 60)}h)\n`
      md += `${r.review_text}\n\n`
    }

    const result = await dialog.showSaveDialog({ defaultPath: `reviews_${appId}.md`, filters: [{ name: 'Markdown', extensions: ['md'] }] })
    if (result.canceled || !result.filePath) return null
    fs.writeFileSync(result.filePath, md, 'utf-8')
    return result.filePath
  })
}
```

- [ ] **Step 3: Create useApi hook for renderer**

Create `src/hooks/useApi.ts`:

```typescript
import type { ElectronAPI } from '../../electron/preload/index'

declare global {
  interface Window {
    api: ElectronAPI
  }
}

export function useApi() {
  return window.api
}
```

- [ ] **Step 4: Wire up main process entry point**

Update `electron/main/index.ts` to initialize DB, sidecar, and IPC handlers. The scaffolded file already creates a BrowserWindow — add after window creation:

```typescript
// Add these imports at the top
import { createDb } from './db'
import { SidecarManager } from './sidecar'
import { registerIpcHandlers } from './ipc-handlers'

// Add after app.whenReady():
const db = createDb()
const sidecar = new SidecarManager()
let mainWindow: BrowserWindow | null = null

// After mainWindow = new BrowserWindow(...):
registerIpcHandlers(db, sidecar, () => mainWindow)

// On app quit:
app.on('before-quit', () => {
  sidecar.stop()
  db.close()
})
```

- [ ] **Step 5: Commit**

```bash
git add electron/main/ipc-handlers.ts electron/preload/index.ts src/hooks/useApi.ts electron/main/index.ts
git commit -m "feat: add IPC bridge connecting renderer, main process, and sidecar"
```

---

## Task 6: Python Analysis Pipeline

**Files:**
- Create: `python/model_manager.py`, `python/embeddings.py`, `python/clustering.py`, `python/keywords.py`, `python/analyzer.py`
- Test: `tests/python/test_clustering.py`, `tests/python/test_keywords.py`

- [ ] **Step 1: Write failing tests for clustering**

Create `tests/python/test_clustering.py`:

```python
import numpy as np
import pytest
from python.clustering import cluster_reviews


def test_kmeans_returns_labels():
    # 3 clear clusters in 2D space
    vecs = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.05, 0.05],
        [5.0, 5.0], [5.1, 5.1], [4.9, 4.9],
        [10.0, 0.0], [10.1, 0.1], [9.9, 0.05],
    ])
    labels = cluster_reviews(vecs, method="kmeans", n_clusters=3)
    assert len(labels) == 9
    # Points 0-2 should share a label, 3-5 another, 6-8 another
    assert labels[0] == labels[1] == labels[2]
    assert labels[3] == labels[4] == labels[5]
    assert labels[6] == labels[7] == labels[8]
    assert len(set(labels)) == 3


def test_hdbscan_returns_labels():
    vecs = np.array([
        [0.0, 0.0], [0.1, 0.1], [0.05, 0.05], [0.02, 0.08],
        [5.0, 5.0], [5.1, 5.1], [4.9, 4.9], [5.05, 5.02],
    ])
    labels = cluster_reviews(vecs, method="hdbscan", min_cluster_size=2)
    assert len(labels) == 8
    # HDBSCAN may assign -1 (noise), but should find at least 2 clusters
    unique = set(l for l in labels if l >= 0)
    assert len(unique) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd python && python -m pytest tests/python/test_clustering.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement model manager**

Create `python/model_manager.py`:

```python
import os
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download


def get_models_dir() -> Path:
    base = Path(os.environ.get("REVIEWFORGE_MODELS_DIR", str(Path.home() / ".reviewforge" / "models")))
    base.mkdir(parents=True, exist_ok=True)
    return base


TIER0_MODEL = "intfloat/multilingual-e5-small"
TIER1_MODEL = "BAAI/bge-m3"


def ensure_model(model_name: str) -> str:
    """Download model if not cached. Returns local path."""
    models_dir = get_models_dir()
    local_dir = models_dir / model_name.replace("/", "--")

    if local_dir.exists() and any(local_dir.iterdir()):
        return str(local_dir)

    snapshot_download(
        repo_id=model_name,
        local_dir=str(local_dir),
        ignore_patterns=["*.msgpack", "*.h5", "*.ot", "flax_*", "tf_*"]
    )
    return str(local_dir)


def get_onnx_path(model_name: str) -> str | None:
    """Find int8 ONNX file if available."""
    model_dir = ensure_model(model_name)
    onnx_dir = Path(model_dir) / "onnx"
    if onnx_dir.exists():
        for f in onnx_dir.glob("*int8*onnx"):
            return str(f)
        for f in onnx_dir.glob("*.onnx"):
            return str(f)

    for f in Path(model_dir).glob("*int8*.onnx"):
        return str(f)
    for f in Path(model_dir).glob("*.onnx"):
        return str(f)

    return None
```

- [ ] **Step 4: Implement embeddings module**

Create `python/embeddings.py`:

```python
import sys
import numpy as np
from typing import Callable
from model_manager import TIER0_MODEL, TIER1_MODEL, ensure_model
from protocol import format_progress


def generate_embeddings(params: dict, msg_id: str) -> dict:
    """Generate embeddings for a list of review texts."""
    texts = params.get("texts", [])
    tier = params.get("tier", 0)

    if not texts:
        return {"embeddings": [], "model": "none"}

    model_name = TIER0_MODEL if tier == 0 else TIER1_MODEL

    def on_progress(percent, message):
        sys.stdout.write(format_progress(msg_id, percent, message) + "\n")
        sys.stdout.flush()

    on_progress(5, f"Loading model {model_name}...")

    model_path = ensure_model(model_name)
    embeddings = _embed_with_sentence_transformers(model_path, texts, on_progress)

    on_progress(100, "Embeddings complete")
    return {
        "embeddings": embeddings.tolist(),
        "model": model_name,
        "dim": embeddings.shape[1]
    }


def _embed_with_sentence_transformers(model_path: str, texts: list[str], on_progress: Callable) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_path)
    batch_size = 64
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        emb = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        all_embeddings.append(emb)
        percent = min(95, int(10 + 85 * (i + len(batch)) / len(texts)))
        on_progress(percent, f"Embedded {min(i + len(batch), len(texts))}/{len(texts)} reviews")

    return np.vstack(all_embeddings)
```

- [ ] **Step 5: Implement clustering module**

Create `python/clustering.py`:

```python
import numpy as np
from sklearn.cluster import KMeans


def cluster_reviews(
    vectors: np.ndarray,
    method: str = "kmeans",
    n_clusters: int = 8,
    min_cluster_size: int = 5
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

    else:  # kmeans
        actual_k = min(n_clusters, len(vectors))
        km = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
        labels = km.fit_predict(vectors)
        return labels.tolist()
```

- [ ] **Step 6: Run clustering tests to verify they pass**

```bash
cd python && python -m pytest tests/python/test_clustering.py -v
```

Expected: Both tests PASS.

- [ ] **Step 7: Write failing tests for keyword extraction**

Create `tests/python/test_keywords.py`:

```python
import pytest
from python.keywords import extract_keywords_yake, extract_keywords_embedding


def test_yake_extracts_keywords():
    texts = [
        "The server lag is terrible and matchmaking takes forever",
        "Server issues are ruining the game, constant lag spikes",
        "Lag and server problems make this unplayable"
    ]
    keywords = extract_keywords_yake(texts, top_n=5)
    assert len(keywords) > 0
    assert len(keywords) <= 5
    # "server" or "lag" should appear in top keywords
    kw_lower = [k[0].lower() for k in keywords]
    assert any("server" in k or "lag" in k for k in kw_lower)


def test_yake_handles_empty():
    keywords = extract_keywords_yake([], top_n=5)
    assert keywords == []
```

- [ ] **Step 8: Run keyword tests to verify they fail**

```bash
cd python && python -m pytest tests/python/test_keywords.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 9: Implement keyword extraction module**

Create `python/keywords.py`:

```python
import numpy as np
from typing import Optional


def extract_keywords_yake(texts: list[str], top_n: int = 10, language: str = "en") -> list[tuple[str, float]]:
    """Extract keywords using YAKE! (CPU-friendly, no model needed)."""
    if not texts:
        return []

    import yake
    combined = " ".join(texts)
    extractor = yake.KeywordExtractor(
        lan=language,
        n=2,  # up to bigrams
        dedupLim=0.7,
        top=top_n,
        features=None
    )
    keywords = extractor.extract_keywords(combined)
    # YAKE returns (keyword, score) where lower score = more important
    # Normalize so higher = better
    if not keywords:
        return []
    max_score = max(k[1] for k in keywords) + 0.001
    return [(kw, 1.0 - score / max_score) for kw, score in keywords]


def extract_keywords_embedding(
    texts: list[str],
    embeddings: np.ndarray,
    top_n: int = 10
) -> list[tuple[str, float]]:
    """Extract keywords using KeyBERT-style embedding similarity + MMR."""
    if not texts or len(embeddings) == 0:
        return []

    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer

    # Use the same model that generated the embeddings
    combined = " ".join(texts[:100])  # limit for KeyBERT input
    kw_model = KeyBERT()
    keywords = kw_model.extract_keywords(
        combined,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        use_mmr=True,
        diversity=0.5,
        top_n=top_n
    )
    return keywords  # list of (keyword, score)


def extract_topic_keywords(
    texts: list[str],
    labels: list[int],
    tier: int = 0,
    embeddings: Optional[np.ndarray] = None,
    top_n: int = 8
) -> dict[int, list[tuple[str, float]]]:
    """Extract keywords per topic cluster."""
    topics: dict[int, list[str]] = {}
    for text, label in zip(texts, labels):
        if label < 0:  # noise in HDBSCAN
            continue
        topics.setdefault(label, []).append(text)

    result = {}
    for topic_id, topic_texts in topics.items():
        if tier >= 1 and embeddings is not None:
            topic_indices = [i for i, l in enumerate(labels) if l == topic_id]
            topic_embs = embeddings[topic_indices]
            result[topic_id] = extract_keywords_embedding(topic_texts, topic_embs, top_n)
        else:
            result[topic_id] = extract_keywords_yake(topic_texts, top_n)

    return result
```

- [ ] **Step 10: Run keyword tests to verify they pass**

```bash
cd python && python -m pytest tests/python/test_keywords.py -v
```

Expected: Both tests PASS.

- [ ] **Step 11: Implement analysis orchestrator**

Create `python/analyzer.py`:

```python
import sys
import numpy as np
from protocol import format_progress
from embeddings import generate_embeddings
from clustering import cluster_reviews
from keywords import extract_topic_keywords


def run_analysis(params: dict, msg_id: str) -> dict:
    """Full analysis pipeline: embed -> cluster -> extract keywords."""
    reviews = params.get("reviews", [])
    config = params.get("config", {})
    tier = config.get("tier", 0)
    n_topics = config.get("n_topics", 8)

    if not reviews:
        return {"positive_topics": [], "negative_topics": []}

    def progress(pct, msg):
        sys.stdout.write(format_progress(msg_id, pct, msg) + "\n")
        sys.stdout.flush()

    # Split by sentiment
    positive = [r for r in reviews if r["voted_up"]]
    negative = [r for r in reviews if not r["voted_up"]]

    progress(5, "Generating embeddings...")

    all_texts = [r["text"] for r in reviews]
    emb_result = generate_embeddings({"texts": all_texts, "tier": tier}, msg_id)
    all_embeddings = np.array(emb_result["embeddings"])

    # Map back to positive/negative
    pos_indices = [i for i, r in enumerate(reviews) if r["voted_up"]]
    neg_indices = [i for i, r in enumerate(reviews) if not r["voted_up"]]

    pos_embeddings = all_embeddings[pos_indices] if pos_indices else np.array([])
    neg_embeddings = all_embeddings[neg_indices] if neg_indices else np.array([])

    progress(60, "Clustering reviews...")

    method = "hdbscan" if tier >= 1 else "kmeans"

    pos_topics = _analyze_group(
        [r["text"] for r in positive], pos_embeddings,
        method, n_topics, tier
    ) if positive else []

    progress(80, "Extracting keywords...")

    neg_topics = _analyze_group(
        [r["text"] for r in negative], neg_embeddings,
        method, n_topics, tier
    ) if negative else []

    progress(100, "Analysis complete")

    return {
        "model": emb_result["model"],
        "tier": tier,
        "total_reviews": len(reviews),
        "positive_count": len(positive),
        "negative_count": len(negative),
        "positive_topics": pos_topics,
        "negative_topics": neg_topics
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

- [ ] **Step 12: Commit**

```bash
git add python/model_manager.py python/embeddings.py python/clustering.py python/keywords.py python/analyzer.py tests/python/test_clustering.py tests/python/test_keywords.py
git commit -m "feat: add Python analysis pipeline with embeddings, clustering, and keyword extraction"
```

---

## Task 7: App Shell and Game Management UI

**Files:**
- Create: `src/App.tsx`, `src/components/Layout.tsx`, `src/components/GameInput.tsx`, `src/components/GameSidebar.tsx`, `src/lib/steam-languages.ts`

- [ ] **Step 1: Create Steam language code mapping**

Create `src/lib/steam-languages.ts`:

```typescript
export const STEAM_LANGUAGES: Record<string, string> = {
  english: 'English',
  koreana: '한국어',
  japanese: '日本語',
  schinese: '简体中文',
  tchinese: '繁體中文',
  russian: 'Русский',
  spanish: 'Español (ES)',
  latam: 'Español (LA)',
  french: 'Français',
  german: 'Deutsch',
  portuguese: 'Português',
  brazilian: 'Português (BR)',
  italian: 'Italiano',
  polish: 'Polski',
  turkish: 'Türkçe',
  thai: 'ไทย',
  vietnamese: 'Tiếng Việt',
  ukrainian: 'Українська',
  czech: 'Čeština',
  dutch: 'Nederlands',
  hungarian: 'Magyar',
  romanian: 'Română',
  swedish: 'Svenska',
  finnish: 'Suomi',
  danish: 'Dansk',
  norwegian: 'Norsk',
  indonesian: 'Bahasa Indonesia',
  arabic: 'العربية',
  greek: 'Ελληνικά',
  bulgarian: 'Български'
}

export function getLanguageDisplayName(code: string): string {
  return STEAM_LANGUAGES[code] ?? code
}
```

- [ ] **Step 2: Build GameInput component**

Create `src/components/GameInput.tsx`:

```tsx
import { useState } from 'react'
import { useApi } from '../hooks/useApi'

interface Props {
  onGameAdded: () => void
}

export function GameInput({ onGameAdded }: Props) {
  const api = useApi()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!input.trim()) return
    setLoading(true)
    setError(null)
    try {
      await api.addGame(input.trim())
      setInput('')
      onGameAdded()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to add game')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="game-input">
      <input
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && handleSubmit()}
        placeholder="App ID or Steam Store URL"
        disabled={loading}
      />
      <button onClick={handleSubmit} disabled={loading || !input.trim()}>
        {loading ? 'Adding...' : 'Add Game'}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  )
}
```

- [ ] **Step 3: Build GameSidebar component**

Create `src/components/GameSidebar.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { GameInput } from './GameInput'

interface Game {
  app_id: number
  app_name: string
  review_score_desc: string
  total_reviews: number
}

interface Props {
  selectedAppId: number | null
  onSelectGame: (appId: number) => void
}

export function GameSidebar({ selectedAppId, onSelectGame }: Props) {
  const api = useApi()
  const [games, setGames] = useState<Game[]>([])

  const loadGames = async () => {
    const list = await api.getGames() as Game[]
    setGames(list)
  }

  useEffect(() => { loadGames() }, [])

  const handleDelete = async (appId: number) => {
    await api.deleteGame(appId)
    loadGames()
  }

  return (
    <aside className="sidebar">
      <GameInput onGameAdded={loadGames} />
      <ul className="game-list">
        {games.map(game => (
          <li
            key={game.app_id}
            className={selectedAppId === game.app_id ? 'active' : ''}
            onClick={() => onSelectGame(game.app_id)}
          >
            <span className="game-name">{game.app_name}</span>
            <span className="game-score">{game.review_score_desc}</span>
            <button
              className="delete-btn"
              onClick={e => { e.stopPropagation(); handleDelete(game.app_id) }}
            >
              x
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
```

- [ ] **Step 4: Build Layout and App root with tabs**

Create `src/components/Layout.tsx`:

```tsx
import { useState } from 'react'
import { GameSidebar } from './GameSidebar'

interface Props {
  children: (appId: number | null, activeTab: string) => React.ReactNode
}

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'topics', label: 'Topics' },
  { id: 'segments', label: 'Segments' },
  { id: 'export', label: 'Export' }
]

export function Layout({ children }: Props) {
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState('dashboard')

  return (
    <div className="app-layout">
      <GameSidebar selectedAppId={selectedAppId} onSelectGame={setSelectedAppId} />
      <main className="main-content">
        <nav className="tab-nav">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={activeTab === tab.id ? 'active' : ''}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="tab-content">
          {children(selectedAppId, activeTab)}
        </div>
      </main>
    </div>
  )
}
```

Update `src/App.tsx`:

```tsx
import { Layout } from './components/Layout'
import { Dashboard } from './components/Dashboard'
import { TopicAnalysis } from './components/TopicAnalysis'
import { SegmentAnalysis } from './components/SegmentAnalysis'
import { ExportPanel } from './components/ExportPanel'

export default function App() {
  return (
    <Layout>
      {(appId, activeTab) => {
        if (!appId) {
          return <div className="empty-state">Add a game to get started</div>
        }
        switch (activeTab) {
          case 'dashboard': return <Dashboard appId={appId} />
          case 'topics': return <TopicAnalysis appId={appId} />
          case 'segments': return <SegmentAnalysis appId={appId} />
          case 'export': return <ExportPanel appId={appId} />
          default: return null
        }
      }}
    </Layout>
  )
}
```

- [ ] **Step 5: Create placeholder components for all 4 tabs**

Create minimal stub for each so the app compiles:

`src/components/Dashboard.tsx`:
```tsx
export function Dashboard({ appId }: { appId: number }) {
  return <div>Dashboard for {appId} — coming in Task 8</div>
}
```

`src/components/TopicAnalysis.tsx`:
```tsx
export function TopicAnalysis({ appId }: { appId: number }) {
  return <div>Topics for {appId} — coming in Task 9</div>
}
```

`src/components/SegmentAnalysis.tsx`:
```tsx
export function SegmentAnalysis({ appId }: { appId: number }) {
  return <div>Segments for {appId} — coming in Task 10</div>
}
```

`src/components/ExportPanel.tsx`:
```tsx
export function ExportPanel({ appId }: { appId: number }) {
  return <div>Export for {appId} — coming in Task 11</div>
}
```

- [ ] **Step 6: Run dev server and verify layout renders**

```bash
pnpmdev
```

Expected: Electron window opens with sidebar (game input + empty game list) and tab navigation. No errors in console.

- [ ] **Step 7: Commit**

```bash
git add src/
git commit -m "feat: add app shell with sidebar, tab navigation, and game management"
```

---

## Task 8: Dashboard Tab

**Files:**
- Modify: `src/components/Dashboard.tsx`
- Create: `src/components/CollectionProgress.tsx`

- [ ] **Step 1: Build CollectionProgress component**

Create `src/components/CollectionProgress.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

interface Props {
  appId: number
  onComplete: () => void
}

export function CollectionProgress({ appId, onComplete }: Props) {
  const api = useApi()
  const [progress, setProgress] = useState({ fetched: 0, total: 0 })
  const [collecting, setCollecting] = useState(false)

  useEffect(() => {
    const cleanup = api.onProgress((data: any) => {
      if (data.type === 'fetch' && data.appId === appId) {
        setProgress({ fetched: data.fetched, total: data.total })
      }
    })
    return cleanup
  }, [appId])

  const startFetch = async () => {
    setCollecting(true)
    try {
      await api.fetchReviews(appId)
      onComplete()
    } finally {
      setCollecting(false)
    }
  }

  const percent = progress.total > 0 ? Math.round(progress.fetched / progress.total * 100) : 0

  return (
    <div className="collection-progress">
      <button onClick={startFetch} disabled={collecting}>
        {collecting ? `Collecting... ${progress.fetched}/${progress.total} (${percent}%)` : 'Fetch Reviews'}
      </button>
      {collecting && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${percent}%` }} />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Implement full Dashboard component**

Replace `src/components/Dashboard.tsx`:

```tsx
import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { useApi } from '../hooks/useApi'
import { CollectionProgress } from './CollectionProgress'
import { getLanguageDisplayName } from '../lib/steam-languages'

interface GameStats {
  total_collected: number
  positive_count: number
  negative_count: number
  positive_rate: number
  languages: string[]
}

interface Game {
  app_id: number
  app_name: string
  review_score: number
  review_score_desc: string
  total_positive: number
  total_negative: number
  total_reviews: number
}

export function Dashboard({ appId }: { appId: number }) {
  const api = useApi()
  const [game, setGame] = useState<Game | null>(null)
  const [stats, setStats] = useState<GameStats | null>(null)
  const [reviews, setReviews] = useState<any[]>([])

  const loadData = async () => {
    const [g, s, r] = await Promise.all([
      api.getGame(appId) as Promise<Game>,
      api.getGameStats(appId) as Promise<GameStats>,
      api.getReviews(appId) as Promise<any[]>
    ])
    setGame(g)
    setStats(s)
    setReviews(r)
  }

  useEffect(() => { loadData() }, [appId])

  if (!game || !stats) return <div>Loading...</div>

  // Donut chart: positive/negative
  const donutOption = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      data: [
        { value: stats.positive_count, name: 'Positive', itemStyle: { color: '#4ade80' } },
        { value: stats.negative_count, name: 'Negative', itemStyle: { color: '#f87171' } }
      ],
      label: { formatter: '{b}: {d}%' }
    }]
  }

  // Time trend: group reviews by day
  const dailyCounts = new Map<string, { pos: number; neg: number }>()
  for (const r of reviews) {
    const date = new Date(r.timestamp_created * 1000).toISOString().slice(0, 10)
    const entry = dailyCounts.get(date) ?? { pos: 0, neg: 0 }
    r.voted_up ? entry.pos++ : entry.neg++
    dailyCounts.set(date, entry)
  }
  const sortedDates = [...dailyCounts.keys()].sort()
  const trendOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: sortedDates },
    yAxis: { type: 'value' as const },
    series: [
      { name: 'Positive', type: 'bar', stack: 'total', data: sortedDates.map(d => dailyCounts.get(d)!.pos), color: '#4ade80' },
      { name: 'Negative', type: 'bar', stack: 'total', data: sortedDates.map(d => dailyCounts.get(d)!.neg), color: '#f87171' }
    ]
  }

  // Language distribution
  const langCounts = new Map<string, number>()
  for (const r of reviews) {
    langCounts.set(r.language, (langCounts.get(r.language) ?? 0) + 1)
  }
  const langSorted = [...langCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15)
  const langOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: langSorted.map(([code]) => getLanguageDisplayName(code)) },
    yAxis: { type: 'value' as const },
    series: [{ type: 'bar', data: langSorted.map(([, count]) => count), color: '#60a5fa' }]
  }

  return (
    <div className="dashboard">
      <div className="game-info-card">
        <h2>{game.app_name}</h2>
        <div className="score-badge">{game.review_score_desc}</div>
        <div className="stats-row">
          <span>Total: {game.total_reviews.toLocaleString()}</span>
          <span>Collected: {stats.total_collected.toLocaleString()}</span>
          <span>Positive: {(stats.positive_rate * 100).toFixed(1)}%</span>
        </div>
      </div>

      <CollectionProgress appId={appId} onComplete={loadData} />

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Positive / Negative</h3>
          <ReactECharts option={donutOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <h3>Review Trend</h3>
          <ReactECharts option={trendOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <h3>Language Distribution</h3>
          <ReactECharts option={langOption} style={{ height: 300 }} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Run dev server and verify Dashboard renders**

```bash
pnpmdev
```

Expected: After adding a game and fetching reviews, Dashboard shows game info card, donut chart, trend chart, and language bar chart.

- [ ] **Step 4: Commit**

```bash
git add src/components/Dashboard.tsx src/components/CollectionProgress.tsx
git commit -m "feat: add Dashboard tab with overview charts and review collection"
```

---

## Task 9: Topic Analysis Tab

**Files:**
- Modify: `src/components/TopicAnalysis.tsx`

- [ ] **Step 1: Implement TopicAnalysis component**

Replace `src/components/TopicAnalysis.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

interface Topic {
  id: number
  label: string
  keywords: { word: string; score: number }[]
  review_count: number
  sample_reviews: string[]
}

interface AnalysisResult {
  positive_topics: Topic[]
  negative_topics: Topic[]
  total_reviews: number
  positive_count: number
  negative_count: number
  tier: number
  model: string
}

export function TopicAnalysis({ appId }: { appId: number }) {
  const api = useApi()
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)
  const [nTopics, setNTopics] = useState(8)

  useEffect(() => {
    const cleanup = api.onProgress((data: any) => {
      if (data.type === 'analysis' && data.appId === appId) {
        setProgress(data.message ?? '')
      }
    })
    return cleanup
  }, [appId])

  const runAnalysis = async () => {
    setLoading(true)
    setProgress('Starting analysis...')
    try {
      const res = await api.runAnalysis(appId, { n_topics: nTopics }) as AnalysisResult
      setResult(res)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
      setProgress('')
    }
  }

  const toggleTopic = (key: string) => {
    setExpandedTopic(expandedTopic === key ? null : key)
  }

  return (
    <div className="topic-analysis">
      <div className="analysis-controls">
        <label>
          Topics per group:
          <input type="number" value={nTopics} onChange={e => setNTopics(Number(e.target.value))} min={2} max={20} />
        </label>
        <button onClick={runAnalysis} disabled={loading}>
          {loading ? progress : 'Run Analysis'}
        </button>
      </div>

      {result && (
        <div className="topics-grid">
          <div className="topic-column">
            <h3>Negative Topics ({result.negative_count} reviews)</h3>
            {result.negative_topics.map(topic => (
              <TopicCard
                key={`neg-${topic.id}`}
                topic={topic}
                type="negative"
                expanded={expandedTopic === `neg-${topic.id}`}
                onToggle={() => toggleTopic(`neg-${topic.id}`)}
              />
            ))}
          </div>
          <div className="topic-column">
            <h3>Positive Topics ({result.positive_count} reviews)</h3>
            {result.positive_topics.map(topic => (
              <TopicCard
                key={`pos-${topic.id}`}
                topic={topic}
                type="positive"
                expanded={expandedTopic === `pos-${topic.id}`}
                onToggle={() => toggleTopic(`pos-${topic.id}`)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

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

- [ ] **Step 2: Run dev server and verify**

```bash
pnpmdev
```

Expected: Topics tab shows controls and runs analysis when clicked. Results display as positive/negative topic cards with keywords and expandable sample reviews.

- [ ] **Step 3: Commit**

```bash
git add src/components/TopicAnalysis.tsx
git commit -m "feat: add Topic Analysis tab with clustering and keyword extraction UI"
```

---

## Task 10: Segment Analysis Tab

**Files:**
- Modify: `src/components/SegmentAnalysis.tsx`

- [ ] **Step 1: Implement SegmentAnalysis component**

Replace `src/components/SegmentAnalysis.tsx`:

```tsx
import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { useApi } from '../hooks/useApi'
import { getLanguageDisplayName } from '../lib/steam-languages'

const PLAYTIME_BRACKETS = [
  { label: '0-2h', min: 0, max: 120 },
  { label: '2-10h', min: 120, max: 600 },
  { label: '10-50h', min: 600, max: 3000 },
  { label: '50h+', min: 3000, max: Infinity }
]

export function SegmentAnalysis({ appId }: { appId: number }) {
  const api = useApi()
  const [reviews, setReviews] = useState<any[]>([])
  const [langFilter, setLangFilter] = useState('all')
  const [languages, setLanguages] = useState<string[]>([])

  useEffect(() => {
    const load = async () => {
      const filter = langFilter === 'all' ? {} : { language: langFilter }
      const r = await api.getReviews(appId, filter) as any[]
      setReviews(r)

      const stats = await api.getGameStats(appId) as { languages: string[] }
      setLanguages(stats.languages)
    }
    load()
  }, [appId, langFilter])

  // Playtime bracket analysis
  const playtimeData = PLAYTIME_BRACKETS.map(bracket => {
    const inBracket = reviews.filter(r =>
      r.playtime_at_review >= bracket.min && r.playtime_at_review < bracket.max
    )
    const pos = inBracket.filter(r => r.voted_up).length
    return {
      label: bracket.label,
      total: inBracket.length,
      positive_rate: inBracket.length > 0 ? pos / inBracket.length : 0
    }
  })

  const playtimeOption = {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}<br/>Positive: ${(p[0].value * 100).toFixed(1)}%<br/>Reviews: ${playtimeData[p[0].dataIndex].total}` },
    xAxis: { type: 'category' as const, data: playtimeData.map(d => d.label) },
    yAxis: { type: 'value' as const, max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{ type: 'bar', data: playtimeData.map(d => d.positive_rate), color: '#60a5fa' }]
  }

  // Language positive rate
  const langStats = new Map<string, { pos: number; total: number }>()
  for (const r of reviews) {
    const entry = langStats.get(r.language) ?? { pos: 0, total: 0 }
    entry.total++
    if (r.voted_up) entry.pos++
    langStats.set(r.language, entry)
  }
  const langData = [...langStats.entries()]
    .map(([code, { pos, total }]) => ({ code, name: getLanguageDisplayName(code), rate: pos / total, total }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 15)

  const langOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: langData.map(d => d.name), axisLabel: { rotate: 45 } },
    yAxis: { type: 'value' as const, max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{
      type: 'bar',
      data: langData.map(d => ({
        value: d.rate,
        itemStyle: { color: d.rate >= 0.7 ? '#4ade80' : d.rate >= 0.4 ? '#fbbf24' : '#f87171' }
      }))
    }]
  }

  // Purchase type comparison
  const steamPurchase = reviews.filter(r => r.steam_purchase)
  const freeReceived = reviews.filter(r => r.received_for_free)
  const purchaseData = [
    { name: 'Steam Purchase', rate: steamPurchase.length > 0 ? steamPurchase.filter(r => r.voted_up).length / steamPurchase.length : 0, count: steamPurchase.length },
    { name: 'Free', rate: freeReceived.length > 0 ? freeReceived.filter(r => r.voted_up).length / freeReceived.length : 0, count: freeReceived.length }
  ]

  const purchaseOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: purchaseData.map(d => d.name) },
    yAxis: { type: 'value' as const, max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{ type: 'bar', data: purchaseData.map(d => d.rate), color: '#a78bfa' }]
  }

  return (
    <div className="segment-analysis">
      <div className="filter-panel">
        <label>
          Language:
          <select value={langFilter} onChange={e => setLangFilter(e.target.value)}>
            <option value="all">All Languages</option>
            {languages.map(lang => (
              <option key={lang} value={lang}>{getLanguageDisplayName(lang)}</option>
            ))}
          </select>
        </label>
        <label>
          Period:
          <select value={periodFilter} onChange={e => setPeriodFilter(e.target.value)}>
            <option value="all">All Time</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="1y">Last Year</option>
          </select>
        </label>
        <label>
          Playtime:
          <select value={playtimeFilter} onChange={e => setPlaytimeFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="0-2h">0-2h</option>
            <option value="2-10h">2-10h</option>
            <option value="10-50h">10-50h</option>
            <option value="50h+">50h+</option>
          </select>
        </label>
        <label>
          Purchase:
          <select value={purchaseFilter} onChange={e => setPurchaseFilter(e.target.value)}>
            <option value="all">All</option>
            <option value="steam">Steam Purchase</option>
            <option value="free">Free</option>
          </select>
        </label>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Positive Rate by Playtime</h3>
          <ReactECharts option={playtimeOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <h3>Positive Rate by Language</h3>
          <ReactECharts option={langOption} style={{ height: 300 }} />
        </div>
        <div className="chart-card">
          <h3>Purchase Type</h3>
          <ReactECharts option={purchaseOption} style={{ height: 300 }} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run dev and verify**

```bash
pnpmdev
```

Expected: Segments tab shows playtime bracket chart, language positive rate chart, and purchase type comparison. Language filter dropdown works.

- [ ] **Step 3: Commit**

```bash
git add src/components/SegmentAnalysis.tsx
git commit -m "feat: add Segment Analysis tab with playtime, language, and purchase breakdowns"
```

---

## Task 11: Export Tab

**Files:**
- Modify: `src/components/ExportPanel.tsx`
- Create: `src/lib/export-utils.ts`

- [ ] **Step 1: Create export utility functions**

Create `src/lib/export-utils.ts`:

```typescript
export function reviewsToMarkdown(reviews: any[], gameName: string, filter: string): string {
  let md = `# ${gameName} Reviews\n\n`
  md += `Filter: ${filter}\n`
  md += `Total: ${reviews.length} reviews\n\n`
  for (const r of reviews) {
    const sentiment = r.voted_up ? '+' : '-'
    const hours = Math.round(r.playtime_at_review / 60)
    md += `### ${sentiment} [${r.language}] (${hours}h)\n${r.review_text}\n\n`
  }
  return md
}

export function reviewsToLlmPrompt(reviews: any[], gameName: string, template: string): string {
  const reviewBlock = reviews.map(r => {
    const sentiment = r.voted_up ? 'Positive' : 'Negative'
    return `[${sentiment}] [${r.language}] (${Math.round(r.playtime_at_review / 60)}h playtime)\n${r.review_text}`
  }).join('\n---\n')

  const posCount = reviews.filter(r => r.voted_up).length
  const negCount = reviews.length - posCount
  const sentiment = posCount > negCount ? 'positive' : negCount > posCount ? 'negative' : 'mixed'

  return template
    .replace('[Game Name]', gameName)
    .replace('[N]', String(reviews.length))
    .replace('[positive/negative]', sentiment)
    .replace('[selected language]', filter.language ?? 'all')
    .replace('[selected period]', filter.period ?? 'all time')
    .replace('[Review data]', reviewBlock)
}

export const DEFAULT_LLM_TEMPLATE = `Below are [N] [positive/negative] reviews for the Steam game [Game Name].
Language: [selected language]
Period: [selected period]

Please analyze the following:
1. Classify main complaints/praises into 5 topics
2. Summarize representative opinions per topic
3. Suggest action items from a planning/marketing perspective

---
[Review data]`
```

- [ ] **Step 2: Implement ExportPanel component**

Replace `src/components/ExportPanel.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { reviewsToMarkdown, reviewsToLlmPrompt, DEFAULT_LLM_TEMPLATE } from '../lib/export-utils'
import { getLanguageDisplayName } from '../lib/steam-languages'

export function ExportPanel({ appId }: { appId: number }) {
  const api = useApi()
  const [reviews, setReviews] = useState<any[]>([])
  const [game, setGame] = useState<any>(null)
  const [langFilter, setLangFilter] = useState('all')
  const [sentimentFilter, setSentimentFilter] = useState<'all' | 'positive' | 'negative'>('all')
  const [languages, setLanguages] = useState<string[]>([])
  const [template, setTemplate] = useState(DEFAULT_LLM_TEMPLATE)
  const [maxReviews, setMaxReviews] = useState(50)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const load = async () => {
      const filter: Record<string, unknown> = {}
      if (langFilter !== 'all') filter.language = langFilter
      const [r, g, stats] = await Promise.all([
        api.getReviews(appId, filter) as Promise<any[]>,
        api.getGame(appId),
        api.getGameStats(appId) as Promise<{ languages: string[] }>
      ])
      let filtered = r
      if (sentimentFilter === 'positive') filtered = r.filter((x: any) => x.voted_up)
      if (sentimentFilter === 'negative') filtered = r.filter((x: any) => !x.voted_up)
      setReviews(filtered)
      setGame(g)
      setLanguages(stats.languages)
    }
    load()
  }, [appId, langFilter, sentimentFilter])

  const limited = reviews.slice(0, maxReviews)
  const gameName = game?.app_name ?? `App ${appId}`
  const filterDesc = `${langFilter === 'all' ? 'All languages' : getLanguageDisplayName(langFilter)}, ${sentimentFilter}`

  const handleCsvExport = () => api.exportCsv(appId, langFilter === 'all' ? {} : { language: langFilter })
  const handleMdExport = () => api.exportMarkdown(appId, langFilter === 'all' ? {} : { language: langFilter })

  const handleCopyReviews = async () => {
    const text = reviewsToMarkdown(limited, gameName, filterDesc)
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleCopyWithPrompt = async () => {
    const text = reviewsToLlmPrompt(limited, gameName, template)
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="export-panel">
      <div className="export-filters">
        <label>
          Language:
          <select value={langFilter} onChange={e => setLangFilter(e.target.value)}>
            <option value="all">All</option>
            {languages.map(l => <option key={l} value={l}>{getLanguageDisplayName(l)}</option>)}
          </select>
        </label>
        <label>
          Sentiment:
          <select value={sentimentFilter} onChange={e => setSentimentFilter(e.target.value as any)}>
            <option value="all">All</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
          </select>
        </label>
        <label>
          Max reviews for clipboard:
          <input type="number" value={maxReviews} onChange={e => setMaxReviews(Number(e.target.value))} min={10} max={500} />
        </label>
      </div>

      <p>{reviews.length} reviews match current filters</p>

      <div className="export-actions">
        <h3>File Export</h3>
        <button onClick={handleCsvExport}>Download CSV</button>
        <button onClick={handleMdExport}>Download Markdown</button>

        <h3>Clipboard</h3>
        <button onClick={handleCopyReviews}>
          {copied ? 'Copied!' : `Copy Reviews (${limited.length})`}
        </button>
        <button onClick={handleCopyWithPrompt}>
          Copy with LLM Prompt
        </button>
      </div>

      <div className="template-editor">
        <h3>LLM Prompt Template</h3>
        <textarea
          value={template}
          onChange={e => setTemplate(e.target.value)}
          rows={10}
        />
        <p className="hint">Use [Game Name], [N], [Review data] as placeholders</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Run dev and verify**

```bash
pnpmdev
```

Expected: Export tab shows filter controls, file export buttons (CSV/Markdown), clipboard copy buttons, and editable LLM prompt template.

- [ ] **Step 4: Commit**

```bash
git add src/components/ExportPanel.tsx src/lib/export-utils.ts
git commit -m "feat: add Export tab with CSV, Markdown, clipboard, and LLM prompt template"
```

---

## Task 12: Game Comparison and Settings

**Files:**
- Modify: `src/components/CompareView.tsx`, `src/components/SettingsDialog.tsx`, `src/components/Layout.tsx`

- [ ] **Step 1: Implement CompareView component**

Replace `src/components/CompareView.tsx`:

```tsx
import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { useApi } from '../hooks/useApi'

interface Props {
  appIds: [number, number]
}

interface CompareData {
  app_id: number
  app_name: string
  review_score_desc: string
  total_reviews: number
  positive_rate: number
  total_collected: number
  languages: string[]
}

export function CompareView({ appIds }: Props) {
  const api = useApi()
  const [data, setData] = useState<[CompareData, CompareData] | null>(null)

  useEffect(() => {
    const load = async () => {
      const results = await Promise.all(appIds.map(async id => {
        const [game, stats] = await Promise.all([
          api.getGame(id) as Promise<any>,
          api.getGameStats(id) as Promise<any>
        ])
        return { ...game, ...stats } as CompareData
      }))
      setData(results as [CompareData, CompareData])
    }
    load()
  }, [appIds[0], appIds[1]])

  if (!data) return <div>Loading comparison...</div>

  const [a, b] = data

  const compareOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category' as const, data: ['Positive Rate', 'Total Reviews (log)'] },
    yAxis: { type: 'value' as const },
    series: [
      { name: a.app_name, type: 'bar', data: [a.positive_rate * 100, Math.log10(a.total_reviews + 1)], color: '#60a5fa' },
      { name: b.app_name, type: 'bar', data: [b.positive_rate * 100, Math.log10(b.total_reviews + 1)], color: '#f472b6' }
    ],
    legend: { show: true }
  }

  return (
    <div className="compare-view">
      <h2>Comparison</h2>
      <table className="compare-table">
        <thead>
          <tr><th></th><th>{a.app_name}</th><th>{b.app_name}</th></tr>
        </thead>
        <tbody>
          <tr><td>Score</td><td>{a.review_score_desc}</td><td>{b.review_score_desc}</td></tr>
          <tr><td>Total Reviews</td><td>{a.total_reviews.toLocaleString()}</td><td>{b.total_reviews.toLocaleString()}</td></tr>
          <tr><td>Collected</td><td>{a.total_collected.toLocaleString()}</td><td>{b.total_collected.toLocaleString()}</td></tr>
          <tr><td>Positive Rate</td><td>{(a.positive_rate * 100).toFixed(1)}%</td><td>{(b.positive_rate * 100).toFixed(1)}%</td></tr>
          <tr><td>Languages</td><td>{a.languages.length}</td><td>{b.languages.length}</td></tr>
        </tbody>
      </table>
      <ReactECharts option={compareOption} style={{ height: 300 }} />
    </div>
  )
}
```

- [ ] **Step 2: Implement SettingsDialog component**

Replace `src/components/SettingsDialog.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

interface Props {
  open: boolean
  onClose: () => void
}

interface Settings {
  tier: 'auto' | '0' | '1'
  apiProvider: 'none' | 'claude' | 'openai' | 'gemini'
  apiKey: string
}

export function SettingsDialog({ open, onClose }: Props) {
  const api = useApi()
  const [settings, setSettings] = useState<Settings>({ tier: 'auto', apiProvider: 'none', apiKey: '' })
  const [gpuInfo, setGpuInfo] = useState<any>(null)

  useEffect(() => {
    if (open) {
      api.getSettings().then((s: any) => s && setSettings(s))
      api.detectGpu().then((info: any) => setGpuInfo(info)).catch(() => {})
    }
  }, [open])

  const handleSave = async () => {
    await api.saveSettings(settings as unknown as Record<string, unknown>)
    onClose()
  }

  if (!open) return null

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-dialog" onClick={e => e.stopPropagation()}>
        <h2>Settings</h2>

        <section>
          <h3>Analysis Tier</h3>
          {gpuInfo && (
            <p className="gpu-info">
              GPU: {gpuInfo.gpu_available ? `${gpuInfo.gpu_name} (${gpuInfo.vram_mb}MB)` : 'Not detected'}
              {gpuInfo.gpu_available && ` — Recommended: Tier ${gpuInfo.recommended_tier}`}
            </p>
          )}
          <select value={settings.tier} onChange={e => setSettings({ ...settings, tier: e.target.value as Settings['tier'] })}>
            <option value="auto">Auto-detect</option>
            <option value="0">Tier 0 (CPU only)</option>
            <option value="1">Tier 1 (GPU)</option>
          </select>
        </section>

        <section>
          <h3>LLM API (Optional)</h3>
          <select value={settings.apiProvider} onChange={e => setSettings({ ...settings, apiProvider: e.target.value as Settings['apiProvider'] })}>
            <option value="none">None</option>
            <option value="claude">Claude</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
          </select>
          {settings.apiProvider !== 'none' && (
            <input
              type="password"
              placeholder="API Key"
              value={settings.apiKey}
              onChange={e => setSettings({ ...settings, apiKey: e.target.value })}
            />
          )}
        </section>

        <div className="dialog-actions">
          <button onClick={onClose}>Cancel</button>
          <button onClick={handleSave} className="primary">Save</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add compare mode and settings button to Layout**

Update `src/components/Layout.tsx` — add to the top bar:

```tsx
// Add state for compare and settings
const [compareMode, setCompareMode] = useState(false)
const [compareIds, setCompareIds] = useState<[number, number] | null>(null)
const [showSettings, setShowSettings] = useState(false)

// Add settings button to nav
<button onClick={() => setShowSettings(true)}>Settings</button>

// Add compare toggle
<button onClick={() => setCompareMode(!compareMode)}>
  {compareMode ? 'Exit Compare' : 'Compare'}
</button>

// Render CompareView when two games are selected in compare mode
// Render SettingsDialog
<SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
```

Imports to add:
```tsx
import { CompareView } from './CompareView'
import { SettingsDialog } from './SettingsDialog'
```

- [ ] **Step 4: Add IPC handlers for settings persistence**

Add to `electron/main/ipc-handlers.ts`:

```typescript
import { app } from 'electron'

const settingsPath = path.join(app.getPath('userData'), 'settings.json')

ipcMain.handle('settings:get', () => {
  try {
    return JSON.parse(fs.readFileSync(settingsPath, 'utf-8'))
  } catch {
    return { tier: 'auto', apiProvider: 'none', apiKey: '' }
  }
})

ipcMain.handle('settings:save', (_event, settings: Record<string, unknown>) => {
  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2))
})
```

- [ ] **Step 5: Run dev and verify**

```bash
pnpmdev
```

Expected: Settings button opens dialog with GPU info, tier selection, and API key config. Compare mode allows selecting two games for side-by-side comparison.

- [ ] **Step 6: Commit**

```bash
git add src/components/CompareView.tsx src/components/SettingsDialog.tsx src/components/Layout.tsx electron/main/ipc-handlers.ts
git commit -m "feat: add game comparison view and settings dialog"
```

---

## Task 13: Styling and Polish

**Files:**
- Create: `src/assets/styles.css`

- [ ] **Step 1: Add CSS for entire app**

Create `src/assets/styles.css` with styles for:
- `.app-layout` — flexbox: sidebar (250px fixed) + main content
- `.sidebar` — dark background, game list with hover/active states
- `.game-input` — input + button row
- `.tab-nav` — horizontal tab buttons
- `.dashboard`, `.charts-grid` — responsive grid layout for chart cards
- `.chart-card` — white card with shadow, padding, heading
- `.topic-card` — bordered card, `.positive` green border, `.negative` red border
- `.topic-keywords` — flex wrap for keyword tags
- `.keyword-tag` — pill-shaped tags
- `.export-panel` — form layout with sections
- `.settings-overlay` — modal backdrop + centered dialog
- `.compare-table` — striped table
- `.progress-bar` — thin bar with animated fill
- `.empty-state` — centered placeholder text

Exact CSS is left to implementation as it depends on overall aesthetic preference, but key structural rules:

```css
.app-layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 260px;
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 16px;
  overflow-y: auto;
  flex-shrink: 0;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #f5f5f5;
}

.tab-nav {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
}

.tab-nav button {
  padding: 8px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab-nav button.active {
  border-bottom-color: #3b82f6;
  color: #3b82f6;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.topics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.topic-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}

.topic-card.negative { border-left: 4px solid #f87171; }
.topic-card.positive { border-left: 4px solid #4ade80; }

.keyword-tag {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px;
  background: #e5e7eb;
  border-radius: 12px;
  font-size: 13px;
}

.progress-bar {
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  margin-top: 8px;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 2px;
  transition: width 0.3s;
}

.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.settings-dialog {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 480px;
  max-height: 80vh;
  overflow-y: auto;
}
```

- [ ] **Step 2: Import styles in main.tsx**

Add to `src/main.tsx`:
```tsx
import './assets/styles.css'
```

- [ ] **Step 3: Run dev and verify visual appearance**

```bash
pnpmdev
```

Expected: App has clean, structured layout with proper spacing, colors, and responsive grid.

- [ ] **Step 4: Commit**

```bash
git add src/assets/styles.css src/main.tsx
git commit -m "feat: add app-wide styling"
```

---

## Task 14: Integration Test — End to End

**Files:** None new — this is a manual verification task.

- [ ] **Step 1: Start the app**

```bash
pnpmdev
```

- [ ] **Step 2: Verify full flow**

1. Enter App ID `730` (or paste `https://store.steampowered.com/app/730/`) and click "Add Game"
2. Click "Fetch Reviews" on Dashboard — watch progress bar
3. After collection, verify Dashboard charts render (donut, trend, language)
4. Switch to Topics tab — click "Run Analysis" — verify topics and keywords appear
5. Switch to Segments tab — verify playtime and language charts, try language filter
6. Switch to Export tab — test CSV download, Markdown download, clipboard copy, copy with prompt
7. Add a second game (e.g., `292030` for Witcher 3)
8. Switch between games in sidebar
9. Open Settings — verify GPU detection, tier selection, API key fields
10. Test Compare mode with both games

- [ ] **Step 3: Fix any issues found during testing**

Address any bugs or UX issues discovered.

- [ ] **Step 4: Commit fixes**

```bash
git add -A
git commit -m "fix: address issues from integration testing"
```

---

## Task 15: Build and Package

**Files:**
- Modify: `electron.vite.config.ts`, `package.json`

- [ ] **Step 1: Configure electron-builder for packaging**

Add to `package.json` build config:

```json
{
  "build": {
    "appId": "com.reviewforge.app",
    "productName": "ReviewForge",
    "win": {
      "target": "nsis"
    },
    "extraResources": [
      {
        "from": "python",
        "to": "python",
        "filter": ["**/*", "!venv/**", "!__pycache__/**"]
      }
    ]
  }
}
```

- [ ] **Step 2: Test production build**

```bash
pnpmbuild
```

Expected: Build succeeds without errors.

- [ ] **Step 3: Commit**

```bash
git add package.json electron.vite.config.ts
git commit -m "feat: configure production build and packaging"
```

---

## Known Items to Address During Implementation

The following items from the spec are intentionally deferred to implementation-time decisions rather than over-specifying in the plan. The executor should address each:

1. **Dashboard trend toggle (daily/weekly/monthly)**: Add a toggle button to the Dashboard trend chart that regroups `dailyCounts` by week/month when selected.

2. **Dashboard 30-day vs all-time comparison**: Add a summary row showing last-30-day positive rate next to all-time positive rate.

3. **Word cloud in Topics tab**: Install `react-wordcloud` or similar. Render keyword frequencies as a word cloud below the topic list. Mark as optional in UI.

4. **Review bomb filter toggle**: Add a checkbox in the Dashboard's collection section: "Include off-topic reviews (review bombs)". Pass `filterOfftopic` to `fetchAllReviews`.

5. **LLM API in-app call**: In ExportPanel, when API key is configured, add a "Send to LLM" button that calls the configured API (Claude/OpenAI/Gemini) with the generated prompt and displays the response inline. Display token usage from the API response.

6. **Model download management UI**: In SettingsDialog, show model download status (downloaded/not downloaded) for Tier 0 and Tier 1 models. Add download/delete buttons.

7. **Compare mode game selection**: In GameSidebar, when compare mode is active, allow selecting two games (checkboxes instead of single click). Pass both selected IDs to CompareView.

8. **Template persistence**: Save custom LLM templates to `settings.json` via the existing settings IPC handlers. Load saved templates in ExportPanel on mount.

9. **Clipboard "Analysis summary" mode**: Add a third clipboard button that copies a formatted summary of the current analysis results (metrics + top topics + keywords) without review text.

10. **Python packaging for distribution**: For production builds, use PyInstaller to bundle the Python sidecar as a standalone executable, or document that users must install Python 3.11+ separately.
