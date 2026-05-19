# ReviewForge Backend

Local FastAPI + DuckDB backend for Steam review analysis.

## Run

```powershell
cd C:\Users\dead4\repo\ReviewForge\backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The database is created at `backend\data\reviewforge.duckdb` by default and is seeded when empty.
Startup also creates a `games` row for every reviewed Steam `app_id` already in
DuckDB, plus the configured default app.

## Configure

Optional environment variables:

```powershell
$env:REVIEWFORGE_DB_PATH="C:\path\to\reviewforge.duckdb"
$env:REVIEWFORGE_STEAM_APP_ID="730"
```

## Quick Verification

```powershell
cd C:\Users\dead4\repo\ReviewForge\backend
uv run python -m compileall app scripts
uv run python scripts\smoke_test.py
```

The smoke test also runs the repository documentation guard, so newly added
FastAPI routes must be documented in `docs\api-contract.md`.

Then open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs`

## Multi-Game API Notes

- `GET /api/games` lists managed games with review, analysis, and next-action
  status.
- `POST /api/games` creates a game from `app_id`, `name`, `short_name`, `note`,
  and `tags`.
- `PUT` or `PATCH /api/games/{app_id}` updates the editable metadata.
- `DELETE /api/games/{app_id}` removes the game and its local scoped data.
- Dashboard, languages, events, reports, timeline, clusters, evidence, claims,
  issues, axes, and axis suggestions accept `app_id`; omitting it keeps the
  previous default-app behavior.
- Steam refresh and analysis requests automatically ensure their target game row
  exists.

## High-Quality Local Analysis

- When `embedding_model` is a SentenceTransformers model such as
  `intfloat/multilingual-e5-large`, the backend uses CUDA automatically when
  PyTorch can see an NVIDIA GPU.
- If GPU semantic embeddings fail, the analysis falls back to TF-IDF/KMeans and
  then keyword clustering, so large runs still complete.
- LM Studio model status is checked through native v1
  `http://127.0.0.1:1234/api/v1/models`, with OpenAI-compatible `/v1/models`
  as fallback.
