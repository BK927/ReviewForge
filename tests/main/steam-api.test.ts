import { describe, it, expect } from 'vitest'
import { parseAppId, transformReview, transformQuerySummary } from '../../src/main/steam-api'

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
