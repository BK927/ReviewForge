from collections import Counter

CJK_LANGUAGES = {
    "schinese", "tchinese", "japanese", "korean",
    "koreana",
}
CJK_CHAR_THRESHOLD_RATIO = 2


def is_short_review(text: str, language: str = "english", min_words: int = 5) -> bool:
    stripped = text.strip()
    if not stripped:
        return True

    if language.lower() in CJK_LANGUAGES:
        min_chars = max(1, min_words * CJK_CHAR_THRESHOLD_RATIO)
        return len(stripped) < min_chars
    else:
        return len(stripped.split()) < min_words


def build_short_review_summary(reviews: list[dict]) -> dict:
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
