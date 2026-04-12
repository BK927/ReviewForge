PLAYTIME_BINS = [
    {"label": "0-2h", "min": 0, "max": 120},
    {"label": "2-10h", "min": 120, "max": 600},
    {"label": "10-50h", "min": 600, "max": 3000},
    {"label": "50h+", "min": 3000, "max": float("inf")},
]


def _bin_playtime(minutes):
    for b in PLAYTIME_BINS:
        if b["min"] <= minutes < b["max"]:
            return b["label"]
    return "50h+"


def _compute_axis(reviews, bin_fn, pos_topic_map, neg_topic_map, sort_order=None):
    """Compute per-segment topic distribution for a single segment axis."""
    bins = {}
    for r in reviews:
        label = bin_fn(r)
        if label is None:
            continue
        bins.setdefault(label, []).append(r)

    if sort_order:
        order = {label: i for i, label in enumerate(sort_order)}
        sorted_items = sorted(bins.items(), key=lambda x: order.get(x[0], 999))
    else:
        sorted_items = sorted(bins.items(), key=lambda x: x[0])

    segments = []
    for label, entries in sorted_items:
        total = len(entries)
        pos_reviews = [r for r in entries if r["sentiment"] == "positive"]
        neg_reviews = [r for r in entries if r["sentiment"] == "negative"]
        pos_count = len(pos_reviews)
        neg_count = len(neg_reviews)

        # Positive topic distribution
        pos_dist = {}
        for r in pos_reviews:
            tid = r["topic_id"]
            if tid >= 0:
                pos_dist[tid] = pos_dist.get(tid, 0) + 1

        pos_topic_dist = []
        for tid, count in sorted(pos_dist.items(), key=lambda x: -x[1]):
            topic = pos_topic_map.get(tid, {})
            pos_topic_dist.append({
                "topic_id": tid,
                "topic_label": topic.get("label", f"Topic {tid}"),
                "count": count,
                "proportion": count / pos_count if pos_count > 0 else 0,
            })

        # Negative topic distribution
        neg_dist = {}
        for r in neg_reviews:
            tid = r["topic_id"]
            if tid >= 0:
                neg_dist[tid] = neg_dist.get(tid, 0) + 1

        neg_topic_dist = []
        for tid, count in sorted(neg_dist.items(), key=lambda x: -x[1]):
            topic = neg_topic_map.get(tid, {})
            neg_topic_dist.append({
                "topic_id": tid,
                "topic_label": topic.get("label", f"Topic {tid}"),
                "count": count,
                "proportion": count / neg_count if neg_count > 0 else 0,
            })

        segments.append({
            "segment_label": label,
            "total_reviews": total,
            "positive_rate": pos_count / total if total > 0 else 0,
            "positive_topic_distribution": pos_topic_dist,
            "negative_topic_distribution": neg_topic_dist,
        })

    return segments


def compute_segment_topic_cross(reviews, pos_topics, neg_topics):
    """Compute segment x topic cross-analysis across all segment axes.

    Args:
        reviews: list of review dicts, each with keys:
            sentiment ("positive"/"negative"), topic_id (int),
            playtime (int, minutes), language (str),
            steam_deck (bool), steam_purchase (bool), timestamp (int)
        pos_topics: list of positive topic dicts with "id" and "label"
        neg_topics: list of negative topic dicts with "id" and "label"

    Returns:
        dict with keys "playtime", "language", "steam_deck", "purchase_type",
        each mapping to a list of segment dicts.
    """
    if not reviews:
        return {"playtime": [], "language": [], "steam_deck": [], "purchase_type": []}

    pos_topic_map = {t["id"]: t for t in pos_topics}
    neg_topic_map = {t["id"]: t for t in neg_topics}

    result = {}

    # Playtime axis (explicit order to avoid lexicographic sort)
    result["playtime"] = _compute_axis(
        reviews,
        lambda r: _bin_playtime(r.get("playtime", 0)),
        pos_topic_map, neg_topic_map,
        sort_order=[b["label"] for b in PLAYTIME_BINS],
    )

    # Language axis (top 10 by review count)
    lang_counts = {}
    for r in reviews:
        lang = r.get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_langs = set(sorted(lang_counts, key=lang_counts.get, reverse=True)[:10])

    result["language"] = _compute_axis(
        reviews,
        lambda r: r.get("language", "unknown") if r.get("language", "unknown") in top_langs else None,
        pos_topic_map, neg_topic_map,
    )

    # Steam Deck axis
    result["steam_deck"] = _compute_axis(
        reviews,
        lambda r: "Deck" if r.get("steam_deck") else "Non-Deck",
        pos_topic_map, neg_topic_map,
    )

    # Purchase type axis
    result["purchase_type"] = _compute_axis(
        reviews,
        lambda r: "Purchase" if r.get("steam_purchase") else "Free",
        pos_topic_map, neg_topic_map,
    )

    return result
