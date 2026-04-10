export interface SavedSettings {
  tier?: 'auto' | '0' | '1'
}

function parseTier(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
    return Math.trunc(value)
  }

  if (value === '0' || value === '1') {
    return Number(value)
  }

  return null
}

export function resolveAnalysisTier(requestedTier: unknown, settings?: SavedSettings, detectedTier = 0): number {
  const explicitTier = parseTier(requestedTier)
  if (explicitTier !== null) return explicitTier

  if (settings?.tier === 'auto') {
    return detectedTier
  }

  const savedTier = parseTier(settings?.tier)
  return savedTier ?? 0
}

export function resolveAnalysisConfig(
  config: Record<string, unknown>,
  settings?: SavedSettings,
  detectedTier = 0
): Record<string, unknown> {
  return {
    ...config,
    tier: resolveAnalysisTier(config.tier, settings, detectedTier)
  }
}
