# ReviewForge Research Memory

This directory is the research memory for ReviewForge's review-analysis algorithms.
Use it to preserve what was tried, why it worked or failed, and what the user decided.

## When To Write Here

Create or update a research record when a change touches:

- review analysis, clustering, issue generation, evidence selection, or verifier logic
- analysis DB schema or response fields that change algorithm interpretation
- planner-facing issue card semantics, cluster audit semantics, or evidence UX
- prompts, model settings, fallback order, thresholds, or quality filters
- user feedback that accepts, rejects, or redirects an analysis approach

Small UI copy fixes, pure styling, dependency chores, and unrelated API plumbing do not need a new experiment unless they change analysis meaning.

## Working Memory Files

- `hypotheses.md`: backlog of ideas that are not yet proven.
- `decision-log.md`: short durable decisions, including rejected approaches.
- `experiments/`: one file per meaningful attempt, using `experiments/TEMPLATE.md`.
- `../evals/review-analysis-eval.md`: current evaluation rubric and pilot dataset notes.

The old `docs/review-analysis-research-log.md` remains historical context. New work should create smaller experiment cards here and only add to the old log when preserving a long-form narrative is useful.

## Required Experiment Shape

Each experiment should answer:

- What question are we testing?
- What data or games did we use?
- What changed compared with the baseline?
- What improved, regressed, or stayed ambiguous?
- What did the user say?
- What did we decide: adopt, reject, or hold?

Keep records compact. A useful one-page experiment is better than a perfect document that nobody writes.

## User Feedback Rule

When the user gives qualitative feedback, preserve it in either the relevant experiment or `decision-log.md`.
Do not translate feedback into a different product direction unless the user explicitly agrees.
