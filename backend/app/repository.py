from datetime import datetime
import json
from typing import Any

import duckdb

from .db import connect, utcnow
from .models import EventIn, ReportIn


REVIEW_COLUMNS = """
recommendation_id, app_id, author_steamid, language, review, voted_up,
votes_up, votes_funny, weighted_vote_score, playtime_forever,
playtime_at_review, steam_created_at, steam_updated_at, collected_at
"""


def rows_to_dicts(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def dashboard_summary() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                count(*) AS total_reviews,
                count(*) FILTER (WHERE voted_up) AS positive_reviews,
                count(*) FILTER (WHERE NOT voted_up) AS negative_reviews,
                coalesce(avg(CASE WHEN voted_up THEN 1.0 ELSE 0.0 END), 0) AS positive_ratio,
                count(DISTINCT language) AS languages,
                (SELECT count(*) FROM clusters) AS clusters,
                (SELECT count(*) FROM evidence) AS evidence_items,
                max(steam_created_at) AS latest_review_at
            FROM reviews
            """
        ).fetchone()
    keys = [
        "total_reviews",
        "positive_reviews",
        "negative_reviews",
        "positive_ratio",
        "languages",
        "clusters",
        "evidence_items",
        "latest_review_at",
    ]
    return dict(zip(keys, row))


def language_summaries() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                """
                SELECT
                    language,
                    count(*) AS review_count,
                    count(*) FILTER (WHERE voted_up) AS positive_count,
                    count(*) FILTER (WHERE NOT voted_up) AS negative_count,
                    coalesce(avg(CASE WHEN voted_up THEN 1.0 ELSE 0.0 END), 0) AS positive_ratio,
                    coalesce(avg(weighted_vote_score), 0) AS avg_weighted_score
                FROM reviews
                GROUP BY language
                ORDER BY review_count DESC, language
                """
            )
        )


def list_events() -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM events ORDER BY occurred_at DESC, id DESC"))


def create_event(payload: EventIn) -> dict[str, Any]:
    with connect() as conn:
        event_id = conn.execute(
            "INSERT INTO events (title, event_type, description, occurred_at) VALUES (?, ?, ?, ?) RETURNING id",
            [payload.title, payload.event_type, payload.description, payload.occurred_at],
        ).fetchone()[0]
        return rows_to_dicts(conn.execute("SELECT * FROM events WHERE id = ?", [event_id]))[0]


def update_event(event_id: int, payload: EventIn) -> dict[str, Any] | None:
    with connect() as conn:
        conn.execute(
            "UPDATE events SET title = ?, event_type = ?, description = ?, occurred_at = ? WHERE id = ?",
            [payload.title, payload.event_type, payload.description, payload.occurred_at, event_id],
        )
        rows = rows_to_dicts(conn.execute("SELECT * FROM events WHERE id = ?", [event_id]))
        return rows[0] if rows else None


def delete_event(event_id: int) -> bool:
    with connect() as conn:
        before = conn.execute("SELECT count(*) FROM events WHERE id = ?", [event_id]).fetchone()[0]
        conn.execute("DELETE FROM events WHERE id = ?", [event_id])
        return bool(before)


def list_clusters(language: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM clusters"
    params: list[Any] = []
    if language:
        sql += " WHERE language = ? OR language IS NULL"
        params.append(language)
    sql += " ORDER BY review_count DESC, avg_weighted_score DESC, id"
    with connect() as conn:
        return rows_to_dicts(conn.execute(sql, params))


def cluster_reviews(cluster_id: int, limit: int, offset: int) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                f"""
                SELECT {REVIEW_COLUMNS}, rc.score AS cluster_score
                FROM review_clusters rc
                JOIN reviews r ON r.recommendation_id = rc.review_id
                WHERE rc.cluster_id = ?
                ORDER BY rc.score DESC, r.weighted_vote_score DESC
                LIMIT ? OFFSET ?
                """,
                [cluster_id, limit, offset],
            )
        )


def list_evidence(cluster_id: int | None = None, evidence_type: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM evidence"
    clauses = []
    params: list[Any] = []
    if cluster_id is not None:
        clauses.append("cluster_id = ?")
        params.append(cluster_id)
    if evidence_type:
        clauses.append("evidence_type = ?")
        params.append(evidence_type)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC, id DESC"
    with connect() as conn:
        return rows_to_dicts(conn.execute(sql, params))


def list_reports() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM reports ORDER BY created_at DESC, id DESC"))
    for row in rows:
        row["filters"] = _loads(row.get("filters"))
    return rows


def create_report(payload: ReportIn) -> dict[str, Any]:
    with connect() as conn:
        report_id = conn.execute(
            "INSERT INTO reports (title, summary, filters) VALUES (?, ?, ?) RETURNING id",
            [payload.title, payload.summary, json.dumps(payload.filters)],
        ).fetchone()[0]
        row = rows_to_dicts(conn.execute("SELECT * FROM reports WHERE id = ?", [report_id]))[0]
    row["filters"] = _loads(row.get("filters"))
    return row


def list_settings() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM settings ORDER BY key"))
    for row in rows:
        row["value"] = _loads(row.get("value"))
    return rows


def upsert_setting(key: str, value: dict[str, Any]) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            [key, json.dumps(value), utcnow()],
        )
        row = rows_to_dicts(conn.execute("SELECT * FROM settings WHERE key = ?", [key]))[0]
    row["value"] = _loads(row.get("value"))
    return row


def create_job(job_type: str, status: str, message: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    with connect() as conn:
        job_id = conn.execute(
            "INSERT INTO jobs (job_type, status, message, metadata) VALUES (?, ?, ?, ?) RETURNING id",
            [job_type, status, message, json.dumps(metadata or {})],
        ).fetchone()[0]
        return get_job_with_conn(conn, job_id)


def finish_job(job_id: int, status: str, message: str, progress: float = 1, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, message = ?, progress = ?, finished_at = ?, metadata = ?
            WHERE id = ?
            """,
            [status, message, progress, utcnow(), json.dumps(metadata or {}), job_id],
        )
        return get_job_with_conn(conn, job_id)


def list_jobs() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM jobs ORDER BY started_at DESC, id DESC"))
    for row in rows:
        row["metadata"] = _loads(row.get("metadata"))
    return rows


def get_job(job_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM jobs WHERE id = ?", [job_id]))
    if not rows:
        return None
    rows[0]["metadata"] = _loads(rows[0].get("metadata"))
    return rows[0]


def get_job_with_conn(conn: duckdb.DuckDBPyConnection, job_id: int) -> dict[str, Any]:
    row = rows_to_dicts(conn.execute("SELECT * FROM jobs WHERE id = ?", [job_id]))[0]
    row["metadata"] = _loads(row.get("metadata"))
    return row


def upsert_reviews(rows: list[tuple[Any, ...]]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    existing_ids = [row[0] for row in rows]
    with connect() as conn:
        existing = set(
            item[0]
            for item in conn.execute(
                "SELECT recommendation_id FROM reviews WHERE recommendation_id IN (" + ",".join(["?"] * len(existing_ids)) + ")",
                existing_ids,
            ).fetchall()
        )
        conn.executemany(
            """
            INSERT INTO reviews (
                recommendation_id, app_id, author_steamid, language, review, voted_up,
                votes_up, votes_funny, weighted_vote_score, playtime_forever,
                playtime_at_review, steam_created_at, steam_updated_at, collected_at,
                developer_response, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, coalesce(?, current_timestamp), ?, ?)
            ON CONFLICT (recommendation_id) DO UPDATE SET
                language = excluded.language,
                review = excluded.review,
                voted_up = excluded.voted_up,
                votes_up = excluded.votes_up,
                votes_funny = excluded.votes_funny,
                weighted_vote_score = excluded.weighted_vote_score,
                playtime_forever = excluded.playtime_forever,
                playtime_at_review = excluded.playtime_at_review,
                steam_updated_at = excluded.steam_updated_at,
                developer_response = excluded.developer_response,
                raw_json = excluded.raw_json
            """,
            rows,
        )
    updated = len(existing)
    return len(rows) - updated, updated


def rebuild_placeholder_clusters() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM review_clusters")
        conn.execute("DELETE FROM evidence")
        conn.execute("DELETE FROM clusters")
        themes = [
            ("후반 반복성과 보상 밀도", "late|repeat|repetitive|reward|loop|보상|반복|후반", "negative", "장기 플레이에서 반복성, 보상 변화 부족, 루프 피로가 함께 언급됩니다."),
            ("전투 손맛과 보스전 긴장감", "combat|boss|fight|rhythm|전투|보스|손맛", "positive", "무기별 리듬, 보스전 압박감, 전투 감각이 핵심 강점으로 반복됩니다."),
            ("무기 밸런스와 빌드 선택지", "balance|build|weapon choice|weapons fall|narrow|밸런스|빌드|选择|choice", "negative", "패치 이후 특정 무기와 빌드 선택지가 좁아졌다는 반응입니다."),
            ("아트와 캐릭터 매력", "art direction|character art|character|atmosphere|illustration|music|아트|캐릭터|분위기", "positive", "캐릭터 표현, 일러스트, 음악, 분위기가 강점으로 반복 언급됩니다."),
        ]
        for label, pattern, sentiment, summary in themes:
            rows = conn.execute(
                """
                SELECT recommendation_id, language, weighted_vote_score, review
                FROM reviews
                WHERE regexp_matches(lower(review), ?)
                ORDER BY weighted_vote_score DESC
                """,
                [pattern],
            ).fetchall()
            if not rows:
                continue
            avg_score = sum(float(row[2]) for row in rows) / len(rows)
            exemplar = rows[0][0]
            cluster_id = conn.execute(
                """
                INSERT INTO clusters (label, summary, sentiment, language, review_count, avg_weighted_score, exemplar_review_id)
                VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id
                """,
                [
                    label,
                    summary,
                    sentiment,
                    None,
                    len(rows),
                    avg_score,
                    exemplar,
                ],
            ).fetchone()[0]
            conn.executemany(
                "INSERT INTO review_clusters (review_id, cluster_id, score) VALUES (?, ?, ?)",
                [(row[0], cluster_id, 1.0) for row in rows],
            )
            conn.execute(
                "INSERT INTO evidence (review_id, cluster_id, quote, evidence_type, note) VALUES (?, ?, ?, ?, ?)",
                [exemplar, cluster_id, rows[0][3][:240], "placeholder", f"Auto-selected exemplar for {label}"],
            )


def _loads(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return json.loads(str(value))
