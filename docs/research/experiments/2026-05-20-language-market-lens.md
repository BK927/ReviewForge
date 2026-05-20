# 2026-05-20 Language Market Lens

## Question

Can ReviewForge make language-specific review differences useful for game planners and marketers without splitting multilingual issues into separate conclusions?

## Hypothesis

Language-specific review scores and evidence concentration can change market decisions. Surfacing issue-backed language concentration should help teams separate global product problems, local market risks, and locale-specific marketing proof points while preserving original evidence.

## Data

- Games: local ReviewForge games
- App IDs: selected app context
- Review counts: existing `/api/languages` and `/api/issues` responses
- Analysis run IDs: latest succeeded issue analysis per app
- Sampling or filters: issue card `language_counts` and `segment_factors.language_counts`

## Baseline

The language screen compared aggregate review counts, positive ratio, and weighted score by language. It did not connect language differences to concrete issue cards, so planners still had to jump manually from language metrics to evidence-backed decisions.

## Change

The language comparison screen now includes a "언어권별 시장 렌즈" section that ranks issue cards by language concentration and priority. Rows are labeled as local review, shared improvement, or marketing material, and selecting a row opens the underlying evidence-backed issue card.

## Results

Quantitative signals:

- broad label rate: not evaluated
- verified match evidence: inherited from issue card counts, not changed
- partial/reject distribution: not changed
- language coverage: displayed from issue card and segment language counts
- duplicate or overlapping issue rate: not evaluated

Qualitative signals:

- improved examples: language tab can now show a KO- or ZH-concentrated complaint as local review work, while repeated praise can become a locale-aware marketing material candidate
- regressed examples: none observed yet
- ambiguous examples: high concentration can reflect sample size, collection mix, or translation quality; the UI labels it as a review lens rather than causation

## User Feedback

The user asked to keep researching cases and logic improvements until the tool is more useful for planners and marketers.

## Decision

Adopt. This is a frontend-only decision lens over existing evidence-backed issue data and does not change the analysis pipeline.

## Follow-Up

Add sample-size guards and a backend-provided `market_lens` object if language concentration needs to become an API contract rather than a UI-derived view.
