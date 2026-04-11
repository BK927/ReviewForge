import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from short_review import is_short_review, build_short_review_summary


def test_is_short_review_english_below_threshold():
    assert is_short_review("good game", language="english", min_words=5) is True


def test_is_short_review_english_above_threshold():
    assert is_short_review("this game is really fun and amazing", language="english", min_words=5) is False


def test_is_short_review_english_exact_threshold():
    assert is_short_review("one two three four five", language="english", min_words=5) is False


def test_is_short_review_cjk_below_threshold():
    assert is_short_review("좋은게임", language="korean", min_words=5) is True


def test_is_short_review_cjk_above_threshold():
    assert is_short_review("이 게임은 정말 재미있고 강력 추천합니다", language="korean", min_words=5) is False


def test_is_short_review_chinese_below_threshold():
    assert is_short_review("好游戏", language="schinese", min_words=5) is True


def test_is_short_review_japanese_below_threshold():
    assert is_short_review("良いゲーム", language="japanese", min_words=5) is True


def test_is_short_review_empty():
    assert is_short_review("", language="english", min_words=5) is True


def test_build_short_review_summary_basic():
    reviews = [
        {"text": "good", "voted_up": True},
        {"text": "good", "voted_up": True},
        {"text": "bad", "voted_up": False},
        {"text": "10/10", "voted_up": True},
    ]
    result = build_short_review_summary(reviews)
    assert result["count"] == 4
    assert result["positive_rate"] == 0.75
    assert result["frequent_phrases"][0]["phrase"] == "good"
    assert result["frequent_phrases"][0]["count"] == 2
    assert len(result["frequent_phrases"]) <= 10


def test_build_short_review_summary_empty():
    result = build_short_review_summary([])
    assert result["count"] == 0
    assert result["positive_rate"] == 0.0
    assert result["frequent_phrases"] == []
