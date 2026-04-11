import sys
import numpy as np
from protocol import format_progress
from embeddings import generate_embeddings
from clustering import cluster_reviews
from keywords import extract_topic_keywords
from topic_recommendation import recommend_topic_count
from short_review import is_short_review, build_short_review_summary
from topic_merge import merge_similar_topics


def run_analysis(params: dict, msg_id: str) -> dict:
    """Full analysis pipeline: filter short → embed → recommend k → cluster → merge → extract keywords."""
    reviews = params.get("reviews", [])
    config = params.get("config", {})
    tier = config.get("tier", 0)
    n_topics = config.get("n_topics", 8)
    topic_count_mode = str(
        config.get("topicCountMode", config.get("topic_count_mode", "manual"))
    ).lower()
    min_review_words = config.get("min_review_words", 5)
    merge_threshold = config.get("merge_threshold", 0.80)

    if not reviews:
        return {"positive_topics": [], "negative_topics": [],
                "short_review_summary": {"count": 0, "positive_rate": 0.0, "frequent_phrases": []}}

    if tier >= 1:
        topic_count_mode = "auto"

    def progress(pct, msg, stage=None, elapsed_ms=None):
        sys.stdout.write(format_progress(msg_id, pct, msg, stage=stage, elapsed_ms=elapsed_ms) + "\n")
        sys.stdout.flush()

    # --- Step 1: Filter short reviews ---
    long_reviews = []
    short_reviews = []
    for r in reviews:
        lang = r.get("language", "english")
        if is_short_review(r["text"], language=lang, min_words=min_review_words):
            short_reviews.append({"text": r["text"], "voted_up": r["voted_up"]})
        else:
            long_reviews.append(r)

    short_review_summary = build_short_review_summary(short_reviews)

    if len(long_reviews) < 2:
        return {
            "positive_topics": [], "negative_topics": [],
            "short_review_summary": short_review_summary,
            "total_reviews": len(reviews),
            "positive_count": sum(1 for r in reviews if r["voted_up"]),
            "negative_count": sum(1 for r in reviews if not r["voted_up"]),
        }

    # --- Step 2: Split by sentiment ---
    positive = [r for r in long_reviews if r["voted_up"]]
    negative = [r for r in long_reviews if not r["voted_up"]]

    progress(5, "Generating embeddings...", stage="embedding")

    all_texts = [r["text"] for r in long_reviews]
    emb_result = generate_embeddings({"texts": all_texts, "tier": tier}, msg_id)
    all_embeddings = np.array(emb_result["embeddings"])

    # Map back to positive/negative
    pos_indices = [i for i, r in enumerate(long_reviews) if r["voted_up"]]
    neg_indices = [i for i, r in enumerate(long_reviews) if not r["voted_up"]]

    pos_embeddings = all_embeddings[pos_indices] if pos_indices else np.array([])
    neg_embeddings = all_embeddings[neg_indices] if neg_indices else np.array([])

    method = "hdbscan" if tier >= 1 else "kmeans"
    requested_k = int(n_topics) if tier == 0 and topic_count_mode == "manual" else None
    positive_k = requested_k
    negative_k = requested_k
    positive_confidence = None
    negative_confidence = None
    positive_reason = None
    negative_reason = None
    recommendation_details = None

    if tier == 0 and topic_count_mode == "auto":
        progress(60, "Calculating recommended topic count...", stage="recommendation")
        recommendation = recommend_topic_count(pos_embeddings, neg_embeddings)
        positive_k = recommendation["positive_k"]
        negative_k = recommendation["negative_k"]
        positive_confidence = recommendation["positive_confidence"]
        negative_confidence = recommendation["negative_confidence"]
        positive_reason = recommendation["positive_reason"]
        negative_reason = recommendation["negative_reason"]
        recommendation_details = recommendation["details"]
        progress(72, "Clustering reviews...", stage="clustering")
    else:
        progress(60, "Clustering reviews...", stage="clustering")

    if tier == 0 and topic_count_mode == "manual":
        positive_reason = "Using requested topic count"
        negative_reason = "Using requested topic count"
        positive_k = requested_k
        negative_k = requested_k
    elif tier >= 1:
        positive_reason = "Auto by HDBSCAN"
        negative_reason = "Auto by HDBSCAN"

    pos_topics = _analyze_group(
        [r["text"] for r in positive], pos_embeddings,
        method, positive_k if positive_k is not None else n_topics, tier,
        merge_threshold
    ) if positive else ([], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []})

    progress(80, "Extracting keywords...", stage="keywords")

    neg_topics = _analyze_group(
        [r["text"] for r in negative], neg_embeddings,
        method, negative_k if negative_k is not None else n_topics, tier,
        merge_threshold
    ) if negative else ([], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []})

    progress(100, "Analysis complete", stage="complete")

    pos_topic_list, pos_merge_info = pos_topics
    neg_topic_list, neg_merge_info = neg_topics

    return {
        "model": emb_result["model"],
        "tier": tier,
        "total_reviews": len(reviews),
        "positive_count": len(positive) + sum(1 for r in short_reviews if r["voted_up"]),
        "negative_count": len(negative) + sum(1 for r in short_reviews if not r["voted_up"]),
        "topic_count_mode": topic_count_mode,
        "requested_k": requested_k,
        "positive_k": positive_k if tier == 0 else None,
        "negative_k": negative_k if tier == 0 else None,
        "positive_confidence": positive_confidence,
        "negative_confidence": negative_confidence,
        "positive_reason": positive_reason,
        "negative_reason": negative_reason,
        "recommendation_details": recommendation_details,
        "short_review_summary": short_review_summary,
        "merge_info": {
            "positive": pos_merge_info,
            "negative": neg_merge_info,
        },
        "positive_topics": pos_topic_list,
        "negative_topics": neg_topic_list,
    }


def _analyze_group(texts, embeddings, method, n_topics, tier, merge_threshold=0.80):
    if len(texts) < 2:
        return [], {"original_topic_count": 0, "merged_topic_count": 0, "merges": []}

    labels = cluster_reviews(
        embeddings,
        method=method,
        n_clusters=min(n_topics, len(texts)),
        min_cluster_size=3
    )

    # Merge similar topics
    labels, merge_info = merge_similar_topics(embeddings, labels, threshold=merge_threshold)

    topic_keywords = extract_topic_keywords(
        texts, labels, tier=tier,
        embeddings=embeddings if tier >= 1 else None
    )

    topics = []
    for topic_id, keywords in sorted(topic_keywords.items()):
        topic_texts = [t for t, l in zip(texts, labels) if l == topic_id]
        # Prefer bigram+ keyphrases for label
        bigram_kws = [kw for kw, _ in keywords if " " in kw]
        unigram_kws = [kw for kw, _ in keywords if " " not in kw]
        label_parts = (bigram_kws + unigram_kws)[:3]
        label = ", ".join(label_parts) if label_parts else f"Topic {topic_id}"

        topics.append({
            "id": topic_id,
            "keywords": [{"word": kw, "score": round(sc, 3)} for kw, sc in keywords],
            "label": label,
            "review_count": len(topic_texts),
            "sample_reviews": topic_texts[:5]
        })

    topics.sort(key=lambda t: t["review_count"], reverse=True)
    return topics, merge_info
