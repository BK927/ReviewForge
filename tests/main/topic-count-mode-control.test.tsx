import { describe, it, expect } from 'vitest'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { TopicCountModeControl } from '../../src/renderer/src/components/TopicCountModeControl'

describe('TopicCountModeControl', () => {
  it('shows auto and manual modes for Tier 0, with manual input disabled in auto mode', () => {
    const html = renderToStaticMarkup(
      React.createElement(TopicCountModeControl, {
        tier: 0,
        mode: 'auto',
        nTopics: 8,
        onModeChange: () => {},
        onNTopicsChange: () => {}
      })
    )

    expect(html).toContain('Auto (recommended)')
    expect(html).toContain('Manual')
    expect(html).toContain('disabled')
  })

  it('locks to auto for Tier 1 with hdbscan explanation copy', () => {
    const html = renderToStaticMarkup(
      React.createElement(TopicCountModeControl, {
        tier: 1,
        mode: 'auto',
        nTopics: 8,
        onModeChange: () => {},
        onNTopicsChange: () => {}
      })
    )

    expect(html).toContain('Auto by HDBSCAN')
    expect(html).not.toContain('Manual')
  })

  it('enables manual numeric input when manual mode is selected', () => {
    const html = renderToStaticMarkup(
      React.createElement(TopicCountModeControl, {
        tier: 0,
        mode: 'manual',
        nTopics: 12,
        onModeChange: () => {},
        onNTopicsChange: () => {}
      })
    )

    expect(html).toContain('value="12"')
    expect(html).not.toContain('disabled')
  })
})
