# ReviewForge

Local Steam review analysis workspace.

## Stack

- Frontend: SvelteKit + TypeScript
- Backend: FastAPI
- Database: DuckDB
- Analysis: Python workers
- LLM: LM Studio by default, with Claude/OpenAI-ready settings

## Local Run

Start both local servers:

```powershell
.\scripts\dev.ps1
```

The app exposes:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000/api`

Run checks:

```powershell
cd backend
uv run python scripts\smoke_test.py

cd ..\frontend
npm run check
npm run build
```
