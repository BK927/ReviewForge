import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import Database from 'better-sqlite3'
import fs from 'fs'
import path from 'path'
import { buildAnalysisCacheIdentity, getCachedAnalysisResult, saveCachedAnalysisResult } from '../../src/main/analysis-cache'
import { createDb, insertGame } from '../../src/main/db'
import type { NormalizedAnalysisConfig } from '../../src/main/analysis-settings'

const TEST_DB_PATH = path.join(__dirname, 'analysis-cache.test.db')

function createConfig(overrides: Partial<NormalizedAnalysisConfig> = {}): NormalizedAnalysisConfig {
  return {
    tier: 0,
    topicCountMode: 'manual',
    n_topics: 8,
    maxReviews: 500,
    filter: { language: 'english' },
    ...overrides
  }
}

describe('analysis cache helpers', () => {
  let db: Database.Database

  beforeEach(() => {
    db = createDb(TEST_DB_PATH)
    insertGame(db, {
      app_id: 730,
      app_name: 'Counter-Strike 2',
      review_score: 8,
      review_score_desc: 'Very Positive',
      total_positive: 1000,
      total_negative: 200,
      total_reviews: 1200
    })
  })

  afterEach(() => {
    db.close()
    if (fs.existsSync(TEST_DB_PATH)) fs.unlinkSync(TEST_DB_PATH)
  })

  it('includes topicCountMode in the cache key', () => {
    const manualIdentity = buildAnalysisCacheIdentity(createConfig({ topicCountMode: 'manual', n_topics: 6 }))
    const autoIdentity = buildAnalysisCacheIdentity(createConfig({ topicCountMode: 'auto', n_topics: undefined }))

    expect(manualIdentity.configHash).not.toBe(autoIdentity.configHash)
  })

  it('ignores manual n_topics when the mode is auto', () => {
    const first = buildAnalysisCacheIdentity(createConfig({ topicCountMode: 'auto', n_topics: 4 }))
    const second = buildAnalysisCacheIdentity(createConfig({ topicCountMode: 'auto', n_topics: 12 }))

    expect(first.configHash).toBe(second.configHash)
  })

  it('includes active filter values in the cache key', () => {
    const first = buildAnalysisCacheIdentity(createConfig({ filter: { language: 'english', steam_purchase: 1, ignored: undefined } }))
    const second = buildAnalysisCacheIdentity(createConfig({ filter: { language: 'english', steam_purchase: 0 } }))

    expect(first.configHash).not.toBe(second.configHash)
  })

  it('reuses only exact cache hits for the normalized mode and filters', () => {
    const config = createConfig({ topicCountMode: 'manual', n_topics: 8, filter: { language: 'english', steam_purchase: 1 } })
    const result = {
      positive_topics: [],
      negative_topics: [],
      total_reviews: 50,
      total_available: 120,
      sampled: true,
      topic_count_mode: 'manual',
      requested_k: 8,
      effective_k: 8,
      recommendation_confidence: 'high',
      recommendation_reason: 'User selected a manual topic count.'
    }

    saveCachedAnalysisResult(db, 730, 'topics', config, result)

    expect(getCachedAnalysisResult(db, 730, 'topics', config)).toEqual(result)
    expect(getCachedAnalysisResult(db, 730, 'topics', createConfig({ topicCountMode: 'auto', filter: { language: 'english', steam_purchase: 1 } }))).toBeNull()
    expect(getCachedAnalysisResult(db, 730, 'topics', createConfig({ topicCountMode: 'manual', n_topics: 8, filter: { language: 'english', steam_purchase: 0 } }))).toBeNull()
  })

  it('persists returned recommendation metadata in the cached result', () => {
    const config = createConfig({ topicCountMode: 'auto', n_topics: undefined, filter: { language: 'english' } })
    const result = {
      positive_topics: [],
      negative_topics: [],
      total_reviews: 400,
      topic_count_mode: 'auto',
      requested_k: null,
      effective_k: 5,
      recommendation_confidence: 'medium',
      recommendation_reason: 'Best balance of separation and stability across tested k values.',
      recommendation_details: {
        candidate_range: [4, 5, 6],
        fallback_used: false
      }
    }

    saveCachedAnalysisResult(db, 730, 'topics', config, result)

    expect(getCachedAnalysisResult(db, 730, 'topics', config)).toEqual(result)
  })
})
