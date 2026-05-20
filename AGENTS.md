# ReviewForge Agent Contract

This repository uses documentation as both human context and an AI coding guardrail.
Before changing code, read this file plus the documents it points to.

## Read First

- [docs/project-intent.md](docs/project-intent.md): product intent and non-negotiable behavior.
- [docs/api-contract.md](docs/api-contract.md): local API surface and wording constraints.
- [docs/research/decision-log.md](docs/research/decision-log.md): adopted and rejected analysis decisions.
- [docs/research/hypotheses.md](docs/research/hypotheses.md): unproven analysis ideas.
- [docs/review-analysis-research-log.md](docs/review-analysis-research-log.md): current analysis pipeline rationale and known failure modes.
- [docs/evals/review-analysis-eval.md](docs/evals/review-analysis-eval.md): evaluation rubric for analysis quality.
- [README.md](README.md) and [backend/README.md](backend/README.md): run and verification commands.

## Intent Change Protocol

If a requested code change conflicts with documented intent, stop before editing.
Explain the conflict, name the affected document section, and ask whether to change the intent.
If the user approves the change, update the relevant document in the same change as the code.

Treat these as intent conflicts unless the user explicitly changes direction:

- Event impact screens compare review windows; they must not claim causation.
- Issue cards must be grounded in linked evidence, not free-form LLM summaries.
- `match`, `partial`, and `reject` evidence are distinct. Final card evidence should prefer verified `match` items.
- Broad labels such as "balance/RNG complaint" are fallback tags, not the desired final insight title.
- Positive feedback is first-class: preserve strengths for maintenance, expansion, marketing, and sequel planning.
- Production analysis changes should keep deterministic fallbacks when optional GPU or LLM paths are unavailable.

## Documentation Rules

- If you add, remove, or rename a backend API route, update `docs/api-contract.md`.
- If you change analysis behavior, evidence rules, issue card semantics, or LLM verification, update `docs/project-intent.md` or `docs/review-analysis-research-log.md`.
- If you change analysis algorithms, prompts, thresholds, verifier behavior, evidence selection, cluster labeling, issue axes, or planner-facing analysis semantics, add or update a research record under `docs/research/` or `docs/evals/`.
- If user feedback accepts, rejects, or redirects an analysis approach, preserve that feedback in the relevant experiment or `docs/research/decision-log.md`.
- If you change local run or verification commands, update `README.md` and any affected component README.
- Do not leave stale docs for a later pass when the same change already knows the new behavior.

## Research Memory Protocol

Before algorithm work, check `docs/research/decision-log.md` for rejected approaches and `docs/research/hypotheses.md` for open ideas.
During algorithm work, keep enough notes to fill one experiment card.
After algorithm work, update one of:

- `docs/research/experiments/YYYY-MM-DD-short-name.md` for a meaningful attempt
- `docs/research/decision-log.md` for a durable adopt/reject/hold decision
- `docs/evals/review-analysis-eval.md` when the evaluation rubric changes

Use `docs/research/experiments/TEMPLATE.md` for new experiment records.

## Verification

Run the smallest relevant checks. For broad changes, prefer:

```powershell
.\scripts\check.ps1
```

For backend-only changes, at least run:

```powershell
cd backend
uv run python scripts\smoke_test.py
```

The smoke test includes a documentation guard that fails when FastAPI routes are missing from `docs/api-contract.md`.
