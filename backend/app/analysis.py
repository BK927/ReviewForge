from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any

import duckdb
import httpx

from .db import connect, utcnow
from .repository import rows_to_dicts


LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_EMBEDDING_MODEL = "local-hash-v1"


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    pattern: str
    summary: str


@dataclass(frozen=True)
class AnalysisPipelineResult:
    reviews_analyzed: int
    clusters_created: int
    evidence_created: int
    clusterer: str
    message: str


THEMES = [
    Theme(
        "late_loop",
        "후반 반복성과 보상 밀도",
        r"late|repeat|repetitive|reward|loop|grind|endgame|보상|반복|후반|루프|recompensa|repetir|報酬|繰り返",
        "후반 플레이에서 반복감, 보상 변화, 장기 동기 문제가 함께 언급됩니다.",
    ),
    Theme(
        "combat",
        "전투 손맛과 보스전 긴장감",
        r"combat|boss|fight|rhythm|weapon feel|전투|보스|손맛|타격|戦闘|ボス",
        "전투 감각, 무기별 리듬, 보스전 압박감이 핵심 경험으로 반복됩니다.",
    ),
    Theme(
        "balance",
        "무기 밸런스와 빌드 선택지",
        r"balance|build|weapon choice|weapons fall|narrow|밸런스|빌드|무기|选择|構成|ビルド|平衡",
        "패치나 성장 구조 이후 무기 밸런스와 빌드 다양성에 대한 반응이 모입니다.",
    ),
    Theme(
        "presentation",
        "아트와 캐릭터 매력",
        r"art|character|atmosphere|illustration|music|visual|아트|캐릭터|분위기|음악|美術|キャラクター",
        "캐릭터 표현, 시각 연출, 음악, 분위기가 강점으로 언급됩니다.",
    ),
    Theme(
        "performance",
        "성능과 안정성",
        r"performance|crash|fps|stutter|bug|loading|성능|버그|튕김|프레임|クラッシュ|卡顿",
        "성능, 충돌, 프레임, 버그처럼 플레이 안정성과 관련된 신호가 묶입니다.",
    ),
    Theme(
        "ui",
        "UI와 가독성",
        r"ui|menu|readability|text|font|interface|가독성|메뉴|인터페이스|글자|읽기|界面",
        "메뉴, 텍스트, 가독성, 조작 흐름에 대한 사용성 의견이 나타납니다.",
    ),
]

STOPWORDS = {
    "the",
    "and",
    "but",
    "for",
    "with",
    "this",
    "that",
    "game",
    "still",
    "feel",
    "feels",
    "after",
    "every",
    "new",
    "same",
    "again",
    "좋지만",
    "조금",
    "아직",
    "최근",
}


def run_local_analysis(
    *,
    analysis_run_id: int,
    app_id: str | None,
    scope: str,
    embedding_model: str | None,
    min_cluster_size: int,
    generate_ai_summary: bool,
    llm_provider: str | None,
) -> AnalysisPipelineResult:
    model_name = embedding_model or DEFAULT_EMBEDDING_MODEL
    with connect() as conn:
        reviews = _load_reviews(conn, app_id, scope)

    if not reviews:
        return AnalysisPipelineResult(
            reviews_analyzed=0,
            clusters_created=0,
            evidence_created=0,
            clusterer="none",
            message="No reviews matched the requested analysis scope.",
        )

    try:
        groups = _cluster_with_sklearn(reviews, min_cluster_size)
        clusterer = "sklearn_tfidf_kmeans"
        message = "Analysis completed with local TF-IDF clustering."
    except Exception as exc:
        groups = _cluster_with_keywords(reviews)
        clusterer = "keyword_fallback"
        message = f"sklearn unavailable or failed; used keyword fallback ({exc.__class__.__name__})."

    if generate_ai_summary and llm_provider == "lmstudio":
        message += " AI summary improvement requested; local rule summaries were kept for v1 reliability."

    with connect() as conn:
        _store_embeddings(conn, reviews, model_name)
        clusters_created, evidence_created = _store_analysis_outputs(conn, analysis_run_id, groups)
        _store_analysis_report(conn, analysis_run_id, app_id, reviews, clusters_created, clusterer)

    return AnalysisPipelineResult(
        reviews_analyzed=len(reviews),
        clusters_created=clusters_created,
        evidence_created=evidence_created,
        clusterer=clusterer,
        message=message,
    )


async def model_settings_status() -> dict[str, Any]:
    lm_status = await _lm_studio_status()
    providers = [
        {
            "id": "local_rules",
            "label": "Local rules",
            "available": True,
            "default": True,
            "notes": "Always available; no external model required.",
        },
        {
            "id": "lmstudio",
            "label": "LM Studio",
            "available": lm_status["available"],
            "default": False,
            "base_url": LM_STUDIO_BASE_URL,
            "models": lm_status["models"],
        },
    ]
    return {
        "default_provider": "local_rules",
        "default_embedding_model": DEFAULT_EMBEDDING_MODEL,
        "providers": providers,
        "lm_studio": lm_status,
    }


async def _lm_studio_status() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{LM_STUDIO_BASE_URL}/models")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return {
            "available": False,
            "base_url": LM_STUDIO_BASE_URL,
            "models": [],
            "default_model": None,
            "message": str(exc),
        }

    models = [str(item.get("id")) for item in payload.get("data", []) if item.get("id")]
    return {
        "available": True,
        "base_url": LM_STUDIO_BASE_URL,
        "models": models,
        "default_model": models[0] if models else None,
        "message": "LM Studio OpenAI-compatible endpoint is reachable.",
    }


def _load_reviews(conn: duckdb.DuckDBPyConnection, app_id: str | None, scope: str) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if app_id:
        clauses.append("r.app_id = ?")
        params.append(app_id)
    if scope == "new":
        clauses.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM review_clusters rc
                JOIN clusters c ON c.id = rc.cluster_id
                WHERE rc.review_id = r.recommendation_id
                  AND c.analysis_run_id IS NOT NULL
            )
            """
        )
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    return rows_to_dicts(
        conn.execute(
            f"""
            SELECT
                r.recommendation_id,
                r.app_id,
                r.language,
                r.review,
                r.voted_up,
                r.votes_up,
                r.weighted_vote_score,
                r.playtime_at_review,
                r.steam_created_at,
                r.collected_at
            FROM reviews r
            {where_sql}
            ORDER BY coalesce(r.steam_created_at, r.collected_at) DESC, r.recommendation_id
            """,
            params,
        )
    )


def _cluster_with_sklearn(reviews: list[dict[str, Any]], min_cluster_size: int) -> list[dict[str, Any]]:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [row["review"] or "" for row in reviews]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=8000)
    matrix = vectorizer.fit_transform(texts)
    cluster_count = max(1, min(20, len(reviews) // max(min_cluster_size, 1)))
    if cluster_count == 1:
        labels = [0 for _ in reviews]
        scores = [1.0 for _ in reviews]
    else:
        model = KMeans(n_clusters=cluster_count, random_state=13, n_init=10)
        labels = model.fit_predict(matrix)
        similarities = cosine_similarity(matrix, model.cluster_centers_)
        scores = [float(similarities[index, labels[index]]) for index in range(len(reviews))]

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row, label, score in zip(reviews, labels, scores, strict=True):
        grouped[int(label)].append({"row": row, "score": max(0.0, min(score, 1.0))})
    return [_describe_group(members) for members in grouped.values()]


def _cluster_with_keywords(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reviews:
        text = str(row.get("review") or "").lower()
        matches = [(theme, len(re.findall(theme.pattern, text, flags=re.IGNORECASE))) for theme in THEMES]
        theme, count = max(matches, key=lambda item: item[1])
        if count <= 0:
            grouped["misc"].append({"row": row, "score": 0.55})
        else:
            grouped[theme.key].append({"row": row, "score": min(1.0, 0.62 + count * 0.12)})
    return [_describe_group(members) for members in grouped.values() if members]


def _describe_group(members: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [member["row"] for member in members]
    sentiment = _sentiment(rows)
    best_theme = _best_theme(rows)
    keywords = _keywords(rows)
    language = _dominant_language(rows)
    if best_theme:
        label = best_theme.label
        summary = f"{len(rows)}개 리뷰에서 {best_theme.summary} 긍정 비율은 {_positive_ratio(rows):.0%}입니다."
    else:
        if sentiment == "positive":
            label = "긍정 경험 묶음"
        elif sentiment == "negative":
            label = "개선 요청 묶음"
        else:
            label = "혼합 의견 묶음"
        keyword_text = ", ".join(keywords[:4]) if keywords else "공통 표현 부족"
        summary = f"{len(rows)}개 리뷰가 유사한 표현으로 묶였습니다. 주요 단어는 {keyword_text}이며 긍정 비율은 {_positive_ratio(rows):.0%}입니다."
    return {
        "label": label,
        "summary": summary,
        "sentiment": sentiment,
        "language": language,
        "reviews": members,
        "keywords": keywords,
    }


def _store_embeddings(conn: duckdb.DuckDBPyConnection, reviews: list[dict[str, Any]], model_name: str) -> None:
    generated_at = utcnow()
    rows = []
    for review in reviews:
        embedding = _hash_embedding(str(review.get("review") or ""))
        rows.append(
            (
                review["recommendation_id"],
                model_name,
                len(embedding),
                json.dumps(embedding),
                generated_at,
            )
        )
    conn.executemany(
        """
        INSERT INTO review_embeddings (review_id, model, dimension, embedding, generated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (review_id, model) DO UPDATE SET
            dimension = excluded.dimension,
            embedding = excluded.embedding,
            generated_at = excluded.generated_at
        """,
        rows,
    )


def _store_analysis_outputs(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    groups: list[dict[str, Any]],
) -> tuple[int, int]:
    clusters_created = 0
    evidence_created = 0
    for group in sorted(groups, key=lambda item: len(item["reviews"]), reverse=True):
        ranked_members = _rank_members(group["reviews"])
        rows = [member["row"] for member in ranked_members]
        review_count = len(rows)
        avg_score = sum(float(row.get("weighted_vote_score") or 0) for row in rows) / review_count
        exemplar = rows[0]["recommendation_id"]
        cluster_id = conn.execute(
            """
            INSERT INTO clusters (
                analysis_run_id, label, summary, sentiment, language, review_count,
                avg_weighted_score, exemplar_review_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
            """,
            [
                analysis_run_id,
                group["label"],
                group["summary"],
                group["sentiment"],
                group["language"],
                review_count,
                avg_score,
                exemplar,
            ],
        ).fetchone()[0]
        clusters_created += 1
        conn.executemany(
            "INSERT INTO review_clusters (review_id, cluster_id, score) VALUES (?, ?, ?)",
            [(member["row"]["recommendation_id"], cluster_id, member["score"]) for member in ranked_members],
        )
        for member in ranked_members[:3]:
            row = member["row"]
            conn.execute(
                """
                INSERT INTO evidence (analysis_run_id, review_id, cluster_id, quote, evidence_type, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    analysis_run_id,
                    row["recommendation_id"],
                    cluster_id,
                    _quote(row["review"]),
                    _evidence_type(group["sentiment"]),
                    f"Representative review score {member['representative_score']:.2f}",
                ],
            )
            evidence_created += 1
    return clusters_created, evidence_created


def _store_analysis_report(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    app_id: str | None,
    reviews: list[dict[str, Any]],
    clusters_created: int,
    clusterer: str,
) -> None:
    positive_ratio = _positive_ratio(reviews)
    summary = (
        f"{len(reviews)}개 리뷰를 분석해 {clusters_created}개 클러스터를 만들었습니다. "
        f"긍정 비율은 {positive_ratio:.0%}이며 사용한 분석기는 {clusterer}입니다."
    )
    conn.execute(
        "INSERT INTO reports (analysis_run_id, title, summary, filters) VALUES (?, ?, ?, ?)",
        [
            analysis_run_id,
            "Local analysis run",
            summary,
            json.dumps({"app_id": app_id, "clusterer": clusterer}),
        ],
    )


def _hash_embedding(text: str, dimension: int = 64) -> list[float]:
    vector = [0.0] * dimension
    terms = _tokens(text)
    compact = re.sub(r"\s+", " ", text.lower())
    terms.extend(compact[index : index + 3] for index in range(max(0, len(compact) - 2)))
    for term in terms:
        digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _rank_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for member in members:
        row = member["row"]
        length_score = min(len(str(row.get("review") or "")) / 500, 1.0)
        weighted_score = max(0.0, min(float(row.get("weighted_vote_score") or 0), 1.0))
        representative_score = member["score"] * 0.55 + weighted_score * 0.3 + length_score * 0.15
        ranked.append({**member, "representative_score": representative_score})
    return sorted(ranked, key=lambda item: item["representative_score"], reverse=True)


def _best_theme(rows: list[dict[str, Any]]) -> Theme | None:
    text = "\n".join(str(row.get("review") or "").lower() for row in rows)
    counts = [(theme, len(re.findall(theme.pattern, text, flags=re.IGNORECASE))) for theme in THEMES]
    theme, count = max(counts, key=lambda item: item[1])
    return theme if count > 0 else None


def _sentiment(rows: list[dict[str, Any]]) -> str:
    ratio = _positive_ratio(rows)
    if ratio >= 0.65:
        return "positive"
    if ratio <= 0.45:
        return "negative"
    return "mixed"


def _positive_ratio(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get("voted_up")) / len(rows)


def _dominant_language(rows: list[dict[str, Any]]) -> str | None:
    counts = Counter(str(row.get("language") or "unknown") for row in rows)
    language, count = counts.most_common(1)[0]
    return language if count / len(rows) >= 0.8 else None


def _keywords(rows: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(token for token in _tokens(str(row.get("review") or "")) if token not in STOPWORDS)
    return [token for token, _ in counter.most_common(8)]


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z가-힣ぁ-んァ-ン一-龥0-9]{2,}", text)]


def _quote(text: str) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    return compact[:300]


def _evidence_type(sentiment: str) -> str:
    if sentiment == "positive":
        return "praise"
    if sentiment == "negative":
        return "pain_point"
    return "representative"
