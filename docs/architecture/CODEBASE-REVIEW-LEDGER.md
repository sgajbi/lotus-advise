# Lotus Advise Codebase Review Ledger

## LA-REV-001

- Scope: Product surface, ecosystem fit, and architecture posture
- Pattern: Service boundaries and integration readiness
- Status: Refactor Needed
- Finding Class: modularity problem
- Summary: `lotus-advise` has a strong deterministic proposal engine, but the service is still shaped like a simulation API rather than a production advisory workstation.
- Evidence:
  - The project overview defines advisory flow primarily as advisor-entered cash/trade proposals and simulation outputs.
  - The public simulation and proposal-create contracts require callers to supply full `portfolio_snapshot`, `market_data_snapshot`, and `shelf_entries`.
  - The current capability contract is environment-flag based rather than dependency-aware.
  - Execution integration is documented as a draft RFC, not a shipped API surface.
- Consequence:
  - The app fits demos and deterministic testing well, but it does not yet own the real advisor workflow loop of sourcing household context, drafting proposals iteratively, requesting analytics, generating client-ready outputs, and handing off to execution with closed-loop status.
- Follow-Up:
  - Add lotus-core snapshot adapters and proposal workspace APIs.
  - Add downstream analytics and execution orchestration seams.
  - Promote capability reporting from env-flag truth to dependency-aware truth.

## LA-REV-002

- Scope: Integration capability contract
- Pattern: documentation drift / observability gap
- Status: Refactor Needed
- Finding Class: observability gap
- Summary: `/platform/capabilities` reports local feature flags, but not whether the service can actually complete end-to-end advisory work with required dependencies.
- Evidence:
  - `integration_capabilities.py` resolves lifecycle and async support entirely from environment flags and returns a static feature list.
- Consequence:
  - `lotus-gateway` and `lotus-workbench` can present enabled workflows even when downstream data, analytics, reporting, or execution dependencies are unavailable.
- Follow-Up:
  - Split `feature_enabled` from `operational_ready`.
  - Include dependency posture for lotus-core, lotus-performance, lotus-report, lotus-ai, and execution adapters.

## LA-REV-003

- Scope: Repository hygiene
- Pattern: stale code / dead code
- Status: Signed Off
- Finding Class: stale code
- Summary: stale active-runtime legacy source remnants were removed from `src/`, reducing ambiguity about current advisory-only ownership.
- Evidence:
  - Legacy runtime subtrees that no longer belonged to advisory were removed from the active source layout.
  - Proposal-specific integration seams and API packages now sit under clean advisory-owned paths such as `src/api/proposals/` and `src/integrations/`.
  - Active repository scans no longer find DPM naming or advisory-external runtime ownership markers across `docs`, `src`, `tests`, `scripts`, and `README.md`.
  - Advisory unit, integration, and shared contract suites passed with `231` tests.
  - `python -m compileall src scripts` completed successfully.
- Consequence:
  - New contributors are less likely to infer obsolete runtime scope from current source structure.
- Follow-Up:
  - Continue treating historical advisory-pack RFC material as archival context until a later documentation cleanup slice decides whether to retain, reframe, or rehome it.

## LA-REV-004

- Scope: API and vocabulary naming
- Pattern: documentation drift / modularity problem
- Status: Signed Off
- Finding Class: modularity problem
- Summary: The advisory public surface and active top-level governance docs were renamed away from inherited rebalance-era numbering and route-family language.
- Evidence:
  - Advisory endpoints now use the canonical `/advisory/...` route family.
  - Active top-level RFCs were renumbered into a contiguous advisory sequence ending at `RFC-0006A`.
  - Active ADRs were renumbered into a contiguous advisory sequence ending at `ADR-0004`.
  - Repository-wide scans no longer find old top-level RFC/ADR numbers or rebalance proposal route family strings in the active advisory surface.
- Consequence:
  - The advisory domain story is now much more consistent for engineers, integrators, and future documentation work.
- Follow-Up:
  - Continue tightening semantic names only where it meaningfully improves clarity without breaking established advisory contracts.

## LA-REV-005

- Scope: Proposal API directory structure
- Pattern: modularity problem
- Status: Signed Off
- Finding Class: modularity problem
- Summary: Proposal lifecycle API wiring was previously spread across generic router files, making the advisory lifecycle surface harder to navigate than necessary.
- Evidence:
  - Proposal runtime wiring, lifecycle routes, async routes, support routes, and proposal-specific HTTP error mapping now live under `src/api/proposals/`.
  - Top-level `src/api/routers/` is reduced to non-proposal router surfaces plus shared runtime utilities.
  - Advisory unit tests, advisory integration tests, compile checks, and Docker build all passed after the package move.
- Consequence:
  - New contributors can find proposal API wiring in one place, and the top-level API layout better reflects service boundaries.
- Follow-Up:
  - Preserve the cleaned public route family and keep future proposal APIs inside the dedicated proposal package unless a stronger bounded-context split is introduced.

## LA-REV-006

- Scope: Public API surface hygiene
- Pattern: stale code / backend leakage
- Status: Signed Off
- Finding Class: stale code
- Summary: The proposal supportability configuration endpoint was removed because it exposed runtime configuration and migration internals as a public advisory contract.
- Evidence:
  - `/advisory/proposals/supportability/config` returned backend readiness flags, migration namespace details, expected migration versions, and advisory-owned table names.
  - The endpoint did not support an advisor workflow, integration handshake, or client-facing decision.
  - The response model and generated vocabulary inventory carried internal persistence terminology into the public contract.
  - OpenAPI tags now include explicit descriptions so operational and business API categories remain self-explanatory without leaking internals through a dedicated supportability config route.
- Consequence:
  - The public API is narrower, easier to reason about, and less coupled to runtime implementation details.
- Follow-Up:
  - Keep internal diagnostics in logs, metrics, startup validation, and private runbooks rather than expanding public contract surface with backend configuration introspection.

## LA-REV-007

- Scope: RFC-0019 closure quality gate
- Pattern: architecture hardening / contract convergence
- Status: Signed Off
- Finding Class: modularity problem
- Summary: RFC-0019 closure work is complete and the remaining contract divergence between direct simulation and workspace evaluation was removed before closeout.
- Evidence:
  - Direct `simulate`, artifact generation, workspace reevaluation, and lifecycle create/version flows now share the same normalized `stateless` and `stateful` advisory context contract.
  - Canonical request hashing now aligns across direct simulation and workspace reevaluation for equivalent advisory inputs.
  - Async runtime recovery, replay evidence endpoints, and downstream execution update reconciliation are covered by unit, integration, and end-to-end tests.
  - Final repository gates passed with `375` tests plus `ruff`, `mypy`, OpenAPI quality, no-alias governance, and vocabulary drift validation.
- Consequence:
  - `lotus-advise` now closes the advisory runtime loop defined by RFC-0019 without leaving workspace, simulation, async, and execution surfaces on inconsistent underlying rules.
- Follow-Up:
  - Move on to `RFC-0014` and `RFC-0017` follow-on work rather than reopening RFC-0019 scope.

## LA-REV-008

- Scope: Stateful Lotus Core context resolution seam
- Pattern: modularity problem / query-performance risk / test gap
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The stateful advisory path had no live runtime resolver and then, once restored, still
  needed stronger hot-path discipline around repeat fetches, mutation isolation, and explicit
  environment wiring.
- Evidence:
  - `src/integrations/lotus_core/stateful_context.py` now owns the runtime translation from Lotus
    Core portfolio, positions, and cash surfaces into the canonical advisory simulation request.
  - `src/api/main.py` now exposes the resolver hook explicitly so simulation, lifecycle, and
    workspace flows all reuse the same stateful seam.
  - The adapter now derives the query-service base URL from `LOTUS_CORE_BASE_URL` when
    `LOTUS_CORE_QUERY_BASE_URL` is not set, which closes the live control-plane/query-service split
    seen in Docker.
  - A short-lived copy-safe in-memory TTL cache now prevents repeated stateful reevaluation flows
    from re-fetching identical upstream context on every call.
  - Unit coverage in `tests/unit/advisory/api/test_lotus_core_stateful_context.py` now proves:
    translation shape, invalid upstream payload handling, cache reuse, and cache mutation
    isolation.
- Consequence:
  - Stateful simulation and proposal creation now work against live Lotus Core portfolios, and the
    hot path is materially cheaper and safer under repeated evaluation workloads.
- Follow-Up:
  - If stateful workflows must support arbitrary new-trade drafting without stateless payload
    enrichment, add a governed market-data/product-shelf expansion seam rather than widening this
    adapter ad hoc.

## LA-REV-009

- Scope: Stateful workspace request construction and live trade drafting
- Pattern: correctness risk / modularity problem / test gap
- Status: Hardened
- Finding Class: race-condition or correctness risk
- Summary: Stateful workspaces were resolving Lotus Core context correctly, but they were not
  consistently applying the current draft state on top of that resolved request, and they could
  not enrich newly drafted non-held instruments from Lotus Core query data.
- Evidence:
  - `src/api/services/workspace_service.py` now applies one shared draft-state overlay path to both
    stateless and stateful workspaces.
  - Stateful workspace creation now seeds draft options from the resolved canonical request instead
    of falling back to empty default engine options.
  - `src/integrations/lotus_core/stateful_context.py` now enriches missing traded instruments with
    instrument metadata, latest price, and FX data through cached Lotus Core query lookups.
  - Unit coverage now proves:
    - stateful draft actions affect evaluation results,
    - stateful workspace parity against equivalent direct simulation at the business-result layer,
    - stateful handoff persists the current drafted proposal result,
    - missing instrument enrichment works through the adapter and the workspace API.
  - Live runtime validation against `DEMO_ADV_USD_001` confirmed:
    - a new EUR fund trade evaluates and surfaces a domain `BLOCKED` result for insufficient cash,
    - a new USD fund trade evaluates successfully and produces a non-held trade intent without
      degraded fallback.
- Consequence:
  - Stateful workspace flows now behave like real advisor drafting workflows instead of a partially
    wired context shell.
- Follow-Up:
  - If product policy requires richer issuer/liquidity metadata for new instruments, source that
    through a governed instrument-policy seam instead of hardcoding defaults in the adapter.

## LA-REV-010

- Scope: Stateful resolver cache behavior and recovery
- Pattern: query/performance risk / resilience gap
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The stateful Lotus Core resolver cache needed stronger proof not just for reuse and
  eviction, but also for recovery after upstream failures so advisor workflows do not stay stuck on
  a transient bad response.
- Evidence:
  - `tests/unit/advisory/api/test_lotus_core_stateful_context.py` now proves:
    - zero-TTL disables cache reuse,
    - max-size eviction removes the oldest portfolio context,
    - failed stateful resolutions are not cached,
    - a later healthy upstream response recovers cleanly after a prior failure.
  - `tests/unit/advisory/api/test_api_workspace.py` now proves the same recovery behavior at the
    workspace API layer: an initial `WORKSPACE_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE` response
    does not poison subsequent evaluation once Lotus Core returns a valid payload again.
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` now proves the same
    recovery behavior for stateful lifecycle create and stateful version creation: an initial
    `PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE` failure does not poison the next request
    after Lotus Core returns a valid payload again.
  - `tests/integration/advisory/api/test_proposal_api_workflow_integration.py` now proves the
    same recovery pattern for stateful async create and stateful async version workflows: an
    initial failed operation remains operation-scoped, the next submission refetches Lotus Core
    context, and the recovered operation persists normal proposal/version replay evidence.
- Consequence:
  - The stateful hot path now has explicit regression protection for both latency discipline and
    operational recovery behavior.
- Follow-Up:
  - Keep further work focused on runtime behavior changes rather than more duplicate coverage; the
    stateful recovery pattern is now proven at adapter, workspace, lifecycle, and async workflow
    layers.

## LA-REV-011

- Scope: Async proposal-create submission idempotency
- Pattern: reliability gap / concurrency risk
- Status: Hardened
- Finding Class: reliability gap
- Summary: Async proposal creation accepted an `Idempotency-Key` but did not deduplicate at
  submission time, so retried requests could create duplicate operations and duplicate background
  execution attempts before the underlying create flow enforced lifecycle idempotency.
- Evidence:
  - `src/core/proposals/service.py` now deduplicates async proposal-create submissions by
    idempotency key and a governed submission hash.
  - Equivalent stateless request shapes now hash consistently across legacy and normalized
    `stateless_input` payloads, so callers do not get false `409` conflicts just because they used
    different but equivalent request envelopes.
  - `src/api/proposals/routes_async.py` now schedules background execution only for new async
    proposal-create operations; replayed submissions return the existing operation without
    re-enqueueing execution.
  - `src/infrastructure/proposals/postgres.py` and migration `0005_async_idempotency_unique.sql`
    now make the async create idempotency contract atomic at the storage layer instead of relying
    on a non-atomic service-side check/create sequence.
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py`,
    `tests/integration/advisory/api/test_proposal_api_workflow_integration.py`, and
    `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` now prove:
    - identical async create submissions reuse the same operation,
    - conflicting async create submissions return `409`,
    - legacy and normalized stateless create payloads are treated as semantically equivalent,
    - replayed submissions are marked as replayed internally and are not rescheduled.
  - `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` and
    `tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py`
    now prove the same async idempotency behavior at the repository/storage layer, including
    atomic create-or-get behavior and idempotency lookup.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` now tracks internal
    async create submission outcomes directly, proving that new accepts, replayed accepts, and
    conflicts are counted consistently instead of being inferred only from end-to-end behavior.
- Consequence:
  - Async proposal-create now behaves like a real idempotent submission surface instead of relying
    on downstream create-time dedupe after multiple operations may already have been accepted.
- Follow-Up:
  - If async proposal-version writes ever gain a public idempotency key, apply the same
    submission-level dedupe pattern there instead of reintroducing operation-level duplication.

## LA-REV-012

- Scope: Proposal allocation and risk-lens domain authority
- Pattern: duplicate logic / cross-service boundary risk / contract gap
- Status: Signed Off
- Finding Class: architecture or modularity issue
- Summary: `lotus-core` already owns live AUM and allocation calculation through its reporting service, but advisory simulation has a separate allocation implementation and `lotus-advise` still exposes only a hook-based `lotus-risk` enrichment seam. Proposal before/after allocation and concentration risk should converge on canonical `lotus-core` and `lotus-risk` authorities instead of becoming advisory-owned calculation logic.
- Evidence:
  - `lotus-core/src/services/query_service/app/services/reporting_service.py` implements live allocation through `ReportingService.get_asset_allocation(...)` and `ALLOCATION_DIMENSION_ACCESSORS`.
  - `lotus-core/src/services/query_service/app/dtos/reporting_dto.py` defines the live `AllocationDimension`, `AssetAllocationQueryRequest`, `AllocationView`, and `AssetAllocationResponse` contract.
  - `lotus-core/src/services/query_service/app/advisory_simulation/valuation.py` separately implements advisory `build_simulated_state(...)` allocation outputs.
  - `lotus-risk/src/app/contracts/concentration.py` and `lotus-risk/src/app/services/concentration_engine.py` define concentration `simulation` mode with current/proposed/delta outputs, but `lotus-advise/src/integrations/lotus_risk/enrichment.py` is still a hook-based override rather than a concrete HTTP integration.
  - RFC-0020 now captures the required convergence program: shared `lotus-core` allocation calculator, proposal allocation views matching live allocation dimensions, concrete `lotus-risk` concentration integration, parity tests, degraded behavior, and rollout gates.
- Consequence:
  - Proposal allocation and risk-lens work is now governed by canonical `lotus-core` allocation views and a concrete `lotus-risk` concentration lens instead of advisory-local calculation authority.
- Follow-Up:
  - RFC-0020 implementation is complete on the feature branches pending PR/CI/merge closure. Any further work belongs in follow-on RFCs, not this convergence program.

## LA-REV-013

- Scope: Live proposal delivery validation and execution-status chronology
- Pattern: reliability gap / integration test hardening
- Status: Hardened
- Finding Class: reliability gap
- Summary: The live proposal path had strong coverage for canonical simulation, allocation, risk lens,
  lifecycle create/version, async, and workspace handoff, but delivery surfaces were still being
  checked ad hoc and execution updates could silently regress status if a downstream timestamp
  predated the recorded handoff.
- Evidence:
  - `scripts/validate_cross_service_parity_live.py` now validates one end-to-end live stateful
    proposal flow across:
    - direct simulation parity against `lotus-core` and `lotus-risk`,
    - sync create and new version,
    - async create and async version,
    - promotion to execution ready,
    - execution handoff,
    - accepted and executed downstream updates,
    - report-request success or governed degraded unavailability,
    - workspace evaluate/save/handoff replay continuity.
  - `tests/e2e/live/test_cross_service_parity_live.py` now gates that full live path behind the
    existing `RUN_LIVE_CROSS_SERVICE_PARITY=1` switch.
  - `src/core/proposals/service.py` now rejects `EXECUTION_UPDATE_OCCURRED_BEFORE_HANDOFF`, which
    prevents an impossible downstream timestamp from being accepted and then misordered behind the
    recorded handoff during execution-status correlation.
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` now proves both:
    - normal downstream execution updates still reconcile correctly, and
    - pre-handoff timestamps are rejected without mutating advisory execution status.
- Consequence:
  - The proposal delivery path is now exercised live with reusable coverage, and execution-status
    correlation is more trustworthy under real downstream event timestamps.
- Follow-Up:
  - If `lotus-report` becomes live locally, keep the validator on the same contract and tighten the
    degraded report assertion to a required `READY` path for environments where reporting is expected.

## LA-REV-014

- Scope: Lotus Core fallback policy and persisted delivery evidence
- Pattern: boundary hardening / auditability gap
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: The controlled local simulation fallback is intentionally a simulation-only escape hatch,
  but that boundary was not proven across lifecycle and workspace stateful flows, and proposal
  replay evidence still stopped at simulation lineage instead of including persisted delivery
  activity such as report requests and execution posture.
- Evidence:
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` now proves stateful create
    and stateful version requests still fail with
    `PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE` even when
    `LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK=true`, which makes the policy boundary explicit:
    fallback does not bypass authoritative Lotus Core context resolution.
  - `tests/unit/advisory/api/test_api_workspace.py` now proves the same for stateful workspace
    evaluation: local fallback cannot substitute for missing authoritative context.
  - `src/api/services/proposal_reporting_service.py` and
    `src/core/proposals/service.py` now persist successful report requests as append-only
    `REPORT_REQUESTED` workflow events instead of leaving reporting as an ephemeral response-only
    seam.
  - `src/core/replay/service.py` now includes normalized `delivery` evidence in proposal-version
    and async replay responses, covering latest execution and reporting posture from persisted
    workflow events.
  - Lifecycle tests now prove:
    - report requests appear in the workflow timeline,
    - proposal replay evidence includes persisted execution/reporting delivery summary,
    - async replay evidence exposes the same persisted delivery summary once the async-created
      proposal continues through execution and reporting.
- Consequence:
  - The platform boundary is clearer: local fallback never fakes authoritative stateful context,
    and persisted proposal replay now reflects delivery truth instead of stopping at simulation
    truth.
- Follow-Up:
  - If report ownership later needs a first-class query surface, build it from the persisted
    workflow events rather than adding a second reporting history store.

## LA-REV-015

- Scope: Delivery read surfaces and fallback-policy executable validation
- Pattern: modularity improvement / operational contract hardening
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: Delivery state was persisted correctly, but there was still no first-class read surface
  for consumers that needed proposal execution/reporting posture without re-parsing full replay
  payloads, and the Lotus Core fallback boundary was only proven inside unit tests rather than by a
  reusable executable validator.
- Evidence:
  - `src/core/proposals/delivery_summary.py` now owns one reusable projector for normalized
    delivery summaries and delivery-event selection from append-only workflow events.
  - `src/core/replay/service.py` now reuses that projector instead of maintaining a second
    delivery-summary implementation.
  - `src/core/proposals/service.py` now exposes:
    - `get_delivery_summary(proposal_id)`, and
    - `get_delivery_history(proposal_id)`,
    both derived from persisted workflow events.
  - `src/api/proposals/routes_delivery.py` now exposes first-class endpoints for:
    - `GET /advisory/proposals/{proposal_id}/delivery-summary`
    - `GET /advisory/proposals/{proposal_id}/delivery-events`
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` now proves those endpoints
    return normalized persisted delivery state and return `404` for missing proposals.
  - `scripts/validate_lotus_core_fallback_policy.py` now provides an executable runtime contract
    check for the fallback boundary:
    - stateless simulate may use controlled local fallback in non-production,
    - stateful create and workspace evaluation still require authoritative Lotus Core context,
    - production rejects local fallback even when requested.
- Consequence:
  - Delivery history is now queryable through a stable domain read surface, replay code is less
    duplicated, and the fallback-policy boundary is validated as an executable operational contract
    instead of relying only on scattered unit tests.
- Follow-Up:
  - If proposal operations later need richer delivery analytics, extend the event projector rather
    than adding parallel execution/reporting history assemblers.

## LA-REV-016

- Scope: Live degraded-runtime validation and dependency readiness truthfulness
- Pattern: operational contract hardening / reliability gap
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: The proposal runtime degraded correctly when `lotus-risk` or `lotus-core` became
  unavailable, but the capability contract still treated configured dependencies as operationally
  ready. That made `/platform/capabilities` optimistic under real outages and left degraded runtime
  drills undocumented and non-repeatable.
- Evidence:
  - `src/integrations/base.py` now supports production-only dependency health probing instead of
    equating `configured=true` with `operational_ready=true`.
  - `tests/unit/advisory/api/test_integration_dependency_base.py` proves:
    - non-production keeps the old no-probe posture,
    - production marks dependencies unready when health probing fails,
    - production marks them ready when health probing succeeds.
  - `tests/unit/advisory/api/test_api_integration_capabilities.py` now proves capability/workflow
    readiness degrades correctly when:
    - `lotus-risk` health probing fails, and
    - `lotus-core` health probing fails in production.
  - `scripts/validate_degraded_runtime_live.py` now provides a self-restoring live drill that:
    - stops `lotus-risk`, verifies proposal simulation degrades to `risk_authority=unavailable`,
      and checks `advisory.proposals.risk_lens` readiness,
    - stops `lotus-core` query/control services, verifies stateless simulation fails without local
      fallback, and checks `advisory.proposals.simulation` readiness.
  - `tests/e2e/live/test_degraded_runtime_live.py` wraps that live drill behind an explicit
    opt-in environment flag.
- Consequence:
  - The operational capability contract now matches real degraded runtime behavior, and the most
    important upstream outage paths are covered by a reusable live validator instead of ad hoc
    manual testing.
- Follow-Up:
  - If dependency probing later becomes too expensive for additional upstreams, keep the shared
    production-only seam but add per-dependency caching rather than reverting to config-only
    readiness.

## LA-REV-017

- Scope: Sequential live runtime validation orchestration
- Pattern: operational reliability / validation-program hardening
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: The live validation assets had become strong individually, but operators still had to
  know which scripts were safe to run together and which drills were intentionally disruptive. That
  made the validation program too easy to misuse under time pressure.
- Evidence:
  - `scripts/validate_live_runtime_suite.py` now orchestrates the live validation program
    sequentially:
    - normal cross-service proposal parity first,
    - degraded runtime drills second.
  - `tests/unit/advisory/api/test_live_runtime_suite.py` now proves:
    - parity always runs before degraded drills,
    - degraded drills can be intentionally skipped for faster non-disruptive passes.
  - `tests/e2e/live/test_live_runtime_suite.py` now provides one explicit opt-in wrapper for the
    full live runtime suite.
- Consequence:
  - The live validation program is easier to run correctly, less likely to self-interfere by
    overlapping disruptive drills, and clearer for future operators who were not present during the
    original integration hardening.
- Follow-Up:
  - If additional disruptive live drills are added later, keep them in the same sequential suite
    rather than introducing another independent operator script.

## LA-REV-018

- Scope: Proposal version lifecycle reset after approvals
- Pattern: workflow correctness / stale-approval hardening
- Status: Hardened
- Finding Class: bug or regression risk
- Summary: Creating a new proposal version after version `1` had already reached
  `EXECUTION_READY` incorrectly preserved that execution-ready state on version `2`. That meant
  stale approvals could leak across versions and make a fresh version look executable before it had
  gone back through the required approval path.
- Evidence:
  - `src/core/proposals/service.py` now resets `proposal.current_state` to `DRAFT` when
    `NEW_VERSION_CREATED` is recorded, and the event now reflects `to_state=DRAFT` rather than
    echoing the previous approved state.
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` now proves:
    - version creation after approvals resets the proposal back to `DRAFT`,
    - the new version cannot be handed off to execution until it is re-approved,
    - multi-version workflow history records `NEW_VERSION_CREATED` with `to_state=DRAFT`.
  - `scripts/validate_cross_service_parity_live.py` now runs a live assertion that:
    - promotes version `1` to `EXECUTION_READY`,
    - creates version `2`,
    - verifies the live stack resets the lifecycle to `DRAFT`, and
    - confirms execution handoff for version `2` is rejected until fresh approvals are recorded.
- Consequence:
  - Proposal versioning now matches the real domain rule that approvals are version-scoped, and
    execution eligibility cannot silently bleed from an old version into a new one.
- Follow-Up:
  - If the product later needs explicit approval-carry-forward semantics, model that as a governed
    workflow decision with a dedicated event and audit trail instead of inferring it from previous
    version state.

## LA-REV-019

- Scope: Mixed approval-route lineage across proposal versions
- Pattern: workflow lineage hardening / validation gap
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: The proposal workflow supports both compliance-first and risk-first approval routes, but
  the validation program had only been exercising one route at a time. That left a gap around
  mixed-version histories where version `1` follows one route and version `2` follows another.
- Evidence:
  - `scripts/validate_cross_service_parity_live.py` now parameterizes the promotion helper so the
    live validator can exercise both approval routes intentionally.
  - The live validator now proves a mixed lineage case where:
    - version `1` reaches `EXECUTION_READY` through `COMPLIANCE_REVIEW`,
    - version `2` reaches `EXECUTION_READY` through `RISK_REVIEW`,
    - workflow timeline retains `COMPLIANCE_APPROVED` on version `1` and `RISK_APPROVED` on
      version `2`,
    - the approvals endpoint preserves the full cross-version approval audit trail.
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` now proves the same mixed
    route lineage contract in a deterministic unit test.
- Consequence:
  - The workflow validation program now covers both supported approval branches in one versioned
    proposal lineage, reducing the risk of route-specific regressions that only appear after a new
    version is created.
- Follow-Up:
  - If future approval policies add route-specific metadata or conditional approvals, keep them in
    the same version-scoped lineage model rather than introducing route-specific side stores.

## LA-REV-020

- Scope: Delivery anchoring after mixed approval-route divergence
- Pattern: workflow lineage hardening / delivery-surface validation gap
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: Mixed approval-route histories were covered at the approval/timeline layer, but delivery
  surfaces still needed explicit validation to prove execution and reporting remain anchored to the
  latest approved version rather than inheriting stale context from earlier approval routes.
- Evidence:
  - `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` now proves a mixed-route
    lineage where:
    - version `1` takes the compliance-first path,
    - version `2` takes the risk-first path,
    - execution and reporting are requested only for version `2`,
    - `delivery-summary` and `delivery-events` remain fully anchored to version `2`.
  - `scripts/validate_cross_service_parity_live.py` now runs the same mixed-route delivery check on
    the live stack and asserts:
    - delivery execution summary is anchored to version `2`,
    - reporting summary is either anchored to version `2` or absent under degraded reporting,
    - delivery history contains only version-`2` execution/reporting events.
- Consequence:
  - The proposal workflow now has explicit regression protection for the most important lifecycle
    invariant in mixed-route histories: approval lineage may span versions, but delivery lineage
    must stay pinned to the latest approved version.
- Follow-Up:
  - If delivery workflows later support partial execution on multiple versions in one lineage,
    promote delivery projection rules into an explicit documented contract rather than inferring them
    only from workflow events.

## LA-REV-021

- Scope: Changed-state cross-service proposal parity
- Pattern: live validation gap / canonical integration hardening
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: The live validation program already proved no-op before-state parity and changed-state
  risk parity, but it still lacked an executable proof that a real proposal delta preserves
  canonical Lotus Core after-state allocation views as well as Lotus Risk concentration.
- Evidence:
  - `scripts/validate_cross_service_parity_live.py` now proves a changed-state path where the
    validator:
    - selects a real held non-cash security from live Lotus Core positions,
    - creates a stateful workspace and adds a draft trade,
    - compares the workspace `risk_lens` to direct `lotus-risk` concentration using the same
      effective `simulation_changes`,
    - compares workspace before/after allocation views to direct Lotus Core
      `/integration/advisory/proposals/simulate-execution` using the same resolved stateful request.
  - `tests/unit/advisory/api/test_live_cross_service_parity.py` now locks the helper contracts for:
    - selecting a real changed-state security from live-style positions,
    - deriving Lotus Risk `simulation_changes` from proposal intents without drift.
- Consequence:
  - The live integration program now covers the core production question for proposal deltas:
    when `lotus-advise` mutates a live portfolio through a real draft trade, both allocation and
    concentration remain aligned with their canonical upstream authorities.
- Follow-Up:
  - If future proposal deltas add more complex change types such as notional-only trades, FX, or
    cash flows, extend the changed-state live parity drill with those cases instead of introducing a
    separate validation path.

## LA-REV-022

- Scope: Cross-currency changed-state proposal parity
- Pattern: FX-sensitive live validation gap
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: Changed-state proposal parity was proven for a real held security, but that still left a
  material blind spot: whether a live proposal delta on a non-base-currency holding preserves
  canonical allocation and concentration behavior through FX conversion.
- Evidence:
  - `scripts/validate_cross_service_parity_live.py` now adds a second changed-state drill that:
    - selects the highest-weight non-cash holding outside the portfolio reporting currency,
    - runs the same workspace draft-trade path against that holding,
    - proves changed-state `risk_lens` still matches direct `lotus-risk` concentration,
    - proves changed-state before/after allocation views still match direct Lotus Core simulation.
  - `tests/unit/advisory/api/test_live_cross_service_parity.py` now proves the helper that selects
    cross-currency live holdings prefers the highest-weight eligible non-base position and ignores
    cash rows.
  - `scripts/live_runtime_suite_artifacts.py` and
    `tests/unit/advisory/api/test_live_runtime_suite.py` now surface the cross-currency security in
    machine-readable and PR-facing evidence output.
- Consequence:
  - The live parity program now covers both same-currency and cross-currency proposal deltas, which
    materially improves confidence in FX-sensitive after-state allocation and risk behavior.
- Follow-Up:
  - If multi-currency proposal support expands to explicit FX intents, add a dedicated drill that
    validates trade-plus-FX interaction rather than assuming security-trade-only changes.

## LA-REV-023

- Scope: Non-held instrument changed-state proposal parity
- Pattern: enrichment and hydration live validation gap
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: Same-currency and cross-currency changed-state drills covered held positions, but the
  proposal path also needs to work when an advisor drafts a buy for a non-held instrument that must
  be hydrated through the stateful Lotus Core enrichment seam.
- Evidence:
  - `scripts/validate_cross_service_parity_live.py` now adds a non-held changed-state drill that:
    - selects a preferred non-held seeded candidate not already present in the live portfolio,
    - runs a stateful workspace draft trade on that instrument,
    - proves changed-state `risk_lens` still matches direct `lotus-risk` concentration,
    - proves changed-state before/after allocation views still match direct Lotus Core simulation.
  - `tests/unit/advisory/api/test_live_cross_service_parity.py` now proves the non-held selector
    prefers the first viable non-held candidate from the governed seeded list.
  - `scripts/live_runtime_suite_artifacts.py` and
    `tests/unit/advisory/api/test_live_runtime_suite.py` now surface the non-held security in the
    suite evidence output.
- Consequence:
  - The live parity program now covers the most failure-prone proposal enrichment path: adding a new
    instrument that was not already in the held portfolio snapshot.
- Follow-Up:
  - If future seeded universes change, keep the non-held candidate list governed and business
    meaningful rather than letting the live drill drift to arbitrary instruments.

## LA-REV-024

- Scope: Operator-grade live evidence generation
- Pattern: validation workflow friction / evidence handoff gap
- Status: Hardened
- Finding Class: architecture or modularity issue
- Summary: The live validation program already produced strong evidence, but it still required
  operators to run the suite and the PR-summary rendering as separate manual steps. That left a
  small but real process gap between successful validation and durable merge-ready evidence.
- Evidence:
  - `scripts/live_runtime_suite_artifacts.py` now includes `write_pr_summary_for_bundle(...)`,
    which writes a PR-ready markdown summary directly alongside a resolved evidence bundle.
  - `scripts/run_live_runtime_evidence_bundle.py` now provides a single operator command that:
    - runs the live runtime suite,
    - writes the timestamped evidence bundle,
    - writes `pr-summary.md` in the bundle or to an explicit output path.
  - `tests/unit/advisory/api/test_live_runtime_suite.py` now proves:
    - PR summaries can be written directly beside a bundle,
    - the one-command wrapper writes `result.json`, `summary.md`, and `pr-summary.md`.
- Consequence:
  - Live validation is now easier to run correctly and easier to hand off into PR notes or review
    records without manual chaining between scripts.
- Follow-Up:
  - If the team wants CI-attached live evidence later, reuse the same bundle and PR-summary writers
    rather than introducing a second evidence format.

## LA-REV-025

- Scope: Integration capability contract modularity
- Pattern: modularity problem / API contract hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: The `/platform/capabilities` route mixed HTTP wiring, Pydantic contract models,
  dependency-readiness interpretation, feature/workflow construction, and supportability metric
  recording in one router-adjacent module. That made a platform-facing contract harder to review,
  extend, and test without touching controller code.
- Evidence:
  - `src/api/routers/integration_capabilities.py` now contains only HTTP route wiring for
    `GET /platform/capabilities`.
  - `src/api/capabilities/models.py` now owns the capability, readiness, workflow, and
    supportability response contracts and Swagger examples.
  - `src/api/capabilities/service.py` now owns feature/workflow assembly, dependency-readiness
    interpretation, fail-closed missing-dependency behavior, and supportability metric emission.
  - `tests/unit/advisory/api/test_api_integration_capabilities.py` now covers the service-level
    missing-dependency path directly, so a malformed readiness payload cannot silently become an
    optimistic AI-rationale posture.
  - `README.md` now references the actual `GET /platform/capabilities` route, and
    `wiki/Supported-Features.md` records implementation-backed functional and non-functional
    capability posture for business, operations, sales, pre-sales, demo, and engineering users.
- Consequence:
  - The platform capability contract is easier to maintain and safer to evolve without coupling
    contract changes to controller code.
- Follow-Up:
  - Continue the same pattern for the larger proposal lifecycle and stateful Lotus Core context
    modules, using `docs/rfcs/WTBD.md` to keep follow-up work scoped and owner-specific.

## LA-REV-026

- Scope: Async proposal submission hashing and replay metadata
- Pattern: modularity problem / idempotency hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Async create/version submission hash logic and replay metadata extraction were embedded
  in the large proposal workflow service, even though they are pure domain helpers. That increased
  the size of `service.py` and made idempotency rules harder to test without constructing the full
  workflow service.
- Evidence:
  - `src/core/proposals/async_payloads.py` now owns canonical async create submission hashing,
    version submission hashing, and persisted submission-hash extraction.
  - `src/core/proposals/service.py` now delegates async submission hashing and replay hash
    extraction to that module while retaining orchestration, repository mutation, and operation
    state transitions.
  - `tests/unit/advisory/engine/test_engine_proposal_async_payloads.py` now proves:
    - legacy and normalized stateless create submissions hash identically,
    - version submission hashes are scoped to `proposal_id`,
    - persisted `submission_hash` takes precedence over fallback payload hashing,
    - fallback payload hashing remains deterministic for older persisted async payloads.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_async_payloads.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - The async idempotency contract is easier to review and extend without expanding the already
    large workflow service.
- Follow-Up:
  - Continue decomposing `src/core/proposals/service.py` by extracting delivery projection,
    lifecycle transition resolution, and report/execution handoff helpers in separate small slices.

## LA-REV-027

- Scope: Proposal workflow transition and execution-status rules
- Pattern: modularity problem / workflow correctness hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Proposal transition maps, approval transition logic, execution-update mapping, execution
  status projection, and state-correlation labels were embedded in `ProposalWorkflowService`.
  These rules are pure workflow policy and should be directly testable outside the repository-backed
  service orchestration path.
- Evidence:
  - `src/core/proposals/workflow_rules.py` now owns terminal states, transition maps,
    approval-transition resolution, execution-update mapping, execution-status projection, and
    execution state-correlation labels.
  - `src/core/proposals/service.py` now delegates those pure rules while keeping temporary wrapper
    methods for existing service call sites and compatibility with current tests.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_rules.py` directly proves cancel
    behavior, invalid transition behavior, approval approved/rejected paths, invalid approval
    states/types, execution update mapping, execution status projection, and default correlation
    fallback.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_workflow_rules.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Workflow rules can now be reviewed and extended as domain policy rather than as hidden private
    service implementation details.
- Follow-Up:
  - Replace direct private-method tests with workflow-rule tests over time, then remove the
    compatibility wrappers once no service-internal test reaches through the class boundary.

## LA-REV-028

- Scope: Delivery projection vocabulary convergence
- Pattern: duplicate logic / workflow correctness hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `src/core/proposals/delivery_summary.py` carried its own execution event set and
  execution-status mapping even after proposal workflow rules were extracted. That created a small
  but important drift risk between execution-status endpoints and delivery-summary projection.
- Evidence:
  - `src/core/proposals/delivery_summary.py` now imports `EXECUTION_STATUS_EVENT_TYPES` and
    `execution_status_for_event(...)` from `src/core/proposals/workflow_rules.py`.
  - `tests/unit/advisory/engine/test_engine_proposal_delivery_summary.py` now directly proves
    latest execution-status projection, report-request projection, and delivery-only event
    filtering.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_delivery_summary.py tests\unit\advisory\engine\test_engine_proposal_workflow_rules.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Execution and delivery surfaces now share one bounded workflow vocabulary instead of maintaining
    duplicate mappings in separate modules.
- Follow-Up:
  - Continue consolidating projection code around explicit modules before decomposing larger
    report-request and execution-handoff service methods.

## LA-REV-029

- Scope: Proposal record-to-DTO projections
- Pattern: modularity problem / DTO mapping hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Proposal summary, version detail, workflow event, and approval record projections were
  pure record-to-DTO mappers embedded in `ProposalWorkflowService`. That kept presentation contract
  shaping inside the already-large orchestration service and made evidence redaction behavior harder
  to test directly.
- Evidence:
  - `src/core/proposals/projections.py` now owns proposal summary, version detail, workflow event,
    and approval record projection helpers.
  - `src/core/proposals/service.py` now delegates those projections while preserving the existing
    service boundary and API payloads.
  - `tests/unit/advisory/engine/test_engine_proposal_projections.py` directly proves lifecycle
    identity projection, evidence bundle redaction/inclusion, gate-decision hydration, workflow
    event audit payloads, and nullable approval projection.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_projections.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - DTO projection behavior can now be reviewed and tested independently from repository-backed
    workflow orchestration.
- Follow-Up:
  - Continue extracting version record creation, report-request projection, and execution handoff
    helpers in separate small slices.

## LA-REV-030

- Scope: Proposal execution-status projection
- Pattern: modularity problem / execution lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Execution-status response assembly, latest execution event selection, and state
  correlation shaping were embedded in `ProposalWorkflowService`. That mixed repository
  orchestration with derived downstream execution lineage and made the fallback paths harder to
  test directly.
- Evidence:
  - `src/core/proposals/execution_status.py` now owns latest execution request/status event
    selection and `ProposalExecutionStatusResponse` assembly from proposal records and workflow
    events.
  - `src/core/proposals/service.py` now delegates status retrieval projection to the execution
    status module while retaining repository lookup and write-path validation.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_status.py` directly proves no-handoff
    defaults, latest handoff/execution projection, execution-id fallback behavior, state-correlation
    labels, and downstream event-only recovery.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_execution_status.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Execution status can now be reviewed as a deterministic projection over workflow events instead
    of hidden logic inside the workflow orchestration service.
- Follow-Up:
  - Continue extracting execution handoff request construction and report request projection in
    separate small slices.

## LA-REV-031

- Scope: Proposal report-request workflow event construction
- Pattern: modularity problem / reporting lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `REPORT_REQUESTED` workflow event construction was embedded in `ProposalWorkflowService`
  even though it is a deterministic translation from the downstream report response, proposal
  aggregate, requesting actor, version scope, and execution-summary flag. That kept report lineage
  payload shaping inside repository mutation code.
- Evidence:
  - `src/core/proposals/reporting.py` now owns `build_report_requested_event(...)`.
  - `src/core/proposals/service.py` now delegates event construction while retaining proposal lookup,
    aggregate timestamp mutation, and repository transition persistence.
  - `tests/unit/advisory/engine/test_engine_proposal_reporting.py` directly proves the report
    lineage payload, actor, state preservation, version scope, and report artifact reference captured
    in the workflow event.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_reporting.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Reporting lineage event construction can now be reviewed and tested independently from workflow
    repository mutation.
- Follow-Up:
  - Continue extracting execution handoff request construction and async operation payload
    resolution in separate small slices.

## LA-REV-032

- Scope: Proposal async operation state transitions
- Pattern: modularity problem / async reliability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Async operation attempt start, success marking, failure marking, runtime retry/fail
  outcome handling, and replay lineage assembly were embedded in `ProposalWorkflowService`. Those
  rules are deterministic state transitions on `ProposalAsyncOperationRecord` and should be
  testable without repository orchestration.
- Evidence:
  - `src/core/proposals/async_operations.py` now owns async attempt lifecycle mutation helpers and
    replay lineage assembly.
  - `src/core/proposals/service.py` now delegates async operation state transitions while retaining
    repository lookup, persistence, and executor orchestration.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` directly proves lease
    assignment, attempt counting, success result persistence, failure payloads, runtime requeue
    versus terminal failure, and replay lineage identity.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_async_operations.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Async retry and terminal-state behavior can now be reviewed as explicit operation-state policy
    instead of service-private mutation code.
- Follow-Up:
  - Continue extracting async payload recovery and execution handoff request construction in
    separate small slices.

## LA-REV-033

- Scope: Proposal async payload recovery
- Pattern: modularity problem / idempotency recovery hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Async create/version payload recovery was embedded in `ProposalWorkflowService`, mixing
  persisted payload validation, fallback payload handling, idempotency key recovery, proposal scope
  recovery, and repository failure marking. The payload recovery rules are deterministic and should
  be reviewable independently from operation persistence.
- Evidence:
  - `src/core/proposals/async_payloads.py` now owns typed create/version async payload recovery
    results and failure outcomes.
  - `src/core/proposals/service.py` now delegates payload recovery and remains responsible only for
    converting recovery failures into persisted async operation errors.
  - `tests/unit/advisory/engine/test_engine_proposal_async_payloads.py` now proves persisted create
    payload recovery, missing/invalid create payload behavior, idempotency-key failure behavior,
    version proposal-scope fallback, and missing version proposal-scope failure behavior.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_async_payloads.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Restart-safe async recovery is now explicit domain logic with typed outcomes rather than
    service-private branching.
- Follow-Up:
  - Continue extracting execution handoff request construction and version-record construction in
    separate small slices.

## LA-REV-034

- Scope: Proposal immutable version-record construction
- Pattern: modularity problem / lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Immutable proposal version construction was embedded in `ProposalWorkflowService`,
  combining simulation payload serialization, simulation hash calculation, artifact hash extraction,
  evidence-bundle retention policy, and gate-decision snapshotting. These rules define version
  lineage and should be testable without workflow repository orchestration.
- Evidence:
  - `src/core/proposals/versions.py` now owns `build_proposal_version_record(...)`.
  - `src/core/proposals/service.py` now supplies the generated version id and delegates record
    construction while preserving existing create/version orchestration.
  - `tests/unit/advisory/engine/test_engine_proposal_versions.py` directly proves artifact hash
    capture, simulation hash calculation, proposal result persistence, gate-decision snapshotting,
    and evidence-bundle retention/redaction behavior.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_versions.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Version lineage construction is now explicit domain logic rather than a private service helper.
- Follow-Up:
  - Continue extracting execution handoff request construction and proposal lifecycle origin
    validation in separate small slices.

## LA-REV-035

- Scope: Proposal lifecycle origin validation
- Pattern: modularity problem / lifecycle-domain hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Lifecycle origin validation was embedded in `ProposalWorkflowService`, even though the
  invariant is a domain rule: workspace handoffs must carry a source workspace id, and direct
  creates must not. Keeping the rule in the orchestration service made lifecycle entry-point policy
  less discoverable and harder to test directly.
- Evidence:
  - `src/core/proposals/lifecycle.py` now owns `validate_lifecycle_origin(...)` and the bounded
    lifecycle-origin validation error.
  - `src/core/proposals/service.py` now delegates lifecycle-origin validation and preserves existing
    `ProposalValidationError` behavior at the service boundary.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle.py` directly proves valid direct
    create and workspace handoff entry points, missing workspace handoff source rejection, and
    direct-create source workspace rejection.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_lifecycle.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Advisory lifecycle entry-point policy is now explicit domain logic instead of service-private
    validation code.
- Follow-Up:
  - Continue extracting execution handoff request construction and create-response projection in
    separate small slices.

## LA-REV-036

- Scope: Proposal create and async response projections
- Pattern: modularity problem / DTO mapping hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Create response, async accepted response, and async status response DTO projection were
  embedded in `ProposalWorkflowService` alongside orchestration and repository access. These
  projections are deterministic record-to-contract mappings and belong with the other proposal
  projection helpers.
- Evidence:
  - `src/core/proposals/projections.py` now owns create response, async accepted response, and async
    operation status response projection helpers.
  - `src/core/proposals/service.py` now delegates those DTO mappings while retaining repository and
    workflow orchestration.
  - `tests/unit/advisory/engine/test_engine_proposal_projections.py` now directly proves create
    response projection with evidence retention and async operation status projection including
    timestamps, status URL, attempt counts, lease expiry, and typed error payload.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_projections.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Proposal API response mapping is further consolidated in a single projection module and is
    testable independently from service orchestration.
- Follow-Up:
  - Continue extracting execution handoff request construction and replay/idempotency lookup helpers
    in separate small slices.

## LA-REV-037

- Scope: Proposal service projection wrapper removal
- Pattern: stale code / modularity hardening
- Status: Hardened
- Finding Class: stale code
- Summary: After consolidating proposal response projections, `ProposalWorkflowService` still kept
  private pass-through methods for create response, summary, version detail, workflow event,
  approval, async accepted, and async status projection. Those wrappers added indirection without
  preserving a service-specific boundary.
- Evidence:
  - `src/core/proposals/service.py` now calls projection helpers directly and no longer carries the
    stale projection wrapper methods.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` no longer reaches into the
    removed private approval projection wrapper; nullable approval projection remains covered by
    `tests/unit/advisory/engine/test_engine_proposal_projections.py`.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_projections.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - The workflow service is smaller and routes DTO mapping through the explicit projection module
    rather than compatibility wrappers.
- Follow-Up:
  - Continue removing service-private wrappers only when the extracted helper owns the behavior and
    tests no longer need to reach through the service boundary.

## LA-REV-038

- Scope: Proposal async replay-lineage wrapper cleanup
- Pattern: stale code / async lineage hardening
- Status: Hardened
- Finding Class: stale code
- Summary: After extracting async operation helpers, `ProposalWorkflowService` still kept a pure
  `_build_async_replay_lineage(...)` pass-through and an unused `_utc_after(...)` helper. Both were
  stale remnants from earlier async operation state extraction.
- Evidence:
  - `src/core/proposals/service.py` now calls `build_async_replay_lineage(...)` directly and no
    longer defines `_build_async_replay_lineage(...)`.
  - The unused `_utc_after(...)` helper and its `timedelta` import were removed from
    `src/core/proposals/service.py`.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_async_operations.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Async replay lineage now flows directly through the extracted async operation module without a
    redundant service-private alias.
- Follow-Up:
  - Continue checking service-private helpers for real boundary value before preserving them.
