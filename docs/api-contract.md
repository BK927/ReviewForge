# ReviewForge API Contract

Server origin: `http://127.0.0.1:8000`

Frontend code uses `http://127.0.0.1:8000/api` as its API base and appends
paths such as `/dashboard`. Endpoint paths below include the full server path
so generated clients do not accidentally call `/api/api/...`.

This is the current v1 local API. It is intentionally simple first: aggregate
screens read from DuckDB, while long-running analysis work is represented as
jobs that the UI can poll.

## Core Endpoints

- `GET /health`
- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/languages`
- `GET /api/games`
- `POST /api/games`
- `GET /api/games/{app_id}`
- `PUT /api/games/{app_id}`
- `PATCH /api/games/{app_id}`
- `DELETE /api/games/{app_id}`
- `GET /api/events`
- `POST /api/events`
- `PUT /api/events/{event_id}`
- `DELETE /api/events/{event_id}`
- `GET /api/clusters`
- `GET /api/clusters/{cluster_id}/reviews`
- `GET /api/evidence`
- `GET /api/claims`
- `GET /api/issues`
- `GET /api/issues/summary`
- `GET /api/issues/{issue_id}/evidence`
- `GET /api/axes`
- `POST /api/axes`
- `PATCH /api/axes/{axis_id}`
- `GET /api/axis-suggestions`
- `POST /api/axis-suggestions/{suggestion_id}/approve`
- `POST /api/axis-suggestions/{suggestion_id}/merge`
- `POST /api/axis-suggestions/{suggestion_id}/ignore`
- `POST /api/axis-suggestions/{suggestion_id}/keep`
- `GET /api/reports`
- `POST /api/reports`
- `GET /api/settings`
- `GET /api/settings/models`
- `PUT /api/settings/{key}`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/refresh-steam`
- `GET /api/analysis-runs`
- `POST /api/analysis-runs`
- `GET /api/timeline`
- `GET /api/events/{event_id}/impact`

`POST /api/refresh-steam` calls Steam by default. Use
`{"use_live_steam": false}` or `{"sample_mode": true}` for deterministic local
sample reviews. Supported request fields:

- `app_id`
- `max_reviews` up to `50000`
- `language`
- `review_type`
- `purchase_type`
- `cursor`
- `use_live_steam`
- `sample_mode`

The response includes `job`, `inserted_reviews`, `updated_reviews`, `source`,
`next_cursor`, and `has_more`.

## Game Management

ReviewForge stores one row per Steam game in `games`. On startup, the backend
seeds game rows from existing review `app_id` values and ensures the configured
default Steam app exists. Refresh and analysis requests also auto-create the
target game when needed.

Game APIs:

- `GET /api/games` returns games with review counts, language count, positive
  ratio, cluster/evidence counts, latest sync/analysis timestamps, status, and
  the next recommended action.
- `POST /api/games` accepts `app_id`, `name`, `short_name`, `note`, `tags`, and
  `status`.
- `GET /api/games/{app_id}` returns one game or `404`.
- `PUT /api/games/{app_id}` and `PATCH /api/games/{app_id}` accept `name`,
  `short_name`, `note`, `tags`, and `status`.
- `DELETE /api/games/{app_id}` deletes that game and its scoped local reviews,
  events, reports, analysis runs, clusters, evidence, and embeddings.

The following endpoints accept optional `app_id` and default to the configured
Steam app when omitted:

- `GET /api/dashboard`
- `GET /api/languages`
- `GET /api/events`
- `GET /api/reports`
- `GET /api/timeline`
- `GET /api/events/{event_id}/impact`
- `GET /api/clusters`
- `GET /api/evidence`
- `GET /api/claims`
- `GET /api/issues`
- `GET /api/issues/summary`
- `GET /api/axes`
- `GET /api/axis-suggestions`

`POST /api/analysis-runs` runs a local synchronous v1 analysis and records both
a job and an analysis run. Supported request fields:

- `app_id`
- `scope`: `all` or `new`
- `embedding_model`
- `min_cluster_size`
- `generate_ai_summary`
- `llm_provider`
- `llm_model`
- `min_quality_score`
- `exclude_duplicate_evidence`
- `use_lmstudio_labels`
- `max_clusters`
- `evidence_per_claim`

The backend prefers GPU-backed SentenceTransformers embeddings when an embedding
model such as `intfloat/multilingual-e5-large` is requested. If that path is not
available, it falls back to local TF-IDF clustering, then deterministic keyword
clustering, and reports the chosen `clusterer` in the analysis response. New
clusters, evidence, and generated reports are linked to `analysis_run_id`;
`GET /api/clusters` and `GET /api/evidence` prefer the latest completed run
while still tolerating seed data.

Cluster labels are diagnostic grouping labels, not final planning insights.
`GET /api/clusters` returns label audit metadata so the UI can show when a
cluster name is reliable enough to inspect and when the issue board should be
trusted first:

- `label_source`: `game_theme`, `common_theme`, `keyword`, or `fallback`.
- `label_confidence`: `high`, `medium`, or `low`; this is a heuristic label
  strength, not a statistical probability.
- `label_warnings`: reasons the label should be treated carefully.
- `matched_theme_key`: the selected theme key when a theme was considered.
- `matched_terms`: review expressions that supported the theme match.

`GET /api/timeline` accepts `app_id`, `bucket=day|week|month`, `language`,
`playtime_min`, and `playtime_max`.

`GET /api/events/{event_id}/impact` compares review windows before and after an
event. Treat the result as a temporal comparison, not a causal claim.

## Issue Board, Claims, and Axes

The issue board is the newer evidence-backed planning layer. It should move the
product away from broad cluster labels and toward concrete, review-linked
planning cards.

- `GET /api/claims` returns generated cluster-level claims. It accepts optional
  `app_id` and `cluster_id`.
- `GET /api/issues` returns issue cards. It accepts optional `app_id`, `status`,
  `intent`, `aspect`, and `limit`. Each card includes total linked
  `evidence_count` plus `match_evidence_count`, `partial_evidence_count`,
  `reject_evidence_count`, and `unverified_evidence_count` so planner-facing
  UI can distinguish verified support from audit context.
- `GET /api/issues/summary` returns issue counts, evidence counts, quarantined
  unit counts, and coverage for the latest run.
- `GET /api/issues/{issue_id}/evidence` returns linked evidence units for one
  issue. It accepts `limit` and optional `language`.
- `GET /api/axes` returns active, disabled, or candidate analysis axes. It
  accepts optional `app_id` and `status`.
- `POST /api/axes` creates a user-defined analysis axis from `key`, `label`,
  `description`, `pattern`, `recommended_action`, `scope`, optional `app_id`,
  optional `genre`, `status`, and `source`.
- `PATCH /api/axes/{axis_id}` updates editable axis metadata.
- `GET /api/axis-suggestions` returns quality-gated unmapped claim candidates.
  It accepts optional `app_id`, `status`, and `include_raw`.
- `POST /api/axis-suggestions/{suggestion_id}/approve` converts a suggestion
  into an active game-specific axis only when its quality gate passed.
- `POST /api/axis-suggestions/{suggestion_id}/merge?target_axis_id=...` merges
  a suggestion into an existing axis.
- `POST /api/axis-suggestions/{suggestion_id}/ignore` hides a suggestion.
- `POST /api/axis-suggestions/{suggestion_id}/keep` marks a passed suggestion
  as a one-off insight without creating or merging an axis.

Issue evidence can carry `verifier_verdict`, `summary_ko`, `subissue`, and
`verifier_reason`. Final issue cards should prefer verified `match` evidence;
`partial` and `reject` evidence are audit context, not primary proof.

## Documentation Guard

`scripts/check_docs.py` introspects FastAPI routes and fails if any route is
missing from this contract. When changing API routes, update this file in the
same change. If implementation needs to break product intent, follow
`AGENTS.md` and update `docs/project-intent.md` after explicit approval.

`GET /api/settings/models` reports the local GPU embedding provider and LM
Studio availability. It checks LM Studio native v1 at
`http://127.0.0.1:1234/api/v1/models` first, with OpenAI-compatible
`http://127.0.0.1:1234/v1/models` as fallback.

## Source Types

- `computed`: direct database aggregation
- `llm`: generated by a language model
- `manual`: user-entered metadata such as patch or sale dates

UI copy must not claim causation from event comparisons. Use wording like “changed together” or “increased after” unless a human verifies a causal claim.
