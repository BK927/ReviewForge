import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from topic_timeline import compute_topics_over_time


def _make_timeline_reviews():
    """Reviews spanning 3 months with topic assignments."""
    return [
        # January 2024
        {"text": "great", "voted_up": True, "timestamp": 1704067200, "sentiment": "positive", "topic_id": 0},  # 2024-01-01
        {"text": "good",  "voted_up": True, "timestamp": 1704153600, "sentiment": "positive", "topic_id": 1},  # 2024-01-02
        {"text": "bad",   "voted_up": False, "timestamp": 1704240000, "sentiment": "negative", "topic_id": 0}, # 2024-01-03
        # February 2024
        {"text": "nice",  "voted_up": True, "timestamp": 1706745600, "sentiment": "positive", "topic_id": 0},  # 2024-02-01
        {"text": "awful", "voted_up": False, "timestamp": 1706832000, "sentiment": "negative", "topic_id": 0}, # 2024-02-02
        {"text": "terrible", "voted_up": False, "timestamp": 1706918400, "sentiment": "negative", "topic_id": 1}, # 2024-02-03
        # March 2024
        {"text": "wow",   "voted_up": True, "timestamp": 1709251200, "sentiment": "positive", "topic_id": 0},  # 2024-03-01
        {"text": "cool",  "voted_up": True, "timestamp": 1709337600, "sentiment": "positive", "topic_id": 1},  # 2024-03-02
    ]


def test_monthly_periods():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    monthly = result["monthly"]
    assert len(monthly) == 3  # Jan, Feb, Mar

    # Periods should be sorted chronologically
    assert monthly[0]["period"] == "2024-01"
    assert monthly[1]["period"] == "2024-02"
    assert monthly[2]["period"] == "2024-03"

    # January: 3 reviews (2 pos, 1 neg)
    jan = monthly[0]
    assert jan["total_reviews"] == 3
    assert abs(jan["positive_rate"] - 2 / 3) < 0.01


def test_weekly_periods():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    weekly = result["weekly"]
    # All reviews should be assigned to some week
    total = sum(p["total_reviews"] for p in weekly)
    assert total == 8

    # Periods should be sorted
    periods = [p["period"] for p in weekly]
    assert periods == sorted(periods)


def test_topic_distribution_in_period():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    # January: 2 positive reviews (topic 0 and topic 1), 1 negative (topic 0)
    jan = result["monthly"][0]
    assert len(jan["positive_topic_distribution"]) == 2
    assert len(jan["negative_topic_distribution"]) == 1

    # Proportions should sum to 1.0 for each sentiment
    pos_sum = sum(d["proportion"] for d in jan["positive_topic_distribution"])
    assert abs(pos_sum - 1.0) < 0.01


def test_empty_reviews():
    result = compute_topics_over_time([], [], [])
    assert result["weekly"] == []
    assert result["monthly"] == []


def test_periods_have_expected_structure():
    reviews = _make_timeline_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_topics_over_time(reviews, pos_topics, neg_topics)

    for granularity in ["weekly", "monthly"]:
        for period in result[granularity]:
            assert "period" in period
            assert "total_reviews" in period
            assert "positive_rate" in period
            assert "positive_topic_distribution" in period
            assert "negative_topic_distribution" in period
            for d in period["positive_topic_distribution"]:
                assert "topic_id" in d
                assert "topic_label" in d
                assert "count" in d
                assert "proportion" in d
