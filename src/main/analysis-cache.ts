import crypto from 'crypto'
import Database from 'better-sqlite3'
import { getAnalysisCache, saveAnalysisCache } from './db'
import type { NormalizedAnalysisConfig } from './analysis-settings'

export interface AnalysisCacheIdentity {
  configHash: string
  languageFilter: string
}

export type CachedAnalysisResult = Record<string, unknown>

function normalizeActiveFilterValues(filter: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!filter) {
    return {}
  }

  return Object.fromEntries(
    Object.entries(filter)
      .filter(([, value]) => value !== undefined && value !== null && value !== '')
      .sort(([left], [right]) => left.localeCompare(right))
  )
}

function serializeCacheValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(serializeCacheValue)
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, entryValue]) => [key, serializeCacheValue(entryValue)])
    )
  }

  return value
}

function parseCachedAnalysisResult(resultJson: string | null): CachedAnalysisResult | null {
  if (!resultJson) {
    return null
  }

  try {
    const parsed = JSON.parse(resultJson) as unknown
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as CachedAnalysisResult
    }
  } catch {
    return null
  }

  return null
}

export function buildAnalysisCacheIdentity(config: NormalizedAnalysisConfig): AnalysisCacheIdentity {
  const activeFilters = normalizeActiveFilterValues(config.filter)
  const cacheDescriptor: Record<string, unknown> = {
    tier: config.tier,
    topicCountMode: config.topicCountMode,
    maxReviews: config.maxReviews ?? null,
    filter: activeFilters
  }

  if (config.topicCountMode === 'manual' && typeof config.n_topics === 'number') {
    cacheDescriptor.n_topics = config.n_topics
  }

  return {
    configHash: crypto.createHash('md5').update(JSON.stringify(serializeCacheValue(cacheDescriptor))).digest('hex'),
    languageFilter: typeof activeFilters.language === 'string' ? activeFilters.language : 'all'
  }
}

export function getCachedAnalysisResult(
  db: Database.Database,
  appId: number,
  analysisType: string,
  config: NormalizedAnalysisConfig
): CachedAnalysisResult | null {
  const { configHash } = buildAnalysisCacheIdentity(config)
  return parseCachedAnalysisResult(getAnalysisCache(db, appId, analysisType, configHash))
}

export function saveCachedAnalysisResult(
  db: Database.Database,
  appId: number,
  analysisType: string,
  config: NormalizedAnalysisConfig,
  result: CachedAnalysisResult
): void {
  const { configHash, languageFilter } = buildAnalysisCacheIdentity(config)
  saveAnalysisCache(db, appId, analysisType, languageFilter, configHash, JSON.stringify(result))
}
