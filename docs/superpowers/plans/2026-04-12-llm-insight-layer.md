# Feature 6: LLM Insight Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LLM-powered natural language insights with three modes: auto (API call), semi-auto (prompt clipboard copy), and off.

**Architecture:** Four prompt builder functions (pure, testable) generate specialized prompts for each analysis aspect. A `llm-service.ts` module in the main process handles API calls to Claude/OpenAI/Gemini using native `fetch`. A single `InsightPanel` component renders both auto mode (generate button + display) and semi-auto mode (copy prompt buttons). Settings extend the existing SettingsDialog with `llmMode` and `llmLanguage`.

**Tech Stack:** TypeScript, Node.js `fetch`, React, Vitest

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/renderer/src/lib/llm-prompts.ts` | 4 prompt builder functions |
| Create | `tests/renderer/llm-prompts.test.ts` | Tests for prompt builders |
| Modify | `src/renderer/src/components/SettingsDialog.tsx:9-13,54-69` | Add llmMode + llmLanguage controls |
| Create | `src/main/llm-service.ts` | API wrapper for Claude/OpenAI/Gemini |
| Create | `tests/main/llm-service.test.ts` | Tests for LLM service (mocked fetch) |
| Modify | `src/main/ipc-handlers.ts:190-197` | Add `llm:call` handler |
| Modify | `src/preload/index.ts:29-31` | Add `callLlm` method |
| Create | `src/renderer/src/components/InsightPanel.tsx` | Unified auto/semi-auto insight UI |
| Modify | `src/renderer/src/components/TopicAnalysis.tsx:317-359` | Integrate InsightPanel |

---

### Task 1: Prompt library + test

**Files:**
- Create: `src/renderer/src/lib/llm-prompts.ts`
- Create: `tests/renderer/llm-prompts.test.ts`

- [ ] **Step 1: Write the test file**

Create `tests/renderer/llm-prompts.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import {
  buildTopicLabelingPrompt,
  buildOverallSummaryPrompt,
  buildSegmentPrompt,
  buildTimelinePrompt,
} from '../../src/renderer/src/lib/llm-prompts'

const mockTopics = [
  {
    id: 0, label: 'combat, system', review_count: 50,
    keywords: [{ word: 'combat', score: 0.9 }, { word: 'system', score: 0.7 }],
    sample_reviews: ['Great combat system', 'The fighting is really good'],
  },
  {
    id: 1, label: 'story, narrative', review_count: 30,
    keywords: [{ word: 'story', score: 0.85 }, { word: 'narrative', score: 0.6 }],
    sample_reviews: ['Amazing story', 'The plot kept me engaged'],
  },
]

const mockResult = {
  positive_topics: mockTopics,
  negative_topics: [
    {
      id: 0, label: 'bugs, crashes', review_count: 40,
      keywords: [{ word: 'bugs', score: 0.9 }, { word: 'crashes', score: 0.8 }],
      sample_reviews: ['Too many bugs', 'Game crashes constantly'],
    },
  ],
  total_reviews: 200,
  positive_count: 120,
  negative_count: 80,
  tier: 0,
  model: 'e5-small',
  segment_topic_cross: {
    playtime: [
      {
        segment_label: '0-2h', total_reviews: 50, positive_rate: 0.4,
        positive_topic_distribution: [{ topic_id: 0, topic_label: 'combat', count: 10, proportion: 0.5 }],
        negative_topic_distribution: [{ topic_id: 0, topic_label: 'bugs', count: 15, proportion: 0.6 }],
      },
    ],
    language: [], steam_deck: [], purchase_type: [],
  },
  topics_over_time: {
    monthly: [
      {
        period: '2024-01', total_reviews: 60, positive_rate: 0.7,
        positive_topic_distribution: [{ topic_id: 0, topic_label: 'combat', count: 20, proportion: 0.6 }],
        negative_topic_distribution: [{ topic_id: 0, topic_label: 'bugs', count: 10, proportion: 0.5 }],
      },
      {
        period: '2024-02', total_reviews: 40, positive_rate: 0.5,
        positive_topic_distribution: [{ topic_id: 0, topic_label: 'combat', count: 10, proportion: 0.4 }],
        negative_topic_distribution: [{ topic_id: 0, topic_label: 'bugs', count: 15, proportion: 0.7 }],
      },
    ],
    weekly: [],
  },
}

describe('buildTopicLabelingPrompt', () => {
  it('includes keywords and sample reviews for each topic', () => {
    const prompt = buildTopicLabelingPrompt(mockTopics, 'English')
    expect(prompt).toContain('combat')
    expect(prompt).toContain('Great combat system')
    expect(prompt).toContain('story')
    expect(prompt).toContain('Topic 1')
    expect(prompt).toContain('Topic 2')
  })

  it('includes language instruction', () => {
    const prompt = buildTopicLabelingPrompt(mockTopics, 'Korean')
    expect(prompt).toContain('Korean')
  })
})

describe('buildOverallSummaryPrompt', () => {
  it('includes review counts and topic data', () => {
    const prompt = buildOverallSummaryPrompt(mockResult as any, 'TestGame', 'English')
    expect(prompt).toContain('TestGame')
    expect(prompt).toContain('200')
    expect(prompt).toContain('120')
    expect(prompt).toContain('80')
    expect(prompt).toContain('bugs')
    expect(prompt).toContain('combat')
  })

  it('includes language instruction', () => {
    const prompt = buildOverallSummaryPrompt(mockResult as any, 'TestGame', 'Korean')
    expect(prompt).toContain('Korean')
  })
})

describe('buildSegmentPrompt', () => {
  it('includes segment data', () => {
    const prompt = buildSegmentPrompt(mockResult as any, 'English')
    expect(prompt).toContain('0-2h')
    expect(prompt).toContain('40.0%')
  })

  it('returns empty-data message when no segments', () => {
    const noSegments = { ...mockResult, segment_topic_cross: undefined }
    const prompt = buildSegmentPrompt(noSegments as any, 'English')
    expect(prompt).toContain('No segment data')
  })
})

describe('buildTimelinePrompt', () => {
  it('includes period data', () => {
    const prompt = buildTimelinePrompt(mockResult as any, 'English')
    expect(prompt).toContain('2024-01')
    expect(prompt).toContain('2024-02')
    expect(prompt).toContain('bugs')
  })

  it('returns empty-data message when no timeline', () => {
    const noTimeline = { ...mockResult, topics_over_time: undefined }
    const prompt = buildTimelinePrompt(noTimeline as any, 'English')
    expect(prompt).toContain('No timeline data')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/renderer/llm-prompts.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the prompt library**

Create `src/renderer/src/lib/llm-prompts.ts`:

```typescript
import type { AnalysisResult, Topic } from '../components/TopicAnalysis'

function languageInstruction(language: string): string {
  if (language === 'auto') return 'Respond in the same language as the majority of the reviews below.'
  return `Respond in ${language}.`
}

function formatTopicForPrompt(topic: Topic, index: number): string {
  const keywords = topic.keywords.slice(0, 8).map(k => k.word).join(', ')
  const samples = topic.sample_reviews.slice(0, 3).map((s, i) => `  ${i + 1}. ${s.slice(0, 300)}`).join('\n')
  return `Topic ${index + 1} (${topic.review_count} reviews):\n  Keywords: ${keywords}\n  Sample reviews:\n${samples}`
}

export function buildTopicLabelingPrompt(topics: Topic[], language: string): string {
  const topicBlocks = topics.map((t, i) => formatTopicForPrompt(t, i)).join('\n\n')
  return `You are analyzing Steam game review topics. For each topic below, generate a short descriptive label (3-6 words).

${languageInstruction(language)}

Return one label per line in the format: "Topic N: <label>"

---
${topicBlocks}`
}

export function buildOverallSummaryPrompt(result: AnalysisResult, gameName: string, language: string): string {
  const posBlock = result.positive_topics.map((t, i) =>
    `${i + 1}. ${t.label} (${t.review_count} reviews) — Keywords: ${t.keywords.slice(0, 5).map(k => k.word).join(', ')}`
  ).join('\n')

  const negBlock = result.negative_topics.map((t, i) =>
    `${i + 1}. ${t.label} (${t.review_count} reviews) — Keywords: ${t.keywords.slice(0, 5).map(k => k.word).join(', ')}`
  ).join('\n')

  return `Analyze the following Steam game review data for "${gameName}" and summarize the key strengths and weaknesses in 1-2 paragraphs.

${languageInstruction(language)}

Total reviews: ${result.total_reviews.toLocaleString()} (${result.positive_count.toLocaleString()} positive, ${result.negative_count.toLocaleString()} negative)

## Positive Topics
${posBlock || '(none)'}

## Negative Topics
${negBlock || '(none)'}

Provide a concise summary focusing on what the game does well and what needs improvement.`
}

export function buildSegmentPrompt(result: AnalysisResult, language: string): string {
  const cross = result.segment_topic_cross
  if (!cross) return 'No segment data available.'

  const lines: string[] = []

  if (cross.playtime.length > 0) {
    lines.push('### Playtime Segments')
    for (const seg of cross.playtime) {
      const topNeg = seg.negative_topic_distribution.slice(0, 3).map(d => `${d.topic_label} (${(d.proportion * 100).toFixed(0)}%)`).join(', ')
      lines.push(`- ${seg.segment_label}: ${seg.total_reviews} reviews, ${(seg.positive_rate * 100).toFixed(1)}% positive. Top complaints: ${topNeg || 'none'}`)
    }
  }

  if (cross.language.length > 0) {
    lines.push('\n### Language Segments')
    for (const seg of cross.language) {
      lines.push(`- ${seg.segment_label}: ${seg.total_reviews} reviews, ${(seg.positive_rate * 100).toFixed(1)}% positive`)
    }
  }

  if (cross.steam_deck.length > 0) {
    lines.push('\n### Steam Deck')
    for (const seg of cross.steam_deck) {
      lines.push(`- ${seg.segment_label}: ${seg.total_reviews} reviews, ${(seg.positive_rate * 100).toFixed(1)}% positive`)
    }
  }

  return `Analyze the following segment × topic cross-analysis data and explain the most notable differences between user segments.

${languageInstruction(language)}

${lines.join('\n')}

Focus on actionable insights: which user groups are most/least satisfied and why.`
}

export function buildTimelinePrompt(result: AnalysisResult, language: string): string {
  const timeline = result.topics_over_time
  if (!timeline || timeline.monthly.length === 0) return 'No timeline data available.'

  const lines = timeline.monthly.map(p => {
    const negTopics = p.negative_topic_distribution.slice(0, 3).map(d => `${d.topic_label} (${(d.proportion * 100).toFixed(0)}%)`).join(', ')
    return `- ${p.period}: ${p.total_reviews} reviews, ${(p.positive_rate * 100).toFixed(1)}% positive. Top complaints: ${negTopics || 'none'}`
  })

  return `Analyze the following monthly topic trend data and identify major change points and possible reasons.

${languageInstruction(language)}

${lines.join('\n')}

Focus on: when did sentiment shift? Which topics emerged or disappeared? What might explain these changes?`
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run tests/renderer/llm-prompts.test.ts`
Expected: PASS — all 8 tests

- [ ] **Step 5: Commit**

```bash
git add src/renderer/src/lib/llm-prompts.ts tests/renderer/llm-prompts.test.ts
git commit -m "feat(llm): add prompt builder library for 4 insight types"
```

---

### Task 2: Settings + LLM service + IPC + test

**Files:**
- Modify: `src/renderer/src/components/SettingsDialog.tsx:9-13,54-69`
- Create: `src/main/llm-service.ts`
- Create: `tests/main/llm-service.test.ts`
- Modify: `src/main/ipc-handlers.ts:190-197`
- Modify: `src/preload/index.ts:29-31`

- [ ] **Step 1: Write the LLM service test**

Create `tests/main/llm-service.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { callLlm } from '../../src/main/llm-service'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
})

describe('callLlm', () => {
  it('calls Claude API with correct URL and headers', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        content: [{ text: 'Claude response' }],
        usage: { input_tokens: 100, output_tokens: 50 },
      }),
    })

    const result = await callLlm({ provider: 'claude', apiKey: 'sk-test' }, 'hello')

    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.anthropic.com/v1/messages',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'x-api-key': 'sk-test' }),
      })
    )
    expect(result.text).toBe('Claude response')
  })

  it('calls OpenAI API with correct URL and auth header', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [{ message: { content: 'OpenAI response' } }],
        usage: { prompt_tokens: 80, completion_tokens: 40 },
      }),
    })

    const result = await callLlm({ provider: 'openai', apiKey: 'sk-test' }, 'hello')

    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.openai.com/v1/chat/completions',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer sk-test' }),
      })
    )
    expect(result.text).toBe('OpenAI response')
  })

  it('calls Gemini API with key in query param', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        candidates: [{ content: { parts: [{ text: 'Gemini response' }] } }],
      }),
    })

    const result = await callLlm({ provider: 'gemini', apiKey: 'gem-key' }, 'hello')

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('key=gem-key'),
      expect.any(Object)
    )
    expect(result.text).toBe('Gemini response')
  })

  it('throws on API error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => 'Unauthorized',
    })

    await expect(callLlm({ provider: 'claude', apiKey: 'bad' }, 'hello'))
      .rejects.toThrow('API error 401')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/main/llm-service.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Implement the LLM service**

Create `src/main/llm-service.ts`:

```typescript
export interface LlmConfig {
  provider: 'claude' | 'openai' | 'gemini'
  apiKey: string
}

export interface LlmResponse {
  text: string
  usage?: { input_tokens: number; output_tokens: number }
}

const MODELS = {
  claude: 'claude-sonnet-4-20250514',
  openai: 'gpt-4o-mini',
  gemini: 'gemini-2.0-flash',
} as const

export async function callLlm(config: LlmConfig, prompt: string): Promise<LlmResponse> {
  switch (config.provider) {
    case 'claude': return callClaude(config.apiKey, prompt)
    case 'openai': return callOpenAI(config.apiKey, prompt)
    case 'gemini': return callGemini(config.apiKey, prompt)
  }
}

async function callClaude(apiKey: string, prompt: string): Promise<LlmResponse> {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: MODELS.claude,
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    }),
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  const data = await res.json()
  return {
    text: data.content[0].text,
    usage: data.usage ? { input_tokens: data.usage.input_tokens, output_tokens: data.usage.output_tokens } : undefined,
  }
}

async function callOpenAI(apiKey: string, prompt: string): Promise<LlmResponse> {
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: MODELS.openai,
      messages: [{ role: 'user', content: prompt }],
    }),
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  const data = await res.json()
  return {
    text: data.choices[0].message.content,
    usage: data.usage ? { input_tokens: data.usage.prompt_tokens, output_tokens: data.usage.completion_tokens } : undefined,
  }
}

async function callGemini(apiKey: string, prompt: string): Promise<LlmResponse> {
  const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODELS.gemini}:generateContent?key=${apiKey}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
    }),
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`)
  const data = await res.json()
  return {
    text: data.candidates[0].content.parts[0].text,
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/main/llm-service.test.ts`
Expected: PASS — all 4 tests

- [ ] **Step 5: Add settings UI controls**

In `src/renderer/src/components/SettingsDialog.tsx`, update the `Settings` interface (lines 9-13) to:

```typescript
interface Settings {
  tier: 'auto' | '0' | '1'
  apiProvider: 'none' | 'claude' | 'openai' | 'gemini'
  apiKey: string
  llmMode: 'auto' | 'semi' | 'off'
  llmLanguage: string
}
```

Update the default state (line 17) to:

```typescript
  const [settings, setSettings] = useState<Settings>({ tier: 'auto', apiProvider: 'none', apiKey: '', llmMode: 'semi', llmLanguage: 'auto' })
```

After the LLM API section (after line 69, before `</section>`), add the LLM mode and language controls. Replace the entire `<section>` block for "LLM API (Optional)" (lines 54-69) with:

```tsx
        <section>
          <h3>LLM API (Optional)</h3>
          <select value={settings.apiProvider} onChange={e => setSettings({ ...settings, apiProvider: e.target.value as Settings['apiProvider'] })}>
            <option value="none">None</option>
            <option value="claude">Claude</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
          </select>
          {settings.apiProvider !== 'none' && (
            <input
              type="password"
              placeholder="API Key"
              value={settings.apiKey}
              onChange={e => setSettings({ ...settings, apiKey: e.target.value })}
            />
          )}
          <label style={{ marginTop: '0.5rem', display: 'block' }}>
            Insight Mode:
            <select value={settings.llmMode} onChange={e => setSettings({ ...settings, llmMode: e.target.value as Settings['llmMode'] })}>
              <option value="semi">Semi-auto (copy prompts)</option>
              <option value="auto">Auto (call API)</option>
              <option value="off">Off</option>
            </select>
          </label>
          <label style={{ marginTop: '0.5rem', display: 'block' }}>
            Response Language:
            <select value={settings.llmLanguage} onChange={e => setSettings({ ...settings, llmLanguage: e.target.value })}>
              <option value="auto">Auto (match reviews)</option>
              <option value="English">English</option>
              <option value="Korean">Korean</option>
              <option value="Japanese">Japanese</option>
              <option value="Chinese">Chinese</option>
            </select>
          </label>
        </section>
```

- [ ] **Step 6: Add IPC handler**

In `src/main/ipc-handlers.ts`, add the import at the top of the file:

```typescript
import { callLlm } from './llm-service'
```

Add this handler before the closing `}` of `registerIpcHandlers` (before line 198):

```typescript
  ipcMain.handle('llm:call', async (_event, prompt: string) => {
    const settings = loadSettings() as Record<string, unknown>
    const provider = settings.apiProvider as string
    const apiKey = settings.apiKey as string
    if (!provider || provider === 'none' || !apiKey) {
      throw new Error('LLM not configured. Set API provider and key in Settings.')
    }
    return callLlm({ provider: provider as 'claude' | 'openai' | 'gemini', apiKey }, prompt)
  })
```

- [ ] **Step 7: Add preload method**

In `src/preload/index.ts`, add after the `saveSettings` line (line 31):

```typescript
  // LLM
  callLlm: (prompt: string) => ipcRenderer.invoke('llm:call', prompt),
```

- [ ] **Step 8: Verify TypeScript compiles and all tests pass**

Run: `npx tsc --noEmit && npx vitest run`
Expected: No type errors, all tests pass

- [ ] **Step 9: Commit**

```bash
git add src/main/llm-service.ts tests/main/llm-service.test.ts src/renderer/src/components/SettingsDialog.tsx src/main/ipc-handlers.ts src/preload/index.ts
git commit -m "feat(llm): add LLM service with Claude/OpenAI/Gemini support and settings UI"
```

---

### Task 3: InsightPanel component + integration

**Files:**
- Create: `src/renderer/src/components/InsightPanel.tsx`
- Modify: `src/renderer/src/components/TopicAnalysis.tsx:317-359`

- [ ] **Step 1: Create InsightPanel component**

Create `src/renderer/src/components/InsightPanel.tsx`:

```tsx
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
```

- [ ] **Step 2: Integrate InsightPanel into TopicAnalysis**

In `src/renderer/src/components/TopicAnalysis.tsx`, add the import at the top:

```typescript
import { InsightPanel } from './InsightPanel'
```

The component needs `gameName`. Add state and fetch it in the `useEffect` for `appId`. Find the existing `useEffect(() => { ... }, [appId])` block (around line 122). Add a `gameName` state before `useEffect`:

```typescript
  const [gameName, setGameName] = useState('')
```

Inside the existing `useEffect(() => { ... }, [appId])` block, after `api.getGameStats(appId).then(...)` (line 129-131), add:

```typescript
    api.getGame(appId).then((g: any) => {
      setGameName(g?.app_name ?? `App ${appId}`)
    })
```

Then insert the InsightPanel. Find the `{result && (` block that wraps `<>` with TopicTimeline and topics-grid (around line 317). Add InsightPanel right after `{result && (` and before `<>`:

Change:
```tsx
      {result && (
        <>
```

To:
```tsx
      {result && (
        <>
          <InsightPanel analysisResult={result} gameName={gameName} />
```

- [ ] **Step 3: Verify TypeScript compiles and all tests pass**

Run: `npx tsc --noEmit && npx vitest run`
Expected: No type errors, all tests pass

- [ ] **Step 4: Commit**

```bash
git add src/renderer/src/components/InsightPanel.tsx src/renderer/src/components/TopicAnalysis.tsx
git commit -m "feat(ui): add InsightPanel with auto and semi-auto LLM insight modes"
```
