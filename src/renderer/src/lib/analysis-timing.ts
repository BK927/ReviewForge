const LOCAL_ANALYSIS_REVIEWS_PER_MINUTE = 450

export function estimateLocalAnalysisMinutes(reviewCount: number): number {
  if (reviewCount <= 0) return 0
  return Math.max(1, Math.ceil(reviewCount / LOCAL_ANALYSIS_REVIEWS_PER_MINUTE))
}
