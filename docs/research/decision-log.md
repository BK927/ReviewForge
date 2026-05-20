# Research Decision Log

Short decisions live here so future AI work does not repeat old mistakes.

## 2026-05-20: Do not use pure clustering as final insight

Decision: rejected as the final planner-facing layer.

Reason: pure TF-IDF/KMeans or multilingual embedding clusters can reveal structure, but they often produce broad labels, split the same issue by language, or merge unrelated complaints.

Implication: clusters may remain as audit diagnostics. Final planning cards should be evidence-backed issues.

Source: `docs/review-analysis-research-log.md`

## 2026-05-20: Treat event impact as temporal comparison

Decision: event impact views must not claim causation.

Reason: the current API compares review windows before and after events. It does not prove that the event caused the change.

Implication: use copy such as "changed after" or "changed together" unless a human explicitly verifies causality.

Source: `docs/api-contract.md`, `docs/project-intent.md`

## 2026-05-20: Verified evidence is required for final issue cards

Decision: issue cards should prefer `match` evidence and keep `partial` or `reject` evidence as audit context.

Reason: LLM summaries can sound plausible while drifting from the source reviews. Evidence verdicts protect the planner from unsupported conclusions.

Implication: do not promote free-form LLM summaries into final planning claims without linked evidence.

Source: `docs/project-intent.md`, `docs/review-analysis-research-log.md`

## 2026-05-20: Cluster labels are diagnostic, not final insight titles

Decision: cluster labels should be treated as audit hints with visible source, confidence, and warnings.

Reason: broad common themes can create genre-inappropriate labels. Game-specific themes and conservative fallbacks are safer than confident but misleading labels.

Implication: planner-facing UI should prioritize issue cards; cluster screens should help inspect grouping quality and label risk.

Source: `docs/review-analysis-research-log.md`
