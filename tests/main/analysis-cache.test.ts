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
    min_review_words: 5,
    merge_threshold: 0.80,
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
      positive_k: 8,
      negative_k: 8,
      positive_confidence: null,
      negative_confidence: null,
      positive_reason: 'Using requested topic count',
      negative_reason: 'Using requested topic count',
      short_review_summary: { count: 0, positive_rate: 0.0, frequent_phrases: [] },
      merge_info: { positive: { original_topic_count: 0, merged_topic_count: 0, merges: [] }, negative: { original_topic_count: 0, merged_topic_count: 0, merges: [] } }
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
      positive_k: 3,
      negative_k: 5,
      positive_confidence: 'high',
      negative_confidence: 'medium',
      positive_reason: 'Best balance of separation and stability across tested k values',
      negative_reason: 'Best balance of separation and stability across tested k values',
      recommendation_details: {
        tested_candidates: { positive: [2, 3, 4], negative: [3, 4, 5, 6] },
        per_group_sample_counts: { positive: 200, negative: 200 },
        positive_summary: { k: 3, score: 0.71, margin: 0.1 },
        negative_summary: { k: 5, score: 0.65, margin: 0.08 },
        used_fallback: false
      },
      short_review_summary: { count: 5, positive_rate: 0.6, frequent_phrases: [] },
      merge_info: { positive: { original_topic_count: 4, merged_topic_count: 3, merges: [] }, negative: { original_topic_count: 6, merged_topic_count: 5, merges: [] } }
    }

    saveCachedAnalysisResult(db, 730, 'topics', config, result)

    expect(getCachedAnalysisResult(db, 730, 'topics', config)).toEqual(result)
  })

  it('cache hash changes when min_review_words changes', () => {
    const base = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 5, merge_threshold: 0.80 } as NormalizedAnalysisConfig)
    const changed = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 3, merge_threshold: 0.80 } as NormalizedAnalysisConfig)
    expect(base.configHash).not.toBe(changed.configHash)
  })

  it('cache hash changes when merge_threshold changes', () => {
    const base = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 5, merge_threshold: 0.80 } as NormalizedAnalysisConfig)
    const changed = buildAnalysisCacheIdentity({ tier: 0, topicCountMode: 'auto', min_review_words: 5, merge_threshold: 0.90 } as NormalizedAnalysisConfig)
    expect(base.configHash).not.toBe(changed.configHash)
  })
})
