# RFC-0020: Canonical Allocation and Risk Lens Convergence for Proposals

- Status: DRAFT
- Created: 2026-04-07
- Owners: lotus-advise
- Requires Approval From: lotus-advise, lotus-core, lotus-risk maintainers
- Depends On: RFC-0006, RFC-0007, RFC-0011, RFC-0014, RFC-0019
- Related Platform Guidance: `lotus-platform/docs/architecture/canonical-simulation-authority-and-domain-evaluation-pattern.md`
- Related Core RFC: `lotus-core/docs/RFCs/RFC 085 - Advisory-Grade Canonical Simulation Execution for lotus-advise.md`

## Executive Summary

`lotus-advise` now delegates proposal simulation authority to `lotus-core`, which is the right
service boundary. The next gap is narrower and more important: the proposal response must use the
same portfolio value, AUM, and allocation calculators that `lotus-core` uses for live portfolios,
and proposal risk analytics must come from `lotus-risk` rather than local advisory enrichment hooks.

The target architecture is:

1. `lotus-core` owns canonical portfolio value, AUM, and allocation calculation for live and
   projected portfolio states.
2. `lotus-risk` owns risk analytics over canonical current/projected states, starting with
   concentration simulation mode because that is the risk surface currently designed for proposed
   holdings.
3. `lotus-advise` owns proposal intent, workflow, suitability, gates, artifacting, persistence, and
   presentation of canonical allocation and risk lenses.

The desired end state is not simply to call another API. It is to remove duplicated calculation
semantics, keep domain authority clean, and make before/after proposal analytics reuse the same
calculators and vocabulary as live portfolio reporting.

## Grounded Current State

This RFC is based on inspection of the current local repositories on 2026-04-07.

### lotus-core

Inspected state:

1. Repository: `C:/Users/Sandeep/projects/lotus-core`
2. Branch: `main`
3. Tip: `ed1fbad fix(control-plane): correct advisory simulation contract import (#293)`
4. Working tree: clean at inspection time

Relevant current implementation:

1. Live portfolio allocation is exposed through the reporting surface:
   - `src/services/query_service/app/routers/reporting.py`
   - `POST /asset-allocation/query`
2. Live allocation contract and dimensions are defined in:
   - `src/services/query_service/app/dtos/reporting_dto.py`
   - `AllocationDimension`
   - `AssetAllocationQueryRequest`
   - `AllocationBucket`
   - `AllocationView`
   - `AssetAllocationResponse`
3. The live allocation dimensions currently supported by `lotus-core` are:
   - `asset_class`
   - `currency`
   - `sector`
   - `country`
   - `region`
   - `product_type`
   - `rating`
   - `issuer_id`
   - `issuer_name`
   - `ultimate_parent_issuer_id`
   - `ultimate_parent_issuer_name`
4. Live allocation implementation is in:
   - `src/services/query_service/app/services/reporting_service.py`
   - `ALLOCATION_DIMENSION_ACCESSORS`
   - `ReportingService.get_asset_allocation(...)`
5. AUM and invested-market-value semantics are already part of the live reporting vocabulary and
   responses, including terms such as:
   - `aum_portfolio_currency`
   - `aum_reporting_currency`
   - `invested_market_value_portfolio_currency`
   - `invested_market_value_reporting_currency`
   - `total_market_value_reporting_currency`
6. Advisory simulation has a separate allocation implementation in:
   - `src/services/query_service/app/advisory_simulation/valuation.py`
   - `build_simulated_state(...)`
7. Advisory simulation currently returns a narrower proposal allocation shape in:
   - `src/services/query_service/app/advisory_simulation/models.py`
   - `SimulatedState.allocation_by_asset_class`
   - `SimulatedState.allocation_by_instrument`
   - `SimulatedState.allocation`
   - `SimulatedState.allocation_by_attribute`

Finding: `lotus-core` already owns the live allocation/AUM authority, but advisory simulation still
has a separate allocation implementation and a narrower allocation surface. That is the duplication
this RFC must eliminate.

### lotus-risk

Inspected state:

1. Repository: `C:/Users/Sandeep/projects/lotus-risk`
2. Branch: `fix/docker-upstream-runtime-validation`
3. Tip: `e8721e4 fix: harden repo-local governance script imports`
4. Working tree: dirty at inspection time; existing changes were not modified by this review

Relevant current implementation:

1. Concentration analytics supports explicit input modes in:
   - `src/app/contracts/concentration.py`
   - `ConcentrationInputMode.STATELESS`
   - `ConcentrationInputMode.STATEFUL`
   - `ConcentrationInputMode.SIMULATION`
2. Simulation-mode concentration input is modeled as:
   - `SimulationConcentrationInput`
   - `simulation_changes`
   - `session_id`
   - `start_new_session`
   - `session_ttl_hours`
   - `expected_version`
3. Simulation mode is executed in:
   - `src/app/services/concentration_engine.py`
   - `_resolve_simulation(...)`
4. The implementation creates or reuses a `lotus-core` simulation session, applies simulation
   changes, requests a projected core snapshot, and computes concentration metrics from baseline
   and projected sections.
5. The concentration response already has before/proposed/delta semantics for:
   - HHI concentration
   - top-position concentration
   - top-N cumulative concentration
   - issuer concentration
   - valuation context
   - simulation session metadata
6. The broader `lotus-risk` RFC state is explicit that simulation mode is legitimate for
   concentration, while historical return-based endpoints such as drawdown, rolling metrics, and
   historical attribution should not expose simulation unless a valid projected return path exists.

Finding: `lotus-risk` has the right concentration simulation mode for a proposal risk lens, but
`lotus-advise` does not yet have a concrete HTTP integration for it.

### lotus-advise

Inspected state:

1. Repository: `C:/Users/Sandeep/projects/lotus-advise`
2. Branch: `feat/stateful-context-hardening-20260407`
3. Tip at RFC creation start: `94e6b4d refactor(test): share stateful fetch assertions`

Relevant current implementation:

1. Normal proposal simulation calls `lotus-core` through:
   - `src/integrations/lotus_core/simulation.py`
   - `simulate_with_lotus_core(...)`
2. The simulation contract is versioned with:
   - `X-Lotus-Contract-Version: advisory-simulation.v1`
3. Local advisory simulation and allocation logic remains in:
   - `src/core/advisory_engine.py`
   - `src/core/valuation.py`
   - this path is controlled fallback and test-oracle behavior, not normal runtime authority
4. `ProposalResult` currently exposes before/after state through:
   - `before: SimulatedState`
   - `after_simulated: SimulatedState`
5. `SimulatedState` currently exposes:
   - `allocation_by_asset_class`
   - `allocation_by_instrument`
   - `allocation`
   - `allocation_by_attribute`
6. `lotus-risk` integration is still hook-based:
   - `src/integrations/lotus_risk/enrichment.py`
   - it looks for an override on `src.api.main`
   - it is not a production HTTP client
7. `evaluate_advisory_proposal(...)` attempts risk enrichment after simulation, but falls back to
   `risk_authority = "lotus_advise_local"` when no concrete enrichment is available.

Finding: `lotus-advise` is aligned with `lotus-core` for simulation authority, but it still needs
canonical allocation parity and a concrete `lotus-risk` proposal risk-lens integration.

## Problem Statement

Proposal analytics should not drift from live portfolio analytics.

Today there are three risks:

1. `lotus-core` has live allocation/AUM calculation semantics and a separate advisory simulation
   allocation implementation.
2. Proposal allocation exposes fewer allocation views than live portfolio reporting, so advisors
   may see different available lenses for actual and proposed states.
3. `lotus-advise` has only a risk enrichment hook, so before/after proposal risk is not yet a real
   governed integration with `lotus-risk`.

In a banking-grade ecosystem, calculation ownership must be explicit. A proposal should not become
another source of truth for AUM, allocation, issuer grouping, or concentration risk.

## Goals

1. Use one canonical `lotus-core` allocation/AUM calculator for live and proposal states.
2. Ensure proposal before/after allocation supports every live allocation dimension that
   `lotus-core` supports.
3. Keep advisory workflow and policy ownership in `lotus-advise`.
4. Integrate `lotus-advise` with the `lotus-risk` simulation-capable concentration API for a
   before/after risk lens.
5. Make all new surfaces contract-governed, documented, and parity-tested.
6. Preserve performance by avoiding duplicate upstream calls and by reusing existing resolved
   `lotus-core` context where safe.
7. Keep degraded behavior explicit when optional risk enrichment is unavailable.

## Non-Goals

1. Do not move proposal lifecycle, approvals, workspaces, artifacts, or execution handoff into
   `lotus-core` or `lotus-risk`.
2. Do not reintroduce a second production allocation calculator in `lotus-advise`.
3. Do not expose simulation mode for historical return-based `lotus-risk` endpoints unless a future
   RFC defines a valid projected return path.
4. Do not add `/v1/...` route families in `lotus-advise`.
5. Do not weaken existing proposal statuses. Keep `READY`, `PENDING_REVIEW`, and `BLOCKED` as the
   top-level proposal outcome vocabulary.

## Architecture Decision

### 1. Domain Authority

| Domain | Owner | Boundary |
| --- | --- | --- |
| Portfolio value and AUM | `lotus-core` | Live and projected state valuation totals |
| Allocation dimensions and bucket aggregation | `lotus-core` | Live and projected allocation views, including issuer and look-through dimensions |
| Portfolio simulation state projection | `lotus-core` | Canonical before/after state returned to advisory consumers |
| Concentration risk analytics | `lotus-risk` | Current/proposed/delta concentration metrics and risk metadata |
| Advisory proposal intent and workflow | `lotus-advise` | Proposal construction, suitability, drift, gates, lifecycle, artifacts, execution handoff |
| Advisor presentation and evidence | `lotus-advise` | Presentation of canonical allocation and risk lenses inside proposal response/artifacts |

### 2. Calculator Reuse Rule

`lotus-core` must not maintain separate allocation semantics for live portfolio reporting and
advisory simulation.

Required direction:

1. Extract the live allocation bucket logic into a reusable calculator/service module inside
   `lotus-core`.
2. Make live `ReportingService.get_asset_allocation(...)` call that shared module.
3. Make advisory simulation before/after state construction call that same shared module against
   current and projected positions.
4. Keep advisory-only fields such as intents, suitability, gates, drift, and rule diagnostics out of
   that shared calculator.

The implementation can preserve a local adapter layer in advisory simulation, but not duplicated
bucket semantics.

### 3. Proposal Allocation Surface

Proposal simulation should expose a canonical allocation lens that is dimension-aware and aligned to
`lotus-core` live reporting.

Target proposal allocation model:

```text
ProposalResult
  before
    allocation_views[]
  after_simulated
    allocation_views[]
  allocation_lens
    before[]
    after[]
    delta[]
    dimensions[]
    look_through
    source_service = lotus-core
    calculator_version
```

The exact field placement can be finalized during implementation, but the contract must satisfy
these invariants:

1. Every allocation dimension supported by live `lotus-core` allocation can be requested or returned
   for proposal before/after state.
2. A no-op proposal against a live portfolio produces the same before allocation as the corresponding
   live `lotus-core` allocation query for the same portfolio, as-of date, reporting currency,
   dimensions, and look-through mode.
3. After allocation is computed by applying the same calculator to the projected state.
4. Existing legacy proposal fields may be retained temporarily for compatibility, but they must be
   derived from the canonical views rather than computed independently.

Required allocation dimensions for this RFC scope are the currently supported `lotus-core` live
allocation dimensions:

1. `asset_class`
2. `currency`
3. `sector`
4. `country`
5. `region`
6. `product_type`
7. `rating`
8. `issuer_id`
9. `issuer_name`
10. `ultimate_parent_issuer_id`
11. `ultimate_parent_issuer_name`

### 4. Risk Lens Surface

`lotus-advise` should call `lotus-risk` for proposal risk analytics rather than using a hook-only
enrichment seam.

Initial scope:

1. Use `POST /analytics/risk/concentration` in `lotus-risk` with `input_mode = simulation` when a
   proposal can be represented as `lotus-core` simulation changes.
2. Use `input_mode = stateless` only as a transitional adapter when `lotus-advise` already has the
   canonical before/after positions from `lotus-core` and the simulation-session path is not yet
   available for a particular proposal shape.
3. Do not call historical return-based endpoints for proposal simulation until future RFCs define a
   projected return path.

Target proposal risk lens:

```text
ProposalResult
  risk_lens
    source_service = lotus-risk
    input_mode = simulation | stateless
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

The exact nested model names should be chosen during implementation, but they must preserve
`lotus-risk` ownership and avoid rebranding risk metrics as advisory-owned calculations.

### 5. Degraded Behavior

Risk enrichment is not allowed to block core proposal simulation unless a strict risk-required mode
is explicitly enabled.

Default behavior:

1. Proposal simulation still returns if `lotus-core` simulation succeeds but `lotus-risk` is
   unavailable.
2. `risk_lens.status` becomes `UNAVAILABLE` or `DEGRADED`.
3. `explanation.authority_resolution.degraded_reasons` includes a stable reason code such as
   `LOTUS_RISK_CONCENTRATION_UNAVAILABLE`.
4. Capability reporting shows whether proposal risk lensing is operationally ready.

Strict behavior, if introduced:

1. A future environment flag may require `lotus-risk` concentration before a proposal can be marked
   `READY`.
2. That strict mode must be documented and tested separately.

## Delivery Slices

### Slice 1: Baseline Contract and Calculator Inventory

Outcome:

1. Document the live allocation/AUM and proposal allocation differences in `lotus-core`.
2. Produce a contract map from live `AssetAllocationResponse` to proposal allocation views.
3. Decide whether proposal allocation views are added to `advisory-simulation.v1` as additive
   fields or introduced under `advisory-simulation.v2`.

Acceptance gate:

1. The inventory identifies every allocation dimension currently supported by live `lotus-core`.
2. Tests exist that fail if live allocation dimensions are changed without updating the proposal
   allocation contract map.

### Slice 2: Shared lotus-core Allocation Calculator

Outcome:

1. Extract a reusable allocation calculator from live reporting logic in `lotus-core`.
2. Make live reporting and advisory simulation call that shared calculator.
3. Preserve live reporting behavior exactly.

Acceptance gate:

1. Live allocation endpoint tests pass unchanged or with only fixture updates for refactored module
   paths.
2. Advisory simulation tests prove before/after allocation views are computed from the shared
   calculator.
3. A no-op advisory simulation before state matches live allocation for the same portfolio/date/
   reporting currency/dimensions/look-through mode.

### Slice 3: Proposal Allocation Contract Expansion

Outcome:

1. Extend `lotus-core` advisory simulation response with canonical allocation views for before and
   after state.
2. Update `lotus-advise` models and OpenAPI docs to expose those views cleanly.
3. Keep old proposal allocation fields as derived compatibility fields only if needed.

Acceptance gate:

1. Proposal simulation exposes all live `lotus-core` allocation dimensions.
2. Contract tests prove no dimension is silently dropped.
3. API vocabulary inventory includes the new canonical terms.
4. Existing `allocation_by_asset_class` and `allocation_by_instrument` behavior remains stable or
   has an explicit migration note.

### Slice 4: Concrete lotus-risk Concentration Client

Outcome:

1. Replace the hook-only `lotus-risk` enrichment seam in `lotus-advise` with a real HTTP client.
2. Call `POST /analytics/risk/concentration` for proposal risk lensing.
3. Preserve the current hook only as a test seam if still useful.

Acceptance gate:

1. Unit tests prove request mapping, response mapping, timeouts, validation errors, and degraded
   behavior.
2. Contract tests prove the proposal response records `risk_authority = lotus_risk` only when a
   valid `lotus-risk` response was used.
3. Capability reporting includes proposal risk lens readiness and dependency status.

### Slice 5: Proposal Risk Lens Contract and Artifacts

Outcome:

1. Add a first-class proposal `risk_lens` model sourced from `lotus-risk` concentration output.
2. Include a concise risk section in proposal artifacts without duplicating raw risk payloads.
3. Persist risk-lens evidence with proposal versions and async operations.

Acceptance gate:

1. Proposal simulation, artifact generation, lifecycle create/version, async create/version, and
   workspace handoff all preserve the same risk-lens evidence where the canonical input is
   equivalent.
2. Failed `lotus-risk` calls remain audit-safe and do not produce misleading risk metrics.
3. Artifact output uses business language and clearly states when risk lensing is unavailable.

### Slice 6: Cross-Service Parity and Performance Governance

Outcome:

1. Add parity tests across `lotus-core`, `lotus-risk`, and `lotus-advise` for representative seeded
   portfolios.
2. Add cache/reuse tests so repeated proposal workflows do not refetch canonical context or recompute
   derived lenses unnecessarily.
3. Add latency-sensitive integration tests around warm-cache stateful proposal simulation.

Acceptance gate:

1. No-op proposal before allocation equals live allocation for representative seeded portfolios.
2. Proposal after allocation equals the shared calculator applied to the projected state.
3. Proposal concentration risk equals direct `lotus-risk` concentration simulation for the same
   session/changes.
4. Repeated stateful proposal workflows reuse safe cache state without blurring `portfolio_id`,
   `as_of`, `mandate_id`, or `benchmark_id` identity boundaries.

## Testing Requirements

This RFC should not be closed with superficial endpoint smoke tests.

Required test classes:

1. `lotus-core` calculator unit tests for every supported allocation dimension.
2. `lotus-core` parity tests between live allocation and advisory simulation before-state
   allocation.
3. `lotus-core` projected-state tests proving after-state allocation uses the same calculator.
4. `lotus-advise` client tests for the `lotus-risk` concentration HTTP integration.
5. `lotus-advise` API tests proving proposal `risk_lens` status and authority semantics.
6. `lotus-advise` lifecycle and async tests proving persisted evidence keeps allocation and risk
   lens lineage.
7. Cross-service integration tests against seeded portfolios, including at least one portfolio with
   issuer data and one with partial issuer coverage.
8. Performance-regression tests for warm-cache repeated stateful proposal workflows.

## Performance and Scalability Requirements

1. `lotus-advise` must not call live allocation endpoints separately if `lotus-core` advisory
   simulation already returns canonical before/after allocation views for the same request.
2. `lotus-advise` should call `lotus-risk` once per canonical proposal evaluation unless the caller
   explicitly requests additional risk lenses.
3. Repeated stateful evaluations must continue to use the copy-safe TTL cache already introduced in
   the Lotus Core context resolver.
4. Any new cache key must include all identity dimensions that affect valuation, allocation, or risk:
   - portfolio id
   - as-of date
   - reporting currency
   - mandate id
   - benchmark id
   - allocation dimensions
   - look-through mode
   - simulation contract version
   - risk lens options
5. Cache statistics and replay evidence should remain internal unless a separate observability RFC
   promotes them to public operational APIs.

## Compatibility and Rollout

1. Do not remove existing proposal allocation fields in the same PR that introduces canonical
   allocation views.
2. Mark legacy proposal allocation fields as derived from canonical views once the shared calculator
   is in place.
3. If `advisory-simulation.v2` is required, `lotus-advise` must negotiate the new contract explicitly
   and reject mismatched response versions.
4. Keep `lotus-risk` risk lensing default-degraded until the integration is proven live across local
   Docker and CI environments.
5. Update RFC-0067 vocabulary artifacts in all affected repositories after contract changes.
6. Update `lotus-platform` architecture documentation if the implementation changes any cross-service
   ownership boundary beyond this RFC.

## Reason Codes

New or stabilized diagnostic codes should use upper snake case.

Proposed codes:

1. `LOTUS_CORE_ALLOCATION_LENS_UNAVAILABLE`
2. `LOTUS_CORE_ALLOCATION_DIMENSION_UNSUPPORTED`
3. `LOTUS_CORE_ALLOCATION_CONTRACT_MISMATCH`
4. `LOTUS_RISK_CONCENTRATION_UNAVAILABLE`
5. `LOTUS_RISK_CONCENTRATION_CONTRACT_MISMATCH`
6. `LOTUS_RISK_CONCENTRATION_DEGRADED`
7. `PROPOSAL_RISK_LENS_UNAVAILABLE`

Do not introduce new top-level proposal statuses for these cases.

## Acceptance Criteria

This RFC is implemented only when all of the following are true:

1. `lotus-core` has one reusable allocation/AUM calculator path for live and advisory projected
   states.
2. Advisory simulation before/after allocation supports the same allocation dimensions as live
   portfolio allocation.
3. `lotus-advise` proposal responses expose canonical before/after allocation views without local
   production recalculation.
4. `lotus-advise` has a concrete HTTP client for `lotus-risk` concentration simulation.
5. Proposal risk lensing records current/proposed/delta concentration metrics sourced from
   `lotus-risk`.
6. Proposal artifact, lifecycle, async, and workspace handoff flows preserve allocation and risk
   evidence consistently.
7. Contract/version mismatches fail deterministically.
8. Degraded `lotus-risk` behavior is explicit and audit-safe.
9. Cross-service parity tests prove no-op live/proposal allocation equivalence and direct
   `lotus-risk`/proposal risk-lens equivalence.
10. Local quality gates, OpenAPI governance, no-alias guard, vocabulary validation, and PR CI pass in
    all affected repositories.

## Open Questions

1. Should canonical proposal allocation views be introduced as additive fields under
   `advisory-simulation.v1`, or should `lotus-core` publish `advisory-simulation.v2` for this
   contract expansion?
2. Should `lotus-risk` concentration simulation accept a direct `lotus-core` advisory-simulation
   result as input, or should it continue orchestrating `lotus-core` simulation sessions itself?
3. Which proposal workflows should require risk lensing before `READY` in strict private-banking
   production profiles?
4. Should live allocation look-through mode default to `direct_only` for proposals, or should proposal
   allocation inherit the same default that front-office reporting uses?

## Implementation Notes

1. Start in `lotus-core`; do not widen `lotus-advise` contract until the shared calculator boundary is
   clear.
2. Keep `lotus-advise` focused on consuming and presenting canonical outputs.
3. Keep `lotus-risk` focused on risk analytics. Do not move concentration formulas into
   `lotus-advise`.
4. Use fixture-backed parity tests instead of broad mirrored duplicate suites.
5. Prefer explicit contract/version checks over implicit best-effort parsing.
