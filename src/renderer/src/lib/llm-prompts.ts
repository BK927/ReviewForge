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
