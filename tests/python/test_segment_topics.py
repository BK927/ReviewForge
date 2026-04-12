import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from segment_topics import compute_segment_topic_cross


def _make_cross_reviews():
    """Build 8 reviews spanning different segments and topic assignments."""
    return [
        # Positive reviews with topic assignments
        {"text": "great combat", "voted_up": True, "playtime": 6000, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 1000, "sentiment": "positive", "topic_id": 0},
        {"text": "good story", "voted_up": True, "playtime": 200, "language": "english", "steam_deck": True, "steam_purchase": True, "timestamp": 2000, "sentiment": "positive", "topic_id": 1},
        {"text": "fun gameplay", "voted_up": True, "playtime": 6000, "language": "koreana", "steam_deck": False, "steam_purchase": False, "timestamp": 3000, "sentiment": "positive", "topic_id": 0},
        {"text": "nice graphics", "voted_up": True, "playtime": 300, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 4000, "sentiment": "positive", "topic_id": 1},
        # Negative reviews with topic assignments
        {"text": "bad performance", "voted_up": False, "playtime": 6000, "language": "english", "steam_deck": True, "steam_purchase": True, "timestamp": 5000, "sentiment": "negative", "topic_id": 0},
        {"text": "buggy game", "voted_up": False, "playtime": 60, "language": "koreana", "steam_deck": False, "steam_purchase": True, "timestamp": 6000, "sentiment": "negative", "topic_id": 1},
        {"text": "crashes often", "voted_up": False, "playtime": 6000, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 7000, "sentiment": "negative", "topic_id": 0},
        {"text": "too expensive", "voted_up": False, "playtime": 200, "language": "english", "steam_deck": False, "steam_purchase": True, "timestamp": 8000, "sentiment": "negative", "topic_id": 1},
    ]


def test_compute_playtime_axis():
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "playtime" in result
    playtime = result["playtime"]

    # Find the 50h+ segment (playtime >= 3000 min)
    seg_50h = next(s for s in playtime if s["segment_label"] == "50h+")
    # Reviews: great combat (pos, t0), fun gameplay (pos, t0), bad performance (neg, t0), crashes often (neg, t0)
    assert seg_50h["total_reviews"] == 4
    assert seg_50h["positive_rate"] == 0.5

    pos_dist = seg_50h["positive_topic_distribution"]
    assert len(pos_dist) == 1
    assert pos_dist[0]["topic_id"] == 0
    assert pos_dist[0]["count"] == 2

    neg_dist = seg_50h["negative_topic_distribution"]
    assert len(neg_dist) == 1
    assert neg_dist[0]["topic_id"] == 0
    assert neg_dist[0]["count"] == 2


def test_compute_language_axis():
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "language" in result
    lang = result["language"]
    eng = next(s for s in lang if s["segment_label"] == "english")
    assert eng["total_reviews"] == 6
    kor = next(s for s in lang if s["segment_label"] == "koreana")
    assert kor["total_reviews"] == 2


def test_compute_steam_deck_axis():
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "steam_deck" in result
    deck_segs = result["steam_deck"]
    deck = next(s for s in deck_segs if s["segment_label"] == "Deck")
    assert deck["total_reviews"] == 2
    assert deck["positive_rate"] == 0.5


def test_compute_purchase_type_axis():
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    assert "purchase_type" in result
    pt = result["purchase_type"]
    purchase = next(s for s in pt if s["segment_label"] == "Purchase")
    free = next(s for s in pt if s["segment_label"] == "Free")
    assert free["total_reviews"] == 1
    assert free["positive_rate"] == 1.0
    assert purchase["total_reviews"] == 7


def test_empty_reviews():
    result = compute_segment_topic_cross([], [], [])
    assert result["playtime"] == []
    assert result["language"] == []
    assert result["steam_deck"] == []
    assert result["purchase_type"] == []


def test_proportion_sums_to_one():
    """Within a segment, positive topic proportions should sum to ~1.0."""
    reviews = _make_cross_reviews()
    pos_topics = [{"id": 0, "label": "combat"}, {"id": 1, "label": "story"}]
    neg_topics = [{"id": 0, "label": "performance"}, {"id": 1, "label": "bugs"}]

    result = compute_segment_topic_cross(reviews, pos_topics, neg_topics)

    for axis_name, segments in result.items():
        for seg in segments:
            pos_dist = seg["positive_topic_distribution"]
            if pos_dist:
                total_prop = sum(d["proportion"] for d in pos_dist)
                assert abs(total_prop - 1.0) < 0.01, f"{axis_name}/{seg['segment_label']} pos proportions sum to {total_prop}"
            neg_dist = seg["negative_topic_distribution"]
            if neg_dist:
                total_prop = sum(d["proportion"] for d in neg_dist)
                assert abs(total_prop - 1.0) < 0.01, f"{axis_name}/{seg['segment_label']} neg proportions sum to {total_prop}"
