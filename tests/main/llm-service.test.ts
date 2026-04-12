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
