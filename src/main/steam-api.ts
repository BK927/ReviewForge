export function parseAppId(input: string): number | null {
  const trimmed = input.trim()

  // Plain number
  if (/^\d+$/.test(trimmed)) return parseInt(trimmed, 10)

  // URL: extract from /app/<id>
  const match = trimmed.match(/\/app\/(\d+)/)
  if (match) return parseInt(match[1], 10)

  return null
}

export function transformReview(raw: Record<string, unknown>, appId: number) {
  const author = raw.author as Record<string, unknown> | undefined
  const weightedScore = raw.weighted_vote_score
  return {
    recommendation_id: String(raw.recommendationid),
    app_id: appId,
    language: String(raw.language ?? ''),
    review_text: String(raw.review ?? ''),
    voted_up: raw.voted_up ? 1 : 0,
    timestamp_created: Number(raw.timestamp_created ?? 0),
    timestamp_updated: Number(raw.timestamp_updated ?? 0),
    playtime_at_review: Number(author?.playtime_at_review ?? 0),
    playtime_forever: Number(author?.playtime_forever ?? 0),
    steam_purchase: raw.steam_purchase ? 1 : 0,
    received_for_free: raw.received_for_free ? 1 : 0,
    written_during_early_access: raw.written_during_early_access ? 1 : 0,
    primarily_steam_deck: raw.primarily_steam_deck ? 1 : 0,
    votes_up: Number(raw.votes_up ?? 0),
    votes_funny: Number(raw.votes_funny ?? 0),
    weighted_vote_score: typeof weightedScore === 'string' ? parseFloat(weightedScore) : Number(weightedScore ?? 0),
    comment_count: Number(raw.comment_count ?? 0)
  }
}

export function transformQuerySummary(raw: Record<string, unknown>, appId: number) {
  return {
    app_id: appId,
    app_name: '',
    review_score: Number(raw.review_score ?? 0),
    review_score_desc: String(raw.review_score_desc ?? ''),
    total_positive: Number(raw.total_positive ?? 0),
    total_negative: Number(raw.total_negative ?? 0),
    total_reviews: Number(raw.total_reviews ?? 0)
  }
}

export interface FetchProgress {
  fetched: number
  total: number
  cursor: string
}

export async function fetchGameName(appId: number): Promise<string> {
  const url = `https://store.steampowered.com/api/appdetails?appids=${appId}&filters=basic`
  try {
    const data = await fetchJson(url) as Record<string, unknown>
    const appData = data[String(appId)] as Record<string, unknown> | undefined
    if (appData?.success && appData.data) {
      const details = appData.data as Record<string, unknown>
      return String(details.name ?? '')
    }
  } catch {
    // Fall through — name will remain empty
  }
  return ''
}

export async function fetchAllReviews(
  appId: number,
  onBatch: (reviews: ReturnType<typeof transformReview>[], summary: ReturnType<typeof transformQuerySummary> | null) => void,
  onProgress: (progress: FetchProgress) => void,
  options: { language?: string; filterOfftopic?: boolean } = {}
): Promise<void> {
  let cursor = '*'
  let totalReviews = 0
  let fetchedCount = 0
  let isFirstPage = true

  const language = options.language ?? 'all'
  const offtopic = options.filterOfftopic !== false ? 1 : 0

  while (true) {
    const url = `https://store.steampowered.com/appreviews/${appId}?json=1&filter=recent&language=${language}&num_per_page=100&cursor=${encodeURIComponent(cursor)}&filter_offtopic_activity=${offtopic}`

    const response = await fetchJson(url)

    if (!response.success) throw new Error(`Steam API returned success=0 for app ${appId}`)

    const reviews = (response.reviews as Record<string, unknown>[]) ?? []

    if (reviews.length === 0) break

    const transformed = reviews.map(r => transformReview(r, appId))
    let summary: ReturnType<typeof transformQuerySummary> | null = null

    if (isFirstPage && response.query_summary) {
      summary = transformQuerySummary(response.query_summary as Record<string, unknown>, appId)
      totalReviews = summary.total_reviews
      isFirstPage = false
    }

    onBatch(transformed, summary)
    fetchedCount += transformed.length
    cursor = String(response.cursor ?? '')

    onProgress({ fetched: fetchedCount, total: totalReviews, cursor })

    // Rate limit: wait 500ms between requests
    await new Promise(resolve => setTimeout(resolve, 500))
  }
}

async function fetchJson(url: string, retries = 3): Promise<Record<string, unknown>> {
  // Use global fetch (available in Electron's main process via node 18+)
  const fetchFn: typeof fetch = (globalThis as unknown as { fetch?: typeof fetch }).fetch ?? fetch

  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const response = await fetchFn(url)

      if (response.status === 429 || response.status >= 500) {
        const delay = Math.pow(2, attempt) * 1000 + Math.random() * 500
        await new Promise(resolve => setTimeout(resolve, delay))
        continue
      }

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      return await response.json() as Record<string, unknown>
    } catch (err) {
      if (attempt === retries - 1) throw err
      const delay = Math.pow(2, attempt) * 1000
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  throw new Error('Max retries exceeded')
}
