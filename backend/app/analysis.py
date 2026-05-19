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


DEFAULT_SEMANTIC_EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
DEFAULT_EMBEDDING_MODEL = DEFAULT_SEMANTIC_EMBEDDING_MODEL
LOCAL_HASH_EMBEDDING_MODEL = "local-hash-v1"
LM_STUDIO_OPENAI_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_NATIVE_BASE_URL = "http://127.0.0.1:1234/api/v1"


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


@dataclass(frozen=True)
class ReviewQuality:
    review_id: str
    normalized_text: str
    text_hash: str
    quality_score: float
    quality_flags: list[str]
    duplicate_count: int


@dataclass(frozen=True)
class ClusterInsight:
    title: str
    summary: str
    praise: str
    pain_point: str
    planner_action: str
    marketing_angle: str
    confidence: float
    warnings: list[str]
    source: str = "deterministic"
    model: str | None = None


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

GAME_THEMES: dict[str, list[Theme]] = {
    "730": [
        Theme("cheaters", "치터/VAC 신뢰", r"cheat|cheater|hacker|vac|spinbot|aimbot|wallhack|читер|читер", "치터, 핵, VAC 대응 신뢰도에 대한 반응입니다."),
        Theme("servers", "서버와 연결 안정성", r"server|tick|ping|lag|packet|disconnect|서버|핑|랙|тик|пинг", "서버 품질, 지연, 접속 안정성 문제가 함께 언급됩니다."),
        Theme("matchmaking", "매치메이킹과 랭크", r"matchmaking|rank|premier|elo|teammate|mmr|매치|랭크|рейтин", "매치 품질, 랭크, 팀 구성에 대한 의견입니다."),
        Theme("performance", "성능과 프레임", r"fps|frame|stutter|crash|freeze|performance|프레임|성능|卡顿", "프레임 드랍, 튕김, 끊김 같은 성능 신호입니다."),
        Theme("csgo_compare", "CS:GO와 변화 비교", r"csgo|cs:go|cs 2|cs2|old cs|source|글옵", "이전 버전과 비교해 달라진 점에 대한 반응입니다."),
        Theme("ui", "UI와 가독성", r"ui|interface|menu|hud|readability|font|메뉴|가독성|интерфейс", "UI, HUD, 메뉴, 가독성에 대한 사용성 의견입니다."),
    ],
    "413150": [
        Theme("cozy", "힐링감과 몰입", r"cozy|relax|chill|comfort|힐링|농장|relaxing|уют", "편안함, 몰입감, 장기 플레이 만족에 대한 반응입니다."),
        Theme("content", "콘텐츠 볼륨", r"content|update|quest|event|festival|콘텐츠|업데이트", "즐길 거리, 업데이트, 이벤트 볼륨에 대한 의견입니다."),
        Theme("multiplayer", "멀티플레이와 협동", r"multiplayer|coop|co-op|friend|친구|멀티", "친구와 함께 하는 플레이 경험에 대한 신호입니다."),
        Theme("mods", "모드와 커뮤니티", r"mod|mods|workshop|community|모드", "모드 친화성과 커뮤니티 확장성에 대한 반응입니다."),
    ],
    "2379780": [
        Theme("addictive", "중독성 있는 반복 플레이", r"addictive|again|one more|replay|중독|한판|もう一回", "계속 다시 하게 만드는 루프에 대한 호평입니다."),
        Theme("deckbuilding", "카드 조합과 덱빌딩", r"deck|card|poker|hand|blind|joker|build|combo|synergy|카드|덱|포커|조커|시너지|组合|卡牌", "카드 조합, 조커 시너지, 덱빌딩 선택지에 대한 반응입니다."),
        Theme("jimbo_meme", "Jimbo와 밈 반응", r"jimbo|clown|meme|mémé|밈|광대", "Jimbo, 광대 캐릭터, 밈성 반응처럼 커뮤니티 농담에 가까운 의견입니다."),
        Theme("rng", "운과 밸런스", r"rng|luck|random|balance|joker|seed|운빨|밸런스", "랜덤성, 조커 조합, 밸런스에 대한 의견입니다."),
        Theme("difficulty", "난이도와 진척", r"difficulty|hard|ante|stake|progress|난이도|어려", "난이도 곡선과 진행 체감에 대한 반응입니다."),
    ],
}

LOW_INFORMATION_PHRASES = {
    "good",
    "great",
    "nice",
    "fun",
    "bad",
    "trash",
    "gg",
    "ez",
    "ok",
    "yes",
    "no",
    "nb",
    "lol",
    "10/10",
    "11/10",
    "추천",
    "비추천",
    "재밌음",
    "재밌다",
    "최고",
    "별로",
}

STOPWORDS = {
    "the",
    "and",
    "but",
    "for",
    "to",
    "with",
    "this",
    "that",
    "game",
    "games",
    "balatro",
    "all",
    "any",
    "around",
    "at",
    "back",
    "be",
    "been",
    "being",
    "big",
    "by",
    "it",
    "is",
    "in",
    "of",
    "on",
    "or",
    "so",
    "some",
    "such",
    "my",
    "we",
    "he",
    "she",
    "them",
    "there",
    "their",
    "these",
    "those",
    "good",
    "great",
    "fun",
    "best",
    "better",
    "well",
    "hours",
    "play",
    "played",
    "playing",
    "still",
    "feel",
    "feels",
    "after",
    "every",
    "new",
    "same",
    "again",
    "about",
    "also",
    "are",
    "can",
    "cant",
    "could",
    "did",
    "didnt",
    "dont",
    "don't",
    "does",
    "doesnt",
    "because",
    "before",
    "ever",
    "even",
    "first",
    "from",
    "go",
    "going",
    "get",
    "got",
    "had",
    "has",
    "have",
    "having",
    "how",
    "if",
    "into",
    "isnt",
    "its",
    "it's",
    "ive",
    "i've",
    "ill",
    "i'll",
    "im",
    "i'm",
    "just",
    "know",
    "like",
    "lot",
    "make",
    "makes",
    "more",
    "most",
    "many",
    "much",
    "need",
    "not",
    "nothing",
    "now",
    "one",
    "only",
    "other",
    "out",
    "over",
    "pretty",
    "really",
    "see",
    "stuff",
    "while",
    "than",
    "then",
    "they",
    "think",
    "too",
    "try",
    "up",
    "very",
    "was",
    "were",
    "what",
    "when",
    "way",
    "which",
    "who",
    "why",
    "will",
    "would",
    "wouldnt",
    "you",
    "youre",
    "you're",
    "your",
    "ve",
    "want",
    "without",
    "review",
    "recommend",
    "recommended",
    "recommendation",
    "steam",
    "10",
    "100",
    "01",
    "2024",
    "2025",
    "2026",
    "de",
    "del",
    "des",
    "du",
    "el",
    "en",
    "es",
    "esse",
    "est",
    "et",
    "eu",
    "il",
    "je",
    "la",
    "las",
    "le",
    "les",
    "lo",
    "los",
    "me",
    "mi",
    "no",
    "pas",
    "por",
    "que",
    "qui",
    "se",
    "un",
    "una",
    "une",
    "juego",
    "juegos",
    "muy",
    "pero",
    "este",
    "esta",
    "como",
    "con",
    "com",
    "do",
    "si",
    "sin",
    "para",
    "te",
    "todo",
    "tudo",
    "mas",
    "mais",
    "muito",
    "na",
    "al",
    "horas",
    "jugar",
    "jogo",
    "jeu",
    "das",
    "der",
    "die",
    "ein",
    "eine",
    "ich",
    "ist",
    "mit",
    "nicht",
    "und",
    "zu",
    "den",
    "dem",
    "einfach",
    "на",
    "не",
    "что",
    "это",
    "как",
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
    llm_model: str | None = None,
    min_quality_score: float = 0.25,
    exclude_duplicate_evidence: bool = True,
    use_lmstudio_labels: bool = True,
    max_clusters: int = 60,
    evidence_per_claim: int = 3,
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

    quality_rows = _score_review_quality(reviews)
    quality_by_id = {row.review_id: row for row in quality_rows}
    clustering_reviews = _select_cluster_candidates(reviews, quality_by_id, min_quality_score)

    embedding_rows: list[list[float]] | None = None
    try:
        groups, embedding_rows, device = _cluster_with_semantic_embeddings(
            clustering_reviews,
            model_name,
            min_cluster_size,
            app_id,
            max_clusters,
            quality_by_id,
        )
        clusterer = f"sentence_transformers_minibatch_kmeans_{device}"
        message = f"Analysis completed with GPU-ready semantic embeddings ({model_name}) on {device}."
    except Exception as exc:
        try:
            groups = _cluster_with_sklearn(clustering_reviews, min_cluster_size, app_id, max_clusters, quality_by_id)
            clusterer = "sklearn_tfidf_kmeans"
            message = (
                "Semantic embedding path unavailable; completed with local TF-IDF clustering "
                f"({exc.__class__.__name__})."
            )
        except Exception as fallback_exc:
            groups = _cluster_with_keywords(clustering_reviews, app_id, quality_by_id)
            clusterer = "keyword_fallback"
            message = (
                "Semantic and TF-IDF clustering failed; used keyword fallback "
                f"({exc.__class__.__name__}, {fallback_exc.__class__.__name__})."
            )

    groups = _apply_ctfidf_keywords(groups)

    if generate_ai_summary and llm_provider in {"lmstudio", "lm_studio"}:
        groups = _enrich_cluster_insights(groups, app_id, use_lmstudio_labels, llm_model)
        message += " Cluster labels and actions were enriched through LM Studio when available."
    else:
        groups = _enrich_cluster_insights(groups, app_id, False, llm_model)

    with connect() as conn:
        _store_review_quality(conn, analysis_run_id, quality_rows)
        _store_embeddings(conn, clustering_reviews, model_name, embedding_rows)
        clusters_created, evidence_created = _store_analysis_outputs(
            conn,
            analysis_run_id,
            groups,
            evidence_per_claim=evidence_per_claim,
            exclude_duplicate_evidence=exclude_duplicate_evidence,
        )
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
            "id": "local_gpu",
            "label": "Local GPU embeddings",
            "available": True,
            "default": True,
            "notes": "Uses SentenceTransformers on CUDA when available; falls back to CPU/TF-IDF.",
            "default_embedding_model": DEFAULT_SEMANTIC_EMBEDDING_MODEL,
        },
        {
            "id": "lmstudio",
            "label": "LM Studio",
            "available": lm_status["available"],
            "default": False,
            "base_url": LM_STUDIO_NATIVE_BASE_URL,
            "openai_base_url": LM_STUDIO_OPENAI_BASE_URL,
            "models": lm_status["models"],
            "embedding_models": lm_status.get("embedding_models", []),
        },
    ]
    return {
        "default_provider": "local_gpu",
        "default_embedding_model": DEFAULT_SEMANTIC_EMBEDDING_MODEL,
        "providers": providers,
        "lm_studio": lm_status,
    }


async def _lm_studio_status() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{LM_STUDIO_NATIVE_BASE_URL}/models")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{LM_STUDIO_OPENAI_BASE_URL}/models")
                response.raise_for_status()
                payload = response.json()
        except Exception as fallback_exc:
            return {
                "available": False,
                "base_url": LM_STUDIO_NATIVE_BASE_URL,
                "openai_base_url": LM_STUDIO_OPENAI_BASE_URL,
                "models": [],
                "embedding_models": [],
                "default_model": None,
                "message": f"{exc}; OpenAI-compatible fallback failed: {fallback_exc}",
            }

        models = [str(item.get("id")) for item in payload.get("data", []) if item.get("id")]
        return {
            "available": True,
            "base_url": LM_STUDIO_OPENAI_BASE_URL,
            "models": models,
            "embedding_models": [model for model in models if "embed" in model.lower()],
            "default_model": models[0] if models else None,
            "message": "LM Studio OpenAI-compatible endpoint is reachable.",
        }

    rows = payload.get("models") or []
    models = [str(item.get("key")) for item in rows if item.get("key")]
    embedding_models = [str(item.get("key")) for item in rows if item.get("type") == "embedding" and item.get("key")]
    llm_models = [str(item.get("key")) for item in rows if item.get("type") == "llm" and item.get("key")]
    return {
        "available": True,
        "base_url": LM_STUDIO_NATIVE_BASE_URL,
        "openai_base_url": LM_STUDIO_OPENAI_BASE_URL,
        "models": models,
        "embedding_models": embedding_models,
        "default_model": llm_models[0] if llm_models else models[0] if models else None,
        "message": "LM Studio native v1 endpoint is reachable.",
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


def _score_review_quality(reviews: list[dict[str, Any]]) -> list[ReviewQuality]:
    base_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for row in reviews:
        normalized = _normalize_review_text(str(row.get("review") or ""))
        text_hash = hashlib.blake2b(normalized.encode("utf-8"), digest_size=12).hexdigest()
        counts[text_hash] += 1
        base_rows.append({**row, "_normalized_text": normalized, "_text_hash": text_hash})

    scored: list[ReviewQuality] = []
    for row in base_rows:
        text = str(row.get("review") or "")
        normalized = str(row["_normalized_text"])
        tokens = _tokens(text)
        unique_tokens = set(tokens)
        flags: list[str] = []
        if len(normalized) < 12 or len(tokens) <= 1:
            flags.append("very_short")
        if normalized in LOW_INFORMATION_PHRASES or _looks_like_low_information(normalized, tokens):
            flags.append("low_information")
        duplicate_count = counts[str(row["_text_hash"])]
        if duplicate_count > 1:
            flags.append("duplicate")
        if not re.search(r"[A-Za-z가-힣ぁ-んァ-ン一-龥]", normalized):
            flags.append("no_words")

        weighted = max(0.0, min(float(row.get("weighted_vote_score") or 0), 1.0))
        length_score = min(len(normalized) / 260, 0.38)
        diversity_score = min(len(unique_tokens) / 14, 0.28)
        vote_score = min(math.log1p(int(row.get("votes_up") or 0)) / 8, 0.08)
        score = 0.16 + length_score + diversity_score + weighted * 0.16 + vote_score
        if "very_short" in flags:
            score -= 0.28
        if "low_information" in flags:
            score -= 0.28
        if "duplicate" in flags:
            score -= min(0.18, 0.04 * math.log2(duplicate_count + 1))
        if "no_words" in flags:
            score -= 0.18
        score = max(0.0, min(score, 1.0))
        scored.append(
            ReviewQuality(
                review_id=str(row["recommendation_id"]),
                normalized_text=normalized,
                text_hash=str(row["_text_hash"]),
                quality_score=score,
                quality_flags=flags,
                duplicate_count=duplicate_count,
            )
        )
    return scored


def _select_cluster_candidates(
    reviews: list[dict[str, Any]],
    quality_by_id: dict[str, ReviewQuality],
    min_quality_score: float,
) -> list[dict[str, Any]]:
    best_by_hash: dict[str, dict[str, Any]] = {}
    for row in reviews:
        quality = quality_by_id.get(str(row["recommendation_id"]))
        if not quality or quality.quality_score < min_quality_score:
            continue
        current = best_by_hash.get(quality.text_hash)
        if current is None:
            best_by_hash[quality.text_hash] = row
            continue
        current_quality = quality_by_id.get(str(current["recommendation_id"]))
        if not current_quality or quality.quality_score > current_quality.quality_score:
            best_by_hash[quality.text_hash] = row

    candidates = list(best_by_hash.values())
    minimum = max(10, min(50, len(reviews) // 10))
    if len(candidates) >= minimum:
        return candidates
    return reviews


def _normalize_review_text(text: str) -> str:
    compact = re.sub(r"\s+", " ", text.casefold()).strip()
    compact = re.sub(r"https?://\S+", "", compact)
    compact = re.sub(r"[\u200b-\u200f]", "", compact)
    compact = re.sub(r"([!?.,~])\1{2,}", r"\1\1", compact)
    return compact.strip()


def _looks_like_low_information(normalized: str, tokens: list[str]) -> bool:
    if not normalized:
        return True
    if len(tokens) <= 2 and len(normalized) <= 18:
        return True
    if len(set(normalized.replace(" ", ""))) <= 3 and len(normalized) <= 24:
        return True
    if re.fullmatch(r"[\W_0-9]+", normalized):
        return True
    return False


def _cluster_with_semantic_embeddings(
    reviews: list[dict[str, Any]],
    model_name: str,
    min_cluster_size: int,
    app_id: str | None,
    max_clusters: int,
    quality_by_id: dict[str, ReviewQuality],
) -> tuple[list[dict[str, Any]], list[list[float]], str]:
    if model_name == LOCAL_HASH_EMBEDDING_MODEL:
        raise RuntimeError("local hash embeddings are only used as a storage fallback")

    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import MiniBatchKMeans

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(model_name, device=device)
    texts = [_embedding_text(model_name, str(row.get("review") or "")) for row in reviews]
    batch_size = 96 if device == "cuda" else 24
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)
    cluster_count = max(1, min(max_clusters, len(reviews) // max(min_cluster_size, 1)))
    if cluster_count == 1:
        labels = np.zeros(len(reviews), dtype=np.int32)
        scores = np.ones(len(reviews), dtype=np.float32)
    else:
        model_batch_size = max(1024, cluster_count * 96)
        clusterer = MiniBatchKMeans(
            n_clusters=cluster_count,
            random_state=13,
            batch_size=model_batch_size,
            n_init=10,
            reassignment_ratio=0.01,
        )
        labels = clusterer.fit_predict(embeddings)
        centers = np.asarray(clusterer.cluster_centers_, dtype=np.float32)
        norms = np.linalg.norm(centers, axis=1, keepdims=True)
        centers = centers / np.maximum(norms, 1e-12)
        scores = np.sum(embeddings * centers[labels], axis=1)

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row, label, score in zip(reviews, labels, scores, strict=True):
        grouped[int(label)].append({
            "row": row,
            "score": max(0.0, min(float(score), 1.0)),
            "quality": quality_by_id.get(str(row["recommendation_id"])),
        })
    return [_describe_group(members, app_id, quality_by_id) for members in grouped.values()], embeddings.tolist(), device


def _embedding_text(model_name: str, text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if "e5" in model_name.lower() and not compact.lower().startswith(("query:", "passage:")):
        return f"passage: {compact}"
    return compact


def _cluster_with_sklearn(
    reviews: list[dict[str, Any]],
    min_cluster_size: int,
    app_id: str | None,
    max_clusters: int,
    quality_by_id: dict[str, ReviewQuality],
) -> list[dict[str, Any]]:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [row["review"] or "" for row in reviews]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=8000)
    matrix = vectorizer.fit_transform(texts)
    cluster_count = max(1, min(max_clusters, len(reviews) // max(min_cluster_size, 1)))
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
        grouped[int(label)].append({
            "row": row,
            "score": max(0.0, min(score, 1.0)),
            "quality": quality_by_id.get(str(row["recommendation_id"])),
        })
    return [_describe_group(members, app_id, quality_by_id) for members in grouped.values()]


def _cluster_with_keywords(
    reviews: list[dict[str, Any]],
    app_id: str | None,
    quality_by_id: dict[str, ReviewQuality],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    themes = [*GAME_THEMES.get(str(app_id or ""), []), *THEMES]
    for row in reviews:
        text = str(row.get("review") or "").lower()
        matches = [(theme, len(re.findall(theme.pattern, text, flags=re.IGNORECASE))) for theme in themes]
        theme, count = max(matches, key=lambda item: item[1])
        if count <= 0:
            grouped["misc"].append({"row": row, "score": 0.55, "quality": quality_by_id.get(str(row["recommendation_id"]))})
        else:
            grouped[theme.key].append({
                "row": row,
                "score": min(1.0, 0.62 + count * 0.12),
                "quality": quality_by_id.get(str(row["recommendation_id"])),
            })
    return [_describe_group(members, app_id, quality_by_id) for members in grouped.values() if members]


def _describe_group(
    members: list[dict[str, Any]],
    app_id: str | None,
    quality_by_id: dict[str, ReviewQuality],
) -> dict[str, Any]:
    rows = [member["row"] for member in members]
    sentiment = _sentiment(rows)
    best_theme = _best_theme(rows, app_id)
    keywords = _keywords(rows)
    language = _dominant_language(rows)
    positive_ratio = _positive_ratio(rows)
    quality_warning = _quality_warning(rows, quality_by_id)
    if best_theme:
        label = best_theme.label
        label_source = "theme"
        summary = f"{len(rows)}개 리뷰에서 {best_theme.summary} 긍정 비율은 {positive_ratio:.0%}입니다."
    else:
        if sentiment == "positive":
            label = "긍정 경험 묶음"
        elif sentiment == "negative":
            label = "개선 요청 묶음"
        else:
            label = "혼합 의견 묶음"
        if keywords:
            label = f"{keywords[0]} 중심 의견"
        label_source = "keyword"
        keyword_text = ", ".join(keywords[:4]) if keywords else "공통 표현 부족"
        summary = f"{len(rows)}개 리뷰가 유사한 표현으로 묶였습니다. 주요 단어는 {keyword_text}이며 긍정 비율은 {_positive_ratio(rows):.0%}입니다."
    return {
        "label": label,
        "summary": summary,
        "sentiment": sentiment,
        "language": language,
        "reviews": members,
        "keywords": keywords,
        "keyword_method": "frequency",
        "label_source": label_source,
        "positive_ratio": positive_ratio,
        "quality_warning": quality_warning,
    }


def _apply_ctfidf_keywords(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(groups) < 2:
        return groups

    try:
        import numpy as np
        from sklearn.feature_extraction.text import CountVectorizer

        documents = [_cluster_keyword_document(group) for group in groups]
        if sum(1 for document in documents if document.strip()) < 2:
            return groups

        vectorizer = CountVectorizer(
            lowercase=True,
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.85 if len(groups) < 4 else 0.55,
            max_features=8000,
            stop_words=sorted(STOPWORDS),
            token_pattern=r"(?u)\b[A-Za-z가-힣ぁ-んァ-ン一-龥0-9][A-Za-z가-힣ぁ-んァ-ン一-龥0-9']+\b",
        )
        matrix = vectorizer.fit_transform(documents).astype(float)
        if matrix.shape[1] == 0:
            return groups

        counts = matrix.toarray()
        row_totals = np.maximum(counts.sum(axis=1, keepdims=True), 1.0)
        term_cluster_counts = np.maximum((counts > 0).sum(axis=0), 1)
        idf = np.log((1 + len(groups)) / (1 + term_cluster_counts)) + 1.0
        scores = (counts / row_totals) * idf
        terms = vectorizer.get_feature_names_out()
    except Exception:
        return groups

    for group_index, group in enumerate(groups):
        ranked: list[tuple[str, float]] = []
        for index in np.argsort(scores[group_index])[::-1][:160]:
            count = float(counts[group_index, index])
            if count < 2:
                continue
            term = str(terms[index])
            length_penalty = 1 + 0.18 * max(0, len(term.split()) - 1)
            ranked.append((term, float(scores[group_index, index]) / length_penalty))
        ranked.sort(key=lambda item: item[1], reverse=True)
        keywords = _distinct_keywords(ranked, limit=8)
        if not keywords:
            continue
        group["keywords"] = keywords
        group["keyword_method"] = "ctfidf"
        rows = [member["row"] for member in group["reviews"]]
        if group.get("label_source") == "keyword":
            group["label"] = f"{keywords[0]} 중심 의견"
            keyword_text = ", ".join(keywords[:4])
            group["summary"] = (
                f"{len(rows)}개 리뷰가 유사한 표현으로 묶였습니다. "
                f"주요 표현은 {keyword_text}이며 긍정 비율은 {_positive_ratio(rows):.0%}입니다."
            )
    return groups


def _cluster_keyword_document(group: dict[str, Any]) -> str:
    reviews = []
    for member in group.get("reviews", []):
        row = member.get("row", {})
        text = _normalize_review_text(str(row.get("review") or ""))
        if text:
            reviews.append(text)
    return " ".join(reviews)


def _distinct_keywords(ranked_terms: list[tuple[str, float]], limit: int) -> list[str]:
    selected: list[str] = []
    for term, score in ranked_terms:
        cleaned = _clean_keyword(term)
        if not cleaned or score <= 0:
            continue
        if _keyword_is_noise(cleaned):
            continue
        if any(_keywords_overlap(cleaned, existing) for existing in selected):
            continue
        selected.append(cleaned)
        if len(selected) >= limit:
            break
    return selected


def _clean_keyword(term: str) -> str:
    compact = re.sub(r"\s+", " ", term.casefold()).strip(" '\".,!?;:()[]{}")
    return compact


def _keyword_is_noise(keyword: str) -> bool:
    parts = keyword.split()
    if not parts:
        return True
    if len(parts) > 2:
        return True
    if len(parts) > 1 and (parts[0] in STOPWORDS or parts[-1] in STOPWORDS):
        return True
    if all(part in STOPWORDS for part in parts):
        return True
    if len(parts) == 1 and parts[0] in STOPWORDS:
        return True
    if len(keyword) <= 2 and not re.search(r"[가-힣ぁ-んァ-ン一-龥]", keyword):
        return True
    if re.fullmatch(r"[\d_]+", keyword):
        return True
    return False


def _keywords_overlap(candidate: str, existing: str) -> bool:
    candidate_parts = set(candidate.split())
    existing_parts = set(existing.split())
    if not candidate_parts or not existing_parts:
        return False
    if candidate in existing or existing in candidate:
        return True
    overlap = len(candidate_parts & existing_parts)
    return overlap >= min(len(candidate_parts), len(existing_parts)) and overlap > 0


def _enrich_cluster_insights(
    groups: list[dict[str, Any]],
    app_id: str | None,
    use_lmstudio: bool,
    llm_model: str | None,
) -> list[dict[str, Any]]:
    enriched = []
    for group in groups:
        insight = _deterministic_cluster_insight(group, app_id)
        if use_lmstudio:
            insight = _lmstudio_cluster_insight(group, insight, app_id, llm_model) or insight
        enriched.append({**group, "insight": insight})
    return enriched


def _deterministic_cluster_insight(group: dict[str, Any], app_id: str | None) -> ClusterInsight:
    rows = [member["row"] for member in group["reviews"]]
    positive_ratio = float(group.get("positive_ratio") or _positive_ratio(rows))
    title = str(group["label"])
    warning = group.get("quality_warning")
    keyword_text = ", ".join(group.get("keywords") or [])
    sentiment_text = "호평" if positive_ratio >= 0.65 else "불만" if positive_ratio <= 0.45 else "호평과 불만이 섞인 반응"
    summary = (
        f"{len(rows)}개 품질 필터 통과 리뷰에서 {title} 관련 {sentiment_text}이 관측됩니다. "
        f"추천 비율은 {positive_ratio:.0%}입니다."
    )
    if keyword_text:
        summary += f" 주요 표현은 {keyword_text}입니다."

    praise = f"{title}을 긍정적으로 언급한 리뷰가 있습니다." if positive_ratio > 0 else ""
    pain_point = f"{title}에 대한 불만 또는 주의 신호가 있습니다." if positive_ratio < 1 else ""
    planner_action = _planner_action_for(title, positive_ratio, app_id)
    marketing_angle = f"{title} 관련 호평은 스토어 문구나 패치 노트에서 강점 근거로 검토할 수 있습니다."
    warnings = [warning] if warning else []
    confidence = 0.7
    if warning:
        confidence -= 0.15
    if len(rows) < 30:
        confidence -= 0.1
    return ClusterInsight(
        title=title,
        summary=summary,
        praise=praise,
        pain_point=pain_point,
        planner_action=planner_action,
        marketing_angle=marketing_angle,
        confidence=max(0.3, min(confidence, 0.9)),
        warnings=warnings,
    )


def _planner_action_for(title: str, positive_ratio: float, app_id: str | None) -> str:
    if positive_ratio <= 0.45:
        return f"{title} 불만 원문을 우선 확인하고 다음 패치/공지에서 대응 여부를 정리하세요."
    if positive_ratio < 0.65:
        return f"{title}은 호불호가 갈립니다. 언어권과 최근 기간별로 나눠 원인을 분리하세요."
    if str(app_id or "") == "730" and ("치터" in title or "서버" in title or "매치" in title):
        return f"{title} 신호는 운영 신뢰와 직접 연결되므로 최근 불만 리뷰를 별도로 추적하세요."
    return f"{title} 호평은 유지해야 할 강점으로 기록하고, 불만 샘플이 있는지 함께 점검하세요."


def _lmstudio_cluster_insight(
    group: dict[str, Any],
    fallback: ClusterInsight,
    app_id: str | None,
    llm_model: str | None,
) -> ClusterInsight | None:
    samples = _balanced_lmstudio_samples(group["reviews"], limit=10)
    keyword_text = ", ".join(group.get("keywords") or []) or "없음"
    warning_text = group.get("quality_warning") or "없음"
    sample_text = "\n".join(
        f"- {'추천' if member['row'].get('voted_up') else '비추천'} / {member['row'].get('language')} / "
        f"{_playtime_hours(member['row'].get('playtime_at_review'))}: "
        f"{_quote(member['row'].get('review') or '')}"
        for member in samples
    )
    prompt = (
        "Steam 리뷰 클러스터를 게임 기획자가 읽을 수 있게 한국어 JSON으로만 요약하세요. "
        "과장하지 말고 원문에 없는 사실을 만들지 마세요. "
        "title은 30자 안팎의 구체적인 명사구로 쓰고, summary는 원인/맥락을 1문장으로 쓰세요. "
        "planner_action은 기획자가 다음에 확인할 액션이어야 합니다.\n"
        f"Steam app_id={app_id}. 기존 라벨={group['label']}. "
        f"키워드={keyword_text}. 추천율={float(group.get('positive_ratio') or 0):.0%}. "
        f"품질 경고={warning_text}.\n"
        f"샘플:\n{sample_text}\n"
        'JSON keys: title, summary, praise, pain_point, planner_action, marketing_angle, confidence, warnings'
    )
    model: str | None = None
    try:
        with httpx.Client(timeout=45) as client:
            model = _lmstudio_default_model_sync(client, llm_model)
            body: dict[str, Any] = {
                "input": prompt,
                "context_length": 8000,
            }
            if model:
                body["model"] = model
            response = client.post(
                f"{LM_STUDIO_NATIVE_BASE_URL}/chat",
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None

    raw = _extract_lmstudio_text(payload)
    if isinstance(raw, dict):
        raw = json.dumps(raw)
    data = _parse_json_object(str(raw))
    if not data:
        return None
    return ClusterInsight(
        title=str(data.get("title") or fallback.title)[:80],
        summary=str(data.get("summary") or fallback.summary),
        praise=str(data.get("praise") or fallback.praise),
        pain_point=str(data.get("pain_point") or fallback.pain_point),
        planner_action=str(data.get("planner_action") or fallback.planner_action),
        marketing_angle=str(data.get("marketing_angle") or fallback.marketing_angle),
        confidence=max(0.0, min(float(data.get("confidence") or fallback.confidence), 1.0)),
        warnings=_coerce_string_list(data.get("warnings", fallback.warnings)),
        source="lm_studio",
        model=model or llm_model,
    )


def _balanced_lmstudio_samples(members: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ranked = _rank_members(members)
    selected: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    def add_matching(predicate: Any, count: int) -> None:
        for member in ranked:
            if len(selected) >= limit:
                return
            if count <= 0:
                return
            if not predicate(member):
                continue
            text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
            if text_hash in seen_hashes:
                continue
            selected.append(member)
            seen_hashes.add(text_hash)
            count -= 1

    add_matching(lambda member: not bool(member["row"].get("voted_up")), max(2, limit // 3))
    add_matching(lambda member: bool(member["row"].get("voted_up")), max(2, limit // 3))
    add_matching(lambda _member: True, limit)
    return selected[:limit]


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _playtime_hours(value: Any) -> str:
    try:
        minutes = int(value or 0)
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return "플레이타임 미상"
    return f"{minutes / 60:.1f}h"


def _extract_lmstudio_text(payload: dict[str, Any]) -> str:
    for key in ("output", "content", "text"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content") or item.get("message")
                    if isinstance(text, list):
                        text = " ".join(str(part.get("text") if isinstance(part, dict) else part) for part in text)
                    parts.append(str(text or ""))
                else:
                    parts.append(str(item))
            return " ".join(part for part in parts if part)
    message = payload.get("message")
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            choice_message = first.get("message")
            if isinstance(choice_message, dict) and isinstance(choice_message.get("content"), str):
                return choice_message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]
    return ""


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def _lmstudio_default_model_sync(client: httpx.Client, preferred_model: str | None = None) -> str | None:
    try:
        response = client.get(f"{LM_STUDIO_NATIVE_BASE_URL}/models")
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None
    rows = payload.get("models") or []
    llm = [str(item.get("key")) for item in rows if item.get("type") == "llm" and item.get("key")]
    if preferred_model and preferred_model in llm:
        return preferred_model
    models = [str(item.get("key")) for item in rows if item.get("key")]
    return llm[0] if llm else models[0] if models else None


def _store_embeddings(
    conn: duckdb.DuckDBPyConnection,
    reviews: list[dict[str, Any]],
    model_name: str,
    embeddings: list[list[float]] | None = None,
) -> None:
    generated_at = utcnow()
    rows = []
    for index, review in enumerate(reviews):
        embedding = embeddings[index] if embeddings is not None else _hash_embedding(str(review.get("review") or ""))
        rows.append(
            (
                review["recommendation_id"],
                model_name,
                len(embedding),
                json.dumps([round(float(value), 6) for value in embedding]),
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


def _store_review_quality(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    quality_rows: list[ReviewQuality],
) -> None:
    if not quality_rows:
        return
    conn.executemany(
        """
        INSERT INTO review_quality (
            analysis_run_id, review_id, normalized_text, text_hash,
            quality_score, quality_flags, duplicate_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (analysis_run_id, review_id) DO UPDATE SET
            normalized_text = excluded.normalized_text,
            text_hash = excluded.text_hash,
            quality_score = excluded.quality_score,
            quality_flags = excluded.quality_flags,
            duplicate_count = excluded.duplicate_count
        """,
        [
            (
                analysis_run_id,
                row.review_id,
                row.normalized_text,
                row.text_hash,
                row.quality_score,
                json.dumps(row.quality_flags),
                row.duplicate_count,
            )
            for row in quality_rows
        ],
    )


def _store_analysis_outputs(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    groups: list[dict[str, Any]],
    *,
    evidence_per_claim: int,
    exclude_duplicate_evidence: bool,
) -> tuple[int, int]:
    clusters_created = 0
    evidence_created = 0
    used_evidence_hashes: set[str] = set()
    for group in sorted(groups, key=lambda item: len(item["reviews"]), reverse=True):
        ranked_members = _rank_members(group["reviews"])
        rows = [member["row"] for member in ranked_members]
        review_count = len(rows)
        avg_score = sum(float(row.get("weighted_vote_score") or 0) for row in rows) / review_count
        exemplar = rows[0]["recommendation_id"]
        insight = group["insight"]
        cluster_id = conn.execute(
            """
            INSERT INTO clusters (
                analysis_run_id, label, summary, sentiment, language, review_count,
                avg_weighted_score, exemplar_review_id, positive_ratio, top_keywords,
                keyword_method, quality_warning
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
            """,
            [
                analysis_run_id,
                insight.title,
                insight.summary,
                group["sentiment"],
                group["language"],
                review_count,
                avg_score,
                exemplar,
                group["positive_ratio"],
                json.dumps(group["keywords"]),
                group.get("keyword_method"),
                group["quality_warning"],
            ],
        ).fetchone()[0]
        _insert_cluster_insight(conn, cluster_id, insight)
        clusters_created += 1
        conn.executemany(
            "INSERT INTO review_clusters (review_id, cluster_id, score) VALUES (?, ?, ?)",
            [(member["row"]["recommendation_id"], cluster_id, member["score"]) for member in ranked_members],
        )
        for claim_type, claim_text in _claim_specs_for_group(group, insight):
            claim_id = conn.execute(
                """
                INSERT INTO claims (analysis_run_id, cluster_id, claim_type, claim_text, confidence)
                VALUES (?, ?, ?, ?, ?) RETURNING id
                """,
                [analysis_run_id, cluster_id, claim_type, claim_text, insight.confidence],
            ).fetchone()[0]
            evidence_members = _select_evidence_members(
                ranked_members,
                claim_type,
                evidence_per_claim,
                used_evidence_hashes,
                exclude_duplicate_evidence,
            )
            for member in evidence_members:
                row = member["row"]
                quality = member.get("quality")
                conn.execute(
                    """
                    INSERT INTO evidence (
                        analysis_run_id, claim_id, review_id, cluster_id, quote,
                        evidence_type, evidence_role, note, quality_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        analysis_run_id,
                        claim_id,
                        row["recommendation_id"],
                        cluster_id,
                        _quote(row["review"]),
                        _evidence_type(claim_type),
                        claim_type,
                        f"{_evidence_role_label(claim_type)} · 품질 {member['representative_score']:.2f}",
                        quality.quality_score if quality else None,
                    ],
                )
                evidence_created += 1
    return clusters_created, evidence_created


def _insert_cluster_insight(conn: duckdb.DuckDBPyConnection, cluster_id: int, insight: ClusterInsight) -> None:
    conn.execute(
        """
        INSERT INTO cluster_insights (
            cluster_id, title, summary, praise, pain_point,
            planner_action, marketing_angle, confidence, warnings, source, model
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            cluster_id,
            insight.title,
            insight.summary,
            insight.praise,
            insight.pain_point,
            insight.planner_action,
            insight.marketing_angle,
            insight.confidence,
            json.dumps(insight.warnings),
            insight.source,
            insight.model,
        ],
    )


def _claim_specs_for_group(group: dict[str, Any], insight: ClusterInsight) -> list[tuple[str, str]]:
    rows = [member["row"] for member in group["reviews"]]
    has_praise = any(row.get("voted_up") for row in rows)
    has_complaint = any(not row.get("voted_up") for row in rows)
    claims: list[tuple[str, str]] = []
    if has_complaint:
        claims.append(("complaint", insight.pain_point or f"{insight.title} 관련 불만 신호가 있습니다."))
    if has_praise:
        claims.append(("praise", insight.praise or f"{insight.title} 관련 호평 신호가 있습니다."))
    if not claims:
        claims.append(("representative", insight.summary))
    return claims[:2]


def _select_evidence_members(
    ranked_members: list[dict[str, Any]],
    role: str,
    limit: int,
    used_hashes: set[str],
    exclude_duplicates: bool,
) -> list[dict[str, Any]]:
    def role_match(member: dict[str, Any]) -> bool:
        voted_up = bool(member["row"].get("voted_up"))
        if role == "complaint":
            return not voted_up
        if role == "praise":
            return voted_up
        return True

    selected: list[dict[str, Any]] = []
    candidates = [member for member in ranked_members if role_match(member)]
    if not candidates:
        candidates = ranked_members

    for member in candidates:
        quality = member.get("quality")
        text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
        if exclude_duplicates and text_hash in used_hashes:
            continue
        if quality and quality.quality_score < 0.2 and len(candidates) > limit:
            continue
        selected.append(member)
        used_hashes.add(text_hash)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for member in candidates:
            if member in selected:
                continue
            text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
            if exclude_duplicates and text_hash in used_hashes:
                continue
            selected.append(member)
            used_hashes.add(text_hash)
            if len(selected) >= limit:
                break
    if not selected and candidates:
        member = candidates[0]
        text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
        selected.append(member)
        used_hashes.add(text_hash)
    return selected


def _text_hash(text: str) -> str:
    return hashlib.blake2b(_normalize_review_text(text).encode("utf-8"), digest_size=12).hexdigest()


def _evidence_role_label(role: str) -> str:
    if role == "complaint":
        return "구체적 불만"
    if role == "praise":
        return "구체적 호평"
    if role == "recent":
        return "최근 리뷰"
    if role == "high_weight":
        return "고가중치 리뷰"
    return "대표 리뷰"


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
        quality = member.get("quality")
        length_score = min(len(str(row.get("review") or "")) / 500, 1.0)
        weighted_score = max(0.0, min(float(row.get("weighted_vote_score") or 0), 1.0))
        quality_score = quality.quality_score if quality else 0.5
        representative_score = member["score"] * 0.45 + quality_score * 0.35 + weighted_score * 0.15 + length_score * 0.05
        ranked.append({**member, "quality": quality, "representative_score": representative_score})
    return sorted(ranked, key=lambda item: item["representative_score"], reverse=True)


def _best_theme(rows: list[dict[str, Any]], app_id: str | None = None) -> Theme | None:
    text = "\n".join(str(row.get("review") or "").lower() for row in rows)
    themes = [*GAME_THEMES.get(str(app_id or ""), []), *THEMES]
    counts = [(theme, len(re.findall(theme.pattern, text, flags=re.IGNORECASE))) for theme in themes]
    theme, count = max(counts, key=lambda item: item[1])
    return theme if count > 0 else None


def _quality_warning(rows: list[dict[str, Any]], quality_by_id: dict[str, ReviewQuality]) -> str | None:
    if not rows:
        return None
    qualities = [quality_by_id.get(str(row["recommendation_id"])) for row in rows]
    qualities = [quality for quality in qualities if quality]
    if not qualities:
        return None
    low_info = sum(1 for quality in qualities if "low_information" in quality.quality_flags or "very_short" in quality.quality_flags)
    duplicates = sum(1 for quality in qualities if "duplicate" in quality.quality_flags)
    if low_info / len(qualities) >= 0.45:
        return "짧거나 정보량이 낮은 리뷰가 많은 묶음"
    if duplicates / len(qualities) >= 0.35:
        return "중복 표현이 많은 묶음"
    if len(rows) < 20:
        return "표본이 작은 묶음"
    return None


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


def _evidence_type(role: str) -> str:
    if role == "praise":
        return "praise"
    if role == "complaint":
        return "pain_point"
    return "representative"
