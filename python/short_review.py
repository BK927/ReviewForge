from collections import Counter

CJK_LANGUAGES = {
    "schinese", "tchinese", "japanese", "korean",
    "koreana",  # Steam uses 'koreana' for Korean
}
# CJK text uses character count instead of word count; min_chars = min_words * ratio
CJK_CHAR_THRESHOLD_RATIO = 2


def is_short_review(text: str, language: str = "english", min_words: int = 5) -> bool:
    """Check if a review is too short for meaningful clustering."""
    stripped = text.strip()
    if not stripped:
        return True

    if language.lower() in CJK_LANGUAGES:
        min_chars = max(1, min_words * CJK_CHAR_THRESHOLD_RATIO)
        return len(stripped) < min_chars
    else:
        return len(stripped.split()) < min_words


def build_short_review_summary(reviews: list[dict]) -> dict:
    """Build summary stats for short reviews. Each review must have 'text' and 'voted_up' keys."""
    if not reviews:
        return {"count": 0, "positive_rate": 0.0, "frequent_phrases": []}

    count = len(reviews)
    positive_count = sum(1 for r in reviews if r["voted_up"])
    positive_rate = positive_count / count if count > 0 else 0.0

    phrase_counter = Counter(r["text"].strip().lower() for r in reviews if r["text"].strip())
    frequent = [
        {"phrase": phrase, "count": freq}
        for phrase, freq in phrase_counter.most_common(10)
    ]

    return {
        "count": count,
        "positive_rate": round(positive_rate, 4),
        "frequent_phrases": frequent,
    }
