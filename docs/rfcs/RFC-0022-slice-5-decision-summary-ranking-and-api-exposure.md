# RFC-0022 Slice 5 Evidence: Decision Summary, Ranking, and API Exposure

- RFC: `docs/rfcs/RFC-0022-proposal-alternatives-and-portfolio-construction-workbench.md`
- Slice: 5
- Date: 2026-04-13
- Status: Completed

## Scope

This slice moves proposal alternatives from internal candidate enrichment into a backend-owned
simulation contract that can be consumed consistently by API, workflow, replay, and later artifact
surfaces.

The slice covers:

1. decision-summary projection for each evaluated alternative,
2. deterministic ranking and tie-break ordering,
3. comparison summary generation,
4. exposure of the alternatives envelope on simulation and persisted proposal results.

## Delivered

### 1. Backend-owned alternatives envelope

Added `ProposalAlternatives` and wired it into the canonical simulation contract:

1. `ProposalSimulateRequest.alternatives_request`
2. `ProposalResult.proposal_alternatives`

This keeps alternatives generation requested explicitly and delivered through the same backend-owned
proposal payload used by API and workflow consumers.

### 2. Projection layer between candidate enrichment and delivery surfaces

Added `src/core/advisory/alternatives_projection.py`.

This module owns:

1. normalization and bounded candidate-plan execution,
2. conversion of simulation results into ranked `ProposalAlternative` records,
3. comparison summaries,
4. stable ranking explanation payloads,
5. alternatives-envelope evidence references.

The projection layer keeps this logic out of the API and out of persistence code, which is the
right separation of concerns for Slice 5.

### 3. Deterministic ranking posture

Ranking now prefers:

1. feasible alternatives over non-feasible posture,
2. fewer missing-evidence items,
3. fewer blocking approval burdens,
4. fewer approvals,
5. lower turnover,
6. stable objective order,
7. stable alternative id as the final tie-breaker.

This satisfies the RFC requirement that alternatives rank deterministically and that blocked
posture cannot outrank ready posture.

### 4. Decision-summary and comparison projection

Each ranked alternative now carries:

1. projected `proposal_decision_summary`,
2. `comparison_summary`,
3. `ranking_projection`,
4. backend-owned evidence references.

That gives downstream consumers a stable delivery surface without re-deriving advisory policy or
ranking logic outside the advisory domain.

### 5. Safe candidate evaluation seam

`evaluate_alternative_candidates_batch` now accepts an explicit evaluator override and performs the
default orchestration import lazily.

This was an important tightening pass because it:

1. removes a circular-import risk,
2. makes the enrichment path easier to test truthfully,
3. avoids monkeypatching internal imports in unit tests.

### 6. Recursive generation guard

Alternative candidate simulation requests now clear `alternatives_request` before canonical
evaluation.

That prevents recursive alternatives generation when a proposal alternative is itself simulated
through the orchestration path.

## Tests Added Or Tightened

Updated or added:

1. `tests/unit/advisory/engine/test_engine_proposal_alternatives_projection.py`
2. `tests/unit/advisory/engine/test_engine_proposal_alternatives_enrichment.py`
3. `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`
4. `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

The slice now proves:

1. ranking remains deterministic,
2. ready alternatives rank ahead of review-posture alternatives,
3. comparison summaries and ranking explanations are backend-owned,
4. simulation responses expose the alternatives envelope,
5. persisted proposal workflow results retain the alternatives envelope,
6. deduplicated candidate evaluation still works after the evaluator seam change.

## Review Notes

The main architectural decision in this slice was to create a dedicated projection layer instead of
folding ranking and comparison logic into orchestration or API handlers.

That keeps:

1. simulation authority in orchestration,
2. candidate enrichment authority in enrichment,
3. delivery-shape and ranking authority in projection.

This is the right modular boundary for later persistence, workspace, artifact, and replay slices.

## Remaining For Later Slices

Still intentionally deferred:

1. persisted selected-alternative handoff semantics,
2. workspace save and replay continuity,
3. artifact and evidence-bundle exposure,
4. live-stack alternatives validation and operator proof.
