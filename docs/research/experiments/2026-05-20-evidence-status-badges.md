# 2026-05-20 Evidence Status Badges

## Question

Can issue cards avoid sounding final when their linked evidence has not passed verification?

## Hypothesis

Planner-facing cards should make verification state more visible than workflow status. If a card has only unverified evidence, lowering the badge from "근거 충분" to "미검증" should reduce premature patch, roadmap, or marketing decisions while preserving access to the card.

## Data

- Games: local ReviewForge games
- App IDs: selected app context
- Review counts: existing issue board data
- Analysis run IDs: latest succeeded issue analysis per app
- Sampling or filters: issue card evidence verdict counts from `/api/issues`

## Baseline

Cards could display a status label such as "근거 충분" even when `match_evidence_count` was zero and all linked evidence was unverified. The detailed evidence label still showed "미검증 연결", but the top badge looked too ready for action.

## Change

The issue board now derives the visible card/detail badge from evidence verdict counts first:

- one or more `match` evidence items: `검증 통과` or `검증된 강점`
- no match but partial evidence: `부분 관련`
- linked but unverified evidence: `미검증`
- no linked evidence: fallback status, with confirmed cards lowered to `검토 필요`

## Results

Quantitative signals:

- broad label rate: not evaluated
- verified match evidence: displayed more prominently
- partial/reject distribution: partial-only cards no longer look final
- language coverage: not changed
- duplicate or overlapping issue rate: not evaluated

Qualitative signals:

- improved examples: deterministic issue cards with only automatic evidence now read as `미검증` instead of `근거 충분`
- regressed examples: none observed yet
- ambiguous examples: a high-priority deterministic card can still be useful, but it now requires source review before external use

## User Feedback

The user asked for continuing improvements until the planner/marketer analysis has fewer misleading gaps.

## Decision

Adopt. This changes UI semantics only and is consistent with the contract that `match`, `partial`, and `reject` evidence are distinct.

## Follow-Up

Consider sorting issue cards by verified support within each planning lane once enough verified evidence exists in typical runs.
