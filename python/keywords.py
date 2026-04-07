import numpy as np
from typing import Optional


def extract_keywords_yake(texts: list[str], top_n: int = 10, language: str = "en") -> list[tuple[str, float]]:
    """Extract keywords using YAKE! (CPU-friendly, no model needed)."""
    if not texts:
        return []

    import yake
    combined = " ".join(texts)
    extractor = yake.KeywordExtractor(
        lan=language,
        n=2,  # up to bigrams
        dedupLim=0.7,
        top=top_n,
        features=None
    )
    keywords = extractor.extract_keywords(combined)
    # YAKE returns (keyword, score) where lower score = more important
    # Normalize so higher = better
    if not keywords:
        return []
    max_score = max(k[1] for k in keywords) + 0.001
    return [(kw, 1.0 - score / max_score) for kw, score in keywords]


def extract_keywords_embedding(
    texts: list[str],
    embeddings: np.ndarray,
    top_n: int = 10
) -> list[tuple[str, float]]:
    """Extract keywords using KeyBERT-style embedding similarity + MMR."""
    if not texts or len(embeddings) == 0:
        return []

    from keybert import KeyBERT

    combined = " ".join(texts[:100])  # limit for KeyBERT input
    kw_model = KeyBERT()
    keywords = kw_model.extract_keywords(
        combined,
        keyphrase_ngram_range=(1, 2),
        stop_words="english",
        use_mmr=True,
        diversity=0.5,
        top_n=top_n
    )
    return keywords  # list of (keyword, score)


def extract_topic_keywords(
    texts: list[str],
    labels: list[int],
    tier: int = 0,
    embeddings: Optional[np.ndarray] = None,
    top_n: int = 8
) -> dict[int, list[tuple[str, float]]]:
    """Extract keywords per topic cluster."""
    topics: dict[int, list[str]] = {}
    for text, label in zip(texts, labels):
        if label < 0:  # noise in HDBSCAN
            continue
        topics.setdefault(label, []).append(text)

    result = {}
    for topic_id, topic_texts in topics.items():
        if tier >= 1 and embeddings is not None:
            topic_indices = [i for i, l in enumerate(labels) if l == topic_id]
            topic_embs = embeddings[topic_indices]
            result[topic_id] = extract_keywords_embedding(topic_texts, topic_embs, top_n)
        else:
            result[topic_id] = extract_keywords_yake(topic_texts, top_n)

    return result
