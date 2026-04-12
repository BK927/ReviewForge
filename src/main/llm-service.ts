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
