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
CREATE SEQUENCE IF NOT EXISTS issue_unit_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS issue_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS issue_evidence_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS analysis_axis_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS axis_suggestion_id_seq START 1;

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
    keyword_method VARCHAR,
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
    source VARCHAR,
    model VARCHAR,
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

CREATE TABLE IF NOT EXISTS issue_units (
    id BIGINT PRIMARY KEY DEFAULT nextval('issue_unit_id_seq'),
    analysis_run_id BIGINT NOT NULL,
    app_id VARCHAR,
    review_id VARCHAR NOT NULL,
    unit_index INTEGER NOT NULL DEFAULT 0,
    unit_text TEXT NOT NULL,
    language VARCHAR,
    voted_up BOOLEAN,
    intent VARCHAR NOT NULL,
    aspect VARCHAR NOT NULL,
    sentiment VARCHAR NOT NULL,
    quality_score DOUBLE NOT NULL DEFAULT 0.5,
    quality_flags JSON,
    is_quarantined BOOLEAN NOT NULL DEFAULT false,
    quarantine_reason VARCHAR,
    text_hash VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS issues (
    id BIGINT PRIMARY KEY DEFAULT nextval('issue_id_seq'),
    analysis_run_id BIGINT NOT NULL,
    app_id VARCHAR,
    title VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    intent VARCHAR NOT NULL,
    aspect VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    confidence_band VARCHAR NOT NULL,
    confidence DOUBLE NOT NULL DEFAULT 0.5,
    priority_score DOUBLE NOT NULL DEFAULT 0.5,
    review_count INTEGER NOT NULL DEFAULT 0,
    unique_review_count INTEGER NOT NULL DEFAULT 0,
    unit_count INTEGER NOT NULL DEFAULT 0,
    complaint_count INTEGER NOT NULL DEFAULT 0,
    praise_count INTEGER NOT NULL DEFAULT 0,
    request_count INTEGER NOT NULL DEFAULT 0,
    bug_count INTEGER NOT NULL DEFAULT 0,
    positive_ratio DOUBLE,
    language_counts JSON,
    top_terms JSON,
    why_it_matters TEXT,
    recommended_action TEXT,
    warnings JSON,
    source VARCHAR,
    model VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS issue_evidence (
    id BIGINT PRIMARY KEY DEFAULT nextval('issue_evidence_id_seq'),
    issue_id BIGINT NOT NULL,
    unit_id BIGINT,
    analysis_run_id BIGINT NOT NULL,
    app_id VARCHAR,
    review_id VARCHAR NOT NULL,
    quote TEXT NOT NULL,
    evidence_role VARCHAR NOT NULL,
    language VARCHAR,
    voted_up BOOLEAN,
    quality_score DOUBLE,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS analysis_axes (
    id BIGINT PRIMARY KEY DEFAULT nextval('analysis_axis_id_seq'),
    key VARCHAR NOT NULL,
    label VARCHAR NOT NULL,
    description TEXT NOT NULL,
    pattern TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    scope VARCHAR NOT NULL DEFAULT 'game',
    app_id VARCHAR,
    genre VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'active',
    source VARCHAR NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS axis_suggestions (
    id BIGINT PRIMARY KEY DEFAULT nextval('axis_suggestion_id_seq'),
    analysis_run_id BIGINT NOT NULL,
    app_id VARCHAR,
    label VARCHAR NOT NULL,
    rationale TEXT NOT NULL,
    suggested_pattern TEXT NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    language_counts JSON,
    example_review_ids JSON,
    kind VARCHAR NOT NULL DEFAULT 'raw_signal',
    canonical_label_ko VARCHAR,
    definition TEXT,
    include_criteria JSON,
    exclude_criteria JSON,
    evidence_claim_ids JSON,
    why_actionable TEXT,
    quality_gate VARCHAR NOT NULL DEFAULT 'fail',
    failure_reason TEXT,
    status VARCHAR NOT NULL DEFAULT 'pending',
    target_axis_id BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
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
        ensure_axes_seeded(conn)
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
    _add_column_if_missing(conn, "clusters", "keyword_method", "VARCHAR")
    _add_column_if_missing(conn, "clusters", "quality_warning", "VARCHAR")
    _add_column_if_missing(conn, "cluster_insights", "source", "VARCHAR")
    _add_column_if_missing(conn, "cluster_insights", "model", "VARCHAR")
    _add_column_if_missing(conn, "evidence", "analysis_run_id", "BIGINT")
    _add_column_if_missing(conn, "evidence", "claim_id", "BIGINT")
    _add_column_if_missing(conn, "evidence", "evidence_role", "VARCHAR")
    _add_column_if_missing(conn, "evidence", "quality_score", "DOUBLE")
    _add_column_if_missing(conn, "reports", "analysis_run_id", "BIGINT")
    _add_column_if_missing(conn, "reports", "app_id", "VARCHAR")
    _add_column_if_missing(conn, "issue_evidence", "verifier_verdict", "VARCHAR")
    _add_column_if_missing(conn, "issue_evidence", "summary_ko", "TEXT")
    _add_column_if_missing(conn, "issue_evidence", "subissue", "VARCHAR")
    _add_column_if_missing(conn, "issue_evidence", "verifier_reason", "TEXT")
    _add_column_if_missing(conn, "axis_suggestions", "kind", "VARCHAR")
    _add_column_if_missing(conn, "axis_suggestions", "canonical_label_ko", "VARCHAR")
    _add_column_if_missing(conn, "axis_suggestions", "definition", "TEXT")
    _add_column_if_missing(conn, "axis_suggestions", "include_criteria", "JSON")
    _add_column_if_missing(conn, "axis_suggestions", "exclude_criteria", "JSON")
    _add_column_if_missing(conn, "axis_suggestions", "evidence_claim_ids", "JSON")
    _add_column_if_missing(conn, "axis_suggestions", "why_actionable", "TEXT")
    _add_column_if_missing(conn, "axis_suggestions", "quality_gate", "VARCHAR")
    _add_column_if_missing(conn, "axis_suggestions", "failure_reason", "TEXT")
    conn.execute("UPDATE axis_suggestions SET kind = COALESCE(kind, 'raw_signal')")
    conn.execute("UPDATE axis_suggestions SET quality_gate = COALESCE(quality_gate, 'fail')")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_axes (
            id BIGINT PRIMARY KEY DEFAULT nextval('analysis_axis_id_seq'),
            key VARCHAR NOT NULL,
            label VARCHAR NOT NULL,
            description TEXT NOT NULL,
            pattern TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            scope VARCHAR NOT NULL DEFAULT 'game',
            app_id VARCHAR,
            genre VARCHAR,
            status VARCHAR NOT NULL DEFAULT 'active',
            source VARCHAR NOT NULL DEFAULT 'user',
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS axis_suggestions (
            id BIGINT PRIMARY KEY DEFAULT nextval('axis_suggestion_id_seq'),
            analysis_run_id BIGINT NOT NULL,
            app_id VARCHAR,
            label VARCHAR NOT NULL,
            rationale TEXT NOT NULL,
            suggested_pattern TEXT NOT NULL,
            evidence_count INTEGER NOT NULL DEFAULT 0,
            language_counts JSON,
            example_review_ids JSON,
            kind VARCHAR NOT NULL DEFAULT 'raw_signal',
            canonical_label_ko VARCHAR,
            definition TEXT,
            include_criteria JSON,
            exclude_criteria JSON,
            evidence_claim_ids JSON,
            why_actionable TEXT,
            quality_gate VARCHAR NOT NULL DEFAULT 'fail',
            failure_reason TEXT,
            status VARCHAR NOT NULL DEFAULT 'pending',
            target_axis_id BIGINT,
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
        )
        """
    )


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


def ensure_axes_seeded(conn: duckdb.DuckDBPyConnection) -> None:
    axes = [
        ("performance", "성능/안정성", "성능, 충돌, 버그, 지연처럼 플레이 안정성을 직접 해치는 신호입니다.", r"crash|bug|bugs|broken|freeze|low fps|fps drop|frame drop|stutter|lag|loading|performance|optimization|disconnect|튕김|버그|프레임|렉|랙|끊김|멈춤|최적화|クラッシュ|バグ|卡顿|崩溃", "재현 가능한 환경, 플랫폼, 최근 패치 이후 증가 여부를 먼저 확인하세요.", "common", None),
        ("balance", "밸런스/RNG", "무작위성, 난이도 체감, 선택지 효율 차이에 대한 신호입니다.", r"balance|balanced|unbalanced|rng|luck|random|unfair|overpowered|op|nerf|buff|밸런스|운빨|운|랜덤|불공평|너프|버프|ランダム|運|平衡", "불만이 집중되는 빌드/구간/조건을 분리해 수치 조정 후보로 검토하세요.", "common", None),
        ("progression", "난이도/진척", "진행 속도, 해금, 보상, 난이도 곡선에 대한 신호입니다.", r"difficulty|hard|easy|progress|progression|grind|unlock|level|rank|reward|난이도|어려|쉬움|진행|진척|해금|노가다|보상|レベル", "초반/중반/후반 어느 구간에서 막히는지 플레이타임별로 다시 확인하세요.", "common", None),
        ("content_repetition", "반복성/콘텐츠", "콘텐츠 다양성, 반복감, 장기 플레이 동기에 대한 신호입니다.", r"repetitive|repeat|same|boring|bored|content|endgame|late game|loop|variety|반복|지루|콘텐츠|컨텐츠|후반|엔드게임|다양성|飽き|繰り返", "새 목표, 변주, 보상 밀도 중 무엇이 부족한지 근거 리뷰를 나눠 보세요.", "common", None),
        ("ui_onboarding", "UI/가독성/온보딩", "메뉴, 조작, 설명, 가독성처럼 이해와 반복 사용을 방해하는 신호입니다.", r"\bui\b|\bux\b|\binterface\b|\bmenu\b|\bhud\b|\breadability\b|\bfont\b|\btext\b|\btutorial\b|confusing|\bcontrols?\b|키설정|조작|가독성|메뉴|인터페이스|글자|튜토리얼|설명|헷갈|界面|文字", "첫 플레이와 장기 플레이를 나눠, 설명 부족인지 조작 피로인지 분리하세요.", "common", None),
        ("story_logic", "스토리/세계관/엔딩", "스토리 전개, 세계관, 캐릭터 서사, 엔딩 납득감에 대한 신호입니다.", r"story|plot|logic|deduction|mystery|twist|foreshadow|case|trick|character|route|ending|스토리|서사|개연성|논리|추리|트릭|반전|떡밥|캐릭터|루트|엔딩|剧情|逻辑|推理|伏笔|角色|路线|结局|ストーリー|推理|伏線|キャラ", "불만이면 개연성/힌트/회수 문제로 쪼개고, 강점이면 후속작과 홍보의 핵심 약속으로 쓸 수 있는지 확인하세요.", "common", None),
        ("localization_readability", "번역/가독성", "번역, 자막, 텍스트 가독성, 언어 지원 품질에 대한 신호입니다.", r"translation|localization|typo|subtitle|korean|english|japanese|chinese|readability|번역|한글화|오역|자막|가독성|텍스트|翻译|本地化|字幕|错字|読みづら|日本語|한국어", "언어별 원문을 비교해 번역 품질 문제인지 텍스트 UI 문제인지 분리하세요.", "common", None),
        ("mystery_logic", "추리/재판/마법 규칙", "추리 파트, 재판 전개, 마법 규칙, 트릭 납득감, 단간론파식 기대와의 비교 신호입니다.", r"mystery|deduction|logic|trick|magic|case|danganronpa|trial|reasoning|추리|논리|트릭|마법|재판|단간|개연성|억지|推理|逻辑|诡计|魔法|审判|裁判", "불만이면 추리 난이도보다 힌트-증거-마법 규칙-결론의 납득성 문제로 우선 확인하세요.", "game", "3101040"),
        ("character_voice", "캐릭터/연출/더빙", "캐릭터 디자인, 더빙, 연출이 구매 만족을 만드는 강점 신호입니다.", r"character|voice|acting|design|cg|art|캐릭터|캐디|더빙|성우|디자인|일러|연출|角色|配音|人设|立绘|演出|キャラ|ボイス", "강점이면 홍보 소재와 팬덤 확장 포인트로 쓰고, 불만이면 특정 캐릭터/연출의 설득력을 점검하세요.", "game", "3101040"),
        ("weapon_card_rng", "무기/카드 RNG", "무기 카드, 랜덤 제시, 내구도, 빌드 선택의 운 의존 신호입니다.", r"weapon|weapons|card|cards|rng|random|luck|durability|shotgun|grenade|무기|카드|운|랜덤|내구도|샷건|武器|カード|運|ランダム|耐久", "런 다양성의 장점인지 통제감 부족인지 추천/비추천 근거를 나눠 보세요.", "game", "1456820"),
        ("martial_story", "무협 서사/인물 매력", "무협 분위기, 인물 매력, 루트별 서사에 대한 신호입니다.", r"martial|wuxia|heroine|character|story|route|무협|협객|히로인|캐릭터|스토리|서사|剧情|武侠|侠客|女主|角色|人设|故事", "강점이면 스토어 문구와 후속 콘텐츠의 핵심 약속으로 쓰고, 불만이면 특정 루트/인물의 서사 납득감을 점검하세요.", "game", "1859910"),
    ]
    now = utcnow()
    for key, label, description, pattern, action, scope, app_id in axes:
        existing = conn.execute(
            """
            SELECT 1
            FROM analysis_axes
            WHERE key = ? AND scope = ? AND coalesce(app_id, '') = coalesce(?, '')
            """,
            [key, scope, app_id],
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO analysis_axes (
                key, label, description, pattern, recommended_action,
                scope, app_id, status, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 'system', ?, ?)
            """,
            [key, label, description, pattern, action, scope, app_id, now, now],
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
