import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import Database from 'better-sqlite3'
import { createDb, insertGame, getGame, getAllGames, upsertReviews, getReviews, getGameStats, deleteGame, saveAnalysisCache, getAnalysisCache } from '../../src/main/db'
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

  it('getAllGames returns all games ordered by last_fetched_at', () => {
    insertGame(db, { app_id: 730, app_name: 'CS2', review_score: 8, review_score_desc: 'Very Positive', total_positive: 100, total_negative: 20, total_reviews: 120 })
    insertGame(db, { app_id: 292030, app_name: 'Witcher 3', review_score: 9, review_score_desc: 'Overwhelmingly Positive', total_positive: 800, total_negative: 50, total_reviews: 850 })
    const games = getAllGames(db)
    expect(games).toHaveLength(2)
    expect(games.map(g => g.app_id)).toContain(730)
    expect(games.map(g => g.app_id)).toContain(292030)
  })

  it('deleteGame removes game and all related data', () => {
    insertGame(db, { app_id: 730, app_name: 'CS2', review_score: 8, review_score_desc: 'Very Positive', total_positive: 100, total_negative: 20, total_reviews: 120 })
    upsertReviews(db, [
      { recommendation_id: 'r1', app_id: 730, language: 'english', review_text: 'Good', voted_up: 1, timestamp_created: 1000, timestamp_updated: 1000, playtime_at_review: 600, playtime_forever: 1200, steam_purchase: 1, received_for_free: 0, written_during_early_access: 0, primarily_steam_deck: 0, votes_up: 10, votes_funny: 0, weighted_vote_score: 0.5, comment_count: 0 }
    ])
    deleteGame(db, 730)
    expect(getGame(db, 730)).toBeNull()
    expect(getReviews(db, 730)).toHaveLength(0)
  })

  it('saves and retrieves analysis cache', () => {
    insertGame(db, { app_id: 730, app_name: 'CS2', review_score: 8, review_score_desc: 'Very Positive', total_positive: 100, total_negative: 20, total_reviews: 120 })
    const result = JSON.stringify({ topics: ['lag', 'server'] })
    saveAnalysisCache(db, 730, 'topics', 'english', 'hash-abc', result)
    const cached = getAnalysisCache(db, 730, 'topics', 'hash-abc')
    expect(cached).toBe(result)
  })

  it('getAnalysisCache returns null for missing cache', () => {
    expect(getAnalysisCache(db, 730, 'topics', 'nonexistent-hash')).toBeNull()
  })
})
