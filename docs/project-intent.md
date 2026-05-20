# ReviewForge Project Intent

ReviewForge is a local Steam review analysis workspace for turning multilingual player reviews into evidence-backed planning insight. It is not just a topic dashboard. The product should help a planner decide what to fix, preserve, expand, or communicate.

## Product Principles

- Evidence first: every important claim should connect back to review IDs, quoted text, language, sentiment, and analysis run context.
- Specific insight over broad buckets: broad tags such as `balance`, `UI`, or `content` can help grouping, but final issue titles should describe a concrete player-facing problem or strength.
- Multilingual by default: Korean, English, Japanese, Chinese, and other languages should be allowed to support the same issue when the meaning matches.
- Strengths matter too: praise is useful for preserving core fun, planning sequels, writing store copy, and deciding what not to break.
- Local-first operation: the app should keep useful deterministic behavior when Steam, GPU embeddings, LM Studio, or other optional services are unavailable.

## Analysis Intent

The desired direction is a hybrid issue pipeline:

1. Extract opinion units from reviews.
2. Recall candidates with game or genre issue axes, multilingual keywords, and semantic matching.
3. Separate uncertain evidence instead of forcing every review into an issue.
4. Verify evidence before final card generation with `match`, `partial`, and `reject`.
5. Generate concise issue cards from verified evidence only.
6. Keep source review data inspectable from the UI.

Current deterministic code may still use fallback clustering and rule-based issue generation. When changing it, move toward the hybrid pipeline above without removing reliable fallback behavior.

## Non-Negotiable Copy Rules

- Event comparisons are temporal comparisons, not causal proof. UI and API copy should say that metrics "changed after" or "changed together"; do not claim an event "caused" a change unless a human has explicitly verified causality.
- Avoid empty generated claims such as "positive feedback is observed", "complaints repeat", or "related opinions exist". Replace them with the concrete player-facing signal.
- Complaint, bug, request, and praise cards must not swap evidence polarity. Pure praise should not become complaint evidence, and pure complaint should not become praise evidence.
- Do not present heuristic `confidence` as a statistical probability. In planner-facing UI, prefer evidence strength, verified evidence counts, verdict distribution, and language coverage.
- Insight cards should be explorable in place. A user should be able to move from a card to subissues, verified evidence, partial/rejected evidence, and source-review context without guessing which separate page to open.
- Cluster labels are a diagnostic aid, not final insight titles. Game-specific themes should be preferred when available, broad/common themes need visible source and strength metadata, and genre-inappropriate labels should fall back to conservative keyword diagnostics instead of sounding certain.
- Raw cluster diagnostics should not be a first-class planner screen. Planner-facing surfaces should start from evidence-backed insight cards, source reviews, subissues, and recommended planning actions. Automatic grouping outputs may remain available for backend debugging or advanced audit workflows, but they should not be presented as the product answer.

## Documentation Contract

Documentation is part of the development harness. Code changes should update docs when they change:

- API routes, request fields, or response semantics.
- Analysis pipeline behavior, fallback order, verifier rules, or evidence requirements.
- Product intent, UX wording policy, or planner workflow assumptions.
- Research hypotheses, rejected approaches, user feedback, or evaluation criteria for review-analysis quality.
- Local run, check, setup, or dependency instructions.

If code needs to intentionally break one of these documented rules, ask first. After approval, update this document or the more specific docs in the same change.
