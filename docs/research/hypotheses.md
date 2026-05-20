# Research Hypotheses

Use this as a backlog for analysis ideas that still need validation. Move an item into `experiments/` when tested, then summarize the outcome in `decision-log.md`.

## Open

### Hybrid issue pipeline improves planning usefulness

Hypothesis: candidate recall plus semantic filtering plus verifier judgement will produce more concrete planning cards than pure clustering or broad deterministic aspect labels.

Signals to measure:

- fewer broad final titles
- more verified `match` evidence per card
- better multilingual evidence coverage
- lower duplicate issue rate
- user can decide an action after reading the card and evidence

### Cluster audit should stay secondary

Hypothesis: raw clusters are useful as a diagnostic surface, but they should not be the primary planner-facing insight view because broad or genre-inappropriate labels can mislead users.

Signals to measure:

- fewer user reports of misleading cluster titles
- cluster warnings reveal low-confidence labels before users treat them as conclusions
- issue board remains the default place for planning decisions

### Evidence translation should be lazy and auditable

Hypothesis: Korean summaries are enough for fast scanning if the original text and review metadata remain one click away.

Signals to measure:

- user can triage cards without reading every original language
- source text still catches mistranslation or verifier mistakes
- translation cost stays bounded

## Closed Or Superseded

Closed items should move into `decision-log.md` with a link to the experiment that resolved them.
