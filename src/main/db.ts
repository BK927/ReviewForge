import Database from 'better-sqlite3'

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
  received_for_free?: number
}

export interface GameStats {
  total_collected: number
  positive_count: number
  negative_count: number
  positive_rate: number
  languages: string[]
}

export function createDb(dbPath?: string): Database.Database {
  let resolvedPath = dbPath
  if (!resolvedPath) {
    const { app } = require('electron')
    resolvedPath = require('path').join(app.getPath('userData'), 'reviewforge.db')
  }
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
  if (filter?.period_start !== undefined) {
    sql += ' AND timestamp_created >= ?'
    params.push(filter.period_start)
  }
  if (filter?.period_end !== undefined) {
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
  if (filter?.received_for_free !== undefined) {
    sql += ' AND received_for_free = ?'
    params.push(filter.received_for_free)
  }

  sql += ' ORDER BY timestamp_created DESC'
  return db.prepare(sql).all(...params) as ReviewRecord[]
}

export function getGameStats(db: Database.Database, appId: number): GameStats {
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
  db.transaction(() => {
    db.prepare('DELETE FROM analysis_cache WHERE app_id = ?').run(appId)
    db.prepare('DELETE FROM embeddings WHERE recommendation_id IN (SELECT recommendation_id FROM reviews WHERE app_id = ?)').run(appId)
    db.prepare('DELETE FROM reviews WHERE app_id = ?').run(appId)
    db.prepare('DELETE FROM games WHERE app_id = ?').run(appId)
  })()
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

export function getTopHelpfulReviews(db: Database.Database, appId: number, votedUp: boolean, limit: number = 5): ReviewRecord[] {
  return db.prepare(
    'SELECT * FROM reviews WHERE app_id = ? AND voted_up = ? ORDER BY weighted_vote_score DESC LIMIT ?'
  ).all(appId, votedUp ? 1 : 0, limit) as ReviewRecord[]
}
