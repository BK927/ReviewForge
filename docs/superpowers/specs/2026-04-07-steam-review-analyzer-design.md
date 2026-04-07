# ReviewForge - Steam Review Analyzer Design Spec

## Overview

Steam 게임 리뷰를 수집하고 분석하는 데스크톱 앱. 게임 기획자/마케터가 특정 게임의 평판을 객관적으로 파악할 수 있도록 메타데이터 기반 통계 + 임베딩 기반 키워드/토픽 분석 + LLM export 경로를 제공한다.

## Tech Stack

| 구성 | 선택 | 이유 |
|---|---|---|
| 앱 프레임워크 | Electron | 깔끔한 데스크톱 UI, 바이브코딩 적합, 웹 기술 기반 |
| 프론트엔드 | React + ECharts/Recharts | 차트/대시보드에 적합, AI가 잘 생성하는 스택 |
| ML 파이프라인 | Python sidecar | onnxruntime, scikit-learn 등 성숙한 ML 생태계 직접 사용 |
| 통신 | Electron Main ↔ Python (stdin/stdout JSON) | 단순하고 안정적 |
| DB | SQLite | 서버 불필요, 단일 파일, 데스크톱에 최적 |

## Architecture

```
+---------------------------------------------+
|              Electron (UI)                  |
|  React + ECharts/Recharts                   |
|  +----------+ +----------+ +--------------+ |
|  | 대시보드  | | 토픽분석 | | Export/설정  | |
|  +----------+ +----------+ +--------------+ |
|                    | IPC                     |
|              Electron Main                  |
|         (SQLite, Steam API 호출)            |
+--------------------+------------------------+
                     | stdin/stdout JSON
+--------------------+------------------------+
|          Python Sidecar                     |
|  +----------------------------------------+ |
|  | Tier 0 (CPU): multilingual-e5-small    | |
|  | Tier 1 (GPU): BGE-M3                   | |
|  +----------------------------------------+ |
|  | 클러스터링 (KMeans / HDBSCAN)           | |
|  | 키워드 추출 (KeyBERT + YAKE!)           | |
|  | 토픽 분류 + 라벨링                      | |
|  +----------------------------------------+ |
+---------------------------------------------+
```

### Role Separation

- **Electron Main**: Steam API 호출, SQLite CRUD, 파일 I/O, Python sidecar 프로세스 lifecycle 관리
- **Electron Renderer**: UI 렌더링, 차트, 사용자 인터랙션
- **Python Sidecar**: GPU 감지, 임베딩 생성, 클러스터링, 키워드/토픽 분석

## Data Collection

### Input Methods

- 스팀 앱 ID 직접 입력 (예: `730`)
- 스토어 URL 붙여넣기 (예: `store.steampowered.com/app/730/...`) -> 앱 ID 자동 파싱

### Steam Review Endpoint

```
GET https://store.steampowered.com/appreviews/<appid>?json=1
```

- API 키 불필요 (공개 엔드포인트, 2026-04-07 테스트 확인 완료)
- `filter=recent`, `cursor` 기반 페이징, `num_per_page=100` (최대)
- `language=all`로 전체 언어 수집
- 빈 리스트가 올 때까지 순회하여 전수 수집
- 리뷰 폭탄 필터 (`filter_offtopic_activity`) 기본 ON, 사용자 토글 가능

### Collected Fields (per review)

- `recommendationid` (PK), `appid`, `language`, `review` (본문)
- `voted_up`, `timestamp_created`, `timestamp_updated`
- `author.playtime_at_review`, `author.playtime_forever`
- `steam_purchase`, `received_for_free`, `written_during_early_access`
- `votes_up`, `votes_funny`, `weighted_vote_score`
- `comment_count`, `primarily_steam_deck`

### Incremental Updates

- `recommendationid` 기준 upsert로 중복 방지
- `timestamp_updated`로 수정된 리뷰 감지

### Rate Limiting

- 요청 간 최소 간격 유지 (500ms~1s)
- 429/5xx 시 지수 백오프 + 재시도

### API Response Notes (2026-04-07 테스트 결과)

- `query_summary` (총 리뷰 수, 점수 등)는 첫 페이지에서만 반환됨 -> 첫 요청에서 캐싱 필요
- `weighted_vote_score`가 문자열 또는 숫자로 올 수 있음 -> 파싱 시 타입 처리 필요
- 언어 코드가 Steam 고유 형식 (`koreana`, `schinese` 등, ISO 코드 아님)

## Data Storage

SQLite 단일 파일 DB.

### Schema

```sql
-- 분석 대상 게임
CREATE TABLE games (
    app_id INTEGER PRIMARY KEY,
    app_name TEXT,
    review_score INTEGER,
    review_score_desc TEXT,
    total_positive INTEGER,
    total_negative INTEGER,
    total_reviews INTEGER,
    first_fetched_at INTEGER,
    last_fetched_at INTEGER
);

-- 리뷰 데이터
CREATE TABLE reviews (
    recommendation_id TEXT PRIMARY KEY,
    app_id INTEGER REFERENCES games(app_id),
    language TEXT,
    review_text TEXT,
    voted_up INTEGER, -- boolean as 0/1
    timestamp_created INTEGER,
    timestamp_updated INTEGER,
    playtime_at_review INTEGER, -- minutes
    playtime_forever INTEGER, -- minutes
    steam_purchase INTEGER, -- boolean as 0/1
    received_for_free INTEGER, -- boolean as 0/1
    written_during_early_access INTEGER, -- boolean as 0/1
    primarily_steam_deck INTEGER, -- boolean as 0/1
    votes_up INTEGER,
    votes_funny INTEGER,
    weighted_vote_score REAL,
    comment_count INTEGER,
    fetched_at INTEGER
);

CREATE INDEX idx_reviews_app_lang ON reviews(app_id, language);
CREATE INDEX idx_reviews_app_time ON reviews(app_id, timestamp_created);

-- 임베딩 벡터 캐시
CREATE TABLE embeddings (
    recommendation_id TEXT PRIMARY KEY REFERENCES reviews(recommendation_id),
    embedding_model TEXT,
    vector BLOB
);

-- 분석 결과 캐시
CREATE TABLE analysis_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER REFERENCES games(app_id),
    analysis_type TEXT, -- 'topics', 'keywords', etc.
    language_filter TEXT,
    config_hash TEXT, -- hash of filter/param combination
    result_json TEXT,
    created_at INTEGER
);
```

## Analysis Pipeline

### Hardware Detection

앱 시작 시 Python sidecar가 GPU를 확인하여 자동 Tier 선택. 사용자가 설정에서 수동 전환 가능.

- CUDA GPU + VRAM >= 8GB -> Tier 1
- Otherwise -> Tier 0

### Tier 0 (CPU) - Laptop-friendly

| Step | Method | Notes |
|---|---|---|
| Embedding | `multilingual-e5-small` int8 ONNX (~118MB) | ~10-60ms per review |
| Clustering | KMeans (scikit-learn) | Fast, stable, user sets topic count |
| Keywords | YAKE! + embedding similarity reranking | YAKE! generates candidates, embedding reranks |
| Topic Labels | Top keywords per cluster | Auto label (e.g., "server, lag, matchmaking") |

### Tier 1 (GPU) - RTX 5060 Ti 16GB

| Step | Method | Notes |
|---|---|---|
| Embedding | `BGE-M3` (~2.3GB) | Higher accuracy, 100+ languages |
| Clustering | HDBSCAN | Auto-determines topic count, separates noise |
| Keywords | KeyBERT (embedding similarity + MMR) | Semantic, removes duplicate keywords |
| Topic Labels | KeyBERT keywords per cluster | More accurate labels |

### Analysis Flow

```
Reviews collected
  -> Generate embeddings for all reviews (once, cached)
  -> Split by positive/negative (voted_up)
  -> Cluster each group -> derive topics
  -> Extract keywords per cluster
  -> Save results to analysis_cache
```

### Filter Options (user-selectable in UI)

- Language: all / specific language
- Period: all / last 30 days / custom range
- Playtime: 0-2h / 2-10h / 10-50h / 50h+
- Purchase: steam purchase / free

When filter changes, re-cluster and re-extract keywords for matching reviews.

## UI Structure

### 4-Tab Layout

**Tab 1: Dashboard (Overview)**
- Game info card (name, score, total reviews)
- Positive/negative ratio donut chart
- Review trend line chart (daily/weekly/monthly toggle)
- Last 30 days vs all-time comparison
- Language distribution bar chart

**Tab 2: Topic/Keyword Analysis**
- Positive topics TOP N / Negative topics TOP N
- Per-topic: keyword list + review count + negative ratio
- Click topic -> show source reviews
- Word cloud (optional visualization)

**Tab 3: Segment Analysis**
- Filter panel (language, period, playtime, purchase type)
- Positive rate comparison bar chart by segment
- Review trend by playtime bracket
- Positive rate heatmap by language

**Tab 4: Export / AI Analysis**
- Export current filtered reviews (CSV, Markdown, Clipboard)
- Built-in LLM prompt templates
- API key settings (optional: Claude / OpenAI / Gemini)

### Common UI Elements

- Top bar: game selection/add (App ID input + URL paste)
- Sidebar: saved games list (click to switch)
- Compare mode: select 2 games -> side-by-side key metrics
- Settings: Tier toggle (auto/manual), model download management, API keys

## Export

### CSV
- Full review data (metadata + body)
- Reflects current filter
- UTF-8 BOM included (Excel Korean compatibility)

### Markdown
- Analysis summary (metrics + topics + keywords)
- Ready to paste into LLM

### Clipboard Copy (3 modes)
- Review text only (for analysis requests)
- Analysis summary (for sharing)
- Reviews + prompt template (for direct LLM paste)

### Built-in LLM Prompt Template

```
Below are [N] [positive/negative] reviews for the Steam game [Game Name].
Language: [selected language]
Period: [selected period]

Please analyze the following:
1. Classify main complaints/praises into 5 topics
2. Summarize representative opinions per topic
3. Suggest action items from a planning/marketing perspective

---
[Review data]
```

Users can edit/add templates in settings.

### Optional API Integration
- API key input in settings (Claude / OpenAI / Gemini)
- In-app analysis results
- Token usage display

## Multi-Game Comparison

- Sidebar에 분석한 게임들 저장 (SQLite에 영구 보관)
- 비교 모드: 게임 2개 선택 시 주요 지표 나란히 표시
  - 긍정률, 총 리뷰 수, 점수
  - 언어별 긍정률 비교
  - 토픽 키워드 비교
- 각 게임의 분석 데이터와 임베딩은 독립적으로 캐싱

## Privacy

- `author.steamid`는 저장하지 않음 (개인 식별 방지)
- `author.personaname`, `author.profile_url` 등 개인 정보 필드도 수집 제외
- 앱은 완전 로컬 — 외부 서버 전송 없음 (사용자가 직접 API 설정한 경우 제외)

## Scope Boundaries (Out of Scope for v1)

- 자동 주기적 수집 (스케줄러) — 수동 수집만 지원
- 로컬 LLM 내장 — export/API 경로로 대체
- 모바일/웹 버전
- Steam 외 플랫폼 (Epic, GOG 등)
