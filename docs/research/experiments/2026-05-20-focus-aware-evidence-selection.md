# 2026-05-20 Focus-Aware Evidence Selection

## Question

Can deterministic issue cards keep their representative evidence aligned with the more specific focus used in the card title?

## Hypothesis

When a broad issue bucket is narrowed by a `ClaimAxisRule`, the evidence selector should prefer units that match that same focus. This should reduce cases where a card title says "route guidance" but the first evidence snippets are generic content-volume complaints.

## Data

- Games: Legend of Mortal, Magical Girl Witch Trials, Marfusha:Sentinel Girls
- App IDs: `1859910`, `3101040`, `1456820`
- Review counts: 5,000; 5,000; 3,148
- Analysis run IDs: latest local issue run per app
- Sampling or filters: non-quarantined issue units, grouped by `aspect + intent`

## Baseline

`_build_issue_card` selected representative evidence before deciding the focus rule. The title could be narrowed after evidence selection, but the evidence list still reflected the broad aspect bucket ordering.

## Change

- Compute the focus rule from all card members before selecting evidence.
- Sort representative evidence by focus-rule term matches before quality and length.
- Add deterministic `subissue` labels to selected evidence that matched the focus rule.
- Keep `verifier_verdict` unset for deterministic evidence; the selector does not claim verification.
- Harden Latin rule-term matching with word boundaries so short terms such as `art` do not match unrelated substrings.

## Results

Quantitative signals:

- broad label rate: not evaluated
- verified match evidence: unchanged; deterministic evidence remains unverified
- partial/reject distribution: unchanged
- language coverage: selection still keeps the existing language diversity cap
- duplicate or overlapping issue rate: not evaluated

Pilot read-only measurement using current local issue units:

| App ID | Focused cards | First evidence aligned with card focus |
| --- | ---: | ---: |
| `1859910` | 10 | 10 |
| `3101040` | 3 | 3 |
| `1456820` | 19 | 19 |

Qualitative signals:

- improved examples: route guidance cards now store focused evidence subissues for representative units
- regressed examples: none observed yet
- ambiguous examples: if too few focus-matching units exist, the selector still fills from the broader candidate pool

## User Feedback

The user specifically asked for backend analysis algorithm improvements and testing, not only UI changes.

## Decision

Adopt. This is a deterministic algorithm improvement with smoke coverage and no API route change.

## Follow-Up

Run a pilot comparison on top issues for app IDs `1859910`, `3101040`, and `1456820` to measure focused-evidence rate and broad-label rate before and after.
