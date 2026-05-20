# 2026-05-20 Hybrid Issue Pipeline

## Question

Can ReviewForge move from broad topic labels to concrete multilingual planning issues backed by review evidence?

## Hypothesis

Candidate recall, semantic filtering, and LLM verifier judgements should produce more useful issue cards than pure clustering or keyword-only labels.

## Data

- Games: Legend of Mortal, Magical Girl Witch Trials, Marfusha: Sentinel Girls
- App IDs: `1859910`, `3101040`, `1456820`
- Review counts: 5,000, 5,000, and 3,148
- Analysis run IDs: `33`, `34`, `35`
- Sampling or filters: existing local Steam review data and issue-unit samples

## Baseline

The top issue names were broad labels such as balance/RNG complaint, UI/onboarding complaint, progression strength, or generic praise. These labels summarized data but did not reliably give a planner a concrete action.

## Change

The research tested a pipeline of opinion-unit extraction, multilingual candidate recall, semantic matching, LLM evidence verification, issue reduction, and card generation from verified evidence.

## Results

Quantitative signals from the pilot:

- broad label rate: baseline top 10 labels were broad across all three games
- verified match evidence: pilot issues produced `match` evidence across several languages
- partial/reject distribution: Magical Girl Witch Trials and Marfusha examples showed that ambiguous or off-target evidence could be separated
- language coverage: several tested issues gathered Korean, English, Japanese, Chinese, and other language evidence
- duplicate or overlapping issue rate: still requires human review

Qualitative signals:

- improved examples: mystery logic and magic-rule complaints became a concrete issue for Magical Girl Witch Trials
- improved examples: Marfusha's short-content loop and bleak-ending tone separated better than generic repetition labels
- regressed or risky examples: LLM output could break JSON format on large batches, and some evidence references became temporary labels instead of real review IDs
- ambiguous examples: seed definitions strongly affected recall and precision

## User Feedback

The user wants the system to preserve not only problems but also positive feedback as planning material for maintenance, sequel direction, marketing copy, and patch-note emphasis.

## Decision

Adopt the direction, but do not treat it as complete. Keep deterministic fallbacks and make the issue board evidence-auditable before relying on LLM-generated cards.

## Follow-Up

Build small pilots before full production rollout. Track broad label rate, verified evidence count, multilingual coverage, duplicate issue rate, and whether the user can make a planning decision from each card.
