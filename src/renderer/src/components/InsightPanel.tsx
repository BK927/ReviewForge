import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import type { AnalysisResult } from './TopicAnalysis'
import {
  buildTopicLabelingPrompt,
  buildOverallSummaryPrompt,
  buildSegmentPrompt,
  buildTimelinePrompt,
} from '../lib/llm-prompts'

type PromptType = 'summary' | 'topics' | 'segments' | 'timeline'

const PROMPT_LABELS: Record<PromptType, string> = {
  summary: 'Overall Summary',
  topics: 'Topic Labels',
  segments: 'Segment Interpretation',
  timeline: 'Timeline Narrative',
}

function getPrompt(type: PromptType, result: AnalysisResult, gameName: string, language: string): string {
  switch (type) {
    case 'summary': return buildOverallSummaryPrompt(result, gameName, language)
    case 'topics': return buildTopicLabelingPrompt(
      [...result.negative_topics, ...result.positive_topics], language
    )
    case 'segments': return buildSegmentPrompt(result, language)
    case 'timeline': return buildTimelinePrompt(result, language)
  }
}

interface InsightPanelProps {
  analysisResult: AnalysisResult
  gameName: string
}

export function InsightPanel({ analysisResult, gameName }: InsightPanelProps) {
  const api = useApi()
  const [llmMode, setLlmMode] = useState<string>('off')
  const [llmLanguage, setLlmLanguage] = useState<string>('auto')
  const [responses, setResponses] = useState<Partial<Record<PromptType, string>>>({})
  const [loading, setLoading] = useState<PromptType | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState<PromptType | null>(null)

  useEffect(() => {
    api.getSettings().then((s: any) => {
      if (s) {
        setLlmMode(s.llmMode ?? 'semi')
        setLlmLanguage(s.llmLanguage ?? 'auto')
      }
    })
  }, [])

  if (llmMode === 'off') return null

  const language = llmLanguage === 'auto' ? 'auto' : llmLanguage

  // Semi-auto: copy prompt to clipboard
  const handleCopy = async (type: PromptType) => {
    const prompt = getPrompt(type, analysisResult, gameName, language)
    await navigator.clipboard.writeText(prompt)
    setCopied(type)
    setTimeout(() => setCopied(null), 2000)
  }

  // Auto: call LLM API
  const handleGenerate = async (type: PromptType) => {
    setLoading(type)
    setError(null)
    try {
      const prompt = getPrompt(type, analysisResult, gameName, language)
      const res = await api.callLlm(prompt) as { text: string }
      setResponses(prev => ({ ...prev, [type]: res.text }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate insight')
    } finally {
      setLoading(null)
    }
  }

  const promptTypes: PromptType[] = ['summary', 'topics', 'segments', 'timeline']

  if (llmMode === 'semi') {
    return (
      <div className="insight-panel" style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
        <h3 style={{ marginTop: 0 }}>AI Prompts</h3>
        <p style={{ fontSize: '0.85rem', opacity: 0.7, marginBottom: '0.75rem' }}>Copy a specialized prompt and paste it into your preferred AI assistant.</p>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {promptTypes.map(type => (
            <button key={type} onClick={() => handleCopy(type)} className="prompt-copy-btn">
              {copied === type ? 'Copied!' : `Copy: ${PROMPT_LABELS[type]}`}
            </button>
          ))}
        </div>
      </div>
    )
  }

  // Auto mode
  return (
    <div className="insight-panel" style={{ marginBottom: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
      <h3 style={{ marginTop: 0 }}>AI Insights</h3>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        {promptTypes.map(type => (
          <button
            key={type}
            onClick={() => handleGenerate(type)}
            disabled={loading !== null}
            className="prompt-copy-btn"
          >
            {loading === type ? 'Generating...' : responses[type] ? `Regenerate: ${PROMPT_LABELS[type]}` : `Generate: ${PROMPT_LABELS[type]}`}
          </button>
        ))}
      </div>
      {error && <div className="analysis-error" style={{ marginBottom: '0.5rem' }}>{error}</div>}
      {promptTypes.filter(t => responses[t]).map(type => (
        <div key={type} style={{ marginBottom: '1rem' }}>
          <h4 style={{ marginBottom: '0.25rem' }}>{PROMPT_LABELS[type]}</h4>
          <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: 1.6, padding: '0.75rem', backgroundColor: '#f9fafb', borderRadius: '6px' }}>
            {responses[type]}
          </div>
        </div>
      ))}
    </div>
  )
}
