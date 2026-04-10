import sys
import numpy as np
from protocol import format_progress
from embeddings import generate_embeddings
from clustering import cluster_reviews
from keywords import extract_topic_keywords


def run_analysis(params: dict, msg_id: str) -> dict:
    """Full analysis pipeline: embed -> cluster -> extract keywords."""
    reviews = params.get("reviews", [])
    config = params.get("config", {})
    tier = config.get("tier", 0)
    n_topics = config.get("n_topics", 8)

    if not reviews:
        return {"positive_topics": [], "negative_topics": []}

    def progress(pct, msg, stage=None, elapsed_ms=None):
        sys.stdout.write(format_progress(msg_id, pct, msg, stage=stage, elapsed_ms=elapsed_ms) + "\n")
        sys.stdout.flush()

    # Split by sentiment
    positive = [r for r in reviews if r["voted_up"]]
    negative = [r for r in reviews if not r["voted_up"]]

    progress(5, "Generating embeddings...", stage="embedding")

    all_texts = [r["text"] for r in reviews]
    emb_result = generate_embeddings({"texts": all_texts, "tier": tier}, msg_id)
    all_embeddings = np.array(emb_result["embeddings"])

    # Map back to positive/negative
    pos_indices = [i for i, r in enumerate(reviews) if r["voted_up"]]
    neg_indices = [i for i, r in enumerate(reviews) if not r["voted_up"]]

    pos_embeddings = all_embeddings[pos_indices] if pos_indices else np.array([])
    neg_embeddings = all_embeddings[neg_indices] if neg_indices else np.array([])

    progress(60, "Clustering reviews...", stage="clustering")

    method = "hdbscan" if tier >= 1 else "kmeans"

    pos_topics = _analyze_group(
        [r["text"] for r in positive], pos_embeddings,
        method, n_topics, tier
    ) if positive else []

    progress(80, "Extracting keywords...", stage="keywords")

    neg_topics = _analyze_group(
        [r["text"] for r in negative], neg_embeddings,
        method, n_topics, tier
    ) if negative else []

    progress(100, "Analysis complete", stage="complete")

    return {
        "model": emb_result["model"],
        "tier": tier,
        "total_reviews": len(reviews),
        "positive_count": len(positive),
        "negative_count": len(negative),
        "positive_topics": pos_topics,
        "negative_topics": neg_topics
    }


def _analyze_group(texts, embeddings, method, n_topics, tier):
    if len(texts) < 2:
        return []

    labels = cluster_reviews(
        embeddings,
        method=method,
        n_clusters=min(n_topics, len(texts)),
        min_cluster_size=3
    )

    topic_keywords = extract_topic_keywords(
        texts, labels, tier=tier,
        embeddings=embeddings if tier >= 1 else None
    )

    topics = []
    for topic_id, keywords in sorted(topic_keywords.items()):
        topic_texts = [t for t, l in zip(texts, labels) if l == topic_id]
        topics.append({
            "id": topic_id,
            "keywords": [{"word": kw, "score": round(sc, 3)} for kw, sc in keywords],
            "label": ", ".join(kw for kw, _ in keywords[:3]),
            "review_count": len(topic_texts),
            "sample_reviews": topic_texts[:5]
        })

    topics.sort(key=lambda t: t["review_count"], reverse=True)
    return topics
