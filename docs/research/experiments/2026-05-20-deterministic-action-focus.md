# 2026-05-20 Deterministic Action Focus

## Question

Can deterministic issue cards become more useful to planners and marketers before the full hybrid verifier pipeline is available?

## Hypothesis

If existing evidence-linked `ClaimAxisRule` matches are reused during card generation, broad aspect labels can be softened into more concrete focus titles. If the existing `recommended_action` field carries an explicit action taxonomy, planners can more quickly decide whether a card is about fixing, expanding, preserving, communicating, or marketing copy.

## Data

- Games: smoke-test sample data plus synthetic helper cases
- App IDs: default smoke app and synthetic cards
- Review counts: smoke fixture size only
- Analysis run IDs: temporary smoke-test database
- Sampling or filters: deterministic issue-card helper cases for route guidance complaints and character/art praise

## Baseline

Deterministic cards used `aspect label + intent suffix` for titles, such as broad `분량/완성도 불만` or `스토리/세계관/엔딩 강점`. `recommended_action` came directly from the matched aspect, so praise and complaint cards could both read like generic planning notes instead of a clear next action.

## Change

- `_build_issue_card` now derives an optional evidence focus from existing `ClaimAxisRule` matches.
- Broad generic aspects can use that focus in the card title, summary, and `why_it_matters`.
- Praise titles use `활용 포인트` instead of treating positive feedback like a problem card.
- `recommended_action` now prefixes a deterministic taxonomy such as `수정`, `개선/확장`, `유지/확장`, `홍보 문구/확장`, or `소통/기대 관리`, while preserving the original aspect or claim-rule action text.
- No API routes or response fields changed.

## Results

Quantitative signals:

- broad label rate: not yet measured on the three pilot games
- verified match evidence: unchanged; this is deterministic pre-verifier copy
- partial/reject distribution: unchanged
- language coverage: unchanged
- duplicate or overlapping issue rate: unchanged

Qualitative signals:

- improved examples: synthetic `content_volume` evidence with route/choice/save terms becomes `루트/선택지 안내와 세이브 편의 불만` instead of only `분량/완성도 불만`.
- improved examples: synthetic praise around character art and music becomes a `캐릭터/아트/연출 매력 활용 포인트` with `추천 액션(홍보 문구/확장)`.
- regressed examples: not observed in smoke helpers, but broad labels remain when no stable claim rule matches the evidence.
- ambiguous examples: action taxonomy is heuristic and should not be treated as a verified strategic decision.

## User Feedback

The user asked for a small, safe backend/algorithm improvement helpful to planners or marketers, prioritizing evidence-based action recommendations, praise/complaint separation, broad title mitigation, marketing-copy signal, and a maintenance/expand/fix/communicate action taxonomy.

## Decision

Adopt as a deterministic fallback improvement. It reuses existing evidence-linked rules and does not remove verifier behavior or deterministic fallbacks.

## Follow-Up

Measure top-card broad-label rate on the pilot games and compare action usefulness before and after full LLM verifier enrichment. If taxonomy labels feel too coarse, consider storing a structured action type in a future API change instead of encoding it in `recommended_action`.
