# ReviewForge

Local Steam review analysis workspace.

## Stack

- Frontend: SvelteKit + TypeScript
- Backend: FastAPI
- Database: DuckDB
- Analysis: synchronous Python analysis pipeline with deterministic fallbacks
- LLM: LM Studio integration, using OpenAI-compatible local endpoints where available

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
.\scripts\check.ps1
```

Or run the major checks individually:

```powershell
cd backend
uv run python scripts\smoke_test.py

cd ..\frontend
npm run check
npm run build
```

`scripts\check.ps1` and the backend smoke test include a documentation guard:
FastAPI routes must be listed in `docs\api-contract.md`, and the AI/project
intent guardrails in `AGENTS.md` and `docs\project-intent.md` must remain in
place.
