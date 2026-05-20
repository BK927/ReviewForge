from datetime import datetime, timedelta
import json
from typing import Any

import duckdb

from .db import connect, utcnow
from .config import get_settings
from .models import AxisIn, AxisUpdate, EventIn, GameIn, GameUpdate, ReportIn


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
            conn.execute(f"DELETE FROM issue_evidence WHERE review_id IN ({placeholders})", review_ids)
            conn.execute(f"DELETE FROM issue_units WHERE review_id IN ({placeholders})", review_ids)
        if run_ids:
            placeholders = ",".join(["?"] * len(run_ids))
            issue_ids = [
                row[0]
                for row in conn.execute(
                    f"SELECT id FROM issues WHERE analysis_run_id IN ({placeholders})",
                    run_ids,
                ).fetchall()
            ]
            if issue_ids:
                issue_placeholders = ",".join(["?"] * len(issue_ids))
                conn.execute(f"DELETE FROM issue_evidence WHERE issue_id IN ({issue_placeholders})", issue_ids)
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
            conn.execute(f"DELETE FROM issue_evidence WHERE analysis_run_id IN ({placeholders})", run_ids)
            conn.execute(f"DELETE FROM issue_units WHERE analysis_run_id IN ({placeholders})", run_ids)
            conn.execute(f"DELETE FROM issues WHERE analysis_run_id IN ({placeholders})", run_ids)
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
            conn.execute("DELETE FROM issue_evidence WHERE analysis_run_id IS NULL")
            conn.execute("DELETE FROM issue_units WHERE analysis_run_id IS NULL")
            conn.execute("DELETE FROM issues WHERE analysis_run_id IS NULL")

        conn.execute("DELETE FROM reports WHERE app_id = ?", [app_id])
        conn.execute("DELETE FROM events WHERE app_id = ?", [app_id])
        conn.execute("DELETE FROM axis_suggestions WHERE app_id = ?", [app_id])
        conn.execute("DELETE FROM analysis_axes WHERE app_id = ?", [app_id])
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
        issue_count = conn.execute("SELECT count(*) FROM issues WHERE analysis_run_id = ?", [latest_run_id]).fetchone()[0]
        confirmed_issue_count = conn.execute(
            "SELECT count(*) FROM issues WHERE analysis_run_id = ? AND status IN ('confirmed', 'strength')",
            [latest_run_id],
        ).fetchone()[0]
        last_analysis_at = conn.execute(
            "SELECT coalesce(finished_at, started_at) FROM analysis_runs WHERE id = ?",
            [latest_run_id],
        ).fetchone()[0]
    elif app_id == default_app_id():
        cluster_count = conn.execute("SELECT count(*) FROM clusters WHERE analysis_run_id IS NULL").fetchone()[0]
        evidence_count = conn.execute("SELECT count(*) FROM evidence WHERE analysis_run_id IS NULL").fetchone()[0]
        issue_count = 0
        confirmed_issue_count = 0
        last_analysis_at = None
    else:
        cluster_count = 0
        evidence_count = 0
        issue_count = 0
        confirmed_issue_count = 0
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
    row["issue_count"] = int(issue_count)
    row["confirmed_issue_count"] = int(confirmed_issue_count)
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
            issues = conn.execute(
                "SELECT count(*) FROM issues WHERE analysis_run_id = ?",
                [latest_run_id],
            ).fetchone()[0]
            confirmed_issues = conn.execute(
                "SELECT count(*) FROM issues WHERE analysis_run_id = ? AND status IN ('confirmed', 'strength')",
                [latest_run_id],
            ).fetchone()[0]
            issue_evidence_items = conn.execute(
                "SELECT count(*) FROM issue_evidence WHERE analysis_run_id = ?",
                [latest_run_id],
            ).fetchone()[0]
            assigned_negative = conn.execute(
                """
                SELECT count(DISTINCT review_id)
                FROM issue_units
                WHERE analysis_run_id = ?
                  AND voted_up = false
                  AND NOT is_quarantined
                  AND intent IN ('complaint', 'request', 'bug')
                """,
                [latest_run_id],
            ).fetchone()[0]
        elif resolved_app_id == default_app_id():
            clusters = conn.execute("SELECT count(*) FROM clusters WHERE analysis_run_id IS NULL").fetchone()[0]
            evidence_items = conn.execute("SELECT count(*) FROM evidence WHERE analysis_run_id IS NULL").fetchone()[0]
            issues = 0
            confirmed_issues = 0
            issue_evidence_items = 0
            assigned_negative = 0
        else:
            clusters = 0
            evidence_items = 0
            issues = 0
            confirmed_issues = 0
            issue_evidence_items = 0
            assigned_negative = 0
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
    data["issues"] = int(issues)
    data["confirmed_issues"] = int(confirmed_issues)
    data["issue_evidence_items"] = int(issue_evidence_items)
    negative_reviews = int(data.get("negative_reviews") or 0)
    data["issue_coverage"] = (int(assigned_negative) / negative_reviews) if negative_reviews else None
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


def _latest_completed_issue_run_id(conn: duckdb.DuckDBPyConnection, app_id: str | None = None) -> int | None:
    clauses = [
        "status = 'succeeded'",
        "EXISTS (SELECT 1 FROM issues i WHERE i.analysis_run_id = analysis_runs.id)",
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
            ci.warnings,
            ci.source AS insight_source,
            ci.model AS insight_model
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


def list_issues(
    app_id: str | None = None,
    status: str | None = None,
    intent: str | None = None,
    aspect: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            i.*,
            count(ie.id) AS evidence_count,
            sum(CASE WHEN ie.verifier_verdict = 'match' THEN 1 ELSE 0 END) AS match_evidence_count,
            sum(CASE WHEN ie.verifier_verdict = 'partial' THEN 1 ELSE 0 END) AS partial_evidence_count,
            sum(CASE WHEN ie.verifier_verdict = 'reject' THEN 1 ELSE 0 END) AS reject_evidence_count,
            sum(
                CASE
                    WHEN ie.id IS NOT NULL
                     AND (ie.verifier_verdict IS NULL OR ie.verifier_verdict NOT IN ('match', 'partial', 'reject'))
                    THEN 1
                    ELSE 0
                END
            ) AS unverified_evidence_count
        FROM issues i
        LEFT JOIN issue_evidence ie ON ie.issue_id = i.id
    """
    clauses: list[str] = []
    params: list[Any] = []
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        latest_run_id = _latest_completed_issue_run_id(conn, resolved_app_id)
        if latest_run_id is None:
            return []
        clauses.append("i.analysis_run_id = ?")
        params.append(latest_run_id)
        if status:
            clauses.append("i.status = ?")
            params.append(status)
        if intent:
            clauses.append("i.intent = ?")
            params.append(intent)
        if aspect:
            clauses.append("i.aspect = ?")
            params.append(aspect)
        sql += " WHERE " + " AND ".join(clauses)
        sql += """
            GROUP BY
                i.id, i.analysis_run_id, i.app_id, i.title, i.summary, i.intent,
                i.aspect, i.status, i.confidence_band, i.confidence, i.priority_score,
                i.review_count, i.unique_review_count, i.unit_count, i.complaint_count,
                i.praise_count, i.request_count, i.bug_count, i.positive_ratio,
                i.language_counts, i.top_terms, i.why_it_matters, i.recommended_action,
                i.warnings, i.source, i.model, i.created_at
            ORDER BY
                CASE i.status
                    WHEN 'confirmed' THEN 1
                    WHEN 'strength' THEN 2
                    WHEN 'needs_review' THEN 3
                    ELSE 4
                END,
                i.priority_score DESC,
                i.unique_review_count DESC,
                i.id
            LIMIT ?
        """
        params.append(limit)
        rows = rows_to_dicts(conn.execute(sql, params))
    return [_hydrate_issue_row(row) for row in rows]


def list_issue_evidence(
    issue_id: int,
    limit: int = 50,
    language: str | None = None,
) -> list[dict[str, Any]]:
    clauses = ["ie.issue_id = ?"]
    params: list[Any] = [issue_id]
    if language:
        clauses.append("ie.language = ?")
        params.append(language)
    params.append(limit)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                f"""
                SELECT
                    ie.*,
                    r.review AS review_text,
                    r.playtime_at_review,
                    r.steam_created_at
                FROM issue_evidence ie
                LEFT JOIN reviews r ON r.recommendation_id = ie.review_id
                WHERE {" AND ".join(clauses)}
                ORDER BY
                    CASE coalesce(ie.verifier_verdict, 'match')
                        WHEN 'match' THEN 1
                        WHEN 'partial' THEN 2
                        WHEN 'reject' THEN 3
                        ELSE 4
                    END,
                    coalesce(ie.quality_score, 0.5) DESC,
                    ie.created_at DESC,
                    ie.id DESC
                LIMIT ?
                """,
                params,
            )
        )


def issue_summary(app_id: str | None = None) -> dict[str, Any]:
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        latest_run_id = _latest_completed_issue_run_id(conn, resolved_app_id)
        if latest_run_id is None:
            return {
                "issues": 0,
                "confirmed_issues": 0,
                "needs_review_issues": 0,
                "strength_issues": 0,
                "diagnostic_issues": 0,
                "issue_evidence_items": 0,
                "issue_units": 0,
                "quarantined_units": 0,
                "issue_coverage": None,
            }
        row = conn.execute(
            """
            SELECT
                count(*) AS issues,
                count(*) FILTER (WHERE status = 'confirmed') AS confirmed_issues,
                count(*) FILTER (WHERE status = 'needs_review') AS needs_review_issues,
                count(*) FILTER (WHERE status = 'strength') AS strength_issues,
                count(*) FILTER (WHERE status = 'diagnostic') AS diagnostic_issues
            FROM issues
            WHERE analysis_run_id = ?
            """,
            [latest_run_id],
        ).fetchone()
        issue_evidence_items = conn.execute(
            "SELECT count(*) FROM issue_evidence WHERE analysis_run_id = ?",
            [latest_run_id],
        ).fetchone()[0]
        unit_row = conn.execute(
            """
            SELECT
                count(*) AS issue_units,
                count(*) FILTER (WHERE is_quarantined) AS quarantined_units,
                count(DISTINCT review_id) FILTER (
                    WHERE voted_up = false AND NOT is_quarantined AND intent IN ('complaint', 'request', 'bug')
                ) AS assigned_negative
            FROM issue_units
            WHERE analysis_run_id = ?
            """,
            [latest_run_id],
        ).fetchone()
        negative_reviews = conn.execute(
            "SELECT count(*) FROM reviews WHERE app_id = ? AND NOT voted_up",
            [resolved_app_id],
        ).fetchone()[0]
    keys = ["issues", "confirmed_issues", "needs_review_issues", "strength_issues", "diagnostic_issues"]
    data = dict(zip(keys, row))
    data["issue_evidence_items"] = int(issue_evidence_items)
    data["issue_units"] = int(unit_row[0] or 0)
    data["quarantined_units"] = int(unit_row[1] or 0)
    data["issue_coverage"] = (int(unit_row[2] or 0) / int(negative_reviews)) if negative_reviews else None
    return data


def list_axes(app_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    resolved_app_id = resolve_app_id(app_id)
    clauses = ["(scope IN ('common', 'genre') OR app_id = ?)"]
    params: list[Any] = [resolved_app_id]
    if status:
        clauses.append("status = ?")
        params.append(status)
    with connect() as conn:
        return rows_to_dicts(
            conn.execute(
                f"""
                SELECT *
                FROM analysis_axes
                WHERE {" AND ".join(clauses)}
                ORDER BY
                    CASE scope WHEN 'game' THEN 1 WHEN 'genre' THEN 2 ELSE 3 END,
                    CASE status WHEN 'active' THEN 1 WHEN 'candidate' THEN 2 ELSE 3 END,
                    label
                """,
                params,
            )
        )


def create_axis(payload: AxisIn) -> dict[str, Any]:
    now = utcnow()
    app_id = resolve_app_id(payload.app_id) if payload.scope == "game" else payload.app_id
    with connect() as conn:
        axis_id = conn.execute(
            """
            INSERT INTO analysis_axes (
                key, label, description, pattern, recommended_action,
                scope, app_id, genre, status, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                payload.key,
                payload.label,
                payload.description,
                payload.pattern,
                payload.recommended_action,
                payload.scope,
                app_id,
                payload.genre,
                payload.status,
                payload.source,
                now,
                now,
            ],
        ).fetchone()[0]
        return rows_to_dicts(conn.execute("SELECT * FROM analysis_axes WHERE id = ?", [axis_id]))[0]


def update_axis(axis_id: int, payload: AxisUpdate) -> dict[str, Any] | None:
    updates = payload.model_dump(exclude_unset=True)
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM analysis_axes WHERE id = ?", [axis_id]).fetchone():
            return None
        if updates:
            assignments = []
            params: list[Any] = []
            for key, value in updates.items():
                assignments.append(f"{key} = ?")
                params.append(value)
            assignments.append("updated_at = ?")
            params.extend([utcnow(), axis_id])
            conn.execute(f"UPDATE analysis_axes SET {', '.join(assignments)} WHERE id = ?", params)
        return rows_to_dicts(conn.execute("SELECT * FROM analysis_axes WHERE id = ?", [axis_id]))[0]


def list_axis_suggestions(
    app_id: str | None = None,
    status: str | None = None,
    include_raw: bool = False,
) -> list[dict[str, Any]]:
    resolved_app_id = resolve_app_id(app_id)
    with connect() as conn:
        latest_run_id = _latest_completed_issue_run_id(conn, resolved_app_id)
        if latest_run_id is None:
            return []
        clauses = ["app_id = ?", "analysis_run_id = ?", "evidence_count >= 5"]
        params: list[Any] = [resolved_app_id, latest_run_id]
        if not include_raw:
            clauses.append("quality_gate = 'pass'")
            clauses.append("kind IN ('merge_candidate', 'axis_candidate', 'one_off_insight')")
        if status:
            clauses.append("status = ?")
            params.append(status)
        rows = rows_to_dicts(
            conn.execute(
                f"""
                SELECT *
                FROM axis_suggestions
                WHERE {" AND ".join(clauses)}
                ORDER BY
                    CASE status WHEN 'pending' THEN 1 WHEN 'approved' THEN 2 WHEN 'merged' THEN 3 ELSE 4 END,
                    evidence_count DESC,
                    id DESC
                """,
                params,
            )
        )
    return [_hydrate_axis_suggestion(row) for row in rows]


def approve_axis_suggestion(suggestion_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM axis_suggestions WHERE id = ?", [suggestion_id]))
        if not rows:
            return None
        suggestion = _hydrate_axis_suggestion(rows[0])
        if suggestion.get("quality_gate") != "pass" or suggestion.get("kind") != "axis_candidate":
            raise ValueError("Only passed axis candidates can be approved as new axes.")
        label = str(suggestion.get("canonical_label_ko") or suggestion["label"])
        definition = str(suggestion.get("definition") or suggestion["rationale"])
        key = _axis_key_from_label(label)
        axis_id = conn.execute(
            """
            INSERT INTO analysis_axes (
                key, label, description, pattern, recommended_action,
                scope, app_id, status, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'game', ?, 'active', 'ai', ?, ?)
            RETURNING id
            """,
            [
                key,
                label,
                definition,
                suggestion["suggested_pattern"],
                suggestion.get("why_actionable") or "승인한 평가축으로 재분석해 실제 문제/강점인지 확인하세요.",
                suggestion.get("app_id"),
                utcnow(),
                utcnow(),
            ],
        ).fetchone()[0]
        conn.execute(
            """
            UPDATE axis_suggestions
            SET status = 'approved', target_axis_id = ?, updated_at = ?
            WHERE id = ?
            """,
            [axis_id, utcnow(), suggestion_id],
        )
        row = rows_to_dicts(conn.execute("SELECT * FROM axis_suggestions WHERE id = ?", [suggestion_id]))[0]
    return _hydrate_axis_suggestion(row)


def merge_axis_suggestion(suggestion_id: int, target_axis_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM axis_suggestions WHERE id = ?", [suggestion_id]).fetchone():
            return None
        if not conn.execute("SELECT 1 FROM analysis_axes WHERE id = ?", [target_axis_id]).fetchone():
            return None
        conn.execute(
            """
            UPDATE axis_suggestions
            SET status = 'merged', target_axis_id = ?, updated_at = ?
            WHERE id = ?
            """,
            [target_axis_id, utcnow(), suggestion_id],
        )
        row = rows_to_dicts(conn.execute("SELECT * FROM axis_suggestions WHERE id = ?", [suggestion_id]))[0]
    return _hydrate_axis_suggestion(row)


def ignore_axis_suggestion(suggestion_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM axis_suggestions WHERE id = ?", [suggestion_id]).fetchone():
            return None
        conn.execute(
            "UPDATE axis_suggestions SET status = 'ignored', updated_at = ? WHERE id = ?",
            [utcnow(), suggestion_id],
        )
        row = rows_to_dicts(conn.execute("SELECT * FROM axis_suggestions WHERE id = ?", [suggestion_id]))[0]
    return _hydrate_axis_suggestion(row)


def keep_axis_suggestion(suggestion_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM axis_suggestions WHERE id = ?", [suggestion_id]).fetchone():
            return None
        conn.execute(
            "UPDATE axis_suggestions SET status = 'kept', updated_at = ? WHERE id = ?",
            [utcnow(), suggestion_id],
        )
        row = rows_to_dicts(conn.execute("SELECT * FROM axis_suggestions WHERE id = ?", [suggestion_id]))[0]
    return _hydrate_axis_suggestion(row)


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
    label_warnings = _loads_list(row.get("label_warnings"))
    matched_terms = _loads_list(row.get("matched_terms"))
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
            "source": row.pop("insight_source", None),
            "model": row.pop("insight_model", None),
        }
    else:
        for key in [
            "insight_title",
            "insight_summary",
            "praise",
            "pain_point",
            "planner_action",
            "marketing_angle",
            "confidence",
            "insight_source",
            "insight_model",
        ]:
            row.pop(key, None)
    row.pop("warnings", None)
    row["top_keywords"] = top_keywords
    row["label_warnings"] = label_warnings
    row["matched_terms"] = matched_terms
    row["insight"] = insight
    return row


def _hydrate_issue_row(row: dict[str, Any]) -> dict[str, Any]:
    row["language_counts"] = _loads_int_dict(row.get("language_counts"))
    row["top_terms"] = _loads_list(row.get("top_terms"))
    row["warnings"] = _loads_list(row.get("warnings"))
    row["evidence_count"] = int(row.get("evidence_count") or 0)
    row["match_evidence_count"] = int(row.get("match_evidence_count") or 0)
    row["partial_evidence_count"] = int(row.get("partial_evidence_count") or 0)
    row["reject_evidence_count"] = int(row.get("reject_evidence_count") or 0)
    row["unverified_evidence_count"] = int(row.get("unverified_evidence_count") or 0)
    return row


def _hydrate_axis_suggestion(row: dict[str, Any]) -> dict[str, Any]:
    row["language_counts"] = _loads_int_dict(row.get("language_counts"))
    row["example_review_ids"] = _loads_list(row.get("example_review_ids"))
    row["include_criteria"] = _loads_list(row.get("include_criteria"))
    row["exclude_criteria"] = _loads_list(row.get("exclude_criteria"))
    row["evidence_claim_ids"] = _loads_list(row.get("evidence_claim_ids"))
    row["kind"] = row.get("kind") or "raw_signal"
    row["quality_gate"] = row.get("quality_gate") or "fail"
    return row


def _axis_key_from_label(label: str) -> str:
    compact = "".join(ch.lower() if ch.isalnum() else "_" for ch in label)
    compact = "_".join(part for part in compact.split("_") if part)
    return (compact or "custom_axis")[:64]


def _loads_int_dict(value: Any) -> dict[str, int]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(key): int(raw or 0) for key, raw in value.items()}
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict):
        return {str(key): int(raw or 0) for key, raw in parsed.items()}
    return {}
