PRESENCE_THRESHOLD = 0.05


def compute_early_access_comparison(cross_reviews, neg_topics):
    """Compare negative topic distributions between Early Access and Post-Launch.

    Activation: EA reviews >= 50 AND EA ratio >= 10% of total.
    Each negative topic is classified as persistent/resolved/new based on its
    proportion in each period (threshold: 5%).

    Args:
        cross_reviews: list of review dicts with keys:
            early_access (bool), sentiment ("positive"/"negative"), topic_id (int)
        neg_topics: list of negative topic dicts with "id" and "label"

    Returns:
        dict with ea_review_count, post_launch_review_count, lifecycle list.
        None if activation conditions not met or no reviews.
    """
    if not cross_reviews:
        return None

    ea_reviews = [r for r in cross_reviews if r.get("early_access")]
    post_reviews = [r for r in cross_reviews if not r.get("early_access")]

    ea_count = len(ea_reviews)
    total_count = len(cross_reviews)

    # Activation check
    if ea_count < 50 or ea_count / total_count < 0.10:
        return None

    post_count = len(post_reviews)

    # Overall positive rates per period
    ea_pos_rate = sum(1 for r in ea_reviews if r["sentiment"] == "positive") / ea_count
    post_pos_rate = sum(1 for r in post_reviews if r["sentiment"] == "positive") / post_count if post_count > 0 else 0

    # Negative reviews per period
    ea_neg = [r for r in ea_reviews if r["sentiment"] == "negative"]
    post_neg = [r for r in post_reviews if r["sentiment"] == "negative"]
    ea_neg_count = len(ea_neg)
    post_neg_count = len(post_neg)

    neg_topic_map = {t["id"]: t for t in neg_topics}

    # Count per negative topic in each period
    ea_topic_counts = {}
    for r in ea_neg:
        tid = r["topic_id"]
        if tid >= 0:
            ea_topic_counts[tid] = ea_topic_counts.get(tid, 0) + 1

    post_topic_counts = {}
    for r in post_neg:
        tid = r["topic_id"]
        if tid >= 0:
            post_topic_counts[tid] = post_topic_counts.get(tid, 0) + 1

    all_topic_ids = set(ea_topic_counts.keys()) | set(post_topic_counts.keys())

    lifecycle = []
    for tid in sorted(all_topic_ids):
        ea_prop = ea_topic_counts.get(tid, 0) / ea_neg_count if ea_neg_count > 0 else 0
        post_prop = post_topic_counts.get(tid, 0) / post_neg_count if post_neg_count > 0 else 0

        in_ea = ea_prop >= PRESENCE_THRESHOLD
        in_post = post_prop >= PRESENCE_THRESHOLD

        if not in_ea and not in_post:
            continue

        if in_ea and in_post:
            status = "persistent"
        elif in_ea:
            status = "resolved"
        else:
            status = "new"

        topic = neg_topic_map.get(tid, {})
        lifecycle.append({
            "topic_id": tid,
            "topic_label": topic.get("label", f"Topic {tid}"),
            "status": status,
            "ea_proportion": round(ea_prop, 4),
            "post_launch_proportion": round(post_prop, 4),
            "ea_positive_rate": round(ea_pos_rate, 4),
            "post_launch_positive_rate": round(post_pos_rate, 4),
        })

    # Sort: persistent first, then resolved, then new; within group by max proportion desc
    status_order = {"persistent": 0, "resolved": 1, "new": 2}
    lifecycle.sort(key=lambda x: (status_order[x["status"]], -max(x["ea_proportion"], x["post_launch_proportion"])))

    return {
        "ea_review_count": ea_count,
        "post_launch_review_count": post_count,
        "lifecycle": lifecycle,
    }
