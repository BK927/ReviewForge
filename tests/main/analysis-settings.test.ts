import { describe, it, expect } from 'vitest'
import { resolveAnalysisConfig } from '../../src/main/analysis-settings'

describe('resolveAnalysisConfig', () => {
  it('uses an explicit numeric tier from the request config', () => {
    const config = resolveAnalysisConfig({ n_topics: 8, tier: 1 }, { tier: '0' }, 0)

    expect(config).toMatchObject({ tier: 1, topicCountMode: 'auto' })
    expect(config).not.toHaveProperty('n_topics')
  })

  it('uses the saved tier when the request does not provide one', () => {
    const config = resolveAnalysisConfig({ n_topics: 8 }, { tier: '1' }, 0)

    expect(config).toMatchObject({ tier: 1, topicCountMode: 'auto' })
    expect(config).not.toHaveProperty('n_topics')
  })

  it('uses detected GPU tier when settings are auto', () => {
    const config = resolveAnalysisConfig({ n_topics: 8 }, { tier: 'auto' }, 1)

    expect(config).toMatchObject({ tier: 1, topicCountMode: 'auto' })
    expect(config).not.toHaveProperty('n_topics')
  })

  it('falls back to tier 0 when settings are missing or invalid', () => {
    expect(resolveAnalysisConfig({ n_topics: 8 }, undefined, 1)).toMatchObject({ tier: 0, topicCountMode: 'manual', n_topics: 8 })
    expect(resolveAnalysisConfig({ n_topics: 8 }, { tier: 'unexpected' as 'auto' }, 1)).toMatchObject({ tier: 0, topicCountMode: 'manual', n_topics: 8 })
  })

  it('treats legacy tier 0 requests with n_topics as manual mode', () => {
    const config = resolveAnalysisConfig({ n_topics: 6 }, { tier: '0' }, 0)

    expect(config).toMatchObject({ tier: 0, topicCountMode: 'manual', n_topics: 6 })
  })

  it('defaults tier 0 requests without a mode or manual count to auto', () => {
    const config = resolveAnalysisConfig({}, { tier: '0' }, 0)

    expect(config).toMatchObject({ tier: 0, topicCountMode: 'auto' })
    expect(config).not.toHaveProperty('n_topics')
  })

  it('forces tier 1 requests to auto mode even when manual is requested', () => {
    const config = resolveAnalysisConfig({ topicCountMode: 'manual', n_topics: 12 }, { tier: '1' }, 0)

    expect(config).toMatchObject({ tier: 1, topicCountMode: 'auto' })
    expect(config).not.toHaveProperty('n_topics')
  })

  it('preserves explicit manual mode for tier 0 requests', () => {
    const config = resolveAnalysisConfig(
      { topicCountMode: 'manual', n_topics: 10, maxReviews: 500, filter: { language: 'english', steam_purchase: 1, ignored: undefined } },
      { tier: '0' },
      0
    )

    expect(config).toMatchObject({
      tier: 0,
      topicCountMode: 'manual',
      n_topics: 10,
      maxReviews: 500,
      filter: { language: 'english', steam_purchase: 1 }
    })
    expect((config.filter as Record<string, unknown>)).not.toHaveProperty('ignored')
  })
})
