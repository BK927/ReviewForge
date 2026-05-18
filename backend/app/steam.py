from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any

import httpx


STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{app_id}"


@dataclass(frozen=True)
class SteamReviewFetchResult:
    rows: list[tuple[Any, ...]]
    next_cursor: str | None
    has_more: bool


def _steam_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value))
    except (TypeError, ValueError, OSError):
        return None


def normalize_steam_review(app_id: str, item: dict[str, Any]) -> tuple[Any, ...]:
    author = item.get("author") or {}
    recommendation_id = str(item.get("recommendationid"))
    return (
        recommendation_id,
        app_id,
        str(author.get("steamid")) if author.get("steamid") else None,
        item.get("language") or "unknown",
        item.get("review") or "",
        bool(item.get("voted_up")),
        int(item.get("votes_up") or 0),
        int(item.get("votes_funny") or 0),
        float(item.get("weighted_vote_score") or 0),
        int(author.get("playtime_forever") or 0),
        int(author.get("playtime_at_review") or 0),
        _steam_time(item.get("timestamp_created")),
        _steam_time(item.get("timestamp_updated")),
        None,
        item.get("developer_response"),
        json.dumps(item),
    )


async def fetch_steam_reviews(
    app_id: str,
    *,
    language: str = "all",
    review_type: str = "all",
    purchase_type: str = "all",
    max_reviews: int = 100,
    cursor: str | None = None,
) -> SteamReviewFetchResult:
    reviews: list[tuple[Any, ...]] = []
    current_cursor = cursor or "*"
    next_cursor: str | None = None
    has_more = False
    async with httpx.AsyncClient(timeout=20) as client:
        while len(reviews) < max_reviews:
            response = await client.get(
                STEAM_REVIEWS_URL.format(app_id=app_id),
                params={
                    "json": 1,
                    "filter": "recent",
                    "language": language,
                    "review_type": review_type,
                    "purchase_type": purchase_type,
                    "num_per_page": min(100, max_reviews - len(reviews)),
                    "cursor": current_cursor,
                },
            )
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("reviews") or []
            if not batch:
                has_more = False
                break
            reviews.extend(normalize_steam_review(app_id, item) for item in batch)
            next_cursor = payload.get("cursor")
            has_more = bool(next_cursor and next_cursor != current_cursor)
            if not has_more:
                break
            current_cursor = next_cursor
    return SteamReviewFetchResult(rows=reviews, next_cursor=next_cursor, has_more=has_more)


def placeholder_reviews(app_id: str, max_reviews: int) -> list[tuple[Any, ...]]:
    now = datetime.utcnow()
    rows = []
    texts = [
        ("english", "The combat is excellent, but late game rewards make the loop feel repetitive.", False, 0.72, 3200),
        ("koreana", "무기별 전투 손맛은 좋지만 후반 보상 변화가 부족해서 반복감이 커집니다.", False, 0.69, 2800),
        ("english", "Boss fights and weapon rhythm are still the strongest parts of the game.", True, 0.86, 1180),
        ("schinese", "After the balance patch, fewer builds feel worth trying and weapon choice feels narrower.", False, 0.81, 2100),
        ("japanese", "The character art, music, and atmosphere make every new scene enjoyable.", True, 0.88, 900),
    ]
    for index in range(max_reviews):
        language, review, sentiment, score, playtime = texts[index % len(texts)]
        rows.append(
            (
                f"stub-{app_id}-{int(now.timestamp())}-{index}",
                app_id,
                f"stub-author-{index}",
                language,
                review,
                sentiment,
                0,
                0,
                score,
                playtime,
                playtime - 40,
                now,
                now,
                None,
                None,
                json.dumps({"source": "stub", "index": index}),
            )
        )
    return rows
