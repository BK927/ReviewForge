# ReviewForge Backend

Local FastAPI + DuckDB backend for Steam review analysis.

## Run

```powershell
cd C:\Users\dead4\repo\ReviewForge\backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The database is created at `backend\data\reviewforge.duckdb` by default and is seeded when empty.

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

Then open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs`
