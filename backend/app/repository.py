from datetime import datetime, timedelta
import json
from typing import Any

import duckdb

from .db import connect, utcnow
from .config import get_settings
from .models import EventIn, GameIn, GameUpdate, ReportIn


REVIEW_COLUMNS = """
recommendation_id, app_id, author_steamid, language, review, voted_up,
votes_up, votes_funny, weighted_vote_score, playtime_forever,
playtime_at_review, steam_created_at, steam_updated_at, collected_at
"""


def rows_to_dicts(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def default_app_id() -> str:
    return get_settings().steam_app_id


def resolve_app_id(app_id: str | None) -> str:
    return app_id or default_app_id()


def default_game_name(app_id: str) -> str:
    if app_id == "1145350":
        return "Hades II"
    return f"Steam App {app_id}"


def _ensure_game_with_conn(conn: duckdb.DuckDBPyConnection, app_id: str, name: str | None = None) -> None:
    now = utcnow()
    conn.execute(
        """
        INSERT INTO games (app_id, name, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (app_id) DO NOTHING
        """,
        [app_id, name or default_game_name(app_id), json.dumps([]), now, now],
    )


def ensure_game(app_id: str, name: str | None = None) -> dict[str, Any]:
    with connect() as conn:
        _ensure_game_with_conn(conn, app_id, name)
        return _game_detail_with_conn(conn, app_id)


def list_games() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT
                    g.app_id,
                    g.name,
                    g.short_name,
                    g.note,
                    g.tags,
                    g.status AS stored_status,
                    g.created_at,
                    g.updated_at,
                    g.last_refreshed_at,
                    count(r.recommendation_id) AS review_count,
                    count(DISTINCT r.language) AS language_count,
                    avg(CASE WHEN r.voted_up THEN 1.0 ELSE 0.0 END) AS positive_ratio,
                    max(coalesce(r.steam_created_at, r.collected_at)) AS latest_review_at
                FROM games g
                LEFT JOIN reviews r ON r.app_id = g.app_id
                GROUP BY g.app_id, g.name, g.short_name, g.note, g.tags, g.status, g.created_at, g.updated_at, g.last_refreshed_at
                ORDER BY g.updated_at DESC, g.app_id
                """
            )
        )
        return [_hydrate_game_row(conn, row) for row in rows]


def get_game(app_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        rows = rows_to_dicts(conn.execute(_game_detail_sql(), [app_id]))
        return _hydrate_game_row(conn, rows[0]) if rows else None


def create_game(payload: GameIn) -> dict[str, Any] | None:
    with connect() as conn:
        if conn.execute("SELECT 1 FROM games WHERE app_id = ?", [payload.app_id]).fetchone():
            return None
        _ensure_game_with_conn(conn, payload.app_id, payload.name)
        conn.execute(
            """
            UPDATE games
            SET short_name = ?, note = ?, tags = ?, status = ?, updated_at = ?
            WHERE app_id = ?
            """,
            [
                payload.short_name,
                payload.note,
                json.dumps(payload.tags),
                payload.status,
                utcnow(),
                payload.app_id,
            ],
        )
        return _game_detail_with_conn(conn, payload.app_id)


def update_game(app_id: str, payload: GameUpdate) -> dict[str, Any] | None:
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM games WHERE app_id = ?", [app_id]).fetchone():
            return None
        updates = payload.model_dump(exclude_unset=True)
        if updates:
            assignments = []
            params: list[Any] = []
            for key, value in updates.items():
                assignments.append(f"{key} = ?")
                params.append(json.dumps(value) if key == "tags" else value)
            assignments.append("updated_at = ?")
            params.extend([utcnow(), app_id])
            conn.execute(
                f"UPDATE games SET {', '.join(assignments)} WHERE app_id = ?",
                params,
            )
        return _game_detail_with_conn(conn, app_id)


def delete_game(app_id: str) -> bool:
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM games WHERE app_id = ?", [app_id]).fetchone():
            return False
        review_ids = [
            row[0]
            for row in conn.execute(
                "SELECT recommendation_id FROM reviews WHERE app_id = ?",
                [app_id],
            ).fetchall()
        ]
        run_ids = [row[0] for row in conn.execute("SELECT id FROM analysis_runs WHERE app_id = ?", [app_id]).fetchall()]

        if review_ids:
            placeholders = ",".join(["?"] * len(review_ids))
            conn.execute(f"DELETE FROM review_embeddings WHERE review_id IN ({placeholders})", review_ids)
            conn.execute(f"DELETE FROM review_clusters WHERE review_id IN ({placeholders})", review_ids)
            conn.execute(f"DELETE FROM evidence WHERE review_id IN ({placeholders})", review_ids)
        if run_ids:
            placeholders = ",".join(["?"] * len(run_ids))
            cluster_ids = [
                row[0]
                for row in conn.execute(
                    f"SELECT id FROM clusters WHERE analysis_run_id IN ({placeholders})",
                    run_ids,
                ).fetchall()
            ]
            if cluster_ids:
                cluster_placeholders = ",".join(["?"] * len(cluster_ids))
                conn.execute(f"DELETE FROM review_clusters WHERE cluster_id IN ({cluster_placeholders})", cluster_ids)
                conn.execute(f"DELETE FROM evidence WHERE cluster_id IN ({cluster_placeholders})", cluster_ids)
                conn.execute(f"DELETE FROM claims WHERE cluster_id IN ({cluster_placeholders})", cluster_ids)
                conn.execute(f"DELETE FROM cluster_insights WHERE cluster_id IN ({cluster_placeholders})", cluster_ids)
            conn.execute(f"DELETE FROM clusters WHERE analysis_run_id IN ({placeholders})", run_ids)
            conn.execute(f"DELETE FROM evidence WHERE analysis_run_id IN ({placeholders})", run_ids)
            conn.execute(f"DELETE FROM claims WHERE analysis_run_id IN ({placeholders})", run_ids)
            conn.execute(f"DELETE FROM review_quality WHERE analysis_run_id IN ({placeholders})", run_ids)
            conn.execute(f"DELETE FROM reports WHERE analysis_run_id IN ({placeholders})", run_ids)
            conn.execute(f"DELETE FROM analysis_runs WHERE id IN ({placeholders})", run_ids)

        if app_id == default_app_id():
            seed_cluster_ids = [
                row[0]
                for row in conn.execute(
                    "SELECT id FROM clusters WHERE analysis_run_id IS NULL",
                ).fetchall()
            ]
            if seed_cluster_ids:
                placeholders = ",".join(["?"] * len(seed_cluster_ids))
                conn.execute(f"DELETE FROM review_clusters WHERE cluster_id IN ({placeholders})", seed_cluster_ids)
                conn.execute(f"DELETE FROM evidence WHERE cluster_id IN ({placeholders})", seed_cluster_ids)
                conn.execute(f"DELETE FROM claims WHERE cluster_id IN ({placeholders})", seed_cluster_ids)
                conn.execute(f"DELETE FROM cluster_insights WHERE cluster_id IN ({placeholders})", seed_cluster_ids)
            conn.execute("DELETE FROM evidence WHERE analysis_run_id IS NULL")
            conn.execute("DELETE FROM claims WHERE analysis_run_id IS NULL")
            conn.execute("DELETE FROM clusters WHERE analysis_run_id IS NULL")

        conn.execute("DELETE FROM reports WHERE app_id = ?", [app_id])
        conn.execute("DELETE FROM events WHERE app_id = ?", [app_id])
        conn.execute("DELETE FROM reviews WHERE app_id = ?", [app_id])
        conn.execute("DELETE FROM games WHERE app_id = ?", [app_id])
        return True


def mark_game_refreshed(app_id: str) -> None:
    now = utcnow()
    with connect() as conn:
        _ensure_game_with_conn(conn, app_id)
        conn.execute(
            "UPDATE games SET last_refreshed_at = ?, updated_at = ? WHERE app_id = ?",
            [now, now, app_id],
        )


def _game_detail_sql() -> str:
    return """
        SELECT
            g.app_id,
            g.name,
            g.short_name,
            g.note,
            g.tags,
            g.status AS stored_status,
            g.created_at,
            g.updated_at,
            g.last_refreshed_at,
            count(r.recommendation_id) AS review_count,
            count(DISTINCT r.language) AS language_count,
            avg(CASE WHEN r.voted_up THEN 1.0 ELSE 0.0 END) AS positive_ratio,
            max(coalesce(r.steam_created_at, r.collected_at)) AS latest_review_at
        FROM games g
        LEFT JOIN reviews r ON r.app_id = g.app_id
        WHERE g.app_id = ?
        GROUP BY g.app_id, g.name, g.short_name, g.note, g.tags, g.status, g.created_at, g.updated_at, g.last_refreshed_at
    """


def _game_detail_with_conn(conn: duckdb.DuckDBPyConnection, app_id: str) -> dict[str, Any]:
    return _hydrate_game_row(conn, rows_to_dicts(conn.execute(_game_detail_sql(), [app_id]))[0])


def _hydrate_game_row(conn: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> dict[str, Any]:
    app_id = str(row["app_id"])
    latest_run_id = _latest_completed_analysis_run_id(conn, app_id)
    if latest_run_id is not None:
        cluster_count = conn.execute("SELECT count(*) FROM clusters WHERE analysis_run_id = ?", [latest_run_id]).fetchone()[0]
        evidence_count = conn.execute("SELECT count(*) FROM evidence WHERE analysis_run_id = ?", [latest_run_id]).fetchone()[0]
        last_analysis_at = conn.execute(
            "SELECT coalesce(finished_at, started_at) FROM analysis_runs WHERE id = ?",
            [latest_run_id],
        ).fetchone()[0]
    elif app_id == default_app_id():
        cluster_count = conn.execute("SELECT count(*) FROM clusters WHERE analysis_run_id IS NULL").fetchone()[0]
        evidence_count = conn.execute("SELECT count(*) FROM evidence WHERE analysis_run_id IS NULL").fetchone()[0]
        last_analysis_at = None
    else:
        cluster_count = 0
        evidence_count = 0
        last_analysis_at = None

    review_count = int(row.get("review_count") or 0)
    status = row.get("stored_status") or _game_status(review_count, int(cluster_count))
    next_action = _next_game_action(review_count, int(cluster_count), str(status))
    row["status"] = status
    row["next_action"] = next_action
    row["short_name"] = row.get("short_name") or _short_name(row.get("name") or app_id)
    row["note"] = row.get("note")
    row["tags"] = _load_tags(row.get("tags")) or _default_tags(next_action)
    row["language_count"] = int(row.get("language_count") or 0)
    row["positive_ratio"] = row.get("positive_ratio")
    row["cluster_count"] = int(cluster_count)
    row["evidence_count"] = int(evidence_count)
    row["last_sync_at"] = row.get("last_refreshed_at") or row.get("latest_review_at")
    row["last_analysis_at"] = last_analysis_at
    row.pop("stored_status", None)
    return row


def _game_status(review_count: int, cluster_count: int) -> str:
    if review_count <= 0:
        return "needs_sync"
    if cluster_count <= 0:
        return "needs_analysis"
    return "ready"


def _next_game_action(review_count: int, cluster_count: int, status: str) -> str:
    normalized = status.lower()
    if normalized in {"watch", "ready", "analyzed"}:
        return "open"
    if review_count <= 0 or normalized == "needs_sync":
        return "sync"
    if cluster_count <= 0 or normalized == "needs_analysis":
        return "analyze"
    return "open"


def _default_tags(next_action: str) -> list[str]:
    if next_action == "sync":
        return ["수집 필요"]
    if next_action == "analyze":
        return ["분석 대기"]
    return ["분석 완료"]


def _short_name(value: str) -> str:
    parts = [part for part in value.replace(":", " ").replace("-", " ").split() if part]
    compact = "".join(part[0] for part in parts)[:3].upper()
    return compact or value[:3].upper()


def _load_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def dashboard_summary(app_id: str | None = None) -> dict[str, Any]:
    resolved_app_id = resolve_app_id(app_id)
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
            WHERE app_id = ?
            """,
            [resolved_app_id],
        ).fetchone()
        latest_run_id = _latest_completed_analysis_run_id(conn, resolved_app_id)
        if latest_run_id is not None:
            clusters = conn.execute(
                "SELECT count(*) FROM clusters WHERE analysis_run_id = ?",
                [latest_run_id],
            ).fetchone()[0]
            evidence_items = conn.execute(
                "SELECT count(*) FROM evidence WHERE analysis_run_id = ?",
                [latest_run_id],
            ).fetchone()[0]
        elif resolved_app_id == default_app_id():
            clusters = conn.execute("SELECT count(*) FROM clusters WHERE analysis_run_id IS NULL").fetchone()[0]
            evidence_items = conn.execute("SELECT count(*) FROM evidence WHERE analysis_run_id IS NULL").fetchone()[0]
        else:
            clusters = 0
            evidence_items = 0
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
    data = dict(zip(keys, row))
    data["clusters"] = clusters
    data["evidence_items"] = evidence_items
    return data


def language_summaries(app_id: str | None = None) -> list[dict[str, Any]]:
    resolved_app_id = resolve_app_id(app_id)
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
                WHERE app_id = ?
                GROUP BY language
                ORDER BY review_count DESC, language
                """,
                [resolved_app_id],
            )
        )


def list_events(app_id: str | None = None) -> list[dict[str, Any]]:
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                "SELECT * FROM events WHERE app_id = ? ORDER BY occurred_at DESC, id DESC",
                [resolved_app_id],
            )
        )


def create_event(payload: EventIn) -> dict[str, Any]:
    app_id = resolve_app_id(payload.app_id)
    with connect() as conn:
        _ensure_game_with_conn(conn, app_id)
        event_id = conn.execute(
            """
            INSERT INTO events (app_id, title, event_type, description, occurred_at)
            VALUES (?, ?, ?, ?, ?) RETURNING id
            """,
            [app_id, payload.title, payload.event_type, payload.description, payload.occurred_at],
        ).fetchone()[0]
        return rows_to_dicts(conn.execute("SELECT * FROM events WHERE id = ?", [event_id]))[0]


def update_event(event_id: int, payload: EventIn) -> dict[str, Any] | None:
    app_id = resolve_app_id(payload.app_id)
    with connect() as conn:
        _ensure_game_with_conn(conn, app_id)
        conn.execute(
            """
            UPDATE events
            SET app_id = ?, title = ?, event_type = ?, description = ?, occurred_at = ?
            WHERE id = ?
            """,
            [app_id, payload.title, payload.event_type, payload.description, payload.occurred_at, event_id],
        )
        rows = rows_to_dicts(conn.execute("SELECT * FROM events WHERE id = ?", [event_id]))
        return rows[0] if rows else None


def delete_event(event_id: int) -> bool:
    with connect() as conn:
        before = conn.execute("SELECT count(*) FROM events WHERE id = ?", [event_id]).fetchone()[0]
        conn.execute("DELETE FROM events WHERE id = ?", [event_id])
        return bool(before)


def _latest_completed_analysis_run_id(conn: duckdb.DuckDBPyConnection, app_id: str | None = None) -> int | None:
    clauses = [
        "status = 'succeeded'",
        "EXISTS (SELECT 1 FROM clusters c WHERE c.analysis_run_id = analysis_runs.id)",
    ]
    params: list[Any] = []
    if app_id:
        clauses.append("app_id = ?")
        params.append(app_id)
    row = conn.execute(
        f"""
        SELECT id
        FROM analysis_runs
        WHERE {" AND ".join(clauses)}
        ORDER BY coalesce(finished_at, started_at) DESC, id DESC
        LIMIT 1
        """,
        params,
    ).fetchone()
    return int(row[0]) if row else None


def list_clusters(language: str | None = None, app_id: str | None = None) -> list[dict[str, Any]]:
    sql = """
        SELECT
            c.*,
            ci.title AS insight_title,
            ci.summary AS insight_summary,
            ci.praise,
            ci.pain_point,
            ci.planner_action,
            ci.marketing_angle,
            ci.confidence,
            ci.warnings
        FROM clusters c
        LEFT JOIN cluster_insights ci ON ci.cluster_id = c.id
    """
    clauses = []
    params: list[Any] = []
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        latest_run_id = _latest_completed_analysis_run_id(conn, resolved_app_id)
        if latest_run_id is not None:
            clauses.append("c.analysis_run_id = ?")
            params.append(latest_run_id)
        elif resolved_app_id == default_app_id():
            clauses.append("c.analysis_run_id IS NULL")
        else:
            return []
        if language:
            clauses.append("(c.language = ? OR c.language IS NULL)")
            params.append(language)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY c.review_count DESC, c.avg_weighted_score DESC, c.id"
        rows = rows_to_dicts(conn.execute(sql, params))
    return [_hydrate_cluster_row(row) for row in rows]


def cluster_reviews(cluster_id: int, limit: int, offset: int, sample: str = "representative") -> list[dict[str, Any]]:
    order_specs = {
        "representative": (
            "rc.score DESC, coalesce(rq.quality_score, 0.5) DESC, r.weighted_vote_score DESC",
            "cluster_score DESC, coalesce(quality_score, 0.5) DESC, weighted_vote_score DESC",
        ),
        "complaint": (
            "CASE WHEN NOT r.voted_up THEN 1 ELSE 0 END DESC, coalesce(rq.quality_score, 0.5) DESC, r.weighted_vote_score DESC",
            "CASE WHEN NOT voted_up THEN 1 ELSE 0 END DESC, coalesce(quality_score, 0.5) DESC, weighted_vote_score DESC",
        ),
        "praise": (
            "CASE WHEN r.voted_up THEN 1 ELSE 0 END DESC, coalesce(rq.quality_score, 0.5) DESC, r.weighted_vote_score DESC",
            "CASE WHEN voted_up THEN 1 ELSE 0 END DESC, coalesce(quality_score, 0.5) DESC, weighted_vote_score DESC",
        ),
        "recent": (
            "coalesce(r.steam_created_at, r.collected_at) DESC, coalesce(rq.quality_score, 0.5) DESC",
            "coalesce(steam_created_at, collected_at) DESC, coalesce(quality_score, 0.5) DESC",
        ),
        "high_weight": (
            "r.weighted_vote_score DESC, coalesce(rq.quality_score, 0.5) DESC",
            "weighted_vote_score DESC, coalesce(quality_score, 0.5) DESC",
        ),
        "raw": (
            "rc.score DESC, r.weighted_vote_score DESC",
            "cluster_score DESC, weighted_vote_score DESC",
        ),
    }
    order_by, outer_order_by = order_specs.get(sample, order_specs["representative"])
    qualified_review_columns = ", ".join(f"r.{column.strip()}" for column in REVIEW_COLUMNS.replace("\n", " ").split(",") if column.strip())
    dedupe_clause = ""
    params: list[Any] = [cluster_id]
    if sample != "raw":
        dedupe_clause = "WHERE duplicate_rank = 1"
    params.extend([limit, offset])
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                f"""
                WITH ranked AS (
                    SELECT
                        {qualified_review_columns},
                        rc.score AS cluster_score,
                        rq.quality_score,
                        rq.quality_flags,
                        rq.duplicate_count,
                        row_number() OVER (
                            PARTITION BY coalesce(rq.text_hash, r.recommendation_id)
                            ORDER BY {order_by}
                        ) AS duplicate_rank
                    FROM review_clusters rc
                    JOIN reviews r ON r.recommendation_id = rc.review_id
                    LEFT JOIN review_quality rq
                        ON rq.review_id = r.recommendation_id
                       AND rq.analysis_run_id = (
                            SELECT analysis_run_id FROM clusters WHERE id = rc.cluster_id
                       )
                    WHERE rc.cluster_id = ?
                )
                SELECT * EXCLUDE (duplicate_rank)
                FROM ranked
                {dedupe_clause}
                ORDER BY {outer_order_by}
                LIMIT ? OFFSET ?
                """,
                params,
            )
        )
    for row in rows:
        row["quality_flags"] = _loads_list(row.get("quality_flags"))
    return rows


def list_evidence(
    cluster_id: int | None = None,
    evidence_type: str | None = None,
    app_id: str | None = None,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            e.*,
            c.claim_text,
            c.claim_type
        FROM evidence e
        LEFT JOIN claims c ON c.id = e.claim_id
    """
    clauses = []
    params: list[Any] = []
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        latest_run_id = _latest_completed_analysis_run_id(conn, resolved_app_id)
        if latest_run_id is not None:
            clauses.append("e.analysis_run_id = ?")
            params.append(latest_run_id)
        elif resolved_app_id == default_app_id():
            clauses.append("e.analysis_run_id IS NULL")
        else:
            return []
        if cluster_id is not None:
            clauses.append("e.cluster_id = ?")
            params.append(cluster_id)
        if evidence_type:
            clauses.append("e.evidence_type = ?")
            params.append(evidence_type)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY e.created_at DESC, e.id DESC"
        return rows_to_dicts(conn.execute(sql, params))


def list_claims(app_id: str | None = None, cluster_id: int | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM claims"
    clauses = []
    params: list[Any] = []
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        latest_run_id = _latest_completed_analysis_run_id(conn, resolved_app_id)
        if latest_run_id is not None:
            clauses.append("analysis_run_id = ?")
            params.append(latest_run_id)
        elif resolved_app_id == default_app_id():
            clauses.append("analysis_run_id IS NULL")
        else:
            return []
        if cluster_id is not None:
            clauses.append("cluster_id = ?")
            params.append(cluster_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY confidence DESC, created_at DESC, id DESC"
        return rows_to_dicts(conn.execute(sql, params))


def list_reports(app_id: str | None = None) -> list[dict[str, Any]]:
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                "SELECT * FROM reports WHERE app_id = ? ORDER BY created_at DESC, id DESC",
                [resolved_app_id],
            )
        )
    for row in rows:
        row["filters"] = _loads(row.get("filters"))
    return rows


def create_report(payload: ReportIn) -> dict[str, Any]:
    app_id = resolve_app_id(payload.app_id)
    filters = {**payload.filters, "app_id": app_id}
    with connect() as conn:
        _ensure_game_with_conn(conn, app_id)
        report_id = conn.execute(
            "INSERT INTO reports (app_id, title, summary, filters) VALUES (?, ?, ?, ?) RETURNING id",
            [app_id, payload.title, payload.summary, json.dumps(filters)],
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


def update_job(
    job_id: int,
    status: str,
    message: str,
    progress: float,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, message = ?, progress = ?, metadata = ?
            WHERE id = ?
            """,
            [status, message, progress, json.dumps(metadata or {}), job_id],
        )
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


def create_analysis_run(app_id: str | None, params: dict[str, Any]) -> dict[str, Any]:
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        _ensure_game_with_conn(conn, resolved_app_id)
        run_id = conn.execute(
            """
            INSERT INTO analysis_runs (app_id, status, progress, message, params)
            VALUES (?, 'running', 0, 'Analysis started', ?) RETURNING id
            """,
            [resolved_app_id, json.dumps(params)],
        ).fetchone()[0]
        return get_analysis_run_with_conn(conn, run_id)


def update_analysis_run(
    run_id: int,
    *,
    status: str,
    progress: float,
    message: str,
    finished: bool = False,
) -> dict[str, Any]:
    with connect() as conn:
        if finished:
            conn.execute(
                """
                UPDATE analysis_runs
                SET status = ?, progress = ?, message = ?, finished_at = ?
                WHERE id = ?
                """,
                [status, progress, message, utcnow(), run_id],
            )
        else:
            conn.execute(
                "UPDATE analysis_runs SET status = ?, progress = ?, message = ? WHERE id = ?",
                [status, progress, message, run_id],
            )
        return get_analysis_run_with_conn(conn, run_id)


def scope_analysis_run_outputs(run_id: int, app_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE reports SET app_id = ? WHERE analysis_run_id = ? AND app_id IS NULL",
            [app_id, run_id],
        )


def list_analysis_runs(app_id: str | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM analysis_runs"
    params: list[Any] = []
    if app_id:
        sql += " WHERE app_id = ?"
        params.append(app_id)
    sql += " ORDER BY started_at DESC, id DESC"
    with connect() as conn:
        rows = rows_to_dicts(conn.execute(sql, params))
    for row in rows:
        row["params"] = _loads(row.get("params"))
    return rows


def get_analysis_run(run_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM analysis_runs WHERE id = ?", [run_id]))
    if not rows:
        return None
    rows[0]["params"] = _loads(rows[0].get("params"))
    return rows[0]


def get_analysis_run_with_conn(conn: duckdb.DuckDBPyConnection, run_id: int) -> dict[str, Any]:
    row = rows_to_dicts(conn.execute("SELECT * FROM analysis_runs WHERE id = ?", [run_id]))[0]
    row["params"] = _loads(row.get("params"))
    return row


def review_timeline(
    *,
    app_id: str | None = None,
    bucket: str = "day",
    language: str | None = None,
    playtime_min: int | None = None,
    playtime_max: int | None = None,
) -> list[dict[str, Any]]:
    if bucket not in {"day", "week", "month"}:
        raise ValueError("bucket must be day, week, or month")
    resolved_app_id = resolve_app_id(app_id)
    time_expr = "coalesce(steam_created_at, collected_at)"
    clauses = [f"{time_expr} IS NOT NULL"]
    params: list[Any] = []
    clauses.append("app_id = ?")
    params.append(resolved_app_id)
    if language:
        clauses.append("language = ?")
        params.append(language)
    if playtime_min is not None:
        clauses.append("playtime_at_review >= ?")
        params.append(playtime_min)
    if playtime_max is not None:
        clauses.append("playtime_at_review <= ?")
        params.append(playtime_max)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                f"""
                SELECT
                    date_trunc('{bucket}', {time_expr}) AS bucket_start,
                    count(*) AS review_count,
                    count(*) FILTER (WHERE voted_up) AS positive_count,
                    count(*) FILTER (WHERE NOT voted_up) AS negative_count,
                    coalesce(avg(CASE WHEN voted_up THEN 1.0 ELSE 0.0 END), 0) AS positive_ratio,
                    coalesce(avg(weighted_vote_score), 0) AS avg_weighted_score
                FROM reviews
                WHERE {" AND ".join(clauses)}
                GROUP BY bucket_start
                ORDER BY bucket_start
                """,
                params,
            )
        )


def event_impact(event_id: int, window_days: int = 14, app_id: str | None = None) -> dict[str, Any] | None:
    with connect() as conn:
        event_rows = rows_to_dicts(conn.execute("SELECT * FROM events WHERE id = ?", [event_id]))
        if not event_rows:
            return None
        event = event_rows[0]
        resolved_app_id = resolve_app_id(app_id or event.get("app_id"))
        occurred_at = event["occurred_at"]
        before_start = occurred_at - timedelta(days=window_days)
        after_end = occurred_at + timedelta(days=window_days)
        before = _impact_window(conn, before_start, occurred_at, resolved_app_id)
        after = _impact_window(conn, occurred_at, after_end, resolved_app_id)
    return {
        "event": event,
        "window_days": window_days,
        "before": before,
        "after": after,
        "delta": {
            "review_count": float(after["review_count"] - before["review_count"]),
            "positive_ratio": float(after["positive_ratio"] - before["positive_ratio"]),
            "avg_weighted_score": float(after["avg_weighted_score"] - before["avg_weighted_score"]),
        },
    }


def _impact_window(
    conn: duckdb.DuckDBPyConnection,
    start_at: datetime,
    end_at: datetime,
    app_id: str | None,
) -> dict[str, Any]:
    time_expr = "coalesce(steam_created_at, collected_at)"
    clauses = [f"{time_expr} >= ?", f"{time_expr} < ?"]
    params: list[Any] = [start_at, end_at]
    if app_id:
        clauses.append("app_id = ?")
        params.append(app_id)
    row = conn.execute(
        f"""
        SELECT
            count(*) AS review_count,
            count(*) FILTER (WHERE voted_up) AS positive_count,
            count(*) FILTER (WHERE NOT voted_up) AS negative_count,
            coalesce(avg(CASE WHEN voted_up THEN 1.0 ELSE 0.0 END), 0) AS positive_ratio,
            coalesce(avg(weighted_vote_score), 0) AS avg_weighted_score
        FROM reviews
        WHERE {" AND ".join(clauses)}
        """,
        params,
    ).fetchone()
    keys = ["review_count", "positive_count", "negative_count", "positive_ratio", "avg_weighted_score"]
    return dict(zip(keys, row))


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
        for app_id in sorted({str(row[1]) for row in rows if row[1]}):
            _ensure_game_with_conn(conn, app_id)
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
        conn.execute("DELETE FROM claims")
        conn.execute("DELETE FROM cluster_insights")
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


def _loads_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _hydrate_cluster_row(row: dict[str, Any]) -> dict[str, Any]:
    top_keywords = _loads_list(row.get("top_keywords"))
    warnings = _loads_list(row.get("warnings"))
    insight = None
    if row.get("insight_title") or row.get("insight_summary"):
        insight = {
            "title": row.pop("insight_title", None),
            "summary": row.pop("insight_summary", None),
            "praise": row.pop("praise", None),
            "pain_point": row.pop("pain_point", None),
            "planner_action": row.pop("planner_action", None),
            "marketing_angle": row.pop("marketing_angle", None),
            "confidence": row.pop("confidence", None),
            "warnings": warnings,
        }
    else:
        for key in ["insight_title", "insight_summary", "praise", "pain_point", "planner_action", "marketing_angle", "confidence"]:
            row.pop(key, None)
    row.pop("warnings", None)
    row["top_keywords"] = top_keywords
    row["insight"] = insight
    return row
