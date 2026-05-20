# 2026-05-20 Claim Axis Rule Expansion

## Question

Can deterministic claim-axis rules better capture concrete planner-facing issues for short-content games and RNG-heavy card/weapon loops?

## Hypothesis

Broad buckets such as `content_volume` and `balance` need narrower fallback rules so card titles and representative evidence point to actionable decisions. Adding rules for short content loops, weapon/card RNG, bleak ending tone, and price/value expectation should reduce generic labels when LLM verification is unavailable.

## Data

- Games: Legend of Mortal, Magical Girl Witch Trials, Marfusha:Sentinel Girls
- App IDs: `1859910`, `3101040`, `1456820`
- Review counts: 5,000; 5,000; 3,148
- Analysis run IDs: latest local issue run per app
- Sampling or filters: non-quarantined issue units, grouped by `aspect + intent`

## Baseline

The previous focus rules covered route guidance, mystery logic, update completion, ending afterstory, character/art, and localization. Marfusha-like issues around short runs, ending repetition, weapon/card RNG, and price/value could still remain under broad fallback axes.

## Change

Added deterministic `ClaimAxisRule` entries for:

- `short_content_loop`
- `weapon_card_rng`
- `bleak_ending_tone`
- `price_value_expectation`

Smoke tests now assert that broad `content_volume` evidence can narrow to short-content loop and broad `balance` evidence can narrow to weapon/card RNG.

After an actual-game pilot surfaced an awkward `가격 대비 기대와 가치 판단 문제` title on bug cards, bug cards were guarded to only use bug-compatible focus rules. This keeps price, ending tone, and short-content rules from overriding bug framing.

## Results

Quantitative signals:

- broad label rate: not fully measured
- verified match evidence: unchanged; deterministic evidence remains unverified
- partial/reject distribution: unchanged
- language coverage: unchanged
- duplicate or overlapping issue rate: not evaluated

Pilot read-only measurement after the bug-focus guard:

| App ID | New rule hits | Bug cards misfocused by these rules |
| --- | ---: | ---: |
| `1859910` | 6 | 0 |
| `3101040` | 4 | 0 |
| `1456820` | 9 | 0 |

Qualitative signals:

- improved examples: synthetic short-content evidence now titles as `짧은 분량과 반복 루프`
- improved examples: synthetic weapon/card RNG evidence now titles as `무기/카드 랜덤성과 통제감`
- improved examples: Marfusha local data now surfaces `어두운 엔딩 톤과 구원감 불만` and `짧은 분량과 반복 루프 불만` without applying those labels to bug cards
- ambiguous examples: price/value can overlap short-content complaints, so future pilot checks should inspect which rule wins in mixed evidence

## User Feedback

The user asked for analysis algorithm improvements and actual-game testing rather than UI-only polish.

## Decision

Adopt. The added rules are narrow, deterministic, and covered by smoke assertions.

## Follow-Up

Run a post-analysis pilot after regenerating issue outputs to measure how often these new rules replace broad `content_volume` or `balance` titles in real cards.
