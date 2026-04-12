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
