// ── File/Clipboard exports (raw reviews) ──

export function reviewsToMarkdown(reviews: any[], gameName: string, filterDesc: string): string {
  let md = `# ${gameName} Reviews\n\n`
  md += `Filter: ${filterDesc}\n`
  md += `Total: ${reviews.length} reviews\n\n`
  for (const r of reviews) {
    const sentiment = r.voted_up ? '+' : '-'
    const hours = Math.round(r.playtime_at_review / 60)
    md += `### ${sentiment} [${r.language}] (${hours}h)\n${r.review_text}\n\n`
  }
  return md
}

// ── Analysis result → LLM prompt ──

interface AnalysisTopic {
  label: string
  keywords: { word: string; score: number }[]
  review_count: number
  sample_reviews: string[]
}

export interface AnalysisResultForPrompt {
  positive_topics: AnalysisTopic[]
  negative_topics: AnalysisTopic[]
  total_reviews: number
  positive_count: number
  negative_count: number
  model: string
}

function truncateReview(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text
  const cut = text.slice(0, maxChars)
  const lastSentence = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('! '), cut.lastIndexOf('? '), cut.lastIndexOf('\n'))
  const trimmed = lastSentence > maxChars * 0.5 ? cut.slice(0, lastSentence + 1) : cut
  return trimmed + ' [...]'
}

function formatTopicBlock(topics: AnalysisTopic[], maxSamples = 5): string {
  if (topics.length === 0) return '(none)\n'
  return topics.map((t, i) => {
    const keywords = t.keywords.map(k => `${k.word} (${k.score})`).join(', ')
    const samples = t.sample_reviews.slice(0, maxSamples).map((s, j) => `  ${j + 1}. ${truncateReview(s, 400)}`).join('\n')
    return `Topic ${i + 1}: ${t.label} (${t.review_count} reviews)\n  Keywords: ${keywords}\n  Sample reviews:\n${samples}`
  }).join('\n\n')
}

export function formatAnalysisData(result: AnalysisResultForPrompt): string {
  const negBlock = formatTopicBlock(result.negative_topics)
  const posBlock = formatTopicBlock(result.positive_topics)
  return `## Negative Topics (${result.negative_count.toLocaleString()} reviews)\n\n${negBlock}\n\n## Positive Topics (${result.positive_count.toLocaleString()} reviews)\n\n${posBlock}`
}

export function analysisToLlmPrompt(result: AnalysisResultForPrompt, gameName: string, template: string): string {
  return template
    .replace('[Game Name]', gameName)
    .replace('[N]', result.total_reviews.toLocaleString())
    .replace('[Positive count]', result.positive_count.toLocaleString())
    .replace('[Negative count]', result.negative_count.toLocaleString())
    .replace('[Model]', result.model)
    .replace('[Review data]', formatAnalysisData(result))
}

export const DEFAULT_LLM_TEMPLATE = `Topic analysis results for Steam game "[Game Name]".
Total reviews analyzed: [N] ([Positive count] positive, [Negative count] negative)
Embedding model: [Model]

Reviews were clustered into topics using ML (sentence embeddings + clustering).
Each topic has auto-extracted keywords and sample reviews from that cluster.

Analyze these results.

---
[Review data]`
