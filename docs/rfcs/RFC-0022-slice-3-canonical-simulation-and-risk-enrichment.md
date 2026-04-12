# RFC-0022 Slice 3 Evidence: Canonical Simulation and Risk Enrichment

- RFC: `docs/rfcs/RFC-0022-proposal-alternatives-and-portfolio-construction-workbench.md`
- Slice: 3
- Date: 2026-04-13
- Status: Completed

## Scope

This slice establishes the internal enrichment seam that turns deterministic alternative
candidate seeds into canonically evaluated advisory alternatives without widening the public API
surface yet.

The implementation goal for this slice is narrow and deliberate:

1. build candidate-specific `ProposalSimulateRequest` payloads,
2. route every unique candidate payload through existing `evaluate_advisory_proposal`,
3. reject alternatives when authoritative upstream services degrade,
4. preserve stable evidence references and replay-safe simulation records,
5. keep the seam reusable for later simulate, persistence, workspace, artifact, and replay slices.

## Delivered

### 1. Canonical single-pass enrichment seam

Added `src/core/advisory/alternatives_enrichment.py` with:

1. `build_alternative_simulate_request`
2. `evaluate_alternative_candidates_batch`
3. `AlternativesBatchEvaluation`
4. `AlternativeSimulationRecord`
5. `AlternativesSimulationError`

The batch evaluator reuses `evaluate_advisory_proposal` instead of introducing a parallel
simulation or risk path.

### 2. Explicit degraded-authority behavior

The slice rejects, rather than silently downgrades, candidate alternatives when:

1. `simulation_authority != lotus_core`
2. `risk_authority != lotus_risk`

That keeps RFC-0022 aligned with its non-negotiable invariant that a feasible alternative must be
backed by canonical upstream evidence.

### 3. Bounded and deduplicated evaluation

The evaluator now:

1. enforces `normalized_request.max_alternatives`,
2. rejects overflow candidates with `ALTERNATIVE_CANDIDATE_LIMIT_EXCEEDED`,
3. deduplicates identical candidate requests by canonical request hash,
4. reuses the single canonical evaluation result across duplicates while still emitting
   candidate-specific evidence references.

This reduces repeated upstream work and keeps latency bounded without hiding candidate outcomes.

### 4. Stable evidence references

Feasible alternatives now emit stable evidence refs:

1. `evidence://proposal-alternatives/{candidate_id}/simulation`
2. `evidence://proposal-alternatives/{candidate_id}/risk`
3. `evidence://proposal-alternatives/{candidate_id}/decision-summary`

Rejected alternatives retain explicit candidate and request-hash evidence lineage.

## Tests Added

Added `tests/unit/advisory/engine/test_engine_proposal_alternatives_enrichment.py`.

Coverage added in this slice proves:

1. candidate intents replace baseline proposal intents without mutating the base request,
2. identical candidate payloads trigger a single canonical orchestration call,
3. degraded `lotus-core` authority rejects the candidate,
4. degraded `lotus-risk` authority rejects the candidate,
5. overflow candidates are rejected explicitly,
6. invalid or empty generated intents are rejected before any upstream call.

## Review Notes

During the slice review, the initial draft enrichment file was tightened because it had three
material issues:

1. duplicate orchestration calls for the same candidate payload,
2. a broken `generated_intents` reference in alternative construction,
3. insufficiently explicit rejection behavior for overflow and invalid-intent cases.

The final version removes those issues and leaves a narrower, more reusable seam for later slices.

## Remaining For Later Slices

Not part of Slice 3 yet:

1. public API exposure of `proposal_alternatives`,
2. persistence and replay wiring,
3. artifact and workspace projection,
4. ranking and comparison projection,
5. direct integration tests against live `lotus-core` and `lotus-risk`.

Those remain intentionally deferred so this slice stays focused on canonical internal enrichment.
