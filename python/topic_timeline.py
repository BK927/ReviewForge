from datetime import datetime, timezone


def _period_key_weekly(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _period_key_monthly(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return f"{dt.year}-{dt.month:02d}"


def _compute_periods(reviews, period_fn, pos_topic_map, neg_topic_map):
    """Group reviews by time period and compute topic distributions."""
    bins = {}
    for r in reviews:
        ts = r.get("timestamp")
        if ts is None:
            continue
        key = period_fn(ts)
        bins.setdefault(key, []).append(r)

    periods = []
    for key in sorted(bins.keys()):
        entries = bins[key]
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

        periods.append({
            "period": key,
            "total_reviews": total,
            "positive_rate": pos_count / total if total > 0 else 0,
            "positive_topic_distribution": pos_topic_dist,
            "negative_topic_distribution": neg_topic_dist,
        })

    return periods


def compute_topics_over_time(reviews, pos_topics, neg_topics):
    """Compute topic distributions over time at both weekly and monthly granularity.

    Args:
        reviews: list of review dicts with keys:
            sentiment ("positive"/"negative"), topic_id (int), timestamp (int, unix epoch)
        pos_topics: list of positive topic dicts with "id" and "label"
        neg_topics: list of negative topic dicts with "id" and "label"

    Returns:
        dict with "weekly" and "monthly" keys, each a list of period dicts.
    """
    if not reviews:
        return {"weekly": [], "monthly": []}

    pos_topic_map = {t["id"]: t for t in pos_topics}
    neg_topic_map = {t["id"]: t for t in neg_topics}

    return {
        "weekly": _compute_periods(reviews, _period_key_weekly, pos_topic_map, neg_topic_map),
        "monthly": _compute_periods(reviews, _period_key_monthly, pos_topic_map, neg_topic_map),
    }
