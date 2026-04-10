import { describe, it, expect } from 'vitest'
import { estimateLocalAnalysisMinutes } from '../../src/renderer/src/lib/analysis-timing'

describe('estimateLocalAnalysisMinutes', () => {
  it('returns a conservative estimate for medium-sized runs', () => {
    expect(estimateLocalAnalysisMinutes(3000)).toBe(7)
  })

  it('scales to larger local CPU-sized runs', () => {
    expect(estimateLocalAnalysisMinutes(5000)).toBe(12)
  })
})
