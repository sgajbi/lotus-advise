# RFC-0020: Canonical Allocation and Risk Lens Convergence for Proposals

- Status: DRAFT
- Created: 2026-04-07
- Owners: lotus-advise
- Requires Approval From: lotus-advise, lotus-core, lotus-risk maintainers
- Depends On: RFC-0006, RFC-0007, RFC-0011, RFC-0014, RFC-0019
- Related Platform Guidance: `lotus-platform/docs/architecture/canonical-simulation-authority-and-domain-evaluation-pattern.md`
- Related Core RFC: `lotus-core/docs/RFCs/RFC 085 - Advisory-Grade Canonical Simulation Execution for lotus-advise.md`

## Executive Summary

`lotus-advise` now delegates proposal simulation to `lotus-core`. That fixes the broad simulation-authority problem, but one narrower gold-standard gap remains: proposal before/after analytics must reuse the same AUM, valuation, and allocation calculators used for live portfolios, and proposal risk analytics must come from `lotus-risk`, not advisory-local enrichment logic.

This RFC defines the convergence program.

The target state is:

1. `lotus-core` owns one canonical valuation/AUM/allocation calculator path for live and projected portfolio states.
2. `lotus-core` advisory simulation exposes the front-office allocation dimensions needed for proposal before/after review.
3. `lotus-risk` owns proposal concentration risk over canonical current/projected states.
4. `lotus-advise` consumes, persists, and presents canonical allocation and risk outputs; it does not become a second calculation authority.

This is a domain-authority cleanup, not a feature expansion for its own sake.

## Grounded Current State

This RFC is based on repository inspection on 2026-04-07.

### lotus-core

Inspected state:

1. Repository: `C:/Users/Sandeep/projects/lotus-core`
2. Branch: `main`
3. Tip: `ed1fbad fix(control-plane): correct advisory simulation contract import (#293)`
4. Working tree: clean at inspection time

Current implementation:

1. Live portfolio allocation is exposed through `POST /asset-allocation/query` in `src/services/query_service/app/routers/reporting.py`.
2. Live allocation contract is defined in `src/services/query_service/app/dtos/reporting_dto.py` through `AllocationDimension`, `AssetAllocationQueryRequest`, `AllocationBucket`, `AllocationView`, and `AssetAllocationResponse`.
3. Live allocation implementation is in `src/services/query_service/app/services/reporting_service.py`, especially `ALLOCATION_DIMENSION_ACCESSORS` and `ReportingService.get_asset_allocation(...)`.
4. Live AUM vocabulary already includes `aum_portfolio_currency`, `aum_reporting_currency`, `invested_market_value_portfolio_currency`, `invested_market_value_reporting_currency`, and `total_market_value_reporting_currency`.
5. Advisory simulation has a separate allocation implementation in `src/services/query_service/app/advisory_simulation/valuation.py` through `build_simulated_state(...)`.
6. Advisory simulation currently exposes a narrower allocation shape in `src/services/query_service/app/advisory_simulation/models.py` through `allocation_by_asset_class`, `allocation_by_instrument`, legacy `allocation`, and `allocation_by_attribute`.

Live allocation dimensions in `lotus-core` reporting include the RFC-0020 proposal subset:

1. `asset_class`
2. `currency`
3. `sector`
4. `country`
5. `region`
6. `product_type`
7. `rating`
Live reporting also supports `issuer_id`, `issuer_name`, `ultimate_parent_issuer_id`, and `ultimate_parent_issuer_name`. Those issuer dimensions remain available to risk analytics and future drill-downs, but they are intentionally not part of the RFC-0020 proposal allocation API surface.

Finding: `lotus-core` already owns live AUM/allocation authority, but advisory simulation still uses separate allocation logic. Proposal output should expose the front-office subset needed for advisory review rather than every internal issuer dimension.

### lotus-risk

Inspected state:

1. Repository: `C:/Users/Sandeep/projects/lotus-risk`
2. Branch: `fix/docker-upstream-runtime-validation`
3. Tip observed during the final tightening pass: `6e7ebc0 test: harden readiness coverage across stateful integrations`
4. Working tree: clean at final tightening pass

Current implementation:

1. `src/app/contracts/concentration.py` defines `ConcentrationInputMode.STATELESS`, `STATEFUL`, and `SIMULATION`.
2. `SimulationConcentrationInput` supports `simulation_changes`, `session_id`, `start_new_session`, `session_ttl_hours`, and `expected_version`.
3. `src/app/services/concentration_engine.py` implements simulation mode in `_resolve_simulation(...)`.
4. Simulation mode creates or reuses a `lotus-core` simulation session, applies simulation changes, pulls a projected core snapshot, and computes concentration from baseline and projected sections.
5. `ConcentrationResponse` already carries current/proposed/delta metrics for HHI, top-position concentration, top-N concentration, and issuer concentration, plus valuation context and simulation metadata.
6. Current `lotus-risk` RFC direction intentionally limits simulation mode to concentration. Historical return-based endpoints should not accept proposal simulation until a future RFC defines a valid projected return path.

Finding: `lotus-risk` has the right simulation-capable risk surface for proposal concentration, but `lotus-advise` does not yet call it through a production HTTP client.

### lotus-advise

Inspected state:

1. Repository: `C:/Users/Sandeep/projects/lotus-advise`
2. Branch: `feat/stateful-context-hardening-20260407`
3. Tip at original RFC creation: `94e6b4d refactor(test): share stateful fetch assertions`

Current implementation:

1. Normal proposal simulation calls `lotus-core` through `src/integrations/lotus_core/simulation.py` and validates `X-Lotus-Contract-Version: advisory-simulation.v1`.
2. Controlled local fallback/test-oracle calculation still exists in `src/core/advisory_engine.py` and `src/core/valuation.py`.
3. `ProposalResult` exposes `before: SimulatedState` and `after_simulated: SimulatedState`.
4. `SimulatedState` exposes `allocation_by_asset_class`, `allocation_by_instrument`, legacy `allocation`, and `allocation_by_attribute`.
5. `src/integrations/lotus_risk/enrichment.py` is hook-based. It looks for an override on `src.api.main`; it is not a production HTTP client.
6. `src/core/advisory/orchestration.py` attempts risk enrichment after simulation, but when no concrete enrichment is present it records `risk_authority = "lotus_advise_local"`.

Finding: `lotus-advise` is aligned with `lotus-core` for simulation authority, but proposal allocation and risk-lens authority are not yet gold-standard.

## Problem Statement

Proposal analytics must not drift from live portfolio analytics.

Current risk:

1. `lotus-core` has live allocation/AUM semantics and a separate advisory-simulation allocation implementation.
2. Proposal allocation exposes fewer allocation views than live portfolio reporting.
3. `lotus-advise` has no concrete `lotus-risk` HTTP integration for before/after proposal concentration risk.

In a banking-grade architecture, calculation ownership must be explicit. A proposal must not create a second source of truth for AUM, allocation, issuer grouping, look-through behavior, or concentration risk.

## Goals

1. Use one canonical `lotus-core` calculator path for live and projected AUM/allocation.
2. Expose every live `lotus-core` allocation dimension for proposal before/after states.
3. Introduce a governed proposal allocation contract with deterministic version negotiation.
4. Integrate `lotus-advise` with `lotus-risk` concentration simulation through a real HTTP client.
5. Persist and replay allocation/risk evidence consistently across simulation, artifact, lifecycle, async, and workspace handoff flows.
6. Keep degraded `lotus-risk` behavior explicit and audit-safe.
7. Preserve performance by avoiding duplicate upstream calls and by keeping cache identity boundaries strict.

## Non-Goals

1. Do not move proposal lifecycle, approvals, workspaces, artifacts, or execution handoff out of `lotus-advise`.
2. Do not move concentration formulas into `lotus-advise`.
3. Do not expose `lotus-risk` simulation mode for drawdown, rolling metrics, historical attribution, or other historical return-based endpoints in this RFC.
4. Do not remove legacy proposal allocation fields until canonical views are live, documented, and compatibility-tested.
5. Do not add `/v1/...` advisory route families.
6. Do not introduce new top-level proposal statuses beyond `READY`, `PENDING_REVIEW`, and `BLOCKED`.

## Architectural Invariants

1. One calculator authority: `lotus-core` owns valuation, AUM, allocation dimensions, and allocation bucket aggregation for live and projected state.
2. One risk authority: `lotus-risk` owns concentration metrics over current/proposed holdings.
3. One advisory authority: `lotus-advise` owns proposal intent, workflow, suitability, gates, artifacts, persistence, execution handoff, and presentation.
4. No hidden duplicate math: compatibility fields must be derived from canonical outputs, not recomputed independently in production.
5. Contract versioning is explicit: `lotus-advise` must send and validate the expected `lotus-core` simulation contract version.
6. Degraded outputs must state source and reason. Missing risk lensing must never look like successful risk analytics.
7. Caches must never blur identity boundaries such as portfolio, as-of date, reporting currency, mandate, benchmark, look-through mode, allocation dimensions, simulation contract version, or risk options.

## Decisions

### Decision 1: Keep `advisory-simulation.v1` and update it in place before live rollout

The apps are not live yet and all callers are under our control. This is still pre-live contract hardening, so introducing `advisory-simulation.v2` would add version churn without protecting any external compatibility commitment.

Required behavior:

1. `advisory-simulation.v1` remains the canonical proposal simulation contract for this phase.
2. `lotus-core` updates `v1` in place with additive canonical allocation-lens fields.
3. `lotus-advise` keeps sending and validating `X-Lotus-Contract-Version: advisory-simulation.v1`.
4. `lotus-advise` rejects response-header or lineage contract mismatches deterministically.
5. Future post-live breaking changes require a new contract version; this RFC does not introduce one.

### Decision 2: Extract shared allocation calculation inside `lotus-core`

`lotus-core` must not maintain separate allocation semantics for live reporting and advisory simulation.

Required direction:

1. Extract allocation bucket construction from reporting into a reusable internal module.
2. Make live `ReportingService.get_asset_allocation(...)` call the shared module.
3. Make advisory simulation before/after state construction call the same shared module.
4. Keep persistence/query orchestration outside the calculator.
5. Keep advisory-only simulation semantics outside the calculator.

The shared calculator should operate on a normalized input row model, not on FastAPI DTOs or repository-specific ORM objects. That keeps it reusable across live and projected states.

### Decision 3: Proposal allocation views expose a curated front-office subset

Live `lotus-core` reporting can support issuer dimensions, but proposal review should avoid excessive clutter. RFC-0020 proposal before/after allocation views must expose this curated front-office subset:

1. `asset_class`
2. `currency`
3. `sector`
4. `country`
5. `region`
6. `product_type`
7. `rating`
Live reporting also supports `issuer_id`, `issuer_name`, `ultimate_parent_issuer_id`, and `ultimate_parent_issuer_name`. Those issuer dimensions remain available to risk analytics and future drill-downs, but they are intentionally not part of the RFC-0020 proposal allocation API surface.

Target model shape:

```text
ProposalResult
  before
    allocation_views[]
  after_simulated
    allocation_views[]
  allocation_lens
    source_service = lotus-core
    simulation_contract_version = advisory-simulation.v1
    calculator_version
    reporting_currency
    look_through_mode
    dimensions[]
    before[]
    after[]
    delta[]
```

Implementation can choose exact class names, but the semantics are fixed:

1. `before` views are produced by the shared `lotus-core` allocation calculator on baseline state.
2. `after` views are produced by the same calculator on projected state.
3. `delta` views are derived mechanically from before/after buckets.
4. Legacy `allocation_by_asset_class`, `allocation_by_instrument`, and `allocation_by_attribute` are derived compatibility fields while retained.

### Decision 4: Use `lotus-risk` concentration simulation as the proposal risk lens

RFC-0020 risk scope is concentration only.

Required behavior:

1. `lotus-advise` calls `POST /analytics/risk/concentration` through a concrete `lotus-risk` HTTP client.
2. The primary production path uses `input_mode = simulation` once proposal intents are mapped to governed `lotus-core` simulation changes.
3. A stateless adapter may exist only as a transitional/test path when the canonical before/after positions are already available and simulation-session mapping is not yet complete.
4. The stateless adapter must not become the long-term production authority.
5. `lotus-advise` records `risk_authority = lotus_risk` only when a valid `lotus-risk` response was used.

Target risk lens shape:

```text
ProposalResult
  risk_lens
    source_service = lotus-risk
    input_mode = simulation
    status = READY | UNAVAILABLE | DEGRADED
    concentration
      hhi_current
      hhi_proposed
      hhi_delta
      top_position_weight_current
      top_position_weight_proposed
      top_position_weight_delta
      top_n_cumulative_weight_current
      top_n_cumulative_weight_proposed
      top_n_cumulative_weight_delta
      issuer_concentration
    valuation_context
    metadata
    diagnostics[]
```

### Decision 5: Risk lensing is default-degraded, not default-blocking

Default behavior:

1. Proposal simulation can return if `lotus-core` simulation succeeds and `lotus-risk` is unavailable.
2. `risk_lens.status` must be `UNAVAILABLE` or `DEGRADED`.
3. `explanation.authority_resolution.degraded_reasons` must include a stable reason code.
4. No concentration metric should be fabricated or copied from stale state.

Strict behavior is future-configurable. If later enabled, strict mode must be documented and tested as a separate policy, not as an implicit behavior change.

## Delivery Slices

### Slice 1: Contract and Calculator Baseline

Outcome:

1. Add a `lotus-core` allocation contract map that lists every live allocation dimension and classifies it as either part of the RFC-0020 proposal subset or intentionally excluded from proposal output.
2. Add tests that fail if live `AllocationDimension` changes without updating advisory allocation contract expectations and subset/exclusion rationale.
3. Finalize the additive `advisory-simulation.v1` allocation-lens response shape.

Acceptance gate:

1. Dimension inventory is test-protected.
2. The additive `advisory-simulation.v1` allocation-lens shape is documented before implementation begins.
3. No proposal API fields are widened in `lotus-advise` before the `lotus-core` contract map exists.

### Slice 2: Shared `lotus-core` Allocation Calculator

Outcome:

1. Extract a reusable allocation calculator from live reporting logic.
2. Make live reporting call the shared calculator without behavioral drift.
3. Make advisory simulation call the same calculator for before and after states.

Acceptance gate:

1. Live allocation endpoint tests pass.
2. Shared calculator unit tests cover every supported allocation dimension.
3. Advisory simulation tests prove before and after allocations come from the shared calculator.
4. A no-op advisory simulation before allocation matches live allocation for the same portfolio, as-of date, reporting currency, dimensions, and look-through mode.

### Slice 3: `advisory-simulation.v1` Allocation Lens Hardening

Outcome:

1. Extend `lotus-core` advisory simulation response with canonical allocation views, deltas, calculator metadata, and look-through metadata.
2. Update `lotus-advise` simulation client and models to consume the additive `advisory-simulation.v1` allocation lens while retaining version validation.
3. Keep retained legacy allocation fields derived from canonical views.

Acceptance gate:

1. Contract mismatch tests fail deterministically.
2. Proposal simulation exposes the curated RFC-0020 proposal allocation dimensions.
3. API vocabulary inventory includes canonical allocation lens terms.
4. Legacy fields remain stable or have explicit compatibility tests and migration notes.

### Slice 4: Concrete `lotus-risk` Concentration Client

Outcome:

1. Replace hook-only risk enrichment with a real `lotus-risk` HTTP client in `lotus-advise`.
2. Map proposal context and intents to `lotus-risk` concentration simulation input.
3. Preserve the hook only as a unit-test seam if still necessary.

Acceptance gate:

1. Client tests cover request mapping, response mapping, timeout, validation failure, upstream 4xx/5xx, contract mismatch, and degraded behavior.
2. API tests prove `risk_authority = lotus_risk` only when a valid `lotus-risk` response was used.
3. Capability reporting exposes proposal risk-lens dependency readiness.

### Slice 5: Proposal Risk Lens Persistence and Artifact Surface

Outcome:

1. Add first-class proposal `risk_lens` output sourced from `lotus-risk` concentration response.
2. Persist risk-lens evidence on proposal versions and async operations.
3. Include concise risk-lens content in proposal artifacts using business language.

Acceptance gate:

1. Simulation, artifact generation, lifecycle create/version, async create/version, and workspace handoff preserve risk-lens evidence for equivalent canonical input.
2. Failed `lotus-risk` calls remain operation/evaluation-scoped and do not borrow unrelated successful risk output.
3. Artifacts state when concentration risk is unavailable or degraded.

### Slice 6: Cross-Service Parity, Performance, and Rollout Proof

Outcome:

1. Add cross-service parity tests across seeded portfolios.
2. Add warm-cache tests for repeated stateful proposal evaluations.
3. Run local Docker validation with `lotus-core`, `lotus-risk`, and `lotus-advise` up together.

Acceptance gate:

1. No-op proposal before allocation equals direct live `lotus-core` allocation.
2. Proposal after allocation equals the shared calculator applied to projected state.
3. Proposal risk lens equals direct `lotus-risk` concentration simulation for the same session and changes.
4. Repeated stateful proposal workflows do not refetch safe cached context unnecessarily.
5. Cache-key tests prove no identity bleed across portfolio id, as-of date, reporting currency, mandate id, benchmark id, dimensions, look-through mode, simulation contract version, or risk options.

## Required Tests

This RFC cannot close with smoke tests only.

Required tests:

1. `lotus-core` allocation calculator unit tests for every live allocation dimension, including dimensions not surfaced in the proposal API.
2. `lotus-core` live allocation endpoint regression tests.
3. `lotus-core` advisory simulation v1 allocation-lens contract tests.
4. `lotus-core` no-op live/proposal allocation parity tests.
5. `lotus-advise` simulation-client allocation-lens contract tests.
6. `lotus-advise` API tests for allocation lens exposure and compatibility fields.
7. `lotus-advise` concrete `lotus-risk` client tests.
8. `lotus-advise` lifecycle, async, artifact, and workspace handoff risk-lens evidence tests.
9. `lotus-risk` concentration simulation tests for proposal-shaped simulation changes.
10. Cross-service Docker validation against seeded portfolios, including one issuer-complete portfolio and one partial-issuer-coverage portfolio.

## Performance and Scalability Requirements

1. `lotus-advise` must not call live allocation endpoints separately when `lotus-core` advisory simulation already returns canonical before/after allocation views.
2. `lotus-advise` should call `lotus-risk` once per canonical proposal evaluation unless the caller explicitly requests additional risk lenses.
3. Repeated stateful workflows must continue using copy-safe TTL caching.
4. New caches must include all valuation/allocation/risk identity dimensions in the key.
5. Cache statistics and internal diagnostics remain internal unless a separate observability RFC promotes them.

## Compatibility and Rollout

1. Keep `advisory-simulation.v1` as the canonical contract during this pre-live hardening phase.
2. Add canonical allocation-lens fields in place and migrate all controlled callers together.
3. Do not remove legacy proposal allocation fields during the first allocation-lens rollout.
4. Mark legacy proposal allocation fields as derived once canonical allocation views are live.
5. Keep `lotus-risk` risk lens default-degraded until local Docker and CI validation prove the integration.
6. Update OpenAPI docs, RFC-0067 vocabulary inventory, no-alias governance, and platform architecture docs where affected.
7. Merge in dependency order: `lotus-core`, then `lotus-risk` if contract changes are needed, then `lotus-advise`.

## Reason Codes

Use upper snake case.

Proposed reason codes:

1. `LOTUS_CORE_ALLOCATION_LENS_UNAVAILABLE`
2. `LOTUS_CORE_ALLOCATION_DIMENSION_UNSUPPORTED`
3. `LOTUS_CORE_ALLOCATION_CONTRACT_MISMATCH`
4. `LOTUS_RISK_CONCENTRATION_UNAVAILABLE`
5. `LOTUS_RISK_CONCENTRATION_CONTRACT_MISMATCH`
6. `LOTUS_RISK_CONCENTRATION_DEGRADED`
7. `PROPOSAL_RISK_LENS_UNAVAILABLE`

Do not introduce new top-level proposal statuses for these cases.

## Completion Criteria

RFC-0020 is complete only when all conditions are met:

1. `lotus-core` has one reusable valuation/AUM/allocation path for live and advisory projected states.
2. `lotus-core` advisory simulation v1 exposes the curated proposal allocation dimensions for before and after states.
3. `lotus-advise` consumes canonical allocation views without production-local recalculation.
4. Legacy proposal allocation fields are derived from canonical views or explicitly documented as compatibility-only.
5. `lotus-advise` has a concrete `lotus-risk` concentration HTTP client.
6. Proposal risk lens records current/proposed/delta concentration metrics sourced from `lotus-risk`.
7. Proposal artifact, lifecycle, async, and workspace handoff flows preserve allocation and risk evidence consistently.
8. Contract/version mismatches fail deterministically.
9. Degraded `lotus-risk` behavior is explicit and audit-safe.
10. Cross-service parity tests prove live/proposal allocation equivalence and direct `lotus-risk`/proposal risk-lens equivalence.
11. Local gates and PR CI pass in all affected repositories.

## Implementation Notes

1. Start in `lotus-core`; do not widen `lotus-advise` proposal contracts until the shared calculator and additive `advisory-simulation.v1` allocation-lens shape are defined.
2. Keep `lotus-advise` focused on consumption, workflow, persistence, and presentation.
3. Keep `lotus-risk` focused on risk analytics; do not move concentration formulas into `lotus-advise`.
4. Prefer fixture-backed parity tests over broad mirrored duplicate suites.
5. Prefer explicit version checks over permissive parsing.
6. Treat any new duplicated calculator logic as a blocker for RFC closure.
