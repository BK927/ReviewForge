from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class GameIn(BaseModel):
    app_id: str
    name: str | None = None
    short_name: str | None = None
    note: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: str | None = None


class GameUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    note: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class Game(BaseModel):
    app_id: str
    name: str
    short_name: str | None = None
    note: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: str
    language_count: int = 0
    positive_ratio: float | None = None
    cluster_count: int = 0
    evidence_count: int = 0
    last_sync_at: datetime | None = None
    last_analysis_at: datetime | None = None
    next_action: str
    created_at: datetime
    updated_at: datetime
    last_refreshed_at: datetime | None = None
    review_count: int = 0
    latest_review_at: datetime | None = None


class EventIn(BaseModel):
    app_id: str | None = None
    title: str
    event_type: str = Field(default="note")
    description: str | None = None
    occurred_at: datetime


class Event(EventIn):
    app_id: str
    id: int
    created_at: datetime


class DashboardSummary(BaseModel):
    total_reviews: int
    positive_reviews: int
    negative_reviews: int
    positive_ratio: float
    languages: int
    clusters: int
    evidence_items: int
    latest_review_at: datetime | None


class LanguageSummary(BaseModel):
    language: str
    review_count: int
    positive_count: int
    negative_count: int
    positive_ratio: float
    avg_weighted_score: float


class Review(BaseModel):
    recommendation_id: str
    app_id: str
    author_steamid: str | None = None
    language: str
    review: str
    voted_up: bool
    votes_up: int
    votes_funny: int
    weighted_vote_score: float
    playtime_forever: int
    playtime_at_review: int
    steam_created_at: datetime | None = None
    steam_updated_at: datetime | None = None
    collected_at: datetime
    cluster_score: float | None = None
    quality_score: float | None = None
    quality_flags: list[str] = Field(default_factory=list)
    duplicate_count: int | None = None


class Cluster(BaseModel):
    id: int
    analysis_run_id: int | None = None
    label: str
    summary: str
    sentiment: str
    language: str | None = None
    review_count: int
    avg_weighted_score: float
    exemplar_review_id: str | None = None
    positive_ratio: float | None = None
    top_keywords: list[str] = Field(default_factory=list)
    quality_warning: str | None = None
    insight: dict[str, Any] | None = None
    created_at: datetime


class Evidence(BaseModel):
    id: int
    analysis_run_id: int | None = None
    claim_id: int | None = None
    review_id: str
    cluster_id: int | None = None
    quote: str
    evidence_type: str
    evidence_role: str | None = None
    note: str | None = None
    quality_score: float | None = None
    claim_text: str | None = None
    claim_type: str | None = None
    created_at: datetime


class Claim(BaseModel):
    id: int
    analysis_run_id: int | None = None
    cluster_id: int | None = None
    claim_type: str
    claim_text: str
    confidence: float
    created_at: datetime


class ReportIn(BaseModel):
    app_id: str | None = None
    title: str
    summary: str
    filters: dict[str, Any] = Field(default_factory=dict)


class Report(ReportIn):
    app_id: str
    id: int
    analysis_run_id: int | None = None
    created_at: datetime


class SettingValue(BaseModel):
    key: str
    value: dict[str, Any]
    updated_at: datetime | None = None


class Job(BaseModel):
    id: int
    job_type: str
    status: str
    message: str | None = None
    progress: float
    started_at: datetime
    finished_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RefreshRequest(BaseModel):
    app_id: str | None = None
    max_reviews: int = Field(default=100, ge=1, le=50000)
    language: str | None = None
    review_type: str | None = None
    purchase_type: str | None = None
    use_live_steam: bool = True
    cursor: str | None = None
    sample_mode: bool = False


class RefreshResult(BaseModel):
    job: Job
    inserted_reviews: int
    updated_reviews: int
    source: str
    next_cursor: str | None = None
    has_more: bool = False


class AnalysisRunRequest(BaseModel):
    app_id: str | None = None
    scope: Literal["all", "new"] = "all"
    embedding_model: str | None = None
    min_cluster_size: int = Field(default=3, ge=1, le=1000)
    generate_ai_summary: bool = False
    llm_provider: str | None = None
    llm_model: str | None = "supergemma4-e4b-abliterated"
    min_quality_score: float = Field(default=0.25, ge=0, le=1)
    exclude_duplicate_evidence: bool = True
    use_lmstudio_labels: bool = True
    max_clusters: int = Field(default=60, ge=1, le=120)
    evidence_per_claim: int = Field(default=3, ge=1, le=10)


class AnalysisRun(BaseModel):
    id: int
    app_id: str | None = None
    status: str
    progress: float
    message: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    finished_at: datetime | None = None


class AnalysisRunResult(BaseModel):
    analysis_run: AnalysisRun
    job: Job
    clusters_created: int
    evidence_created: int
    reviews_analyzed: int
    clusterer: str
    message: str


class TimelinePoint(BaseModel):
    bucket_start: datetime
    review_count: int
    positive_count: int
    negative_count: int
    positive_ratio: float
    avg_weighted_score: float


class EventImpactWindow(BaseModel):
    review_count: int
    positive_count: int
    negative_count: int
    positive_ratio: float
    avg_weighted_score: float


class EventImpact(BaseModel):
    event: Event
    window_days: int
    before: EventImpactWindow
    after: EventImpactWindow
    delta: dict[str, float]
