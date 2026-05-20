# 2026-05-20 Event Impact Topics

## Question

Can event impact screens show what moved together around a patch, sale, or note without claiming the event caused the change?

## Hypothesis

Planners and marketers need more than before/after review counts. Showing issue-unit aspect + intent changes should make the event view useful for patch review and campaign retrospectives while staying inside the no-causation contract.

## Data

- Games: local ReviewForge games
- App IDs: selected app context
- Review counts: endpoint-dependent
- Analysis run IDs: latest succeeded issue analysis per app
- Sampling or filters: reviews in the selected before/after window; non-quarantined issue units only

## Baseline

`GET /api/events/{event_id}/impact` returned before/after review counts, positive ratio, weighted score, and deltas. The frontend already had a "함께 움직인 표현" panel, but the backend did not provide topic rows, so the panel could only show a placeholder.

## Change

The event impact endpoint now returns `topics`:

- preferred source: latest issue analysis `issue_units`, grouped by `aspect + intent`
- fallback source: review language distribution
- ranking: absolute share-point movement, then total before/after count
- wording: co-movement and before/after comparison only

## Results

Quantitative signals:

- broad label rate: not evaluated in this change
- verified match evidence: not directly evaluated; issue units remain the source of the topic movement signal
- partial/reject distribution: not evaluated
- language coverage: fallback covers language movement when issue units are unavailable
- duplicate or overlapping issue rate: not evaluated

Qualitative signals:

- improved examples: event view can now show `분기/힌트/공략 의존 · 불만` or a language fallback row instead of an empty topic panel
- regressed examples: none observed yet
- ambiguous examples: a topic can move because of sampling or timing; UI/docs must keep the non-causal wording

## User Feedback

The user asked to continuously research logic/cases and improve the tool for game planners and marketers, committing improvements at each stage.

## Decision

Adopt. This is a deterministic, low-risk API extension that uses existing issue-unit outputs and keeps a language fallback when issue analysis is unavailable.

## Follow-Up

Evaluate whether event topics should also expose segment tags such as early-player, long-player, or language concentration once sample-size guards are stable.
