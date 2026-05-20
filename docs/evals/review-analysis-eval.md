# Review Analysis Evaluation

This file defines the working rubric for deciding whether ReviewForge's analysis is getting better.

## Primary Goal

The output should help a planner decide what to fix, preserve, expand, or communicate. A card that sounds fluent but cannot be traced to review evidence is not good output.

## Core Metrics

- Broad-label rate: how many top cards use generic labels instead of concrete player-facing issues or strengths.
- Verified evidence count: how many `match` evidence items support each card.
- Verdict distribution: `match`, `partial`, and `reject` counts should be visible and explainable.
- Language coverage: important issues should avoid unnecessary language silos when reviews in multiple languages express the same concern.
- Unique review ratio: repeated quotes from the same review should not inflate confidence.
- Duplicate issue rate: similar cards should not split the same player concern unless subissues are meaningful.
- Evidence polarity consistency: complaint, bug, request, and praise cards should not use the wrong kind of evidence as primary proof.

## Qualitative Review

For every meaningful analysis change, inspect examples in these buckets:

- improved outputs that are more specific or more actionable
- regressions where a label became misleading or overconfident
- ambiguous outputs that need user judgement
- evidence where the source review does not support the summary

## Pilot Dataset

Current recurring pilot games:

- Legend of Mortal, app id `1859910`
- Magical Girl Witch Trials, app id `3101040`
- Marfusha: Sentinel Girls, app id `1456820`

Add more games when a change is genre-sensitive. Do not assume one genre's issue axes transfer cleanly to another.

## Acceptance Questions

- Can the user tell what player-facing problem or strength the card describes?
- Can the user inspect source evidence without leaving the workflow?
- Does the card avoid causal claims unless causality was verified by a human?
- Would this output change a planning, patch, marketing, or sequel decision?
- Did the change avoid repeating an approach already rejected in `docs/research/decision-log.md`?
