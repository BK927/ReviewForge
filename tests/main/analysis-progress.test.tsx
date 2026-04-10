import { describe, it, expect } from 'vitest'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { AnalysisProgress } from '../../src/renderer/src/components/AnalysisProgress'

describe('AnalysisProgress', () => {
  it('shows recommendation stage for auto tier 0 runs', () => {
    const html = renderToStaticMarkup(
      React.createElement(AnalysisProgress, {
        data: {
          stage: 'recommendation',
          percent: 52,
          message: 'Calculating recommended topic count...',
          elapsed_ms: 3200
        },
        showRecommendationStage: true
      })
    )

    expect(html).toContain('Recommendation')
    expect(html).toContain('Calculating recommended topic count...')
  })

  it('does not show recommendation stage for manual or tier 1 runs', () => {
    const html = renderToStaticMarkup(
      React.createElement(AnalysisProgress, {
        data: {
          stage: 'clustering',
          percent: 65,
          message: 'Clustering reviews...',
          elapsed_ms: 2000
        },
        showRecommendationStage: false
      })
    )

    expect(html).not.toContain('Recommendation')
    expect(html).toContain('Clustering')
  })
})
