import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { reviewsToMarkdown, analysisToLlmPrompt, DEFAULT_LLM_TEMPLATE } from '../lib/export-utils'
import { getLanguageDisplayName } from '../lib/steam-languages'
import type { AnalysisResult } from './TopicAnalysis'

interface ExportPanelProps {
  appId: number
  analysisResult: AnalysisResult | null
}

export function ExportPanel({ appId, analysisResult }: ExportPanelProps) {
  const api = useApi()
  const [reviews, setReviews] = useState<any[]>([])
  const [game, setGame] = useState<any>(null)
  const [langFilter, setLangFilter] = useState('all')
  const [sentimentFilter, setSentimentFilter] = useState<'all' | 'positive' | 'negative'>('all')
  const [languages, setLanguages] = useState<string[]>([])
  const [template, setTemplate] = useState(DEFAULT_LLM_TEMPLATE)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const load = async () => {
      const filter: Record<string, unknown> = {}
      if (langFilter !== 'all') filter.language = langFilter
      const [r, g, stats] = await Promise.all([
        api.getReviews(appId, filter) as Promise<any[]>,
        api.getGame(appId),
        api.getGameStats(appId) as Promise<{ languages: string[] }>
      ])
      let filtered = r
      if (sentimentFilter === 'positive') filtered = r.filter((x: any) => x.voted_up)
      if (sentimentFilter === 'negative') filtered = r.filter((x: any) => !x.voted_up)
      setReviews(filtered)
      setGame(g)
      setLanguages(stats.languages)
    }
    load()
  }, [appId, langFilter, sentimentFilter])

  const gameName = (game as any)?.app_name ?? `App ${appId}`
  const filterDesc = `${langFilter === 'all' ? 'All languages' : getLanguageDisplayName(langFilter)}, ${sentimentFilter}`

  const handleCsvExport = () => api.exportCsv(appId, langFilter === 'all' ? {} : { language: langFilter })
  const handleMdExport = () => api.exportMarkdown(appId, langFilter === 'all' ? {} : { language: langFilter })

  const setCopiedBriefly = () => {
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleCopyReviews = async () => {
    const text = reviewsToMarkdown(reviews, gameName, filterDesc)
    await navigator.clipboard.writeText(text)
    setCopiedBriefly()
  }

  const handleCopyWithPrompt = async () => {
    if (!analysisResult) return
    const text = analysisToLlmPrompt(analysisResult, gameName, template)
    await navigator.clipboard.writeText(text)
    setCopiedBriefly()
  }

  const hasAnalysis = analysisResult !== null

  return (
    <div className="export-panel">
      <div className="export-filters">
        <label>
          Language:
          <select value={langFilter} onChange={e => setLangFilter(e.target.value)}>
            <option value="all">All</option>
            {languages.map(l => <option key={l} value={l}>{getLanguageDisplayName(l)}</option>)}
          </select>
        </label>
        <label>
          Sentiment:
          <select value={sentimentFilter} onChange={e => setSentimentFilter(e.target.value as any)}>
            <option value="all">All</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
          </select>
        </label>
      </div>

      <p className="review-count">{reviews.length} reviews match current filters</p>

      <div className="export-actions">
        <h3>File Export</h3>
        <button onClick={handleCsvExport}>Download CSV</button>
        <button onClick={handleMdExport}>Download Markdown</button>

        <h3>Clipboard</h3>
        <button onClick={handleCopyReviews}>
          {copied ? 'Copied!' : `Copy Reviews (${reviews.length})`}
        </button>
        <button onClick={handleCopyWithPrompt} disabled={!hasAnalysis}>
          {!hasAnalysis ? 'Run Topic Analysis first' : copied ? 'Copied!' : 'Copy with LLM Prompt'}
        </button>
      </div>

      <div className="template-editor">
        <h3>LLM Prompt Template</h3>
        <textarea
          value={template}
          onChange={e => setTemplate(e.target.value)}
          rows={12}
        />
        <p className="hint">Placeholders: [Game Name], [N], [Positive count], [Negative count], [Model], [Review data]</p>
      </div>
    </div>
  )
}
