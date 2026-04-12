import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from early_access import compute_early_access_comparison


def _make_lifecycle_reviews():
    """Create cross_reviews for lifecycle classification testing.

    200 total: 100 EA (50 pos + 50 neg), 100 Post (50 pos + 50 neg).
    Negative topic distributions:
      Topic 0: 15/50 EA (30%), 15/50 Post (30%) -> persistent
      Topic 1: 15/50 EA (30%), 1/50 Post (2%)   -> resolved
      Topic 2: 1/50 EA (2%),  15/50 Post (30%)  -> new
      Topic 3: 19/50 EA (38%), 19/50 Post (38%) -> persistent
    """
    reviews = []

    # EA positive (50)
    for _ in range(50):
        reviews.append({"early_access": True, "sentiment": "positive", "topic_id": 0, "timestamp": 1000})

    # EA negative (50): topic 0 x15, topic 1 x15, topic 2 x1, topic 3 x19
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 0, "timestamp": 1000})
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 1, "timestamp": 1000})
    reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 2, "timestamp": 1000})
    for _ in range(19):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 3, "timestamp": 1000})

    # Post positive (50)
    for _ in range(50):
        reviews.append({"early_access": False, "sentiment": "positive", "topic_id": 0, "timestamp": 2000})

    # Post negative (50): topic 0 x15, topic 1 x1, topic 2 x15, topic 3 x19
    for _ in range(15):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 0, "timestamp": 2000})
    reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 1, "timestamp": 2000})
    for _ in range(15):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 2, "timestamp": 2000})
    for _ in range(19):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 3, "timestamp": 2000})

    return reviews


def test_returns_none_when_ea_count_below_50():
    """Activation requires at least 50 EA reviews."""
    reviews = []
    # 30 EA + 30 Post = 60 total, EA ratio = 50% (ok), but EA count = 30 (< 50)
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "positive", "topic_id": 0})
    for _ in range(15):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 0})
    for _ in range(30):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 0})

    result = compute_early_access_comparison(reviews, [{"id": 0, "label": "t0"}])
    assert result is None


def test_returns_none_when_ea_ratio_below_10_percent():
    """Activation requires EA >= 10% of total."""
    reviews = []
    # 5 EA + 95 Post = 100 total, EA ratio = 5% (< 10%), EA count = 5 (< 50 too)
    for _ in range(5):
        reviews.append({"early_access": True, "sentiment": "negative", "topic_id": 0})
    for _ in range(95):
        reviews.append({"early_access": False, "sentiment": "negative", "topic_id": 0})

    result = compute_early_access_comparison(reviews, [{"id": 0, "label": "t0"}])
    assert result is None


def test_returns_none_for_empty_reviews():
    result = compute_early_access_comparison([], [])
    assert result is None


def test_lifecycle_classification():
    reviews = _make_lifecycle_reviews()
    neg_topics = [
        {"id": 0, "label": "performance"},
        {"id": 1, "label": "bugs"},
        {"id": 2, "label": "crashes"},
        {"id": 3, "label": "balance"},
    ]

    result = compute_early_access_comparison(reviews, neg_topics)
    assert result is not None
    assert result["ea_review_count"] == 100
    assert result["post_launch_review_count"] == 100

    lifecycle = result["lifecycle"]
    status_map = {entry["topic_id"]: entry["status"] for entry in lifecycle}

    # Topic 0: 30% EA, 30% Post -> persistent
    assert status_map[0] == "persistent"
    # Topic 1: 30% EA, 2% Post -> resolved
    assert status_map[1] == "resolved"
    # Topic 2: 2% EA, 30% Post -> new
    assert status_map[2] == "new"
    # Topic 3: 38% EA, 38% Post -> persistent
    assert status_map[3] == "persistent"


def test_lifecycle_entry_structure():
    reviews = _make_lifecycle_reviews()
    neg_topics = [
        {"id": 0, "label": "performance"},
        {"id": 1, "label": "bugs"},
        {"id": 2, "label": "crashes"},
        {"id": 3, "label": "balance"},
    ]

    result = compute_early_access_comparison(reviews, neg_topics)
    assert "ea_review_count" in result
    assert "post_launch_review_count" in result
    assert "lifecycle" in result

    for entry in result["lifecycle"]:
        assert "topic_id" in entry
        assert "topic_label" in entry
        assert entry["status"] in ("persistent", "resolved", "new")
        assert "ea_proportion" in entry
        assert "post_launch_proportion" in entry
        assert "ea_positive_rate" in entry
        assert "post_launch_positive_rate" in entry
        assert 0 <= entry["ea_proportion"] <= 1
        assert 0 <= entry["post_launch_proportion"] <= 1
