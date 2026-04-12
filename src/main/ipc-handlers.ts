import { ipcMain, BrowserWindow, dialog, app } from 'electron'
import Database from 'better-sqlite3'
import { insertGame, getGame, getAllGames, deleteGame, getGameStats, upsertReviews, getReviews, getTopHelpfulReviews } from './db'
import { parseAppId, fetchAllReviews, fetchGameName, transformQuerySummary } from './steam-api'
import { SidecarManager } from './sidecar'
import { resolveAnalysisConfig, type NormalizedAnalysisConfig, type SavedSettings } from './analysis-settings'
import { getCachedAnalysisResult, saveCachedAnalysisResult } from './analysis-cache'
import fs from 'fs'
import path from 'path'

export function registerIpcHandlers(db: Database.Database, sidecar: SidecarManager, getMainWindow: () => BrowserWindow | null): void {
  const settingsPath = path.join(app.getPath('userData'), 'settings.json')

  const loadSettings = (): SavedSettings & { apiProvider?: string; apiKey?: string } => {
    try {
      return JSON.parse(fs.readFileSync(settingsPath, 'utf-8'))
    } catch {
      return { tier: 'auto', apiProvider: 'none', apiKey: '' }
    }
  }

  ipcMain.handle('game:add', async (_event, input: string) => {
    const appId = parseAppId(input)
    if (!appId) throw new Error('Invalid App ID or URL')

    const existing = getGame(db, appId)
    if (existing) return existing

    // Fetch first page to get query_summary
    const url = `https://store.steampowered.com/appreviews/${appId}?json=1&language=all&num_per_page=1`
    const response = await fetch(url)
    const data = await response.json() as Record<string, unknown>
    if (!data.success) throw new Error('Failed to fetch game info')

    const summary = transformQuerySummary(data.query_summary as Record<string, unknown>, appId)
    summary.app_name = await fetchGameName(appId) || `App ${appId}`

    insertGame(db, summary)
    return getGame(db, appId)
  })

  ipcMain.handle('game:list', () => getAllGames(db))
  ipcMain.handle('game:get', (_event, appId: number) => getGame(db, appId))
  ipcMain.handle('game:delete', (_event, appId: number) => deleteGame(db, appId))
  ipcMain.handle('game:stats', (_event, appId: number) => getGameStats(db, appId))

  ipcMain.handle('reviews:fetch', async (_event, appId: number, options?: { maxReviews?: number }) => {
    const win = getMainWindow()
    const existing = getGame(db, appId)
    await fetchAllReviews(
      appId,
      (reviews, summary) => {
        if (summary) {
          // Preserve app_name from initial game:add fetch
          if (!summary.app_name && existing?.app_name) summary.app_name = existing.app_name
          insertGame(db, summary)
        }
        upsertReviews(db, reviews)
      },
      (progress) => {
        win?.webContents.send('progress', { type: 'fetch', appId, ...progress })
      },
      { maxReviews: options?.maxReviews }
    )
    return getGameStats(db, appId)
  })

  ipcMain.handle('reviews:get', (_event, appId: number, filter?: Record<string, unknown>) => {
    return getReviews(db, appId, filter as Parameters<typeof getReviews>[2])
  })

  ipcMain.handle('reviews:top-helpful', (_event, appId: number, votedUp: boolean, limit?: number) => {
    return getTopHelpfulReviews(db, appId, votedUp, limit ?? 5)
  })

  ipcMain.handle('analysis:get-cached', async (_event, appId: number, config?: Record<string, unknown>) => {
    if (config) {
      const settings = loadSettings()
      const detectedTier = settings.tier === 'auto'
        ? Number(((await sidecar.send('detect_gpu')) as { recommended_tier?: unknown })?.recommended_tier ?? 0)
        : 0
      const analysisConfig = resolveAnalysisConfig(config, settings, detectedTier)

      return getCachedAnalysisResult(db, appId, 'topics', analysisConfig)
    }

    // Return the most recent cached result for this app, regardless of config
    const row = db.prepare('SELECT result_json FROM analysis_cache WHERE app_id = ? AND analysis_type = ? ORDER BY created_at DESC LIMIT 1').get(appId, 'topics') as { result_json: string } | undefined
    if (!row) return null
    try {
      return JSON.parse(row.result_json)
    } catch {
      return null
    }
  })

  ipcMain.handle('analysis:detect-gpu', async () => {
    return sidecar.send('detect_gpu')
  })

  ipcMain.handle('analysis:run', async (_event, appId: number, config: Record<string, unknown>) => {
    const win = getMainWindow()
    const sendProgress = async (message: string): Promise<void> => {
      win?.webContents.send('progress', { type: 'analysis', appId, stage: 'idle', percent: 0, message })
      // Yield event loop so the queued IPC message is actually delivered before blocking work
      await new Promise(resolve => setImmediate(resolve))
    }

    const settings = loadSettings()
    const detectedTier = settings.tier === 'auto'
      ? Number(((await sidecar.send('detect_gpu')) as { recommended_tier?: unknown })?.recommended_tier ?? 0)
      : 0
    const analysisConfig: NormalizedAnalysisConfig = resolveAnalysisConfig(config, settings, detectedTier)
    const cachedResult = getCachedAnalysisResult(db, appId, 'topics', analysisConfig)

    if (cachedResult) {
      return cachedResult
    }

    await sendProgress('Loading reviews from database...')

    let reviews = getReviews(db, appId, analysisConfig.filter as Parameters<typeof getReviews>[2])
    const totalAvailable = reviews.length
    const maxReviews = analysisConfig.maxReviews as number | undefined
    if (maxReviews && reviews.length > maxReviews) {
      reviews = reviews.slice(0, maxReviews)
    }
    const reviewData = reviews.map(r => ({
      id: r.recommendation_id,
      text: r.review_text,
      voted_up: r.voted_up === 1,
      language: r.language,
      playtime: r.playtime_at_review,
      steam_deck: r.primarily_steam_deck === 1,
      steam_purchase: r.steam_purchase === 1,
      timestamp: r.timestamp_created
    }))

    await sendProgress(`Sending ${reviewData.length.toLocaleString()} reviews to analysis engine...`)

    const result = await sidecar.send('analyze', { reviews: reviewData, config: analysisConfig }, (progress) => {
      win?.webContents.send('progress', { type: 'analysis', appId, ...progress })
    }) as Record<string, unknown>
    const finalResult = { ...result, total_available: totalAvailable, sampled: reviews.length < totalAvailable }

    saveCachedAnalysisResult(db, appId, 'topics', analysisConfig, finalResult)

    return finalResult
  })

  ipcMain.handle('export:csv', async (_event, appId: number, filter: Record<string, unknown>) => {
    const reviews = getReviews(db, appId, filter as Parameters<typeof getReviews>[2])
    const result = await dialog.showSaveDialog({ defaultPath: `reviews_${appId}.csv`, filters: [{ name: 'CSV', extensions: ['csv'] }] })
    if (result.canceled || !result.filePath) return null

    const BOM = '\uFEFF'
    const header = 'recommendation_id,language,review_text,voted_up,timestamp_created,playtime_at_review,steam_purchase,votes_up,weighted_vote_score\n'
    const rows = reviews.map(r => {
      const text = `"${r.review_text.replace(/"/g, '""')}"`
      return `${r.recommendation_id},${r.language},${text},${r.voted_up},${r.timestamp_created},${r.playtime_at_review},${r.steam_purchase},${r.votes_up},${r.weighted_vote_score}`
    }).join('\n')

    fs.writeFileSync(result.filePath, BOM + header + rows, 'utf-8')
    return result.filePath
  })

  ipcMain.handle('export:markdown', async (_event, appId: number, filter: Record<string, unknown>) => {
    const reviews = getReviews(db, appId, filter as Parameters<typeof getReviews>[2])
    const game = getGame(db, appId)
    const stats = getGameStats(db, appId)

    let md = `# ${game?.app_name ?? `App ${appId}`} Review Analysis\n\n`
    md += `- Total Reviews: ${stats.total_collected}\n`
    md += `- Positive Rate: ${(stats.positive_rate * 100).toFixed(1)}%\n`
    md += `- Languages: ${stats.languages.join(', ')}\n\n`
    md += `## Reviews\n\n`

    for (const r of reviews.slice(0, 200)) {
      md += `### ${r.voted_up ? '+' : '-'} [${r.language}] (${Math.round(r.playtime_at_review / 60)}h)\n`
      md += `${r.review_text}\n\n`
    }

    const result = await dialog.showSaveDialog({ defaultPath: `reviews_${appId}.md`, filters: [{ name: 'Markdown', extensions: ['md'] }] })
    if (result.canceled || !result.filePath) return null
    fs.writeFileSync(result.filePath, md, 'utf-8')
    return result.filePath
  })

  ipcMain.handle('settings:get', () => {
    return loadSettings()
  })

  ipcMain.handle('settings:save', (_event, settings: Record<string, unknown>) => {
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf-8')
    return true
  })
}
