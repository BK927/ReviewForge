from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import repository
from .config import get_settings
from .db import initialize_database
from .models import (
    Cluster,
    DashboardSummary,
    Event,
    EventIn,
    Evidence,
    Job,
    LanguageSummary,
    RefreshRequest,
    RefreshResult,
    Report,
    ReportIn,
    Review,
    SettingValue,
)
from .steam import fetch_steam_reviews, placeholder_reviews


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="ReviewForge API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return health()


@app.get("/api/dashboard", response_model=DashboardSummary)
def dashboard() -> dict:
    return repository.dashboard_summary()


@app.get("/api/languages", response_model=list[LanguageSummary])
def languages() -> list[dict]:
    return repository.language_summaries()


@app.get("/api/events", response_model=list[Event])
def events() -> list[dict]:
    return repository.list_events()


@app.post("/api/events", response_model=Event)
def create_event(payload: EventIn) -> dict:
    return repository.create_event(payload)


@app.put("/api/events/{event_id}", response_model=Event)
def update_event(event_id: int, payload: EventIn) -> dict:
    event = repository.update_event(event_id, payload)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.delete("/api/events/{event_id}")
def delete_event(event_id: int) -> dict[str, bool]:
    deleted = repository.delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": True}


@app.get("/api/clusters", response_model=list[Cluster])
def clusters(language: str | None = None) -> list[dict]:
    return repository.list_clusters(language)


@app.get("/api/clusters/{cluster_id}/reviews", response_model=list[Review])
def reviews_for_cluster(
    cluster_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return repository.cluster_reviews(cluster_id, limit, offset)


@app.get("/api/evidence", response_model=list[Evidence])
def evidence(cluster_id: int | None = None, evidence_type: str | None = None) -> list[dict]:
    return repository.list_evidence(cluster_id, evidence_type)


@app.get("/api/reports", response_model=list[Report])
def reports() -> list[dict]:
    return repository.list_reports()


@app.post("/api/reports", response_model=Report)
def create_report(payload: ReportIn) -> dict:
    return repository.create_report(payload)


@app.get("/api/settings", response_model=list[SettingValue])
def settings() -> list[dict]:
    return repository.list_settings()


@app.put("/api/settings/{key}", response_model=SettingValue)
def update_setting(key: str, payload: dict) -> dict:
    return repository.upsert_setting(key, payload)


@app.get("/api/jobs", response_model=list[Job])
def jobs() -> list[dict]:
    return repository.list_jobs()


@app.get("/api/jobs/{job_id}", response_model=Job)
def job(job_id: int) -> dict:
    found = repository.get_job(job_id)
    if not found:
        raise HTTPException(status_code=404, detail="Job not found")
    return found


@app.post("/api/refresh-steam", response_model=RefreshResult)
async def refresh_steam(payload: RefreshRequest) -> dict:
    settings = get_settings()
    app_id = payload.app_id or settings.steam_app_id
    started = repository.create_job(
        "steam_refresh",
        "running",
        "Refreshing Steam reviews",
        {"app_id": app_id, "live": payload.use_live_steam},
    )
    try:
        if payload.use_live_steam:
            rows = await fetch_steam_reviews(
                app_id,
                language=settings.steam_language,
                review_type=settings.steam_review_type,
                purchase_type=settings.steam_purchase_type,
                max_reviews=payload.max_reviews,
            )
            source = "steam"
        else:
            rows = placeholder_reviews(app_id, min(payload.max_reviews, 25))
            source = "stub"
        inserted, updated = repository.upsert_reviews(rows)
        repository.rebuild_placeholder_clusters()
        finished = repository.finish_job(
            started["id"],
            "succeeded",
            f"Refresh completed from {source}",
            metadata={"app_id": app_id, "inserted": inserted, "updated": updated, "source": source},
        )
        return {"job": finished, "inserted_reviews": inserted, "updated_reviews": updated, "source": source}
    except Exception as exc:
        failed = repository.finish_job(started["id"], "failed", str(exc), progress=0, metadata={"app_id": app_id})
        return {"job": failed, "inserted_reviews": 0, "updated_reviews": 0, "source": "error"}
