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

export function reviewsToLlmPrompt(reviews: any[], gameName: string, template: string, filter?: { language?: string; period?: string }): string {
  const reviewBlock = reviews.map(r => {
    const sentiment = r.voted_up ? 'Positive' : 'Negative'
    return `[${sentiment}] [${r.language}] (${Math.round(r.playtime_at_review / 60)}h playtime)\n${r.review_text}`
  }).join('\n---\n')

  const posCount = reviews.filter(r => r.voted_up).length
  const negCount = reviews.length - posCount
  const sentiment = posCount > negCount ? 'positive' : negCount > posCount ? 'negative' : 'mixed'

  return template
    .replace('[Game Name]', gameName)
    .replace('[N]', String(reviews.length))
    .replace('[positive/negative]', sentiment)
    .replace('[selected language]', filter?.language ?? 'all')
    .replace('[selected period]', filter?.period ?? 'all time')
    .replace('[Review data]', reviewBlock)
}

export const DEFAULT_LLM_TEMPLATE = `Below are [N] [positive/negative] reviews for the Steam game [Game Name].
Language: [selected language]
Period: [selected period]

Please analyze the following:
1. Classify main complaints/praises into 5 topics
2. Summarize representative opinions per topic
3. Suggest action items from a planning/marketing perspective

---
[Review data]`
