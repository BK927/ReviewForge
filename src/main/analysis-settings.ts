export interface SavedSettings {
  tier?: 'auto' | '0' | '1'
}

export type TopicCountMode = 'auto' | 'manual'

export interface NormalizedAnalysisConfig extends Record<string, unknown> {
  tier: number
  topicCountMode: TopicCountMode
  n_topics?: number
  maxReviews?: number
  filter?: Record<string, unknown>
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

function parsePositiveInteger(value: unknown, minimum = 1): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value >= minimum) {
    return Math.trunc(value)
  }

  if (typeof value === 'string' && /^\d+$/.test(value)) {
    const parsed = Number(value)
    if (Number.isFinite(parsed) && parsed >= minimum) {
      return Math.trunc(parsed)
    }
  }

  return null
}

function parseTopicCountMode(value: unknown): TopicCountMode | null {
  if (value === 'auto' || value === 'manual') {
    return value
  }

  return null
}

function normalizeFilter(filter: unknown): Record<string, unknown> | undefined {
  if (!filter || typeof filter !== 'object' || Array.isArray(filter)) {
    return undefined
  }

  const activeEntries = Object.entries(filter).filter(([, value]) => value !== undefined && value !== null && value !== '')
  if (activeEntries.length === 0) {
    return undefined
  }

  return Object.fromEntries(activeEntries)
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

export function resolveTopicCountMode(config: Record<string, unknown>, tier: number): TopicCountMode {
  if (tier >= 1) {
    return 'auto'
  }

  const requestedMode = parseTopicCountMode(config.topicCountMode)
  if (requestedMode !== null) {
    return requestedMode
  }

  return parsePositiveInteger(config.n_topics, 2) !== null ? 'manual' : 'auto'
}

export function resolveAnalysisConfig(
  config: Record<string, unknown>,
  settings?: SavedSettings,
  detectedTier = 0
): NormalizedAnalysisConfig {
  const tier = resolveAnalysisTier(config.tier, settings, detectedTier)
  const topicCountMode = resolveTopicCountMode(config, tier)
  const nTopics = parsePositiveInteger(config.n_topics, 2)
  const maxReviews = parsePositiveInteger(config.maxReviews)
  const filter = normalizeFilter(config.filter)

  const normalizedConfig: NormalizedAnalysisConfig = {
    ...config,
    tier,
    topicCountMode
  }

  if (topicCountMode === 'manual' && nTopics !== null) {
    normalizedConfig.n_topics = nTopics
  } else {
    delete normalizedConfig.n_topics
  }

  if (maxReviews !== null) {
    normalizedConfig.maxReviews = maxReviews
  } else {
    delete normalizedConfig.maxReviews
  }

  if (filter) {
    normalizedConfig.filter = filter
  } else {
    delete normalizedConfig.filter
  }

  return normalizedConfig
}
