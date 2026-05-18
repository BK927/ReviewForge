from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import repository
from .analysis import model_settings_status, run_local_analysis
from .config import get_settings
from .db import initialize_database
from .models import (
    AnalysisRun,
    AnalysisRunRequest,
    AnalysisRunResult,
    Cluster,
    DashboardSummary,
    Event,
    EventImpact,
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
    TimelinePoint,
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
def clusters(language: str | None = None, app_id: str | None = None) -> list[dict]:
    return repository.list_clusters(language, app_id)


@app.get("/api/clusters/{cluster_id}/reviews", response_model=list[Review])
def reviews_for_cluster(
    cluster_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    return repository.cluster_reviews(cluster_id, limit, offset)


@app.get("/api/evidence", response_model=list[Evidence])
def evidence(cluster_id: int | None = None, evidence_type: str | None = None, app_id: str | None = None) -> list[dict]:
    return repository.list_evidence(cluster_id, evidence_type, app_id)


@app.get("/api/reports", response_model=list[Report])
def reports() -> list[dict]:
    return repository.list_reports()


@app.post("/api/reports", response_model=Report)
def create_report(payload: ReportIn) -> dict:
    return repository.create_report(payload)


@app.get("/api/settings", response_model=list[SettingValue])
def settings() -> list[dict]:
    return repository.list_settings()


@app.get("/api/settings/models")
async def settings_models() -> dict:
    return await model_settings_status()


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


@app.get("/api/analysis-runs", response_model=list[AnalysisRun])
def analysis_runs(app_id: str | None = None) -> list[dict]:
    return repository.list_analysis_runs(app_id)


@app.post("/api/analysis-runs", response_model=AnalysisRunResult)
def create_analysis_run(payload: AnalysisRunRequest) -> dict:
    settings = get_settings()
    app_id = payload.app_id or settings.steam_app_id
    params = payload.model_dump()
    params["app_id"] = app_id
    started_job = repository.create_job(
        "analysis_run",
        "running",
        "Starting local analysis",
        {"app_id": app_id, "scope": payload.scope},
    )
    run = repository.create_analysis_run(app_id, params)
    try:
        repository.update_job(
            started_job["id"],
            "running",
            "Clustering review text",
            0.35,
            {"app_id": app_id, "analysis_run_id": run["id"]},
        )
        repository.update_analysis_run(
            run["id"],
            status="running",
            progress=0.35,
            message="Clustering review text",
        )
        result = run_local_analysis(
            analysis_run_id=run["id"],
            app_id=app_id,
            scope=payload.scope,
            embedding_model=payload.embedding_model,
            min_cluster_size=payload.min_cluster_size,
            generate_ai_summary=payload.generate_ai_summary,
            llm_provider=payload.llm_provider,
        )
        finished_run = repository.update_analysis_run(
            run["id"],
            status="succeeded",
            progress=1,
            message=result.message,
            finished=True,
        )
        finished_job = repository.finish_job(
            started_job["id"],
            "succeeded",
            result.message,
            metadata={
                "app_id": app_id,
                "analysis_run_id": run["id"],
                "reviews": result.reviews_analyzed,
                "clusters": result.clusters_created,
                "clusterer": result.clusterer,
            },
        )
        return {
            "analysis_run": finished_run,
            "job": finished_job,
            "clusters_created": result.clusters_created,
            "evidence_created": result.evidence_created,
            "reviews_analyzed": result.reviews_analyzed,
            "clusterer": result.clusterer,
            "message": result.message,
        }
    except Exception as exc:
        failed_run = repository.update_analysis_run(
            run["id"],
            status="failed",
            progress=0,
            message=str(exc),
            finished=True,
        )
        failed_job = repository.finish_job(
            started_job["id"],
            "failed",
            str(exc),
            progress=0,
            metadata={"app_id": app_id, "analysis_run_id": run["id"]},
        )
        return {
            "analysis_run": failed_run,
            "job": failed_job,
            "clusters_created": 0,
            "evidence_created": 0,
            "reviews_analyzed": 0,
            "clusterer": "failed",
            "message": str(exc),
        }


@app.get("/api/timeline", response_model=list[TimelinePoint])
def timeline(
    app_id: str | None = None,
    bucket: str = Query(default="day", pattern="^(day|week|month)$"),
    language: str | None = None,
    playtime_min: int | None = Query(default=None, ge=0),
    playtime_max: int | None = Query(default=None, ge=0),
) -> list[dict]:
    return repository.review_timeline(
        app_id=app_id,
        bucket=bucket,
        language=language,
        playtime_min=playtime_min,
        playtime_max=playtime_max,
    )


@app.get("/api/events/{event_id}/impact", response_model=EventImpact)
def event_impact(
    event_id: int,
    window_days: int = Query(default=14, ge=1, le=365),
    app_id: str | None = None,
) -> dict:
    impact = repository.event_impact(event_id, window_days, app_id)
    if not impact:
        raise HTTPException(status_code=404, detail="Event not found")
    return impact


@app.post("/api/refresh-steam", response_model=RefreshResult)
async def refresh_steam(payload: RefreshRequest) -> dict:
    settings = get_settings()
    app_id = payload.app_id or settings.steam_app_id
    language = payload.language or settings.steam_language
    review_type = payload.review_type or settings.steam_review_type
    purchase_type = payload.purchase_type or settings.steam_purchase_type
    sample_mode = payload.sample_mode or not payload.use_live_steam
    started = repository.create_job(
        "steam_refresh",
        "running",
        "Refreshing Steam reviews",
        {"app_id": app_id, "live": not sample_mode, "cursor": payload.cursor},
    )
    try:
        if sample_mode:
            rows = placeholder_reviews(app_id, min(payload.max_reviews, 5000))
            source = "sample"
            next_cursor = None
            has_more = False
        else:
            fetched = await fetch_steam_reviews(
                app_id,
                language=language,
                review_type=review_type,
                purchase_type=purchase_type,
                max_reviews=payload.max_reviews,
                cursor=payload.cursor,
            )
            rows = fetched.rows
            source = "steam"
            next_cursor = fetched.next_cursor
            has_more = fetched.has_more
        inserted, updated = repository.upsert_reviews(rows)
        repository.upsert_setting(
            "steam",
            {"app_id": app_id, "language": language, "review_type": review_type, "purchase_type": purchase_type},
        )
        repository.upsert_setting(
            "steam_cursor",
            {
                "app_id": app_id,
                "cursor": next_cursor,
                "has_more": has_more,
                "source": source,
            },
        )
        finished = repository.finish_job(
            started["id"],
            "succeeded",
            f"Refresh completed from {source}",
            metadata={
                "app_id": app_id,
                "inserted": inserted,
                "updated": updated,
                "source": source,
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        )
        return {
            "job": finished,
            "inserted_reviews": inserted,
            "updated_reviews": updated,
            "source": source,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
    except Exception as exc:
        failed = repository.finish_job(started["id"], "failed", str(exc), progress=0, metadata={"app_id": app_id})
        return {
            "job": failed,
            "inserted_reviews": 0,
            "updated_reviews": 0,
            "source": "error",
            "next_cursor": None,
            "has_more": False,
        }
