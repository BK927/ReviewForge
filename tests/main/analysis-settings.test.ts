import { describe, it, expect } from 'vitest'
import { resolveAnalysisConfig } from '../../src/main/analysis-settings'

describe('resolveAnalysisConfig', () => {
  it('uses an explicit numeric tier from the request config', () => {
    const config = resolveAnalysisConfig({ n_topics: 8, tier: 1 }, { tier: '0' }, 0)

    expect(config).toMatchObject({ n_topics: 8, tier: 1 })
  })

  it('uses the saved tier when the request does not provide one', () => {
    const config = resolveAnalysisConfig({ n_topics: 8 }, { tier: '1' }, 0)

    expect(config).toMatchObject({ n_topics: 8, tier: 1 })
  })

  it('uses detected GPU tier when settings are auto', () => {
    const config = resolveAnalysisConfig({ n_topics: 8 }, { tier: 'auto' }, 1)

    expect(config).toMatchObject({ n_topics: 8, tier: 1 })
  })

  it('falls back to tier 0 when settings are missing or invalid', () => {
    expect(resolveAnalysisConfig({ n_topics: 8 }, undefined, 1)).toMatchObject({ tier: 0 })
    expect(resolveAnalysisConfig({ n_topics: 8 }, { tier: 'unexpected' as 'auto' }, 1)).toMatchObject({ tier: 0 })
  })
})
