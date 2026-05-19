from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import json
from datetime import datetime, timezone

import duckdb

from .config import get_settings


SCHEMA_SQL = """
CREATE SEQUENCE IF NOT EXISTS event_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS cluster_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS evidence_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS report_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS job_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS analysis_run_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS claim_id_seq START 1;

CREATE TABLE IF NOT EXISTS games (
    app_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    short_name VARCHAR,
    note TEXT,
    tags JSON,
    status VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    last_refreshed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    recommendation_id VARCHAR PRIMARY KEY,
    app_id VARCHAR NOT NULL,
    author_steamid VARCHAR,
    language VARCHAR NOT NULL,
    review TEXT NOT NULL,
    voted_up BOOLEAN NOT NULL,
    votes_up INTEGER NOT NULL DEFAULT 0,
    votes_funny INTEGER NOT NULL DEFAULT 0,
    weighted_vote_score DOUBLE NOT NULL DEFAULT 0,
    playtime_forever INTEGER NOT NULL DEFAULT 0,
    playtime_at_review INTEGER NOT NULL DEFAULT 0,
    steam_created_at TIMESTAMP,
    steam_updated_at TIMESTAMP,
    collected_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    developer_response TEXT,
    raw_json JSON
);

CREATE TABLE IF NOT EXISTS events (
    id BIGINT PRIMARY KEY DEFAULT nextval('event_id_seq'),
    app_id VARCHAR,
    title VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    description TEXT,
    occurred_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS clusters (
    id BIGINT PRIMARY KEY DEFAULT nextval('cluster_id_seq'),
    analysis_run_id BIGINT,
    label VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    sentiment VARCHAR NOT NULL,
    language VARCHAR,
    review_count INTEGER NOT NULL DEFAULT 0,
    avg_weighted_score DOUBLE NOT NULL DEFAULT 0,
    exemplar_review_id VARCHAR,
    positive_ratio DOUBLE,
    top_keywords JSON,
    quality_warning VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS review_clusters (
    review_id VARCHAR NOT NULL,
    cluster_id BIGINT NOT NULL,
    score DOUBLE NOT NULL DEFAULT 1,
    PRIMARY KEY (review_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id BIGINT PRIMARY KEY DEFAULT nextval('evidence_id_seq'),
    analysis_run_id BIGINT,
    claim_id BIGINT,
    review_id VARCHAR NOT NULL,
    cluster_id BIGINT,
    quote TEXT NOT NULL,
    evidence_type VARCHAR NOT NULL,
    evidence_role VARCHAR,
    note TEXT,
    quality_score DOUBLE,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS review_quality (
    analysis_run_id BIGINT NOT NULL,
    review_id VARCHAR NOT NULL,
    normalized_text TEXT NOT NULL,
    text_hash VARCHAR NOT NULL,
    quality_score DOUBLE NOT NULL,
    quality_flags JSON,
    duplicate_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (analysis_run_id, review_id)
);

CREATE TABLE IF NOT EXISTS cluster_insights (
    cluster_id BIGINT PRIMARY KEY,
    title VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    praise TEXT,
    pain_point TEXT,
    planner_action TEXT,
    marketing_angle TEXT,
    confidence DOUBLE NOT NULL DEFAULT 0.5,
    warnings JSON,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS claims (
    id BIGINT PRIMARY KEY DEFAULT nextval('claim_id_seq'),
    analysis_run_id BIGINT,
    cluster_id BIGINT,
    claim_type VARCHAR NOT NULL,
    claim_text TEXT NOT NULL,
    confidence DOUBLE NOT NULL DEFAULT 0.5,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS reports (
    id BIGINT PRIMARY KEY DEFAULT nextval('report_id_seq'),
    analysis_run_id BIGINT,
    app_id VARCHAR,
    title VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    filters JSON,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR PRIMARY KEY,
    value JSON NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT PRIMARY KEY DEFAULT nextval('job_id_seq'),
    job_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    message TEXT,
    progress DOUBLE NOT NULL DEFAULT 0,
    started_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    finished_at TIMESTAMP,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id BIGINT PRIMARY KEY DEFAULT nextval('analysis_run_id_seq'),
    app_id VARCHAR,
    status VARCHAR NOT NULL,
    progress DOUBLE NOT NULL DEFAULT 0,
    message TEXT,
    params JSON,
    started_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    finished_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_embeddings (
    review_id VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    dimension INTEGER NOT NULL,
    embedding TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (review_id, model)
);
"""


def _db_path() -> Path:
    path = get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect() -> Iterator[duckdb.DuckDBPyConnection]:
    conn = duckdb.connect(str(_db_path()))
    try:
        yield conn
    finally:
        conn.close()


def initialize_database() -> None:
    with connect() as conn:
        conn.execute(SCHEMA_SQL)
        run_migrations(conn)
        ensure_default_settings(conn)
        seed_if_empty(conn)
        ensure_games_seeded(conn)
        backfill_scoped_rows(conn)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    _add_column_if_missing(conn, "games", "short_name", "VARCHAR")
    _add_column_if_missing(conn, "games", "note", "TEXT")
    _add_column_if_missing(conn, "games", "tags", "JSON")
    _add_column_if_missing(conn, "games", "status", "VARCHAR")
    _add_column_if_missing(conn, "events", "app_id", "VARCHAR")
    _add_column_if_missing(conn, "clusters", "analysis_run_id", "BIGINT")
    _add_column_if_missing(conn, "clusters", "positive_ratio", "DOUBLE")
    _add_column_if_missing(conn, "clusters", "top_keywords", "JSON")
    _add_column_if_missing(conn, "clusters", "quality_warning", "VARCHAR")
    _add_column_if_missing(conn, "evidence", "analysis_run_id", "BIGINT")
    _add_column_if_missing(conn, "evidence", "claim_id", "BIGINT")
    _add_column_if_missing(conn, "evidence", "evidence_role", "VARCHAR")
    _add_column_if_missing(conn, "evidence", "quality_score", "DOUBLE")
    _add_column_if_missing(conn, "reports", "analysis_run_id", "BIGINT")
    _add_column_if_missing(conn, "reports", "app_id", "VARCHAR")


def ensure_default_settings(conn: duckdb.DuckDBPyConnection) -> None:
    defaults = [
        (
            "steam_cursor",
            {
                "app_id": get_settings().steam_app_id,
                "cursor": None,
                "has_more": False,
                "source": "not_refreshed",
            },
        ),
        (
            "models",
            {
                "default_provider": "local_rules",
                "embedding_model": "intfloat/multilingual-e5-large",
                "lm_studio_base_url": "http://127.0.0.1:1234/v1",
            },
        ),
    ]
    for key, value in defaults:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT (key) DO NOTHING
            """,
            [key, json.dumps(value), utcnow()],
        )


def _add_column_if_missing(conn: duckdb.DuckDBPyConnection, table: str, column: str, column_type: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def _default_game_name(app_id: str) -> str:
    if app_id == "1145350":
        return "Hades II"
    return f"Steam App {app_id}"


def _primary_app_id(conn: duckdb.DuckDBPyConnection) -> str:
    row = conn.execute(
        """
        SELECT app_id
        FROM reviews
        GROUP BY app_id
        ORDER BY count(*) DESC, app_id
        LIMIT 1
        """
    ).fetchone()
    return str(row[0]) if row else get_settings().steam_app_id


def ensure_games_seeded(conn: duckdb.DuckDBPyConnection) -> None:
    app_ids = [str(row[0]) for row in conn.execute("SELECT DISTINCT app_id FROM reviews ORDER BY app_id").fetchall()]
    if get_settings().steam_app_id not in app_ids:
        app_ids.append(get_settings().steam_app_id)
    now = utcnow()
    for app_id in app_ids:
        conn.execute(
            """
            INSERT INTO games (app_id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (app_id) DO NOTHING
            """,
            [app_id, _default_game_name(app_id), now, now],
        )
    conn.execute(
        "UPDATE games SET name = ? WHERE app_id = ? AND name = ?",
        ["Hades II", "1145350", "Steam App 1145350"],
    )


def backfill_scoped_rows(conn: duckdb.DuckDBPyConnection) -> None:
    app_id = _primary_app_id(conn)
    conn.execute("UPDATE events SET app_id = ? WHERE app_id IS NULL", [app_id])
    conn.execute("UPDATE analysis_runs SET app_id = ? WHERE app_id IS NULL", [app_id])
    rows = conn.execute("SELECT id, filters FROM reports WHERE app_id IS NULL").fetchall()
    for report_id, filters in rows:
        report_app_id = _app_id_from_filters(filters) or app_id
        conn.execute("UPDATE reports SET app_id = ? WHERE id = ?", [report_app_id, report_id])


def _app_id_from_filters(filters: object) -> str | None:
    if not filters:
        return None
    try:
        value = filters if isinstance(filters, dict) else json.loads(str(filters))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    app_id = value.get("app_id") if isinstance(value, dict) else None
    return str(app_id) if app_id else None


def seed_if_empty(conn: duckdb.DuckDBPyConnection) -> None:
    count = conn.execute("SELECT count(*) FROM reviews").fetchone()[0]
    if count:
        return

    now = utcnow()
    reviews = [
        (
            "seed-1001",
            "1145350",
            "76561198000000001",
            "english",
            "The combat still feels sharp and every weapon has a distinct rhythm, especially in boss fights.",
            True,
            48,
            3,
            0.82,
            1180,
            1140,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
        (
            "seed-1002",
            "1145350",
            "76561198000000002",
            "english",
            "Late game runs start to feel repetitive because the rewards do not change enough after thirty hours.",
            False,
            31,
            1,
            0.74,
            3120,
            3040,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
        (
            "seed-1003",
            "1145350",
            "76561198000000003",
            "koreana",
            "무기별 리듬과 보스전 긴장감이 좋아서 전투 자체는 계속 재미있습니다.",
            True,
            22,
            0,
            0.67,
            1320,
            1280,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
        (
            "seed-1004",
            "1145350",
            "76561198000000004",
            "schinese",
            "After the balance patch, fewer builds feel worth trying and some weapons fall too far behind.",
            False,
            57,
            4,
            0.88,
            1900,
            1860,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
        (
            "seed-1005",
            "1145350",
            "76561198000000005",
            "japanese",
            "The character art and atmosphere are outstanding, and every new interaction feels worth seeing.",
            True,
            64,
            5,
            0.91,
            840,
            830,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
        (
            "seed-1006",
            "1145350",
            "76561198000000006",
            "spanish",
            "The loop works, but the late rewards do not justify repeating the same route again.",
            False,
            38,
            2,
            0.79,
            3300,
            3260,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
        (
            "seed-1007",
            "1145350",
            "76561198000000007",
            "koreana",
            "최근 패치 뒤 UI 가독성은 조금 나아졌지만, 후반 보상 루프는 아직 아쉽습니다.",
            False,
            19,
            0,
            0.61,
            2760,
            2710,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
        (
            "seed-1008",
            "1145350",
            "76561198000000008",
            "english",
            "The patch made the game smoother, but the weapon balance still narrows my build choices.",
            True,
            44,
            1,
            0.77,
            1680,
            1600,
            now,
            now,
            now,
            None,
            json.dumps({"source": "seed"}),
        ),
    ]
    conn.executemany(
        """
        INSERT INTO reviews (
            recommendation_id, app_id, author_steamid, language, review, voted_up,
            votes_up, votes_funny, weighted_vote_score, playtime_forever,
            playtime_at_review, steam_created_at, steam_updated_at, collected_at,
            developer_response, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        reviews,
    )

    conn.executemany(
        """
        INSERT INTO clusters (label, summary, sentiment, language, review_count, avg_weighted_score, exemplar_review_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("후반 반복성과 보상 밀도", "장기 플레이 구간에서 반복성, 보상 변화 부족, 루프 피로가 함께 언급됩니다.", "negative", None, 3, 0.71, "seed-1002"),
            ("전투 손맛과 보스전 긴장감", "무기별 리듬, 회피 타이밍, 보스전 압박감이 핵심 강점으로 반복됩니다.", "positive", None, 3, 0.75, "seed-1001"),
            ("무기 밸런스와 빌드 선택지", "패치 이후 특정 무기와 빌드 선택지가 좁아졌다는 반응입니다.", "negative", None, 2, 0.82, "seed-1004"),
            ("아트와 캐릭터 매력", "캐릭터 표현, 일러스트, 분위기는 언어권을 가리지 않고 강하게 호평받습니다.", "positive", None, 2, 0.84, "seed-1005"),
        ],
    )
    conn.executemany(
        "INSERT INTO review_clusters (review_id, cluster_id, score) VALUES (?, ?, ?)",
        [
            ("seed-1002", 1, 0.94),
            ("seed-1006", 1, 0.91),
            ("seed-1007", 1, 0.76),
            ("seed-1001", 2, 0.94),
            ("seed-1003", 2, 0.89),
            ("seed-1008", 2, 0.61),
            ("seed-1004", 3, 0.92),
            ("seed-1008", 3, 0.78),
            ("seed-1005", 4, 0.94),
            ("seed-1003", 4, 0.64),
        ],
    )
    conn.executemany(
        "INSERT INTO evidence (review_id, cluster_id, quote, evidence_type, note) VALUES (?, ?, ?, ?, ?)",
        [
            ("seed-1002", 1, "Late game runs start to feel repetitive", "pain_point", "Long-run motivation signal"),
            ("seed-1004", 3, "fewer builds feel worth trying", "pain_point", "Build variety signal"),
            ("seed-1005", 4, "character art and atmosphere are outstanding", "praise", "Presentation strength"),
        ],
    )
    conn.executemany(
        "INSERT INTO events (title, event_type, description, occurred_at) VALUES (?, ?, ?, ?)",
        [
            ("Early access release", "launch", "Initial Steam review window.", now),
            ("Balance patch 1", "patch", "Weapon tuning and progression adjustments.", now),
            ("Content update", "patch", "New encounters and reward tuning.", now),
        ],
    )
    conn.execute(
        "INSERT INTO reports (title, summary, filters) VALUES (?, ?, ?)",
        [
            "Seed review pulse",
            "Sample data highlights combat praise, late-game repetition, balance concerns, and art strengths.",
            json.dumps({"source": "seed", "app_id": "1145350"}),
        ],
    )
    conn.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        [
            ("steam", json.dumps({"app_id": "1145350", "language": "all", "review_type": "all", "purchase_type": "all"})),
            ("analysis", json.dumps({"provider": "local_gpu", "clusterer": "semantic_embeddings", "embedding_model": "intfloat/multilingual-e5-large"})),
        ],
    )
