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
- Status: Hardened
- Finding Class: observability gap
- Summary: `/platform/capabilities` now separates local feature enablement, workflow readiness,
  dependency posture, supportability metrics, and dependency readiness evidence.
- Evidence:
  - Capability construction now lives under `src/api/capabilities/` instead of a monolithic router.
  - `IntegrationCapabilitiesResponse` includes feature, workflow, dependency-readiness, and
    `supportability` posture for Gateway and platform consumers.
  - Dependency readiness now reports `runtime_probe_enabled`, `readiness_basis`, and
    `degraded_reason`, so consumers can distinguish missing configuration, configuration-only
    non-production posture, successful runtime probes, and failed runtime probes.
  - Unit coverage proves ready, degraded, lifecycle-disabled, missing-configuration, local fallback,
    and production probe-failure posture.
- Consequence:
  - `lotus-gateway`, `lotus-workbench`, operations, and pre-sales demo preparation can present
    advisory capability truth without treating environment flags as operational readiness.
- Follow-Up:
  - Keep future capability additions dependency-aware and document their readiness evidence in the
    OpenAPI contract.

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

## LA-REV-039

- Scope: Proposal version-record wrapper removal
- Pattern: stale code / lineage hardening
- Status: Hardened
- Finding Class: stale code
- Summary: After extracting immutable version-record construction, `ProposalWorkflowService` still
  carried `_to_version_record(...)`, a thin wrapper that generated a version id and forwarded to the
  extracted builder. It was another service-private alias around domain logic now owned by
  `src/core/proposals/versions.py`.
- Evidence:
  - `src/core/proposals/service.py` now calls `build_proposal_version_record(...)` directly at the
    proposal create and new-version creation sites.
  - The unused `ProposalVersionRecord` import and `_to_version_record(...)` method were removed from
    `src/core/proposals/service.py`.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_versions.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Version lineage construction has a single explicit module boundary and no stale service alias.
- Follow-Up:
  - Continue decomposing orchestration only where a helper owns domain behavior or removes meaningful
    coupling.

## LA-REV-040

- Scope: Wiki architecture implementation map
- Pattern: documentation drift / modularity hardening
- Status: Hardened
- Finding Class: documentation drift
- Summary: The repo-local wiki architecture page described proposal lifecycle ownership at a high
  level but did not reflect the current modular proposal backend after the service decomposition
  slices. That left engineering, operations, and demo-facing documentation behind the code.
- Evidence:
  - `wiki/Architecture.md` now documents the implementation-backed proposal module map for service
    orchestration, models, context resolution, workflow rules, projections, version lineage, async
    payload recovery, async operation state, execution status, delivery summary, reporting, and
    lifecycle validation.
  - `wiki/Architecture.md` now includes Mermaid diagrams for proposal lifecycle orchestration and
    operational lineage.
  - `python -m pytest tests\unit\test_ci_workflow_contracts.py -q` passed.
  - `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-advise` was run and reported expected
    unpublished repo-local wiki drift: `_Sidebar.md`, `Architecture.md`, `Home.md`, and
    `Supported-Features.md`.
- Consequence:
  - The wiki now explains the current backend module boundaries and evidence flow in a way that is
    useful to engineering, operations, pre-sales, and client-demo preparation.
- Follow-Up:
  - Publish the repo-local wiki after merge to `main` using the governed wiki publication flow.

## LA-REV-041

- Scope: Proposal replay idempotency lookup
- Pattern: modularity problem / idempotency hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workflow event and approval replay lookup for idempotent lifecycle calls was embedded in
  `ProposalWorkflowService`, including latest-match scan behavior and request-hash conflict
  detection. Those rules are deterministic over append-only event and approval history and should be
  testable outside repository orchestration.
- Evidence:
  - `src/core/proposals/idempotency.py` now owns replay lookup for workflow events and approvals,
    plus the bounded replay hash conflict error.
  - `src/core/proposals/service.py` now delegates replay lookup and translates replay hash conflicts
    into the existing service-level `ProposalIdempotencyConflictError`.
  - `tests/unit/advisory/engine/test_engine_proposal_idempotency.py` directly proves latest matching
    event/approval replay behavior, empty idempotency-key behavior, and hash conflict behavior.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_idempotency.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Idempotency replay semantics are now explicit proposal-domain logic instead of service-private
    list scanning.
- Follow-Up:
  - Continue extracting only deterministic replay or validation logic where repository interaction
    remains clearly owned by the service.

## LA-REV-042

- Scope: Proposal expected-state concurrency validation
- Pattern: modularity problem / optimistic-concurrency hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Expected-state optimistic concurrency validation was embedded in
  `ProposalWorkflowService`, even though the rule is deterministic and shared by workflow,
  approval, and execution lifecycle commands. That made a banking-grade state-concurrency guard
  harder to test and reuse independently from repository orchestration.
- Evidence:
  - `src/core/proposals/concurrency.py` now owns expected-state validation and the bounded
    proposal-domain validation error.
  - `src/core/proposals/service.py` delegates expected-state checks to the proposal concurrency
    helper and translates domain validation failures into the existing service-level
    `ProposalStateConflictError`.
  - `tests/unit/advisory/engine/test_engine_proposal_concurrency.py` directly proves matching,
    optional-missing, required-missing, and mismatched expected-state behavior.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_concurrency.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Optimistic concurrency policy is now explicit proposal-domain logic instead of a
    service-private condition, while service methods remain the orchestration and error-translation
    boundary.
- Follow-Up:
  - Continue extracting deterministic validation rules where they improve reuse and testability
    without moving persistence orchestration out of the service boundary.

## LA-REV-043

- Scope: Proposal simulation enablement gate
- Pattern: duplicated validation / API-service consistency
- Status: Hardened
- Finding Class: duplicate logic
- Summary: The `options.enable_proposal_simulation` proposal guard was enforced separately in the
  proposal lifecycle service and the direct simulation API service. Both paths used the same
  private-banking product-control rule and error message, but the implementation lived at two
  boundaries instead of in shared proposal-domain validation.
- Evidence:
  - `src/core/proposals/simulation_gate.py` now owns the simulation enablement guard, canonical
    disabled message, and bounded domain error.
  - `src/core/proposals/service.py` delegates lifecycle proposal validation to the shared gate and
    translates failures into `ProposalValidationError`.
  - `src/api/services/advisory_simulation_service.py` delegates direct simulation validation to the
    shared gate and translates failures into the existing HTTP 422 response.
  - `tests/unit/advisory/engine/test_engine_proposal_simulation_gate.py` directly proves enabled,
    disabled, and not-required behavior.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_simulation_gate.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py tests\unit\advisory\api\test_api_advisory_proposal_simulate.py tests\unit\advisory\api\test_api_advisory_proposal_lifecycle.py -q`.
- Consequence:
  - Proposal simulation gating now has one reusable validation rule while API and lifecycle service
    boundaries keep their own error translation responsibilities.
- Follow-Up:
  - Continue scanning API/service pairs for duplicated proposal product-control rules before they
    diverge across channels.

## LA-REV-044

- Scope: Proposal correlation identifier resolution
- Pattern: observability consistency / lineage hardening
- Status: Hardened
- Finding Class: duplicate logic
- Summary: Proposal lifecycle, async submission, async versioning, and direct simulation paths each
  generated fallback correlation IDs with local inline UUID formatting. The format was consistent,
  but the policy was duplicated across API and service boundaries that both feed advisory lineage
  and operational diagnostics.
- Evidence:
  - `src/core/proposals/correlation.py` now owns proposal fallback correlation ID resolution.
  - `src/core/proposals/service.py` now uses the shared resolver for lifecycle simulation and async
    operation correlation IDs.
  - `src/api/services/advisory_simulation_service.py` now uses the same resolver for direct
    simulation fallback correlation IDs.
  - `tests/unit/advisory/engine/test_engine_proposal_correlation.py` directly proves supplied ID
    preservation and governed fallback ID shape.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_correlation.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py tests\unit\advisory\api\test_api_advisory_proposal_simulate.py -q`.
- Consequence:
  - Proposal correlation lineage now has one explicit policy point, reducing drift risk across API,
    async, and lifecycle execution paths.
- Follow-Up:
  - Consider extracting proposal identifier factories only when a broader ID-governance slice can
    cover proposal, version, event, approval, execution, and async operation identifiers together.

## LA-REV-045

- Scope: Proposal identifier factories
- Pattern: duplicate logic / lineage hardening
- Status: Hardened
- Finding Class: duplicate logic
- Summary: Proposal, version, workflow event, async operation, execution request, approval, and
  report request identifiers were generated inline across service and reporting boundaries. The
  prefixes are part of advisory lineage and operational diagnostics, so they should be governed in
  one proposal-domain module rather than repeated at each write path.
- Evidence:
  - `src/core/proposals/identifiers.py` now owns proposal-domain identifier factories for `pp`,
    `ppv`, `pwe`, `pop`, `pex`, `pap`, and `prr` prefixes.
  - `src/core/proposals/service.py` now uses the shared factories for proposal lifecycle, async,
    execution, approval, and workflow event records.
  - `src/api/services/proposal_reporting_service.py` now uses the shared report-request identifier
    factory before calling `lotus-report`.
  - `tests/unit/advisory/engine/test_engine_proposal_identifiers.py` directly proves governed
    prefix and suffix shape for every proposal-domain factory.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_identifiers.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py tests\unit\advisory\api\test_api_advisory_proposal_lifecycle.py -q`.
- Consequence:
  - Proposal lineage identifiers now have a single explicit policy point, reducing drift risk across
    lifecycle, reporting, async, approval, and execution write paths.
- Follow-Up:
  - Keep identifier factories thin unless platform-wide ID policy, entropy length, or audit
    requirements change.

## LA-REV-046

- Scope: Async submission hash wrapper removal
- Pattern: stale code / async idempotency hardening
- Status: Hardened
- Finding Class: stale code
- Summary: After async create/version submission hashing moved into
  `src/core/proposals/async_payloads.py`, `ProposalWorkflowService` still carried private
  `_hash_async_create_submission(...)` and `_hash_async_version_submission(...)` wrappers. Those
  wrappers added no boundary behavior and obscured the module that owns async submission hash
  canonicalization.
- Evidence:
  - `src/core/proposals/service.py` now imports and calls `hash_async_create_submission(...)` and
    `hash_async_version_submission(...)` directly.
  - The stale service-private hash wrapper methods and alias imports were removed.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\engine\test_engine_proposal_async_payloads.py tests\unit\advisory\engine\test_engine_proposal_workflow_service.py -q`.
- Consequence:
  - Async submission idempotency hashing has one explicit proposal-domain owner and no redundant
    service-private alias layer.
- Follow-Up:
  - Continue removing service-private wrappers only where they do not provide persistence,
    orchestration, or error-translation boundary value.

## LA-REV-047

- Scope: Workspace identifier factories
- Pattern: duplicate logic / workspace lineage hardening
- Status: Hardened
- Finding Class: duplicate logic
- Summary: Workspace session, trade draft, cash-flow draft, and saved-version identifiers were
  generated inline inside `src/api/services/workspace_service.py`. Those identifiers are part of
  workspace replay evidence, lifecycle handoff lineage, and client-facing workspace URLs, so their
  prefix policy should be explicit and testable outside the API service implementation.
- Evidence:
  - `src/core/workspace/identifiers.py` now owns workspace identifier factories for `aws`, `wtd`,
    `wcf`, and `awv` prefixes.
  - `src/api/services/workspace_service.py` now uses those factories when creating sessions, draft
    trade rows, draft cash-flow rows, and saved workspace versions.
  - `src/api/services/workspace_service.py` now uses the shared proposal correlation resolver for
    workspace reevaluation correlation IDs, aligning workspace-originated simulation lineage with
    proposal-originated simulation lineage.
  - `tests/unit/advisory/api/test_workspace_identifiers.py` directly proves governed prefix and
    suffix shape for every workspace identifier factory.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\api\test_workspace_identifiers.py tests\unit\advisory\api\test_workspace_service.py tests\unit\advisory\api\test_api_workspace.py -q`.
- Consequence:
  - Workspace lineage identifiers now have a single explicit policy point and no inline UUID
    formatting inside the workspace service.
- Follow-Up:
  - Continue decomposing `workspace_service.py` around replay evidence, handoff orchestration, and
    draft action handling only where the extraction reduces real coupling and keeps API behavior
    stable.

## LA-REV-048

- Scope: Workspace replay evidence and handoff continuity
- Pattern: modularity problem / lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace replay evidence construction, matching saved-version lookup, and handoff
  continuity mutation lived inside `src/api/services/workspace_service.py`. Those behaviors are
  deterministic workspace-domain lineage rules and should be directly testable without requiring
  callers to inspect the API service implementation.
- Evidence:
  - `src/core/workspace/replay.py` now owns workspace draft-state hashing, replay evidence
    construction, saved-version matching, handoff lineage construction, and continuity application.
  - `src/api/services/workspace_service.py` now delegates replay evidence and handoff continuity
    behavior to the workspace replay module while retaining orchestration and persistence.
  - `tests/unit/advisory/api/test_workspace_replay.py` directly proves handoff lineage selects the
    matching saved version and applies continuity to both latest replay evidence and saved-version
    replay evidence.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\api\test_workspace_replay.py tests\unit\advisory\api\test_workspace_service.py tests\unit\advisory\api\test_api_workspace.py -q`.
- Consequence:
  - Workspace replay lineage is now explicit workspace-domain behavior, reducing the size and
    responsibility of the API service without changing API contracts.
- Follow-Up:
  - Continue extracting workspace handoff request assembly and draft mutation only where direct
    tests can prove behavior more clearly than API-level coverage alone.

## LA-REV-049

- Scope: Workspace saved-version metadata and lookup
- Pattern: modularity problem / saved-version lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Saved-version summary refresh and saved-version lookup lived inside
  `src/api/services/workspace_service.py`, even though they are deterministic workspace-domain
  rules used by save, list, compare, resume, and replay-evidence flows. Keeping them in the large
  API service made saved-version behavior harder to test directly.
- Evidence:
  - `src/core/workspace/versions.py` now owns saved-version summary construction, latest-version
    metadata refresh, saved-version lookup, and the bounded lookup error.
  - `src/api/services/workspace_service.py` now delegates saved-version lookup and metadata refresh
    to the workspace versions module while preserving the existing API-service
    `WorkspaceSavedVersionNotFoundError` translation.
  - `tests/unit/advisory/api/test_workspace_versions.py` directly proves latest saved-version
    metadata refresh and missing saved-version lookup behavior.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\api\test_workspace_versions.py tests\unit\advisory\api\test_workspace_service.py tests\unit\advisory\api\test_api_workspace.py -q`.
- Consequence:
  - Workspace saved-version behavior now has a reusable module boundary and direct tests, while
    API behavior and error vocabulary remain unchanged.
- Follow-Up:
  - Continue extracting workspace draft mutation and handoff request assembly only where it reduces
    service coupling and preserves current API contracts.

## LA-REV-050

- Scope: Workspace draft-state projection
- Pattern: modularity problem / draft workflow hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace draft-state construction from proposal simulation requests and reconstruction
  of simulation requests from draft rows lived inside `src/api/services/workspace_service.py`.
  These are deterministic workspace-domain mappers used by stateless and stateful workspaces before
  evaluation, draft actions, and lifecycle handoff.
- Evidence:
  - `src/core/workspace/draft_state.py` now owns construction of editable workspace draft state
    from simulation requests and rehydration of simulation requests from workspace draft rows.
  - `src/api/services/workspace_service.py` now delegates draft-state projection to the workspace
    draft-state module while retaining stateful context resolution and persistence orchestration.
  - `tests/unit/advisory/api/test_workspace_draft_state.py` directly proves trade/cash-flow draft
    row preservation, governed draft-row identifiers, `Decimal` cash-flow amount normalization, and
    reconstruction of simulation requests from edited draft state.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\api\test_workspace_draft_state.py tests\unit\advisory\api\test_workspace_service.py tests\unit\advisory\api\test_api_workspace.py -q`.
- Consequence:
  - Workspace draft projection now has a reusable, directly tested module boundary and the API
    service no longer owns row-level mapping behavior.
- Follow-Up:
  - Continue extracting mutable draft action application only when error translation and
    persistence boundaries remain explicit.

## LA-REV-051

- Scope: Workspace draft action mutation
- Pattern: modularity problem / draft workflow hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace draft mutation for add, update, remove, and replace actions lived inside
  `src/api/services/workspace_service.py`. The API service should own session lookup, persistence,
  reevaluation, and error translation, while deterministic draft-row mutation should be reusable
  workspace-domain behavior.
- Evidence:
  - `src/core/workspace/draft_actions.py` now owns draft action application, trade/cash-flow row
    lookup, row removal, and bounded draft-action errors.
  - `src/api/services/workspace_service.py` now delegates draft mutation and translates
    `WorkspaceDraftActionError` into the existing service-level `WorkspaceNotFoundError`.
  - `tests/unit/advisory/api/test_workspace_draft_actions.py` directly proves add/update/remove
    behavior for trade and cash-flow draft rows and missing-row error behavior.
  - Existing workspace service tests now validate missing row behavior through the service action
    path rather than removed service-private lookup helpers.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\api\test_workspace_draft_actions.py tests\unit\advisory\api\test_workspace_service.py tests\unit\advisory\api\test_api_workspace.py -q`.
- Consequence:
  - Workspace draft mutation now has a directly tested domain module while service responsibilities
    are narrowed to orchestration, persistence, reevaluation, and API error vocabulary.
- Follow-Up:
  - Continue decomposing workspace handoff request assembly and evaluation context construction
    only where behavior can be pinned by focused tests.

## LA-REV-052

- Scope: Workspace handoff request assembly
- Pattern: modularity problem / lifecycle handoff hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace lifecycle handoff metadata construction, proposal create/version request
  assembly, simulate-request guards, and context-resolution evidence construction lived inside
  `src/api/services/workspace_service.py`. These rules are deterministic workspace-domain handoff
  behavior, while the service should retain orchestration, persistence, and proposal service calls.
- Evidence:
  - `src/core/workspace/handoff.py` now owns handoff metadata construction, proposal create/version
    request assembly, handoff context-resolution evidence construction, and bounded handoff errors.
  - `src/api/services/workspace_service.py` now delegates handoff request assembly and context
    evidence construction while retaining proposal service orchestration and error translation.
  - `tests/unit/advisory/api/test_workspace_handoff.py` directly proves title fallback/override,
    proposal create request assembly, context-resolution evidence shape, and missing resolved
    context behavior.
  - Existing workspace service tests now call the workspace handoff module for expected-current
    version request behavior instead of service-private helpers.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\api\test_workspace_handoff.py tests\unit\advisory\api\test_workspace_service.py tests\unit\advisory\api\test_api_workspace.py -q`.
- Consequence:
  - Workspace lifecycle handoff rules now have a reusable, directly tested domain boundary and the
    API service is narrower.
- Follow-Up:
  - Consider extracting workspace reevaluation context construction only if it can be made
    independently testable without duplicating proposal context resolution behavior.

## LA-REV-053

- Scope: Workspace evaluation summary construction
- Pattern: modularity problem / evaluation summary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace evaluation summary construction, blocking/review issue counts, and portfolio
  delta formatting lived inside `src/api/services/workspace_service.py`. These are deterministic
  workspace-domain presentation rules used after evaluation, while the service should own
  reevaluation orchestration and persistence.
- Evidence:
  - `src/core/workspace/evaluation.py` now owns blocking issue counts, review issue counts,
    portfolio delta formatting, and workspace evaluation summary assembly.
  - `src/api/services/workspace_service.py` now delegates summary construction after advisory
    proposal evaluation.
  - `tests/unit/advisory/api/test_workspace_evaluation.py` directly proves blocking/review issue
    counts, no-reconciliation portfolio delta formatting, and draft-row count propagation into the
    evaluation summary.
  - Existing workspace service tests now call the workspace evaluation module for portfolio delta
    formatting instead of service-private helpers.
  - Targeted proof passed with
    `python -m pytest tests\unit\advisory\api\test_workspace_evaluation.py tests\unit\advisory\api\test_workspace_service.py tests\unit\advisory\api\test_api_workspace.py -q`.
- Consequence:
  - Workspace evaluation summary behavior now has a reusable, directly tested module boundary and
    the workspace service no longer owns summary presentation rules.
- Follow-Up:
  - Keep reevaluation orchestration in the service unless context construction can be extracted
    without duplicating proposal context resolution semantics.

## LA-REV-054

- Scope: Workspace session store boundary
- Pattern: modularity problem / persistence-boundary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace session cache state and LRU eviction logic lived directly inside
  `src/api/services/workspace_service.py`. This kept mutable persistence concerns interleaved with
  workspace orchestration and made cache behavior harder to test without invoking workspace
  creation flows.
- Evidence:
  - `src/api/services/workspace_store.py` now owns the in-memory workspace session store, bounded
    LRU eviction, lookup error vocabulary, and reset behavior.
  - `src/api/services/workspace_service.py` keeps the existing public service functions while
    delegating save/get/reset operations to the store boundary.
  - `tests/unit/advisory/api/test_workspace_store.py` directly proves oldest-session eviction and
    reset semantics without depending on workspace orchestration.
- Consequence:
  - Workspace orchestration is narrower, the mutable session store has a focused replacement
    boundary for future durable persistence, and cache behavior is directly characterized.
- Follow-Up:
  - Keep the compatibility `MAX_WORKSPACE_SESSION_CACHE_SIZE` assignment path until callers can be
    migrated to explicit store configuration.

## LA-REV-055

- Scope: Workspace saved-version compare projection
- Pattern: modularity problem / deterministic projection hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Saved-version comparison response assembly and draft-delta calculation lived inside
  `src/api/services/workspace_service.py`. This comparison is deterministic workspace-domain
  projection logic, while the service should own lookup, error translation, and persistence
  boundaries.
- Evidence:
  - `src/core/workspace/compare.py` now owns workspace compare response assembly, draft-count
    deltas, option/reference-model change detection, evaluation-status change detection, and
    defensive response copying.
  - `src/api/services/workspace_service.py` now delegates comparison projection after locating the
    requested saved version.
  - `tests/unit/advisory/api/test_workspace_compare.py` directly proves trade/cash-flow deltas,
    options/reference-model change flags, evaluation-status change detection, and defensive
    baseline copying.
- Consequence:
  - Workspace compare behavior is reusable and directly tested outside the API service, reducing
    controller-service coupling around saved-version workflows.
- Follow-Up:
  - Consider moving workspace session creation projection into a similarly deterministic builder if
    it can be extracted without weakening stateful context-resolution behavior.

## LA-REV-056

- Scope: Workspace saved-version record construction
- Pattern: modularity problem / lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Saved-version record construction lived inside `src/api/services/workspace_service.py`,
  mixing immutable version DTO assembly, replay-evidence fallback, and defensive copy rules into the
  API service. The service should supply orchestration inputs such as generated IDs and timestamps,
  while workspace-domain code should own the saved-version snapshot shape.
- Evidence:
  - `src/core/workspace/versions.py` now owns `build_saved_workspace_version`, including version
    numbering, label/actor/timestamp assignment, draft/evaluation/proposal defensive copies, and
    replay-evidence fallback.
  - `src/api/services/workspace_service.py` now delegates saved-version record construction and
    retains lookup, generated identity, timestamp, metadata refresh, and persistence responsibilities.
  - `tests/unit/advisory/api/test_workspace_versions.py` directly proves supplied identity/time,
    version numbering, advisor label/actor propagation, and replay evidence copy semantics.
- Consequence:
  - Saved-version lineage behavior is reusable and directly tested in the workspace domain module,
    reducing service-layer coupling around audit snapshots.
- Follow-Up:
  - Keep generated identifier and clock ownership in the service boundary unless a repository-wide
    clock/ID provider abstraction is introduced.

## LA-REV-057

- Scope: Workspace saved-version resume application
- Pattern: modularity problem / lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Saved-version resume behavior lived inside `src/api/services/workspace_service.py`,
  including draft, evaluation, proposal-result, and replay-evidence copy semantics. This is
  deterministic workspace snapshot application logic; the API service should own lookup and
  persistence boundaries.
- Evidence:
  - `src/core/workspace/versions.py` now owns `apply_saved_workspace_version`, restoring the saved
    draft state, evaluation summary, proposal result, and replay evidence with defensive copies.
  - `src/api/services/workspace_service.py` now delegates resume snapshot application after locating
    the requested saved version.
  - `tests/unit/advisory/api/test_workspace_versions.py` directly proves saved-version resume
    restores the saved snapshot and does not alias mutable saved-version state.
- Consequence:
  - Saved-version resume lineage is reusable and testable outside the API service, reducing the
    service's responsibility to orchestration and persistence.
- Follow-Up:
  - Keep saved-version lookup error translation in the API service unless a broader service-error
    vocabulary boundary is introduced.

## LA-REV-058

- Scope: Workspace saved-version list projection
- Pattern: modularity problem / deterministic projection hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Saved-version list response assembly lived inside `src/api/services/workspace_service.py`,
  mixing defensive read-model copying into the API service. Saved-version list projection is
  deterministic workspace-domain behavior.
- Evidence:
  - `src/core/workspace/versions.py` now owns `build_saved_version_list_response`, including
    workspace identity propagation and defensive saved-version copies.
  - `src/api/services/workspace_service.py` now delegates saved-version list projection after
    session lookup.
  - `tests/unit/advisory/api/test_workspace_versions.py` directly proves list response identity and
    defensive copy behavior.
- Consequence:
  - Saved-version read models are consolidated in the workspace versions module and the API service
    is narrower.
- Follow-Up:
  - Keep persistence lookup and service-level error translation in `workspace_service.py`.

## LA-REV-059

- Scope: Workspace session construction
- Pattern: modularity problem / session lifecycle hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace session DTO construction lived directly inside
  `src/api/services/workspace_service.py`, mixing generated identity, timestamp, resolved context,
  draft state, and default lifecycle fields into the orchestration service. The service should keep
  context resolution, ID generation, clock, and persistence concerns, while workspace-domain code
  owns deterministic session assembly.
- Evidence:
  - `src/core/workspace/sessions.py` now owns `build_workspace_session`, including lifecycle state,
    input payload retention, draft/resolved context assignment, and initial saved-version/link
    defaults.
  - `src/api/services/workspace_service.py` now delegates session DTO construction after resolving
    context and draft state.
  - `tests/unit/advisory/api/test_workspace_sessions.py` directly proves supplied identity,
    timestamp, context, draft state, input payload, lifecycle state, and initial metadata defaults.
- Consequence:
  - Workspace session assembly is reusable and directly tested, and the API service is narrower
    without moving upstream stateful context-resolution behavior.
- Follow-Up:
  - Keep stateful context resolution in the service boundary unless a dedicated adapter orchestration
    module is introduced with explicit Lotus Core failure semantics.

## LA-REV-060

- Scope: Workspace stateless resolved-context construction
- Pattern: modularity problem / dead-code removal
- Status: Hardened
- Finding Class: modularity problem
- Summary: Stateless workspace resolved-context construction lived in
  `src/api/services/workspace_service.py`, and the service also retained an unused
  `_build_stateful_resolved_context` helper. The stateless context builder is deterministic
  workspace-domain behavior, while the unused stateful helper created misleading service surface.
- Evidence:
  - `src/core/workspace/sessions.py` now owns `build_stateless_workspace_resolved_context`,
    including portfolio identity, reference-model or fallback as-of selection, and snapshot IDs.
  - `src/api/services/workspace_service.py` now delegates stateless resolved-context construction
    and no longer carries the unused stateful resolved-context helper.
  - `tests/unit/advisory/api/test_workspace_sessions.py` directly proves fallback as-of and
    snapshot ID propagation for stateless workspace contexts.
- Consequence:
  - Workspace session context assembly is narrower and directly tested, while a stale private helper
    path has been removed from the service.
- Follow-Up:
  - Keep stateful context-resolution failure behavior in the service until a dedicated integration
    orchestration module can preserve exact Lotus Core error semantics.

## LA-REV-061

- Scope: Workspace lifecycle handoff completion
- Pattern: modularity problem / lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace lifecycle handoff completion lived inside `src/api/services/workspace_service.py`,
  including proposal ID/version lineage mutation, replay-continuity application, lifecycle-link
  assignment, and response construction. Proposal service orchestration belongs in the service, but
  deterministic handoff completion is workspace-domain behavior.
- Evidence:
  - `src/core/workspace/handoff.py` now owns `complete_workspace_lifecycle_handoff`, applying
    proposal lineage, replay continuity, lifecycle link metadata, and response construction.
  - `src/api/services/workspace_service.py` now delegates completion after proposal create/version
    orchestration succeeds.
  - `tests/unit/advisory/api/test_workspace_handoff.py` directly proves proposal link assignment,
    completed timestamp/actor propagation, response shape, and replay-continuity mutation.
- Consequence:
  - Lifecycle handoff state application is reusable and directly tested outside the API service,
    while the service remains responsible for proposal-service calls, persistence, and error
    translation.
- Follow-Up:
  - Keep proposal create/version orchestration in the service boundary unless a workflow-specific
    application service is introduced.

## LA-REV-062

- Scope: Workspace reevaluation context assembly
- Pattern: modularity problem / lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workspace reevaluation context assembly lived inside
  `src/api/services/workspace_service.py`, mixing proposal resolved-context projection, policy
  selector construction, context-resolution evidence, and canonical request hashing into the service.
  Actual proposal evaluation and persistence belong in the service, but deterministic context
  assembly is workspace-domain behavior.
- Evidence:
  - `src/core/workspace/reevaluation.py` now owns `build_workspace_evaluation_context`, including
    resolved request construction, stateful policy selectors, context-resolution evidence, and
    evaluation request hash construction.
  - `src/api/services/workspace_service.py` now delegates reevaluation context assembly and
    translates missing resolved context into the existing `WorkspaceEvaluationUnavailableError`
    vocabulary.
  - `tests/unit/advisory/api/test_workspace_reevaluation.py` directly proves stateful selector
    propagation, resolution source, resolved as-of, request-hash shape, and missing-context error
    behavior.
- Consequence:
  - Workspace reevaluation has a clearer domain boundary for lineage and policy-context assembly,
    while the service remains responsible for proposal evaluation, correlation, persistence, and
    error translation.
- Follow-Up:
  - Keep `_build_simulate_request_for_workspace` in the service while it owns live Lotus Core
    resolution and state mutation during stateful reevaluation.

## LA-REV-063

- Scope: Proposal lineage response projection
- Pattern: modularity problem / lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Proposal lineage response assembly lived inside
  `src/core/proposals/service.py`, mixing repository orchestration with immutable version read-model
  projection, latest-version selection, and missing-version detection. The service should fetch
  proposal/version records; deterministic lineage projection belongs in the proposal projection
  module.
- Evidence:
  - `src/core/proposals/projections.py` now owns `build_proposal_lineage_response`, including
    version-lineage item construction, latest persisted version metadata, and gap detection across
    the aggregate's current version range.
  - `src/core/proposals/service.py` now delegates lineage response assembly after fetching version
    records from the repository.
  - `tests/unit/advisory/engine/test_engine_proposal_projections.py` directly proves complete
    lineage projection and missing-version reporting.
- Consequence:
  - Proposal lineage semantics are reusable and directly tested outside the workflow service, while
    service logic remains focused on lookup, not DTO assembly.
- Follow-Up:
  - Continue extracting proposal lifecycle read-model assembly where behavior is deterministic and
    can be pinned without changing workflow command semantics.

## LA-REV-064

- Scope: Proposal lifecycle timeline and approval read-model projection
- Pattern: modularity problem / auditability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Workflow timeline and approval-history response assembly lived directly inside
  `src/core/proposals/service.py`, mixing repository lookup with lifecycle read-model projection and
  latest approval/event selection. These projections are deterministic and should be reusable
  outside the workflow service.
- Evidence:
  - `src/core/proposals/projections.py` now owns `build_workflow_timeline_response` and
    `build_approvals_response`.
  - `src/core/proposals/service.py` now fetches proposal events/approvals and delegates lifecycle
    read-model assembly to the projection module.
  - `tests/unit/advisory/engine/test_engine_proposal_projections.py` directly proves ordered
    timeline projection, latest-event posture, approval filtering, latest approval timestamp, and
    domain approval vocabulary preservation.
- Consequence:
  - Audit-facing lifecycle projections are centralized in the proposal projection module, reducing
    workflow-service DTO assembly while preserving command and persistence behavior.
- Follow-Up:
  - Continue with delivery summary/history projection only if it remains deterministic after
    preserving the existing execution/reporting summary semantics.

## LA-REV-065

- Scope: Proposal delivery summary and history projection
- Pattern: modularity problem / delivery observability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Delivery summary and delivery-history response assembly lived in
  `src/core/proposals/service.py`, while the deterministic delivery event selection and
  execution/reporting posture extraction already lived in `src/core/proposals/delivery_summary.py`.
  This split forced the workflow service to know delivery DTO assembly details.
- Evidence:
  - `src/core/proposals/delivery_summary.py` now owns `build_delivery_summary_response` and
    `build_delivery_history_response`, keeping delivery event filtering, execution/reporting
    posture extraction, response DTO validation, and explanation metadata in one module.
  - `src/core/proposals/service.py` now delegates delivery summary/history projection after proposal
    and event lookup.
  - `tests/unit/advisory/engine/test_engine_proposal_delivery_summary.py` directly proves response
    projection for execution/reporting posture and delivery-only history filtering.
- Consequence:
  - Delivery observability read models are centralized and directly tested, while the workflow
    service remains focused on lookup and command orchestration.
- Follow-Up:
  - Continue decomposing proposal service command paths only where the extraction can preserve
    idempotency, expected-state, and workflow transition semantics exactly.

## LA-REV-066

- Scope: Proposal idempotency lookup projection
- Pattern: modularity problem / auditability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Proposal idempotency lookup response assembly lived directly in
  `src/core/proposals/service.py`, leaving audit timestamp formatting and response DTO construction
  in the workflow service even after other proposal read-model projections were centralized.
- Evidence:
  - `src/core/proposals/projections.py` now owns `to_idempotency_lookup_response`.
  - `src/core/proposals/service.py` now delegates idempotency lookup response assembly after
    repository lookup and not-found translation.
  - `tests/unit/advisory/engine/test_engine_proposal_projections.py` directly proves idempotency
    key, request hash, proposal/version identity, and UTC audit timestamp projection.
- Consequence:
  - Idempotency lookup formatting is reusable and covered with the other proposal projection
    helpers, and service code retains only repository lookup plus error translation.
- Follow-Up:
  - Keep idempotency conflict detection in command paths and the dedicated idempotency helper module;
    only response projection belongs here.

## LA-REV-067

- Scope: Proposal execution handoff event and response construction
- Pattern: modularity problem / auditability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Execution handoff replay response assembly, handoff requested-event construction, and
  accepted response projection lived directly in `src/core/proposals/service.py`, mixing deterministic
  audit payload construction with repository lookup, idempotency replay detection, expected-state
  validation, and persistence.
- Evidence:
  - `src/core/proposals/execution_handoff.py` now owns
    `build_execution_handoff_replay_response`, `build_execution_handoff_requested_event`, and
    `build_execution_handoff_response`.
  - `src/core/proposals/service.py` now delegates deterministic handoff event/response assembly
    while retaining repository orchestration, replay lookup, expected-state validation, generated
    execution-request identity selection, and transition persistence.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py` directly proves
    execution-request identity, provider, correlation, external request, notes, idempotency audit
    metadata, related-version defaulting, replay identity, and accepted response projection.
- Consequence:
  - Execution handoff audit payload construction is reusable and directly tested, and the workflow
    service is narrower without weakening idempotency or state-transition semantics.
- Follow-Up:
  - Consider extracting execution update event construction separately only if it can preserve
    handoff identity matching, terminal-state rejection, timestamp ordering, and replay semantics.

## LA-REV-068

- Scope: Proposal execution update event construction
- Pattern: modularity problem / execution reconciliation hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Execution update workflow-event construction lived directly in
  `src/core/proposals/service.py`, mixing deterministic reconciliation payload assembly with
  handoff identity matching, terminal-state rejection, timestamp ordering, idempotency replay
  detection, and persistence.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns `build_execution_update_event`.
  - `src/core/proposals/service.py` now delegates deterministic execution update event construction
    after preserving the existing request-id/provider match, replay lookup, terminal-state guard,
    and occurred-at ordering checks.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves update
    identity, execution request/provider, external execution id, details payload, idempotency audit
    metadata, explicit related-version handling, fallback to handoff version, and null omission.
- Consequence:
  - Execution reconciliation audit payload construction is reusable and directly tested, while the
    workflow service remains responsible for stateful validation and persistence.
- Follow-Up:
  - Keep execution status derivation in `execution_status.py`; only consider further extraction if
    command validation can remain visibly separated from event construction.

## LA-REV-069

- Scope: Proposal state-transition event and response construction
- Pattern: modularity problem / lifecycle auditability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Generic state-transition event construction and transition response projection lived
  directly in `src/core/proposals/service.py`, mixing deterministic lifecycle audit payload
  assembly with proposal lookup, idempotency replay detection, expected-state validation,
  transition-rule resolution, and persistence.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns `build_state_transition_event` and
    `build_state_transition_response`.
  - `src/core/proposals/service.py` now delegates deterministic transition event/response assembly
    while preserving proposal lookup, replay detection, expected-state validation,
    transition-rule resolution, state mutation, and repository persistence.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves
    transition reason preservation, idempotency audit metadata, actor/version/state propagation,
    latest-event projection, and no-approval response posture.
- Consequence:
  - Generic lifecycle transition audit construction is reusable and directly tested, reducing
    workflow-service DTO/event assembly without changing command validation behavior.
- Follow-Up:
  - Extract approval event/record construction separately only if replay referent handling and
    approval-transition rule behavior remain visibly service-owned.

## LA-REV-070

- Scope: Proposal approval record, event, and response construction
- Pattern: modularity problem / approval auditability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Approval record construction, approval workflow-event construction, and approval
  transition response projection lived directly in `src/core/proposals/service.py`, mixing
  deterministic approval audit payload assembly with approval replay lookup, replay referent
  validation, expected-state validation, approval-transition rule resolution, and persistence.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns `build_approval_record`,
    `build_approval_transition_event`, and `build_approval_transition_response`.
  - `src/core/proposals/service.py` now delegates deterministic approval record/event/response
    assembly while preserving approval replay lookup, replay referent checks, expected-state
    validation, approval-transition rule resolution, state mutation, and repository persistence.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves approval
    details preservation, idempotency audit metadata, actor/version/state propagation, approval
    event payload construction, and response projection with approval details.
- Consequence:
  - Approval audit payload construction is reusable and directly tested, and the workflow service
    is narrower without weakening replay, state, or approval rule semantics.
- Follow-Up:
  - Continue command-path decomposition only where deterministic construction can be separated from
    stateful validation and persistence with direct tests.

## LA-REV-071

- Scope: Proposal evidence-bundle enrichment
- Pattern: duplication / lineage hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Proposal create and proposal-version create both assembled evidence bundles inline in
  `src/core/proposals/service.py`, duplicating context-resolution override handling, risk-lens
  extraction, and replay-lineage attachment. This lineage behavior should stay consistent across
  immutable advisory versions.
- Evidence:
  - `src/core/proposals/evidence.py` now owns `build_proposal_evidence_bundle`.
  - `src/core/proposals/service.py` now delegates evidence-bundle enrichment from both create and
    create-version flows after artifact construction and proposal simulation.
  - `tests/unit/advisory/engine/test_engine_proposal_evidence.py` directly proves override versus
    default context-resolution behavior, risk-lens extraction, replay-lineage attachment, and
    omission of absent replay lineage.
- Consequence:
  - Version lineage enrichment is centralized and directly tested, reducing duplicate evidence
    assembly in the workflow service without moving simulation, artifact creation, or persistence.
- Follow-Up:
  - Keep proposal simulation and artifact creation in the service until a larger application command
    boundary is introduced with full create/version characterization coverage.

## LA-REV-072

- Scope: Proposal create and new-version lifecycle event construction
- Pattern: duplication / lifecycle auditability hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Proposal `CREATED` and `NEW_VERSION_CREATED` workflow events were constructed directly
  in `src/core/proposals/service.py`, leaving create/version command orchestration responsible for
  deterministic lifecycle audit event assembly while other lifecycle event builders had already been
  extracted.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns `build_proposal_created_event` and
    `build_new_version_created_event`.
  - `src/core/proposals/service.py` now delegates create and create-version lifecycle event
    construction while retaining proposal aggregate creation, version creation, idempotency
    persistence, state mutation, and repository orchestration.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves draft
    lifecycle state, prior-state preservation for new versions, correlation metadata, and related
    version linkage.
- Consequence:
  - Lifecycle event construction for create, new version, transition, approval, execution handoff,
    and execution update now follows dedicated domain helpers with direct tests.
- Follow-Up:
  - Consider a larger create/version command boundary only with full characterization of
    idempotency, proposal aggregate defaults, version persistence, and replay lineage.

## LA-REV-073

- Scope: Proposal aggregate and create-idempotency record construction
- Pattern: modularity problem / replay identity hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Initial proposal aggregate construction and proposal-create idempotency record
  construction lived directly in `src/core/proposals/service.py`, mixing default lifecycle state,
  metadata propagation, workspace handoff identity, and replay identity construction into the
  workflow service create path.
- Evidence:
  - `src/core/proposals/records.py` now owns `build_proposal_record` and
    `build_proposal_idempotency_record`.
  - `src/core/proposals/service.py` now delegates deterministic proposal aggregate and
    create-idempotency record construction while preserving context resolution, idempotency conflict
    handling, simulation, artifact/version creation, event append, and persistence orchestration.
  - `tests/unit/advisory/engine/test_engine_proposal_records.py` directly proves initial `DRAFT`
    lifecycle state, current-version initialization, `last_event_at` alignment, metadata/workspace
    propagation, and replay identity preservation.
- Consequence:
  - Proposal create defaults and idempotency replay identity are centralized and directly tested,
    reducing create-path DTO construction inside the workflow service.
- Follow-Up:
  - Keep create command orchestration in the service until a larger command handler can be introduced
    without obscuring idempotency conflict behavior and persistence ordering.

## LA-REV-074

- Scope: Proposal async operation record construction
- Pattern: modularity problem / async replay lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Async create-proposal and create-version submission paths constructed persisted
  `ProposalAsyncOperationRecord` instances directly in `src/core/proposals/service.py`, mixing
  operation payload shape, submission hash lineage, retry defaults, and initial status state into
  the workflow service.
- Evidence:
  - `src/core/proposals/async_operations.py` now owns
    `build_create_proposal_async_operation` and `build_create_version_async_operation`.
  - `src/core/proposals/service.py` now delegates deterministic async operation record construction
    while retaining correlation/idempotency lookup, conflict detection, repository persistence, and
    accepted-response projection.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` directly proves persisted
    create/version operation type, pending status, correlation and idempotency identity, proposal
    scoping, submission hash lineage, retry counters, and clean initial execution state.
- Consequence:
  - Async submission persistence defaults and replay metadata are centralized and directly tested,
    reducing workflow-service DTO assembly and making retry/recovery behavior easier to reason
    about.
- Follow-Up:
  - Keep async execution orchestration in the service until repository lease, retry, and recovery
    ordering can be extracted with stronger integration characterization.

## LA-REV-075

- Scope: Async operation replay result version extraction
- Pattern: modularity problem / replay evidence hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Async operation replay evidence selection parsed `operation.result_json["version"]`
  directly inside `src/core/proposals/service.py`, mixing payload-shape interpretation into the
  workflow-service read path that should otherwise coordinate repository lookups and replay
  response assembly.
- Evidence:
  - `src/core/proposals/async_operations.py` now owns `extract_async_result_version_no`.
  - `src/core/proposals/service.py` delegates successful async result-version extraction before
    falling back to the current proposal version when no valid version number is present.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` directly proves valid
    version extraction and rejection of missing, non-object, and non-integer result payloads.
- Consequence:
  - Replay-evidence version selection now has an explicit, tested parser for async operation result
    payloads, reducing hidden result-shape coupling in the workflow service.
- Follow-Up:
  - Keep repository-backed replay material loading in the service until a larger replay-query
    object can be introduced with current-version fallback characterization.

## LA-REV-076

- Scope: New proposal-version lifecycle state mutation
- Pattern: modularity problem / lifecycle state hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: The create-version command path directly mutated proposal lifecycle state in
  `src/core/proposals/service.py`, coupling version-number advancement, `DRAFT` reset semantics,
  and `last_event_at` update behavior to workflow orchestration.
- Evidence:
  - `src/core/proposals/versions.py` now owns `apply_new_version_lifecycle_state`.
  - `src/core/proposals/service.py` delegates new-version aggregate state mutation while retaining
    proposal lookup, terminal-state and expected-version checks, context resolution, simulation,
    event construction, and persistence ordering.
  - `tests/unit/advisory/engine/test_engine_proposal_versions.py` directly proves current-version
    advancement, lifecycle reset to `DRAFT`, and last-event timestamp update.
- Consequence:
  - New-version lifecycle semantics are centralized beside version-record construction and tested
    independently from service orchestration.
- Follow-Up:
  - Keep create-version eligibility checks in the service until a dedicated command policy can wrap
    proposal lookup errors, expected-version conflicts, and portfolio-context validation without
    weakening current API error behavior.

## LA-REV-077

- Scope: Stale async operation time helper removal
- Pattern: dead code
- Status: Hardened
- Finding Class: stale code
- Summary: `src/core/proposals/async_operations.py` exposed a module-level `utc_now` helper that was
  no longer called by production code or tests after async state transitions were changed to accept
  explicit timestamps from the workflow service.
- Evidence:
  - Removed the unused `utc_now` helper and its `timezone` import from
    `src/core/proposals/async_operations.py`.
  - Repository search confirms remaining proposal clock usage is the service-local `_utc_now`
    orchestration helper.
- Consequence:
  - Async operation state helpers keep deterministic, caller-supplied timestamps without carrying a
    second unused clock abstraction.
- Follow-Up:
  - Continue removing stale service-private wrappers and module-level helpers as proposal workflow
    orchestration is decomposed.

## LA-REV-078

- Scope: Async create-submission outcome statistics
- Pattern: modularity problem / operational diagnostics hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService` owned a raw dictionary and lock for async create-submission
  accepted-new, accepted-replayed, and conflict counters, mixing operational diagnostic bookkeeping
  into workflow orchestration.
- Evidence:
  - `src/core/proposals/async_operations.py` now owns `AsyncCreateSubmissionStats` and
    `AsyncCreateSubmissionStatsTracker`.
  - `src/core/proposals/service.py` records accepted and conflict outcomes through the tracker while
    retaining idempotency lookup, hash conflict detection, repository persistence, and accepted
    response projection.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` directly proves tracker
    snapshots for accepted-new, accepted-replayed, and conflict outcomes; existing workflow-service
    tests continue to prove replay, conflict, and concurrent submission behavior.
- Consequence:
  - Async submission diagnostics now have a typed, thread-safe domain helper instead of service-local
    dictionary mutation.
- Follow-Up:
  - Promote these counters into the runtime metrics layer only when a production metrics contract is
    introduced for async proposal submission observability.

## LA-REV-079

- Scope: Idempotency replay create-response referent projection
- Pattern: modularity problem / replay identity hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: The create-proposal idempotency replay path in `ProposalWorkflowService` directly
  combined proposal, version, and workflow-event referents into a create response, coupling
  missing-referent detection and response assembly to repository orchestration.
- Evidence:
  - `src/core/proposals/projections.py` now owns `build_create_response_from_referents`.
  - `src/core/proposals/service.py` keeps repository reads and maps a missing referent response to
    `PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND`.
  - `tests/unit/advisory/engine/test_engine_proposal_projections.py` directly proves successful
    response assembly from complete referents and `None` results for missing proposal, version, or
    event referents.
- Consequence:
  - Create-proposal replay response assembly is centralized with the other proposal response
    projections, making the service read path smaller and preserving existing API error behavior.
- Follow-Up:
  - Keep repository read orchestration in the service until replay query objects can cover
    idempotency, async replay, and version replay consistently.

## LA-REV-080

- Scope: Create-version eligibility policy
- Pattern: modularity problem / lifecycle correctness hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.create_version` directly owned terminal-state rejection,
  expected-current-version conflict detection, and portfolio-context mismatch validation, mixing
  create-version policy with context resolution, simulation, event construction, and persistence.
- Evidence:
  - `src/core/proposals/versions.py` now owns `validate_create_version_state` and
    `validate_create_version_portfolio_context` plus typed version eligibility exceptions.
  - `src/core/proposals/service.py` delegates create-version eligibility policy while preserving the
    existing API-facing exception classes and messages.
  - `tests/unit/advisory/engine/test_engine_proposal_versions.py` directly proves terminal-state
    rejection, expected-version conflict rejection, matching portfolio acceptance, configured
    portfolio-change allowance, and portfolio-context mismatch rejection.
- Consequence:
  - Create-version eligibility policy is centralized beside version record and lifecycle helpers,
    reducing inline business policy in the workflow service.
- Follow-Up:
  - Keep proposal lookup and API error mapping in the service until a broader command handler can
    preserve not-found, validation, conflict, and persistence ordering semantics.

## LA-REV-081

- Scope: Lifecycle transition aggregate state mutation
- Pattern: modularity problem / lifecycle state hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: State-transition and approval command paths directly mutated `proposal.current_state`
  and `proposal.last_event_at` inside `ProposalWorkflowService`, coupling deterministic aggregate
  state mutation to workflow orchestration after event construction.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns `apply_lifecycle_transition_state`.
  - `src/core/proposals/service.py` delegates aggregate mutation for generic state transitions and
    approval transitions while retaining lookup, replay detection, expected-state validation,
    rule resolution, event construction, and persistence ordering.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves lifecycle
    state and last-event timestamp mutation from the generated workflow event.
- Consequence:
  - Lifecycle aggregate mutation is centralized beside event construction and response projection,
    reducing repeated state/timestamp assignment in the workflow service.
- Follow-Up:
  - Consider a broader lifecycle command boundary only after execution handoff, execution update,
    reporting, transition, and approval mutation semantics are all characterized together.

## LA-REV-082

- Scope: Execution update aggregate state mutation
- Pattern: modularity problem / execution lifecycle hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_execution_update` directly mutated proposal lifecycle
  state and `last_event_at` after execution update event construction, coupling execution update
  aggregate mutation to service orchestration.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns `apply_execution_update_state`.
  - `src/core/proposals/service.py` delegates execution update aggregate mutation while retaining
    proposal lookup, handoff identity matching, replay detection, terminal-state rejection,
    timestamp ordering, event construction, and persistence.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves execution
    update state and last-event timestamp mutation from the generated workflow event.
- Consequence:
  - Execution update lifecycle mutation is centralized beside execution update event construction,
    reducing repeated state/timestamp mutation in the workflow service.
- Follow-Up:
  - Keep handoff lookup, execution request/provider matching, and timestamp ordering in the service
    until execution update policy is extracted with full replay and handoff identity
    characterization.

## LA-REV-083

- Scope: Report-request aggregate timestamp mutation
- Pattern: modularity problem / reporting lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_report_request` directly applied report-request
  `last_event_at` mutation after building the reporting workflow event, leaving the report lineage
  timestamp policy inside service orchestration.
- Evidence:
  - `src/core/proposals/reporting.py` now owns `apply_report_request_state`.
  - `src/core/proposals/service.py` delegates report-request aggregate timestamp mutation while
    retaining proposal lookup, event construction, persistence, and API-facing error behavior.
  - `tests/unit/advisory/engine/test_engine_proposal_reporting.py` directly proves timestamp
    advancement for newer report events and preservation when the proposal already has a newer
    lifecycle timestamp.
- Consequence:
  - Report-request timestamp policy is centralized beside reporting event construction, reducing
    inline aggregate mutation in the workflow service.
- Follow-Up:
  - Keep report request orchestration in the service until reporting provider calls, lifecycle
    timeline projection, and report delivery-history semantics can be characterized together.

## LA-REV-084

- Scope: Execution handoff aggregate timestamp mutation
- Pattern: modularity problem / execution handoff hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.request_execution_handoff` directly assigned
  `proposal.last_event_at` after building the execution handoff workflow event, coupling handoff
  aggregate mutation to service orchestration.
- Evidence:
  - `src/core/proposals/execution_handoff.py` now owns `apply_execution_handoff_state`.
  - `src/core/proposals/service.py` delegates handoff aggregate timestamp mutation while retaining
    proposal lookup, replay detection, expected-state validation, execution-ready enforcement,
    event construction, persistence, and response projection.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py` directly proves handoff
    last-event timestamp mutation from the generated workflow event.
- Consequence:
  - Execution handoff timestamp policy is centralized beside handoff event construction and
    response projection, removing another direct aggregate mutation from the workflow service.
- Follow-Up:
  - Keep execution-ready validation and replay lookup in the service until a broader execution
    handoff command policy can preserve current API error ordering and idempotency behavior.

## LA-REV-085

- Scope: Execution handoff readiness validation
- Pattern: modularity problem / execution handoff hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.request_execution_handoff` directly enforced the
  `EXECUTION_READY` precondition for handoff requests, leaving a domain execution-readiness rule
  inside service orchestration.
- Evidence:
  - `src/core/proposals/execution_handoff.py` now owns `validate_execution_handoff_ready` and the
    typed `ProposalExecutionHandoffStateError`.
  - `src/core/proposals/service.py` delegates the readiness rule and maps the domain exception back
    to the existing `ProposalStateConflictError` message.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py` directly proves accepted
    `EXECUTION_READY` state and rejected non-ready state behavior.
- Consequence:
  - Execution handoff readiness vocabulary is centralized beside handoff event construction,
    response projection, and aggregate timestamp mutation.
- Follow-Up:
  - Keep expected-state validation and idempotency replay orchestration in the service until a
    broader command boundary can preserve replay-before-validation ordering.

## LA-REV-086

- Scope: Execution update handoff identity validation
- Pattern: modularity problem / execution reconciliation hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_execution_update` directly compared execution update
  request/provider identity against the latest execution handoff event, leaving reconciliation
  vocabulary and mismatch messages inside service orchestration.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns
    `validate_execution_update_handoff_identity` and typed mismatch errors.
  - `src/core/proposals/service.py` delegates request/provider identity validation and maps domain
    errors back to the existing `ProposalStateConflictError` details.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves matching
    identity acceptance plus request ID and provider mismatch rejection.
- Consequence:
  - Execution update reconciliation identity rules are centralized beside update event construction
    and aggregate state mutation.
- Follow-Up:
  - Keep handoff lookup, replay-before-validation ordering, terminal-state rejection, and timestamp
    ordering in the service until execution update command orchestration can be extracted as a
    single policy boundary.

## LA-REV-087

- Scope: Execution update terminal-state validation
- Pattern: modularity problem / execution lifecycle hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_execution_update` directly rejected execution updates
  for terminal proposal states, leaving terminal lifecycle policy inside service orchestration.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns `validate_execution_update_state` and
    `ProposalExecutionUpdateTerminalStateError`.
  - `src/core/proposals/service.py` delegates terminal-state validation and maps the domain error
    back to the existing `ProposalStateConflictError` detail.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves
    non-terminal acceptance and terminal-state rejection.
- Consequence:
  - Execution update lifecycle eligibility is centralized beside update identity validation, event
    construction, and aggregate state mutation.
- Follow-Up:
  - Keep replay-before-validation ordering and handoff timestamp ordering in the service until the
    complete execution update command boundary can be extracted without changing API behavior.

## LA-REV-088

- Scope: Execution update handoff timestamp ordering
- Pattern: modularity problem / execution reconciliation hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_execution_update` directly rejected update events that
  occurred before the latest execution handoff event, keeping event-time reconciliation policy
  inside service orchestration.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns
    `validate_execution_update_occurred_after_handoff` and
    `ProposalExecutionUpdateTimestampError`.
  - `src/core/proposals/service.py` delegates update-versus-handoff timestamp ordering and maps the
    domain error back to the existing `ProposalValidationError` detail.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves equal and
    later timestamps are accepted while earlier timestamps are rejected.
- Consequence:
  - Execution update reconciliation rules now centralize identity, terminal-state, event-time,
    event construction, and aggregate state mutation in the execution update module.
- Follow-Up:
  - Keep replay-before-validation ordering and event timestamp resolution in the service until the
    complete execution update command boundary can be extracted without changing API behavior.

## LA-REV-089

- Scope: Execution update event-time resolution
- Pattern: modularity problem / execution reconciliation hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_execution_update` directly selected between a
  payload-supplied execution update timestamp and the service clock fallback, leaving event-time
  resolution policy inside orchestration.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns `resolve_execution_update_occurred_at`.
  - `src/core/proposals/service.py` provides the service clock fallback while delegating
    payload-versus-default timestamp selection.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves payload
    timestamp precedence and default timestamp fallback.
- Consequence:
  - Execution update event-time policy is centralized with identity, terminal-state, timestamp
    ordering, event construction, and aggregate state mutation.
- Follow-Up:
  - Keep repository reads, idempotency replay ordering, and persistence orchestration in the service
    until the complete execution update command boundary can be extracted without changing API
    behavior.

## LA-REV-090

- Scope: Execution update idempotency-key construction
- Pattern: duplication / replay-lineage hardening
- Status: Hardened
- Finding Class: duplication
- Summary: The execution update idempotency key format was assembled separately in replay lookup and
  workflow-event lineage payload construction, creating a small but important drift risk for update
  replay identity.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns
    `build_execution_update_idempotency_key`.
  - `src/core/proposals/service.py` uses the shared helper for replay lookup.
  - `src/core/proposals/execution_update.py` uses the same helper when building update event
    lineage payloads.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves the
    governed execution update idempotency-key format.
- Consequence:
  - Execution update replay lookup identity and persisted event lineage identity now share one
    construction path.
- Follow-Up:
  - Keep replay lookup ordering in the service until the complete execution update command boundary
    can be extracted without changing API behavior.

## LA-REV-091

- Scope: Execution update canonical request hashing
- Pattern: modularity problem / replay-lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_execution_update` directly built the canonical request
  hash used for replay lookup and workflow-event lineage, leaving execution update replay hashing
  outside the execution update module.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns `build_execution_update_request_hash`.
  - `src/core/proposals/service.py` delegates execution update request hashing before replay lookup
    and event construction.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` directly proves canonical
    ordering stability and sensitivity to changed execution details.
- Consequence:
  - Execution update replay identity now centralizes idempotency-key construction and canonical
    request hashing beside event lineage construction.
- Follow-Up:
  - Keep replay lookup ordering and repository orchestration in the service until the complete
    execution update command boundary can be extracted without changing API behavior.

## LA-REV-092

- Scope: State-transition canonical request hashing
- Pattern: modularity problem / replay-lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.transition_state` directly built the canonical request hash
  used for transition replay lookup and workflow-event lineage, while transition event construction
  already lived in `src/core/proposals/lifecycle_events.py`.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns `build_state_transition_request_hash`.
  - `src/core/proposals/service.py` delegates generic state-transition request hashing before
    replay lookup and event construction.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves canonical
    ordering stability and sensitivity to changed transition reason details.
- Consequence:
  - Generic transition replay hashing is centralized beside transition event construction and
    response projection.
- Follow-Up:
  - Keep replay lookup ordering, expected-state validation, transition-rule resolution, and
    persistence orchestration in the service until a broader lifecycle command boundary can be
    extracted without changing API behavior.

## LA-REV-093

- Scope: Approval canonical request hashing
- Pattern: modularity problem / replay-lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_approval` directly built the canonical request hash used
  for approval replay lookup, approval record lineage, and approval workflow-event lineage, while
  approval record and event construction already lived in `src/core/proposals/lifecycle_events.py`.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns `build_approval_request_hash`.
  - `src/core/proposals/service.py` delegates approval request hashing before replay lookup,
    approval record construction, and approval event construction.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves canonical
    ordering stability and sensitivity to changed approval details.
- Consequence:
  - Approval replay hashing is centralized beside approval record and approval event construction,
    reducing service-owned lineage mechanics.
- Follow-Up:
  - Keep replay lookup ordering, expected-state validation, approval-transition rule resolution,
    and persistence orchestration in the service until a broader approval command boundary can be
    extracted without changing API behavior.

## LA-REV-094

- Scope: Approval replay response referent projection
- Pattern: modularity problem / replay-lineage hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_approval` directly assembled approval replay responses
  and handled missing replay-event referents after repository lookup, coupling replay projection to
  service orchestration.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns
    `build_approval_replay_response_from_referents`.
  - `src/core/proposals/service.py` delegates replay response assembly and preserves the existing
    `PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND` error when the replay event is missing.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves replay
    response projection from complete referents and `None` for a missing replay event.
- Consequence:
  - Approval replay projection now lives beside approval response projection, reducing service-owned
    DTO assembly for replay paths.
- Follow-Up:
  - Keep replay lookup ordering and repository access in the service until a broader approval
    command boundary can be extracted without changing API behavior.

## LA-REV-095

- Scope: State-transition replay response projection
- Pattern: modularity problem / idempotency replay hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.transition_state` directly assembled idempotent replay
  responses from replayed workflow events, leaving replay projection logic in service
  orchestration instead of the lifecycle response module.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now owns
    `build_state_transition_replay_response`.
  - `src/core/proposals/service.py` delegates transition replay response projection while keeping
    replay lookup and conflict handling unchanged.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` directly proves replay
    responses derive current state and lineage from the replayed event.
- Consequence:
  - State-transition replay projection now has a named domain helper beside normal transition
    response projection, reducing service-owned DTO assembly.
- Follow-Up:
  - Keep replay-event retrieval in the service until a broader lifecycle command boundary can be
    extracted without changing repository access behavior.

## LA-REV-096

- Scope: Execution-update replay event reuse
- Pattern: query/performance risk / idempotency replay hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: `ProposalWorkflowService.record_execution_update` loaded workflow events for handoff
  validation, then reused the generic replay helper and status accessor, causing extra event reads
  on idempotent execution-update replay.
- Evidence:
  - `src/core/proposals/execution_update.py` now owns
    `find_replayed_execution_update_event`, which scopes replay lookup to execution-update
    identity while preserving request-hash conflict behavior.
  - `src/core/proposals/service.py` uses the already-loaded workflow events for replay detection
    and status projection.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` proves execution-update
    replay lookup and hash-conflict behavior.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` proves an execution
    update replay projects status with one event-list read.
- Consequence:
  - Execution-update replay now avoids duplicate repository event reads and keeps update-specific
    idempotency vocabulary in the execution-update module.
- Follow-Up:
  - Keep non-replay execution-update persistence in the service until a broader execution command
    boundary can be extracted without changing lifecycle behavior.

## LA-REV-097

- Scope: Execution-handoff request hash construction
- Pattern: modularity problem / idempotency replay hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.request_execution_handoff` built the canonical replay request
  hash inline, leaving handoff idempotency identity in service orchestration instead of the
  execution-handoff domain module.
- Evidence:
  - `src/core/proposals/execution_handoff.py` now owns
    `build_execution_handoff_request_hash`.
  - `src/core/proposals/service.py` delegates execution-handoff request hashing before replay
    lookup and event construction.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py` proves handoff request
    hashing is canonical and payload-sensitive.
- Consequence:
  - Execution-handoff replay hash construction now sits beside handoff event and replay response
    construction, matching the lifecycle, approval, and execution-update module boundaries.
- Follow-Up:
  - Keep handoff replay lookup and persistence orchestration in the service until a broader
    execution handoff command boundary can be extracted without changing behavior.

## LA-REV-098

- Scope: Proposal create/version request hash construction
- Pattern: modularity problem / idempotency replay hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService` built proposal create and version canonical request hashes
  inline after advisory-context resolution, coupling request identity to service orchestration even
  though canonical payload construction already lived in the context module.
- Evidence:
  - `src/core/proposals/context.py` now owns `build_create_request_hash` and
    `build_version_request_hash`.
  - `src/core/proposals/service.py` delegates create/version request hash construction after
    resolving advisory context.
  - `tests/unit/advisory/engine/test_engine_proposal_context.py` proves legacy/stateless create and
    version contracts normalize to the same canonical hash, while version concurrency input remains
    hash-sensitive.
- Consequence:
  - Create and version idempotency identity now sits beside resolved advisory-context
    canonicalization, reducing service-owned hash assembly.
- Follow-Up:
  - Keep context resolution and idempotency repository checks in the service until a broader create
    command boundary can be extracted without changing behavior.

## LA-REV-099

- Scope: Advisory proposal simulation execution boundary
- Pattern: modularity problem / service-boundary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService` directly resolved correlation IDs and invoked advisory
  proposal orchestration for create and version flows, coupling simulation execution mechanics to
  lifecycle command orchestration.
- Evidence:
  - `src/core/proposals/simulation_execution.py` now owns
    `run_advisory_proposal_simulation`.
  - `src/core/proposals/service.py` delegates simulation execution and no longer imports advisory
    orchestration directly.
  - `tests/unit/advisory/engine/test_engine_proposal_simulation_execution.py` proves missing
    correlation IDs are resolved and supplied correlation IDs are preserved when invoking advisory
    orchestration.
- Consequence:
  - Proposal create/version command handling now depends on a proposal-domain simulation execution
    boundary instead of the lower-level advisory orchestration function.
- Follow-Up:
  - Keep simulation flag validation and artifact/evidence assembly in the service until a broader
    create/version command handler can own the complete proposal-build transaction.

## LA-REV-100

- Scope: Stale simulation execution wrapper removal
- Pattern: stale code / modularity hardening
- Status: Hardened
- Finding Class: stale code
- Summary: After extracting `run_advisory_proposal_simulation`, `ProposalWorkflowService` retained
  a private `_run_simulation` wrapper that only forwarded arguments to the new proposal-domain
  boundary.
- Evidence:
  - `src/core/proposals/service.py` now calls `run_advisory_proposal_simulation` directly from
    create and version flows.
  - The stale `_run_simulation` method and unused `ProposalResult` import were removed.
  - Existing workflow service tests and simulation execution tests cover the direct call path.
- Consequence:
  - Proposal create/version orchestration has one fewer service-private indirection and a clearer
    dependency on the proposal-domain simulation execution boundary.
- Follow-Up:
  - Continue removing thin service-private wrappers when extracted domain modules fully own the
    behavior.

## LA-REV-101

- Scope: Proposal version artifact/evidence materialization
- Pattern: duplication / service-boundary hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Proposal create and version flows duplicated artifact construction and evidence-bundle
  enrichment in `ProposalWorkflowService`, coupling proposal materialization mechanics to command
  orchestration.
- Evidence:
  - `src/core/proposals/materialization.py` now owns
    `build_proposal_version_materialization`.
  - `src/core/proposals/service.py` delegates artifact and evidence-bundle assembly for both
    create and version flows.
  - `tests/unit/advisory/engine/test_engine_proposal_materialization.py` proves artifact creation,
    evidence enrichment inputs, context override, and replay lineage are passed through.
- Consequence:
  - Create and version flows share one materialization path before immutable version-record
    construction, reducing duplicated evidence assembly logic in the workflow service.
- Follow-Up:
  - Keep version-record persistence and transaction ordering in the service until a broader
    create/version command handler owns the full proposal-build transaction.

## LA-REV-102

- Scope: Proposal lineage version-list query shape
- Pattern: query/performance risk / read-model hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: `ProposalWorkflowService.get_lineage` loaded proposal versions by calling
  `get_version` for every version number up to `current_version_no`, creating an N+1 read shape for
  lineage reads.
- Evidence:
  - `src/core/proposals/repository.py` now exposes `list_versions`.
  - `src/infrastructure/proposals/in_memory.py` and
    `src/infrastructure/proposals/postgres.py` implement ordered version listing.
  - `src/core/proposals/service.py` builds lineage from a single ordered version-list read while
    preserving missing-version detection in projection logic.
  - Repository tests cover ordered list behavior for in-memory and Postgres implementations.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` proves lineage uses
    `list_versions` once and does not call per-version `get_version`.
- Consequence:
  - Proposal lineage read latency and database round trips now scale with one ordered query rather
    than one query per version number.
- Follow-Up:
  - Keep projection-level missing-version reporting unchanged until broader lineage read-model
    certification is performed against production-sized histories.

## LA-REV-103

- Scope: Async operation replay referent loading
- Pattern: modularity problem / replay evidence hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.get_async_operation_replay` embedded proposal lookup,
  successful-operation version selection, current-version fallback, and event loading directly in
  the service method.
- Evidence:
  - `src/core/proposals/async_replay.py` now owns async replay referent loading and version
    selection rules.
  - `src/core/proposals/service.py` delegates referent loading before building the replay evidence
    response.
  - `tests/unit/advisory/engine/test_engine_proposal_async_replay.py` covers exact result-version
    selection, fallback to current version, no-proposal operations, and pending operations.
- Consequence:
  - Async replay evidence assembly has a reusable, directly tested domain boundary instead of
    service-local orchestration logic.
- Follow-Up:
  - Continue extracting replay/report read-model helpers where multiple service methods still
    duplicate proposal, version, and event loading.

## LA-REV-104

- Scope: Proposal version replay referent loading
- Pattern: duplication / replay evidence hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Version replay and idempotent create replay both loaded proposal, version, and workflow
  events directly inside `ProposalWorkflowService`, duplicating read-model boundary rules.
- Evidence:
  - `src/core/proposals/proposal_replay.py` now owns proposal-version replay referent loading.
  - `src/core/proposals/service.py` reuses that loader for `get_version_replay` and
    idempotent create-response reconstruction.
  - `tests/unit/advisory/engine/test_engine_proposal_replay.py` covers complete replay context,
    missing proposal, and missing version boundaries.
- Consequence:
  - Replay evidence paths now share one tested proposal/version/event loading boundary, reducing
    service coupling and drift risk as replay evidence expands.
- Follow-Up:
  - Review delivery summary/history/report request read paths for similar reusable read-model
    boundaries once replay extraction settles.

## LA-REV-105

- Scope: Proposal activity read-model loading
- Pattern: duplication / read-model hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Workflow timeline, execution status, delivery summary, delivery history, and execution
  update replay loaded proposal and workflow events independently in the workflow service.
- Evidence:
  - `src/core/proposals/activity_read_model.py` now owns proposal activity read-model loading.
  - `src/core/proposals/service.py` reuses that loader across workflow timeline, execution status,
    delivery summary/history, and execution update handling.
  - `tests/unit/advisory/engine/test_engine_proposal_activity_read_model.py` covers ordered event
    loading and missing-proposal boundaries.
- Consequence:
  - Proposal activity read paths now share one tested repository boundary, reducing duplicated
    service orchestration and making later event pagination/caching changes easier to isolate.
- Follow-Up:
  - Revisit activity read-model pagination once production-sized proposal event histories are
    certified.

## LA-REV-106

- Scope: Proposal approval read-model loading
- Pattern: duplication / read-model hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Approval posture reads loaded proposal and approval records directly in
  `ProposalWorkflowService`, keeping private-banking approval read-model assembly in the service.
- Evidence:
  - `src/core/proposals/approval_read_model.py` now owns proposal approval read-model loading.
  - `src/core/proposals/service.py` delegates approval loading before projecting the approvals
    response.
  - `tests/unit/advisory/engine/test_engine_proposal_approval_read_model.py` covers ordered
    approval loading and missing-proposal boundaries.
- Consequence:
  - Approval posture has a reusable domain read boundary that can later absorb pagination,
    approval filtering, or audit enrichment without growing the workflow service.
- Follow-Up:
  - Keep approval replay/idempotency lookup separate until approval audit enrichment requirements
    are clearer.

## LA-REV-107

- Scope: Idempotent replay repository lookup boundary
- Pattern: duplication / replay-idempotency hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService` loaded workflow events and approvals directly before calling
  idempotency replay matching functions, splitting replay lookup behavior between service and domain
  helper code.
- Evidence:
  - `src/core/proposals/idempotency.py` now exposes repository-backed replay event and approval
    lookup helpers next to the hash-conflict matching rules.
  - `src/core/proposals/service.py` delegates replay lookup to those helpers while preserving
    service-level exception mapping.
  - `tests/unit/advisory/engine/test_engine_proposal_idempotency.py` covers repository-backed event
    and approval replay lookup.
- Consequence:
  - Idempotent transition and approval replay now share a cohesive lookup boundary, reducing
    service-level repository orchestration and keeping conflict behavior easier to audit.
- Follow-Up:
  - Consider repository-indexed idempotency lookup for workflow events/approvals if production event
    histories grow beyond acceptable scan latency.

## LA-REV-108

- Scope: Report request command state helper
- Pattern: service-boundary hardening / modularity problem
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_report_request` built report-request events and applied
  aggregate timestamp mutation inline, keeping report command state logic in the service layer.
- Evidence:
  - `src/core/proposals/reporting.py` now exposes
    `build_report_request_event_and_apply_state`.
  - `src/core/proposals/service.py` delegates report event construction and aggregate timestamp
    mutation to the reporting domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_reporting.py` covers the combined helper.
- Consequence:
  - Report request lineage and aggregate timestamp behavior are now directly tested at the domain
    boundary and can evolve without expanding the workflow service.
- Follow-Up:
  - Keep repository persistence in the service until broader command-handler extraction is
    justified for report orchestration.

## LA-REV-109

- Scope: Execution handoff command state helper
- Pattern: service-boundary hardening / modularity problem
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.request_execution_handoff` built execution handoff events and
  applied aggregate timestamp mutation inline, keeping handoff command state logic in the service
  layer.
- Evidence:
  - `src/core/proposals/execution_handoff.py` now exposes
    `build_execution_handoff_event_and_apply_state`.
  - `src/core/proposals/service.py` delegates handoff event construction and aggregate timestamp
    mutation to the execution handoff domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py` covers the combined
    helper.
- Consequence:
  - Execution handoff audit payload and aggregate timestamp behavior are directly tested at the
    domain boundary and can evolve without expanding the workflow service.
- Follow-Up:
  - Keep execution request id generation and repository persistence in the service until a broader
    command-handler boundary owns external execution orchestration.

## LA-REV-110

- Scope: State transition command state helper
- Pattern: service-boundary hardening / modularity problem
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.transition_state` built workflow transition events and applied
  aggregate state mutation inline, keeping transition command state logic in the service layer.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now exposes
    `build_state_transition_event_and_apply_state`.
  - `src/core/proposals/service.py` delegates transition event construction and aggregate state
    mutation to the lifecycle domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` covers the combined
    helper.
- Consequence:
  - State-transition audit payload and aggregate mutation behavior are directly tested at the
    domain boundary and can evolve without expanding the workflow service.
- Follow-Up:
  - Apply the same command-state boundary to approval transitions once approval command handling is
    isolated.

## LA-REV-111

- Scope: Approval command state helper
- Pattern: service-boundary hardening / modularity problem
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_approval` built approval records, approval transition
  events, and aggregate state mutation inline, keeping approval command state logic in the service
  layer.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now exposes
    `build_approval_command_state_and_apply_transition`.
  - `src/core/proposals/service.py` delegates approval record creation, transition event
    construction, and aggregate state mutation to the lifecycle domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py` covers the combined
    helper.
- Consequence:
  - Approval audit payload, persisted approval referent, and aggregate mutation behavior are
    directly tested at the domain boundary and can evolve without expanding the workflow service.
- Follow-Up:
  - Keep approval replay response reconstruction separate until approval audit enrichment is
    expanded.

## LA-REV-112

- Scope: Execution update command state helper
- Pattern: service-boundary hardening / modularity problem
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.record_execution_update` built execution update events and
  applied aggregate state mutation inline, keeping execution update command state logic in the
  service layer.
- Evidence:
  - `src/core/proposals/execution_update.py` now exposes
    `build_execution_update_event_and_apply_state`.
  - `src/core/proposals/service.py` delegates execution update event construction and aggregate
    state mutation to the execution update domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` covers the combined
    helper.
- Consequence:
  - Execution reconciliation audit payload and aggregate mutation behavior are directly tested at
    the domain boundary and can evolve without expanding the workflow service.
- Follow-Up:
  - Keep handoff identity and timestamp validation separate until execution update command handling
    is fully isolated.

## LA-REV-113

- Scope: New-version command state helper
- Pattern: service-boundary hardening / modularity problem
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.create_version` built the `NEW_VERSION_CREATED` event and
  applied proposal version-state mutation inline, keeping create-version command state logic in the
  service layer.
- Evidence:
  - `src/core/proposals/versions.py` now exposes
    `build_new_version_created_event_and_apply_state`.
  - `src/core/proposals/service.py` delegates new-version lifecycle event construction and
    aggregate version-state mutation to the versions domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_versions.py` covers the combined helper.
- Consequence:
  - Version lineage, draft reset, current-version increment, and last-event timestamp behavior are
    directly tested at the domain boundary and can evolve without expanding the workflow service.
- Follow-Up:
  - Review initial proposal creation for the same command-state boundary once create command
    materialization and idempotency persistence are isolated.

## LA-REV-114

- Scope: Initial proposal create command state helper
- Pattern: service-boundary hardening / modularity problem
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.create_proposal` assembled the initial proposal aggregate,
  `CREATED` lineage event, and proposal-create idempotency record inline, keeping create command
  referent construction in the service layer.
- Evidence:
  - `src/core/proposals/records.py` now exposes `build_proposal_create_command_state`.
  - `src/core/proposals/service.py` delegates initial proposal aggregate, lineage event, and
    idempotency referent construction to the records domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_records.py` covers the combined helper.
- Consequence:
  - Initial advisory proposal creation now has a directly tested command-state boundary for the
    persisted aggregate, audit lineage event, and replay identity referent.
- Follow-Up:
  - Keep proposal version materialization and persistence ordering in the service until a broader
    create command handler can own transaction boundaries.

## LA-REV-115

- Scope: Async create-version submission replay identity
- Pattern: service-boundary hardening / idempotency correctness
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.accept_create_version_async_submission` checked async operation
  type, proposal scope, and submission hash inline when deciding whether a correlation ID replay was
  valid.
- Evidence:
  - `src/core/proposals/async_operations.py` now exposes
    `is_matching_create_version_async_submission`.
  - `src/core/proposals/service.py` delegates create-version async replay matching to the async
    operations domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` covers type, proposal,
    and submission-hash mismatch behavior.
- Consequence:
  - Create-version async idempotency replay identity is directly tested beside async operation
    construction, reducing drift risk in service-level correlation replay checks.
- Follow-Up:
  - Apply the same explicit replay-identity helper pattern to create-proposal async submissions
    once acceptance metrics and conflict bookkeeping are isolated.

## LA-REV-116

- Scope: Async create-proposal submission replay identity
- Pattern: service-boundary hardening / idempotency correctness
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.accept_create_proposal_async_submission` checked replayed async
  create submissions by comparing the submission hash inline, leaving operation type and
  idempotency-key scope implicit in the service path.
- Evidence:
  - `src/core/proposals/async_operations.py` now exposes
    `is_matching_create_proposal_async_submission`.
  - `src/core/proposals/service.py` delegates create-proposal async replay matching to the async
    operations domain helper while retaining acceptance metric bookkeeping.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` covers type,
    idempotency-key, and submission-hash mismatch behavior.
- Consequence:
  - Create-proposal async idempotency replay identity is directly tested beside async operation
    construction, matching the create-version replay identity boundary.
- Follow-Up:
  - Isolate async acceptance metric bookkeeping once create and version submission acceptance share
    a broader command handler.

## LA-REV-117

- Scope: Recoverable async operation kind classification
- Pattern: service-boundary hardening / async recovery correctness
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.recover_async_operations` matched raw async operation type
  strings inline when routing recoverable create-proposal and create-version operations.
- Evidence:
  - `src/core/proposals/async_operations.py` now exposes
    `resolve_recoverable_async_operation_kind`.
  - `src/core/proposals/service.py` delegates supported recovery kind classification to the async
    operations domain helper while retaining execution dispatch and unsupported-operation failure
    handling.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` covers supported and
    unsupported recovery operation kinds.
- Consequence:
  - Async recovery supported-operation vocabulary is directly tested beside async operation
    construction, reducing drift risk when new recoverable operation types are added.
- Follow-Up:
  - Move recovery dispatch into a dedicated async command runner once executor ownership and
    transaction boundaries are isolated.

## LA-REV-118

- Scope: Async operation run skip predicate
- Pattern: service-boundary hardening / async retry correctness
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService._run_async_operation` owned the terminal async status set and
  checked missing or terminal operations inline before starting a retry attempt.
- Evidence:
  - `src/core/proposals/async_operations.py` now exposes `should_skip_async_operation_run`.
  - `src/core/proposals/service.py` delegates missing/terminal operation run skipping to the async
    operations domain helper.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` covers missing, pending,
    succeeded, and failed operation outcomes.
- Consequence:
  - Async retry-loop terminal state vocabulary is directly tested beside attempt, success, failure,
    and runtime exception state helpers.
- Follow-Up:
  - Move the full async runner loop behind a repository-aware command runner when persistence and
    executor boundaries can be isolated cleanly.

## LA-REV-119

- Scope: Proposal detail read-model loading
- Pattern: duplication / read-model hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService.get_proposal` loaded the proposal aggregate and current version
  directly, unlike other detail-style reads that now use dedicated proposal read-model loaders.
- Evidence:
  - `src/core/proposals/detail_read_model.py` now owns proposal detail read-model loading.
  - `src/core/proposals/service.py` delegates proposal/current-version loading before projecting
    the detail response.
  - `tests/unit/advisory/engine/test_engine_proposal_detail_read_model.py` covers complete detail,
    missing-proposal, and missing-current-version boundaries.
- Consequence:
  - Proposal detail loading now has a reusable domain read boundary that can later absorb caching,
    evidence redaction policy, or current-version fallback rules without expanding the workflow
    service.
- Follow-Up:
  - Review `get_version` and idempotency lookup read paths for similarly small read-model
    boundaries once detail loading settles.

## LA-REV-120

- Scope: Proposal lineage read-model loading
- Pattern: duplication / read-model hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService.get_lineage` loaded the proposal aggregate and version list
  directly before delegating lineage projection, leaving query-shape and missing-proposal behavior
  in service orchestration.
- Evidence:
  - `src/core/proposals/lineage_read_model.py` now owns proposal lineage read-model loading.
  - `src/core/proposals/service.py` delegates proposal/version-list loading before projecting the
    lineage response.
  - `tests/unit/advisory/engine/test_engine_proposal_lineage_read_model.py` covers complete
    lineage, missing-proposal, and missing-version-gap boundaries.
- Consequence:
  - Proposal lineage loading now has a reusable domain read boundary for future lineage pagination,
    caching, or version-gap diagnostics without expanding the workflow service.
- Follow-Up:
  - Keep missing-version detection in projection until lineage response policy changes beyond
    read-model loading.

## LA-REV-121

- Scope: Proposal version read-model loading
- Pattern: duplication / read-model hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService.get_version` loaded proposal version records directly before
  projection, leaving version-detail read boundaries in service orchestration.
- Evidence:
  - `src/core/proposals/version_read_model.py` now owns version-detail read-model loading.
  - `src/core/proposals/service.py` delegates requested-version loading before projecting the
    version detail response.
  - `tests/unit/advisory/engine/test_engine_proposal_version_read_model.py` covers found and
    missing version boundaries.
- Consequence:
  - Version detail loading now has a reusable domain read boundary that can later absorb evidence
    redaction, caching, or version authorization without expanding the workflow service.
- Follow-Up:
  - Review idempotency and async-operation status reads for the same direct-read boundary pattern.

## LA-REV-122

- Scope: Proposal idempotency read-model loading
- Pattern: duplication / replay-audit read hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService.get_idempotency_lookup` loaded idempotency replay records
  directly before projecting replay-audit metadata.
- Evidence:
  - `src/core/proposals/idempotency_read_model.py` now owns idempotency key read-model loading.
  - `src/core/proposals/service.py` delegates replay-audit key lookup before projecting the
    idempotency lookup response.
  - `tests/unit/advisory/engine/test_engine_proposal_idempotency_read_model.py` covers found and
    missing idempotency-key boundaries.
- Consequence:
  - Replay-audit key lookup now has a reusable domain read boundary that can later absorb
    authorization, audit lineage enrichment, or indexed lookup changes without expanding the
    workflow service.
- Follow-Up:
  - Review async-operation status reads for the same direct-read boundary pattern.

## LA-REV-123

- Scope: Proposal async-operation read-model loading
- Pattern: duplication / operational status read hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Async operation status and replay endpoints loaded operation records directly from the
  workflow service by operation id or correlation id before projection and replay referent loading.
- Evidence:
  - `src/core/proposals/async_operation_read_model.py` now owns operation-id and correlation-id
    read-model loading.
  - `src/core/proposals/service.py` delegates async-operation status and replay operation loading
    before status projection or replay referent resolution.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operation_read_model.py` covers found
    and missing operation boundaries for both lookup keys.
- Consequence:
  - Async operational diagnostics now have a reusable read boundary for future status caching,
    tenant authorization, or indexed correlation lookup without expanding the workflow service.
- Follow-Up:
  - Review proposal list filtering and pagination as the next read-model boundary after compact
    status lookups.

## LA-REV-124

- Scope: Proposal list read-model loading and projection
- Pattern: modularity / pagination boundary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.list_proposals` owned repository filtering, pagination tuple
  handling, and list DTO assembly inline, unlike the newer proposal read paths with dedicated
  read-model and projection boundaries.
- Evidence:
  - `src/core/proposals/list_read_model.py` now owns proposal list filter and cursor loading.
  - `src/core/proposals/projections.py` now owns `ProposalListResponse` assembly.
  - `src/core/proposals/service.py` delegates list loading and projection instead of assembling the
    response inline.
  - `tests/unit/advisory/engine/test_engine_proposal_list_read_model.py` covers filtered paging and
    empty-result boundaries.
- Consequence:
  - Proposal list pagination now has a reusable domain read boundary that can later absorb stable
    sort policy, portfolio authorization, cursor hardening, or query diagnostics without expanding
    the workflow service.
- Follow-Up:
  - Review remaining write-path repository reads in create-version and transition commands for
    opportunities to reuse existing activity/detail read models without hiding command invariants.

## LA-REV-125

- Scope: Async operation command read-model reuse
- Pattern: duplication / operational command boundary hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Async create execution, async version execution, retry-loop reloads, and async version
  correlation replay checks still loaded operation records directly even after status and replay
  lookups moved to a domain read-model boundary.
- Evidence:
  - `src/core/proposals/service.py` now reuses
    `src/core/proposals/async_operation_read_model.py` for async execution lookup, retry-loop
    reloads, and correlation-id submission lookup.
  - Existing workflow-service tests cover missing operation no-op behavior, async version
    correlation replay/conflict behavior, and runtime retry/failure paths through the reused read
    model boundary.
- Consequence:
  - Async operational reads now follow one reusable boundary across status, replay, execution, and
    correlation acceptance paths, reducing future drift in retry, authorization, and diagnostics
    handling.
- Follow-Up:
  - Review proposal aggregate command loading separately; command-state invariants should remain
    explicit even if a loader is introduced.

## LA-REV-126

- Scope: Proposal command aggregate loading
- Pattern: duplication / command boundary hardening
- Status: Hardened
- Finding Class: duplication
- Summary: Create-version, execution-handoff, lifecycle transition, approval, and report-request
  commands loaded proposal aggregates directly from the workflow service, even though the command
  invariants around expected state, lifecycle rules, and transition persistence were already split
  into focused domain helpers.
- Evidence:
  - `src/core/proposals/command_read_model.py` now owns command aggregate loading by proposal id.
  - `src/core/proposals/service.py` delegates proposal aggregate loading to the command read model
    while leaving command validation and state mutation explicit at the call site.
  - `tests/unit/advisory/engine/test_engine_proposal_command_read_model.py` covers found and
    missing proposal aggregate boundaries.
- Consequence:
  - Command aggregate reads now have a reusable boundary for future authorization, tenant scoping,
    or lock-aware loading without obscuring command-specific invariants.
- Follow-Up:
  - Review whether command loaders should become lock-aware in the Postgres repository before
    introducing any stronger transactional behavior.

## LA-REV-127

- Scope: Proposal create idempotency replay lookup
- Pattern: duplication / replay command boundary hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService.create_proposal` still loaded proposal idempotency records
  directly even after replay-audit lookup moved behind `idempotency_read_model.py`.
- Evidence:
  - `src/core/proposals/service.py` now reuses
    `src/core/proposals/idempotency_read_model.py` for create replay lookup before request-hash
    conflict checks and create-response reconstruction.
  - Existing workflow-service tests cover idempotent create replay and hash-conflict behavior, and
    `tests/unit/advisory/engine/test_engine_proposal_idempotency_read_model.py` covers found and
    missing idempotency-key boundaries.
- Consequence:
  - Create replay and replay-audit lookup now share one idempotency read boundary, reducing drift
    if indexed lookup, tenant scoping, or audit enrichment is added later.
- Follow-Up:
  - Review create persistence as a future transactional-unit boundary; avoid hiding the explicit
    proposal/version/event/idempotency write sequence until repository semantics are strengthened.

## LA-REV-128

- Scope: Initial proposal persistence sequence
- Pattern: modularity / transactional-boundary preparation
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.create_proposal` persisted the initial proposal aggregate,
  version, created event, and idempotency record inline, making the future transactional boundary
  harder to isolate and test.
- Evidence:
  - `src/core/proposals/create_persistence.py` now owns the named initial create persistence
    sequence.
  - `src/core/proposals/service.py` delegates proposal/version/event/idempotency persistence after
    command-state and version construction.
  - `tests/unit/advisory/engine/test_engine_proposal_create_persistence.py` verifies that the
    proposal, initial version, created event, and replay identity are persisted together.
- Consequence:
  - Initial proposal persistence now has a focused boundary that can later become repository-atomic
    without expanding workflow orchestration or obscuring the write order.
- Follow-Up:
  - Add repository-level atomic create support before changing transactional semantics.

## LA-REV-129

- Scope: Proposal version persistence sequence
- Pattern: modularity / transactional-boundary preparation
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.create_version` persisted the new version record and lifecycle
  transition inline, leaving the future version-create transactional boundary mixed into workflow
  orchestration.
- Evidence:
  - `src/core/proposals/create_persistence.py` now owns `persist_created_proposal_version`.
  - `src/core/proposals/service.py` delegates new-version record and transition-event persistence
    after version record and event construction.
  - `tests/unit/advisory/engine/test_engine_proposal_create_persistence.py` verifies version
    persistence stores the new version, advances aggregate state, and records the lifecycle event.
- Consequence:
  - Proposal version persistence now has a focused boundary that can later become repository-atomic
    without expanding workflow orchestration or changing version lifecycle rules.
- Follow-Up:
  - Add repository-level atomic version-create support before changing transactional semantics.

## LA-REV-130

- Scope: Proposal lifecycle transition persistence
- Pattern: modularity / transactional-boundary preparation
- Status: Hardened
- Finding Class: modularity problem
- Summary: Lifecycle commands persisted proposal transitions directly from the workflow service,
  repeating the same repository transition call across execution handoff, execution update,
  state transition, approval, and report-request flows.
- Evidence:
  - `src/core/proposals/transition_persistence.py` now owns generic transition and
    approval-transition persistence.
  - `src/core/proposals/service.py` delegates lifecycle transition writes while preserving
    command-specific validation, event construction, and response assembly.
  - `tests/unit/advisory/engine/test_engine_proposal_transition_persistence.py` verifies aggregate
    state, event persistence, and approval referent persistence through the new helpers.
- Consequence:
  - Lifecycle transition persistence now has a focused boundary that can later become lock-aware or
    repository-atomic without expanding workflow orchestration.
- Follow-Up:
  - Review Postgres transaction semantics before changing repository behavior beyond delegation.

## LA-REV-131

- Scope: Async operation state persistence
- Pattern: modularity / operational persistence hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService` owned repeated async operation state mutation plus
  `update_operation` persistence for attempts, success, lifecycle failure, payload recovery
  failure, and runtime retry/final-failure outcomes.
- Evidence:
  - `src/core/proposals/async_operation_persistence.py` now owns async operation state mutation plus
    repository update persistence.
  - `src/core/proposals/service.py` delegates async attempt, success, failure, and runtime outcome
    persistence while preserving async orchestration flow.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operation_persistence.py` verifies
    running leases, success results, terminal errors, and retry/final-failure persistence.
- Consequence:
  - Async operation persistence now has a reusable boundary for future metrics, tracing, optimistic
    locking, or repository-atomic updates without expanding workflow orchestration.
- Follow-Up:
  - Review async operation creation and recoverable-operation listing for similar persistence/read
    boundaries once update semantics settle.

## LA-REV-132

- Scope: Async operation submission persistence
- Pattern: modularity / replay-boundary hardening
- Status: Hardened
- Finding Class: duplication
- Summary: `ProposalWorkflowService` still owned async operation creation, replay matching, and
  conflict classification for create-proposal idempotency keys and create-version correlation IDs.
- Evidence:
  - `src/core/proposals/async_operation_submission.py` now owns async submission persistence
    results for new, replayed, and conflicting submissions.
  - `src/core/proposals/service.py` delegates create-proposal idempotency and create-version
    correlation persistence decisions while preserving orchestration, stats, and API error mapping.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operation_submission.py` verifies new
    persistence, replay behavior, and mismatch classification for both async submission families.
- Consequence:
  - Async submission persistence now has a reusable boundary for future idempotency metrics,
    tenant scoping, optimistic locking, and repository-atomic submission APIs without increasing
    workflow-service branching.
- Follow-Up:
  - Review recoverable-operation listing and async recovery dispatch as the remaining direct
    repository-owned async operation boundary in `ProposalWorkflowService`.

## LA-REV-133

- Scope: Async operation recovery read model
- Pattern: modularity / recovery-boundary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService.recover_async_operations` still owned recoverable-operation
  repository listing and operation-kind classification inline, leaving recovery scanning as the
  remaining direct async repository read boundary in workflow orchestration.
- Evidence:
  - `src/core/proposals/async_operation_recovery_read_model.py` now owns recoverable async
    operation listing plus supported/unsupported operation-kind classification.
  - `src/core/proposals/service.py` delegates recovery scanning while preserving dispatch and
    unsupported-operation failure handling.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operation_recovery_read_model.py`
    verifies supported classification, unsupported preservation, and repository recoverability
    filtering for expired running operations.
- Consequence:
  - Async recovery scanning now has a reusable boundary for future batching, lease diagnostics,
    recovery metrics, or tenant-scoped recovery without increasing workflow-service coupling.
- Follow-Up:
  - Review recovery dispatch as a possible command-router boundary only if more async operation
    families are added.

## LA-REV-134

- Scope: Proposal exception taxonomy
- Pattern: modularity / API-facing vocabulary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: Proposal lifecycle exceptions were defined inside `ProposalWorkflowService`, forcing API
  routers, workspace integration, tests, and package exports to depend on the workflow service
  module for reusable domain error vocabulary.
- Evidence:
  - `src/core/proposals/exceptions.py` now owns proposal lifecycle, not-found, validation,
    idempotency-conflict, state-conflict, and transition error classes.
  - `src/core/proposals/service.py` imports the exception taxonomy instead of defining it inline.
  - `src/core/proposals/__init__.py` exports exceptions from the dedicated module while preserving
    package-level compatibility.
  - `tests/unit/advisory/engine/test_engine_proposal_exceptions.py` verifies inheritance and
    existing service/package import compatibility.
- Consequence:
  - API-facing proposal error vocabulary is now reusable by routers, support services, and future
    command modules without expanding workflow-service coupling.
- Follow-Up:
  - Move router imports to `src.core.proposals.exceptions` in a later compatibility-preserving
    cleanup once service refactoring stabilizes.

## LA-REV-135

- Scope: API proposal exception import boundaries
- Pattern: modularity / dependency-flow hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: API routers, workspace routing, and proposal-reporting support still imported proposal
  exception vocabulary through the package facade, leaving API error handling coupled to broad
  package exports instead of the dedicated exception taxonomy module.
- Evidence:
  - `src/api/proposals/errors.py`, proposal lifecycle/async/delivery/support routers,
    `src/api/workspaces/router.py`, and `src/api/services/proposal_reporting_service.py` now
    import proposal exceptions from `src.core.proposals.exceptions`.
  - `tests/unit/advisory/api/test_proposal_exception_import_boundaries.py` prevents API modules
    from reintroducing proposal exception imports through the package facade.
  - Existing API error handling and proposal lifecycle tests verify HTTP behavior remains stable.
- Consequence:
  - API-facing error mapping now depends on a narrow domain vocabulary module rather than the
    workflow service/package facade, reducing import coupling and startup side effects.
- Follow-Up:
  - Consider moving engine tests to the exception module for exception imports once the service
    compatibility shim is no longer needed by downstream callers.

## LA-REV-136

- Scope: Proposal command validation adapters
- Pattern: modularity / domain-error mapping hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: `ProposalWorkflowService` still owned private wrappers that translated low-level
  simulation-gate, expected-state, transition-rule, and approval-rule errors into proposal
  lifecycle exceptions.
- Evidence:
  - `src/core/proposals/command_validation.py` now owns proposal command validation adapters and
    domain error mapping for simulation flags, expected state, state transitions, and approvals.
  - `src/core/proposals/service.py` delegates command validation and transition resolution to the
    adapter module instead of carrying private wrapper methods.
  - `tests/unit/advisory/engine/test_engine_proposal_command_validation.py` verifies validation
    and transition-rule errors map to proposal lifecycle exceptions.
  - Existing workflow-service tests continue to verify end-to-end command behavior.
- Consequence:
  - Validation error mapping is reusable by future command modules and remains test-covered outside
    workflow orchestration.
- Follow-Up:
  - Review remaining service-local replay helper methods once command modules stabilize.

## LA-REV-137

- Scope: Lotus Core stateful-context classification vocabulary
- Pattern: modularity / upstream authority boundary hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The Lotus Core stateful-context adapter still mixed upstream HTTP/cache orchestration
  with classification taxonomy parsing, governed label resolution, supportability attributes, and
  liquidity-tier fallback rules.
- Evidence:
  - `src/integrations/lotus_core/classification.py` now owns the pure instrument-classification
    vocabulary helpers and the `ClassificationTaxonomy` model.
  - `src/integrations/lotus_core/stateful_context.py` imports those helpers and remains focused on
    context resolution, source reads, cache usage, request translation, and enrichment assembly.
  - `tests/unit/advisory/api/test_lotus_core_stateful_context.py` continues to validate taxonomy
    mapping, liquidity-tier behavior, source supportability attributes, cache behavior, and resolved
    simulation request assembly.
- Consequence:
  - Private-banking instrument vocabulary is now reusable and testable without expanding the
    stateful-context adapter, and the adapter lost a pure domain block while preserving public
    compatibility for existing callers.
- Follow-Up:
  - Continue WTBD-002 by extracting source-read, market-data hydration, and cache-policy modules
    only when behavior can remain pinned to existing RFC-0082 authority tests.

## LA-REV-138

- Scope: Lotus Core stateful-context cache policy
- Pattern: modularity / operational diagnostics hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The stateful-context adapter still owned cache configuration, cache instances,
  copy-safety policy, fetch counters, cache statistics, and test reset behavior inline with
  upstream HTTP reads and request translation.
- Evidence:
  - `src/integrations/lotus_core/stateful_context_cache.py` now owns stateful-context cache TTL and
    size policy, cache key construction, clone policy, named cache instances, fetch counters, cache
    stats, and cache reset behavior.
  - `src/integrations/lotus_core/stateful_context.py` delegates cache lifecycle and diagnostics to
    that module while retaining compatibility wrappers for existing characterization tests.
  - `tests/unit/advisory/api/test_lotus_core_stateful_context.py` continues to prove cache TTL/size
    parsing, cache reuse, copy-safe cached responses, cache isolation, eviction, failure recovery,
    and fetch counter behavior.
- Consequence:
  - Cache behavior is now a named operational boundary that can be tuned, instrumented, or reused
    without expanding the upstream adapter. The adapter is smaller and more focused on source reads,
    request translation, and enrichment assembly.
- Follow-Up:
  - Continue WTBD-002 by extracting source-read and market-data hydration modules only where
    existing RFC-0082 authority and failure-mode tests can pin behavior.

## LA-REV-139

- Scope: Lotus Core stateful-context route policy
- Pattern: modularity / upstream route-boundary hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The stateful-context adapter still owned Lotus Core endpoint constants, query-plane and
  control-plane base URL derivation, and dated positions/cash path construction inline with HTTP
  request execution and advisory request translation.
- Evidence:
  - `src/integrations/lotus_core/stateful_context_routes.py` now owns stateful-context endpoint
    constants and the Lotus Core query/control-plane URL derivation policy.
  - `src/integrations/lotus_core/stateful_context.py` delegates base URL and path construction
    through compatibility wrappers so existing characterization tests keep pinning behavior.
  - `tests/unit/advisory/api/test_lotus_core_stateful_context.py` continues to prove query versus
    control-plane separation, Docker/local port derivation, authenticated URL preservation, default
    service identity, and as-of propagation to positions/cash reads.
- Consequence:
  - Upstream route policy is now a named boundary that can evolve with Lotus Core contract changes
    without mixing endpoint decisions into source-read execution or advisory context translation.
- Follow-Up:
  - Continue WTBD-002 by extracting HTTP source-read execution and market-data hydration only when
    route policy and failure semantics remain pinned by focused tests.

## LA-REV-140

- Scope: Lotus Core stateful-context source reads
- Pattern: modularity / upstream failure-boundary hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The stateful-context adapter still mixed HTTP request execution, cached JSON lookup,
  source fetch counters, bulk instrument enrichment reads, and classification taxonomy fetches with
  advisory context translation.
- Evidence:
  - `src/integrations/lotus_core/stateful_context_source_reads.py` now owns stateful request
    execution, upstream error mapping, fetch counter classification, cached JSON reads, bulk
    instrument enrichment reads, and classification taxonomy reads.
  - `src/integrations/lotus_core/stateful_context.py` imports those boundaries while preserving
    existing private-name compatibility for the focused stateful-context test module.
  - `tests/unit/advisory/api/test_lotus_core_stateful_context.py` continues to prove source-read
    error mapping, cache reuse, enrichment caching, taxonomy fallback, fetch counters, and full
    resolved simulation request assembly.
- Consequence:
  - Upstream read mechanics are now separated from advisory translation, making it easier to add
    batching, diagnostics, retry policy, or lineage around source reads without expanding the
    stateful-context adapter.
- Follow-Up:
  - Continue WTBD-002 by extracting source-to-request translation and market-data hydration where
    behavior can be characterized without weakening RFC-0082 source authority boundaries.

## LA-REV-141

- Scope: Lotus Core stateful-context payload translation
- Pattern: modularity / advisory translation boundary hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The stateful-context adapter still owned payload translation from Lotus Core portfolio,
  position, cash, enrichment, price, and FX records into Advise simulation request models.
- Evidence:
  - `src/integrations/lotus_core/stateful_context_translation.py` now owns decimal parsing, shelf
    attribute construction, cash balance construction, position construction, price construction,
    FX-rate derivation, and governed shelf-entry translation.
  - `src/integrations/lotus_core/stateful_context.py` imports the translation helpers while
    preserving compatibility for focused characterization tests.
  - `tests/unit/advisory/api/test_lotus_core_stateful_context.py` continues to prove invalid
    source rows are skipped safely, cash/positions/prices/FX/shelf entries are built correctly,
    governed taxonomy supportability attributes survive, and full resolved request assembly remains
    stable.
- Consequence:
  - Advisory source-to-request translation is now a named boundary separate from upstream reads,
    route policy, cache policy, and non-held trade-draft hydration.
- Follow-Up:
  - Continue WTBD-002 by extracting non-held trade-draft market-data hydration into a separate
    module with the existing cache and taxonomy behavior pinned.

## LA-REV-142

- Scope: Lotus Core stateful-context trade-draft hydration
- Pattern: modularity / advisory enrichment boundary hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The stateful-context adapter still owned non-held trade-draft hydration inline with
  context resolution, including missing-instrument detection, instrument/price/FX lookup selection,
  shelf-entry append behavior, and classification-aware enrichment.
- Evidence:
  - `src/integrations/lotus_core/stateful_context_hydration.py` now owns non-held proposed-trade
    market-data hydration and delegates source reads through the existing cache/source-read seams.
  - `src/integrations/lotus_core/stateful_context.py` delegates trade-draft enrichment through a
    thin wrapper that keeps existing public imports and test monkeypatch points stable.
  - `tests/unit/advisory/api/test_lotus_core_stateful_context.py` continues to prove missing
    trade input hydration, malformed lookup skipping, duplicate avoidance, FX append behavior,
    cache reuse, taxonomy supportability attributes, and resolved request compatibility.
- Consequence:
  - WTBD-002 is closed for the recorded Advise-owned decomposition scope. The adapter now keeps
    source facts in Lotus Core, advisory translation in Advise, and trade-draft hydration in a
    named module that can be tuned for batching, diagnostics, or lineage without expanding context
    resolution orchestration.
- Follow-Up:
  - Monitor future stateful-context growth through the codebase review ledger; do not reopen
    WTBD-002 unless new behavior materially expands the adapter boundary.

## LA-REV-143

- Scope: Workspace API service orchestration
- Pattern: modularity / service-boundary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: The workspace API service still carried stateful/stateless context resolution and
  lifecycle handoff branch orchestration alongside session lookup, persistence, draft actions,
  evaluation, saved-version operations, replay reads, and comparison.
- Evidence:
  - `src/api/services/workspace_context_resolution.py` now owns workspace simulate-request
    assembly, stateful Lotus Core context resolution, trade-draft hydration, stateless request
    application, and create-time stateful fallback context construction.
  - `src/api/services/workspace_lifecycle_handoff.py` now owns workspace-to-proposal create versus
    version handoff orchestration, idempotency-key enforcement, replay-lineage construction,
    context-resolution override assembly, and proposal service invocation.
  - `src/api/services/workspace_errors.py` now owns workspace service exception vocabulary, while
    `src/api/services/workspace_service.py` re-exports the existing symbols for callers and tests.
  - `tests/unit/advisory/api/test_workspace_service.py`,
    `tests/unit/advisory/api/test_workspace_handoff.py`,
    `tests/unit/advisory/api/test_workspace_replay.py`, and
    `tests/unit/advisory/api/test_workspace_versions.py` continue to prove create validation,
    context-resolution failure mapping, reevaluation, lifecycle handoff, replay continuity,
    saved-version resume/list/replay behavior, and comparison compatibility.
- Consequence:
  - WTBD-003 is closed for the recorded Advise-owned decomposition scope. The API service is now a
    smaller facade over named workspace boundaries, with upstream context resolution and proposal
    lifecycle handoff isolated for future diagnostics, lineage, and contract testing.
- Follow-Up:
  - Track any future workspace service growth as a new finding only when a concrete behavior starts
    mixing endpoint facade responsibilities with domain or integration orchestration again.

## LA-REV-144

- Scope: Proposal workflow async runner and command extraction
- Pattern: modularity / command-boundary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: The proposal workflow service still owned async operation retry-loop mechanics, async
  payload failure persistence, lifecycle transition command persistence, approval command
  persistence, execution handoff command persistence, execution update command persistence, and
  report-request command persistence inline with high-level create, version, lifecycle, approval,
  execution, query, and replay coordination.
- Evidence:
  - `src/core/proposals/async_operation_runner.py` now owns async operation lease acquisition,
    terminal-skip handling, lifecycle failure persistence, runtime retry/final-failure behavior,
    and success persistence.
  - `src/core/proposals/report_request_command.py` now owns report-request aggregate loading,
    report lineage event construction, aggregate timestamp mutation, and transition persistence.
  - `src/core/proposals/execution_handoff_command.py` now owns execution-handoff aggregate loading,
    idempotent replay detection, expected-state validation, execution-ready validation, event
    construction, aggregate mutation, and transition persistence.
  - `src/core/proposals/execution_update_command.py` now owns execution-update aggregate loading,
    handoff identity validation, idempotent replay detection, terminal-state validation, timestamp
    ordering, event construction, aggregate mutation, and transition persistence while preserving
    the existing reload-after-write response behavior.
  - `src/core/proposals/lifecycle_command.py` now owns lifecycle state-transition and approval
    aggregate loading, idempotent replay detection, expected-state validation, transition
    resolution, approval record construction, event construction, aggregate mutation, and
    transition persistence.
  - `src/core/proposals/async_payload_resolution.py` now owns async create/version payload recovery
    failure mapping and persistence, keeping payload resolution outcomes outside the workflow
    service.
  - `src/core/proposals/service.py` delegates to those helpers while keeping the public workflow
    service API and existing exception behavior stable.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` continues to prove async
    create/version execution, lifecycle failure handling, runtime retry behavior, recovery of
    pending/expired operations, recovered async payload failure handling, lifecycle transition
    replay/conflict behavior, approval replay/conflict behavior, execution handoff replay/conflict
    behavior, execution update replay/conflict behavior, report request event recording, and
    proposal command compatibility.
- Consequence:
  - WTBD-001 is narrowed further: async runtime mechanics, async payload failure handling,
    lifecycle and approval writes, execution handoff writes, execution update writes, and report
    command writes are now named proposal-domain boundaries rather than service-private branches.
    The remaining WTBD-001 risk is concentrated in the large API contract module, which should be
    split only with explicit schema-compatibility safeguards.
- Follow-Up:
  - Continue WTBD-001 in small command-oriented slices; do not split `models.py` mechanically
    without a compatibility/export plan and OpenAPI regression proof.

## LA-REV-145

- Scope: Proposal contract model module boundaries
- Pattern: modularity / API-contract compatibility hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: The proposal contract model module still carried literals, input envelopes, API/read
  response DTOs, and persistence records in one large file even after workflow service command
  decomposition was substantially complete.
- Evidence:
  - `src/core/proposals/contract_types.py` now owns proposal lifecycle, execution, async,
    reporting, approval, and input-mode literal vocabularies.
  - `src/core/proposals/input_models.py` now owns proposal create/version/simulation input
    envelopes and compatibility validators for legacy, stateless, and stateful request shapes.
  - `src/core/proposals/response_models.py` now owns proposal API/read response DTOs, including
    workflow, approval, execution, delivery, lineage, idempotency, async status, and transition
    responses.
  - `src/core/proposals/persistence_models.py` now owns internal proposal aggregate, version,
    workflow event, approval, idempotency, simulation idempotency, transition-result, and async
    operation records.
  - `src/core/proposals/models.py` remains the stable public import module and re-exports the same
    proposal contract names for existing callers.
  - `tests/unit/advisory/contracts/test_proposal_model_module_boundaries.py` pins the compatibility
    re-export behavior and schema titles after the split.
- Consequence:
  - WTBD-001 is closed for the recorded Advise-owned decomposition scope. The proposal workflow
    service is now a smaller coordinator over named command/read-model boundaries, and the proposal
    contract module is split by responsibility without forcing immediate caller churn or changing
    schema titles.
- Follow-Up:
  - Treat future proposal contract moves as explicit API-governance work with OpenAPI regression
    evidence; do not move public DTO names out of `src.core.proposals.models` without a deprecation
    plan.

## LA-REV-146

- Scope: Downstream capability consumer alignment
- Pattern: cross-app contract hardening / supportability preservation
- Status: Hardened
- Finding Class: integration drift
- Summary: WTBD-004 required verifying Gateway and Workbench capability consumers after Advise
  capability-contract hardening. The source contract remained stable, but the Gateway Advise client
  was still flattening capability discovery to the default Advise query posture by not sending the
  canonical snake_case `consumer_system` and `tenant_id` query parameters.
- Evidence:
  - `lotus-gateway` branch `feat/advise-capability-query-alignment` commit `7f282e7` updates
    `src/app/clients/advise_client.py` so Gateway calls Advise `GET /platform/capabilities` with
    `consumer_system=lotus-gateway` and the caller tenant id.
  - Gateway test
    `tests/unit/test_upstream_clients.py::test_advise_client_capabilities_uses_gateway_consumer_and_tenant_context`
    pins the canonical Advise capability query parameters and tenant propagation.
  - Gateway read-only review confirmed `src/app/services/platform_capabilities_service.py`
    preserves Advise `supportability` into proposal/advisory shell workspace descriptors through
    `_source_supportability(...)`.
  - Workbench read-only review confirmed `src/features/platform-capabilities/api.ts`,
    `src/features/platform-capabilities/use-platform-capabilities.ts`, and
    `src/shell/workspace-supportability-copy.ts` consume the Gateway platform-capability contract
    and prefer Gateway-provided supportability reasons over local fallback copy.
  - Gateway validation:
    `python -m pytest tests/unit/test_upstream_clients.py::test_advise_client_capabilities_uses_gateway_consumer_and_tenant_context tests/unit/test_router_upstream_selection.py tests/integration/test_platform_capabilities_router.py::test_platform_capabilities_router_preserves_correlation_and_query_context -q`
    passed with `7 passed`; `python -m ruff check src/app/clients/advise_client.py tests/unit/test_upstream_clients.py`
    and `git diff --check` also passed in `lotus-gateway`.
- Consequence:
  - WTBD-004 is closed. Gateway now preserves tenant-shaped Advise capability posture at the source
    boundary, and Workbench remains a consumer of Gateway capability truth rather than a local
    advisory supportability authority.
- Documentation:
  - No wiki change is required for this closure because the public Advise capability API contract
    and existing wiki-described supportability fields did not change; the fix was downstream query
    propagation plus ledger closure evidence.
- Follow-Up:
  - Reopen only if the Advise capability response shape changes or a downstream surface starts
    deriving advisory readiness from local feature flags instead of source-backed supportability.

## LA-REV-147

- Scope: WTBD ledger closure governance
- Pattern: documentation contract hardening
- Status: Hardened
- Finding Class: governance drift
- Summary: The WTBD ledger had closed each recorded item, but it still required manual reading to
  prove that every WTBD carried an explicit closed disposition. That left future refactor agents
  vulnerable to reopening already-closed work or leaving observation-only downstream language behind.
- Evidence:
  - `docs/rfcs/WTBD.md` now has a Closure Register for WTBD-001 through WTBD-004 with owner,
    status, and closure evidence.
  - Each WTBD section now carries an explicit `Status: Closed` marker.
  - `tests/unit/test_wtbd_ledger_contract.py` parses the ledger and fails if a recorded WTBD lacks
    closed status or if stale observation-only / unconfirmed-defect language is reintroduced.
- Consequence:
  - Advise WTBD closure is now test-pinned instead of relying on manual narrative inspection.
- Documentation:
  - No wiki change is required for this governance guardrail because it changes the internal RFC
    ledger contract, not the public API, feature, or operator-facing wiki truth.
- Follow-Up:
  - Add new WTBD entries only with an explicit status and owner, and update the closure register in
    the same slice when a WTBD is closed.

## LA-REV-148

- Scope: WTBD closure proof pack
- Pattern: validation evidence / closure hardening
- Status: Hardened
- Finding Class: test evidence gap
- Summary: After WTBD-001 through WTBD-004 were closed, the branch needed one consolidated
  WTBD-aligned proof pass that exercised the closure-critical surfaces together rather than relying
  only on the incremental test runs from each slice.
- Evidence:
  - Ran
    `python -m pytest tests/unit/test_wtbd_ledger_contract.py tests/unit/advisory/contracts/test_proposal_model_module_boundaries.py tests/unit/advisory/contracts tests/unit/advisory/api/test_api_integration_capabilities.py tests/unit/advisory/api/test_api_workspace.py tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py tests/unit/advisory/api/test_lotus_core_stateful_context.py tests/unit/advisory/engine/test_engine_proposal_workflow_service.py -q`.
  - Result: `256 passed in 30.81s`.
  - Covered WTBD ledger closure governance, proposal contract compatibility, OpenAPI contract docs,
    integration capabilities/supportability, workspace API/service decomposition behavior,
    Lotus Core stateful-context adapter behavior, and proposal workflow service command behavior.
- Consequence:
  - The recorded WTBD closures now have a consolidated feature-lane proof pack tied to the review
    ledger.
- Documentation:
  - No wiki change is required because this is validation evidence for internal WTBD closure, not a
    public capability or operator workflow change.
- Follow-Up:
  - Before PR merge, run the repo-native `make check` or stronger local/CI equivalent and keep the
    published wiki drift disposition explicit.

## LA-REV-149

- Scope: WTBD feature-lane gate
- Pattern: type safety / feature-lane validation
- Status: Hardened
- Finding Class: validation failure
- Summary: The consolidated WTBD proof pack passed, but the repo-native `make check` gate initially
  failed because three recently extracted proposal command helper functions lacked explicit return
  type annotations.
- Evidence:
  - `src/core/proposals/lifecycle_command.py` now annotates replayed lifecycle event and approval
    helper return types with `ProposalWorkflowEventRecord | None` and
    `ProposalApprovalRecordData | None`.
  - `src/core/proposals/execution_handoff_command.py` now annotates replayed execution-handoff
    event lookup with `ProposalWorkflowEventRecord | None`.
  - Reran `make check`.
  - Result: ruff check passed, ruff format check passed for 333 files, monetary-float guard passed,
    mypy passed for 174 source files, OpenAPI quality gate passed, lifecycle OpenAPI docs tests
    passed (`5 passed`), no-alias guard passed, API vocabulary inventory generated and validate-only
    passed with no drift, domain-data product declarations validated, and unit tests passed
    (`807 passed in 59.13s`).
- Consequence:
  - WTBD closure now satisfies the repository-native feature-lane gate, not only the targeted proof
    pack.
- Documentation:
  - No wiki change is required because this is validation/type-safety evidence for internal WTBD
    closure, not a public capability or operator workflow change.
- Follow-Up:
  - Keep `make check` as the minimum local gate for any further WTBD reopening or closure claim.

## LA-REV-150

- Scope: WTBD PR-grade local gate
- Pattern: merge-gate validation evidence
- Status: Hardened
- Finding Class: validation evidence gap
- Summary: WTBD closure had feature-lane proof, but bank-buyable closure also needs the stronger
  local PR-grade gate covering dependency posture, security audit, migration smoke, integration and
  e2e coverage, and the repository coverage threshold.
- Evidence:
  - Ran `make ci-local`.
  - Dependency health check completed; direct outdated package posture remains informational under
    the current repository gate: `certifi 2026.4.22 -> 2026.5.20`, `click 8.3.3 -> 8.4.0`,
    `cvxpy 1.8.2 -> 1.9.0`, `numpy 2.4.4 -> 2.4.6`, `ruff 0.15.12 -> 0.15.13`, and
    `uvicorn 0.46.0 -> 0.47.0`.
  - Security audit reported `Known vulnerabilities: 0`.
  - Lint, formatting, monetary-float guard, mypy, OpenAPI quality, lifecycle OpenAPI docs tests,
    no-alias guard, API vocabulary generation plus validate-only, domain-data product validation,
    and migration smoke all passed.
  - Coverage-combined ran unit, integration, and e2e suites:
    `807 passed in 61.50s`, `54 passed in 7.57s`, and `12 passed, 3 skipped in 4.06s`.
  - Coverage report passed the repository threshold with `TOTAL 98%` against `--fail-under=97`.
- Consequence:
  - WTBD-001 through WTBD-004 closure is now backed by the local PR-grade gate, not only targeted
    or feature-lane checks.
- Documentation:
  - No wiki change is required because this is validation evidence for internal WTBD closure, not a
    public API, feature, or operator workflow change.
- Follow-Up:
  - Resolve the existing published GitHub wiki drift during PR/mainline closure or wiki publication
    workflow; the repo-local authored wiki source was not changed by this validation slice.

## LA-REV-151

- Scope: Integration capability dependency diagnostics
- Pattern: observability gap / operational contract hardening
- Status: Hardened
- Finding Class: observability gap
- Summary: The capability API exposed dependency `configured` and `operational_ready` booleans, but
  it did not explain the evidence basis behind readiness. That was too weak for banking-grade
  operational diagnostics because a non-production configuration-only posture, missing
  configuration, successful runtime probe, and failed runtime probe all require different operator
  and demo-readiness actions.
- Evidence:
  - `src/integrations/base.py` now records bounded dependency readiness evidence:
    `runtime_probe_enabled`, `readiness_basis`, and `degraded_reason`.
  - `src/api/capabilities/models.py` and `src/api/capabilities/readiness.py` publish that evidence
    through `GET /platform/capabilities` without exposing dependency base URLs.
  - `tests/unit/advisory/api/test_integration_dependency_base.py`,
    `tests/unit/advisory/api/test_integrations_base.py`, and
    `tests/unit/advisory/api/test_api_integration_capabilities.py` prove missing configuration,
    configuration-only readiness, successful production probes, failed production probes, and
    per-dependency degraded reasons.
  - Focused validation passed:
    `python -m pytest tests/unit/advisory/api/test_integration_dependency_base.py tests/unit/advisory/api/test_integrations_base.py tests/unit/advisory/api/test_api_integration_capabilities.py -q`
    with `21 passed`.
- Consequence:
  - Gateway, Workbench, operations, and sales-engineering users can now distinguish enabled
    advisory capabilities from runtime-proven readiness and can explain degraded states without
    leaking sensitive endpoint configuration.
- Documentation:
  - README and wiki API/supportability pages now describe dependency readiness evidence as part of
    the implementation-backed capability contract.
- Follow-Up:
  - If Gateway begins rendering dependency diagnostics directly, keep consumer wording tied to
    these bounded evidence fields instead of inventing local supportability copy.

## LA-REV-152

- Scope: Advisory execution ownership-boundary evidence
- Pattern: domain modeling / auditability hardening
- Status: Hardened
- Finding Class: auditability gap
- Summary: Execution handoff, execution-status, and delivery-summary behavior correctly kept
  downstream execution outside `lotus-advise`, but the event payloads and read projections did not
  consistently carry a structured boundary label. That left operators and client-demo users relying
  on surrounding documentation to distinguish advisory handoff/status posture from downstream
  execution system-of-record truth.
- Evidence:
  - `src/core/proposals/execution_boundary.py` now centralizes the execution ownership vocabulary:
    advisory role, downstream execution system of record, and ownership boundary.
  - Execution handoff events now preserve `execution_ownership` evidence in append-only workflow
    history.
  - Execution handoff responses, execution status responses, delivery execution summaries, and
    delivery/history explanations now expose the same bounded ownership evidence.
  - Focused validation passed:
    `python -m pytest tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py tests/unit/advisory/engine/test_engine_proposal_execution_status.py tests/unit/advisory/engine/test_engine_proposal_delivery_summary.py -q`
    with `17 passed`.
  - API contract validation passed:
    `python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py -q`
    with `5 passed`.
  - API lifecycle validation passed:
    `python -m pytest tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py -q`
    with `77 passed`.
  - Repo-native feature lane passed with `make check`: ruff check passed, ruff format check passed
    for 334 files, monetary-float guard passed, mypy passed for 175 source files, OpenAPI quality
    gate passed, lifecycle OpenAPI docs tests passed, no-alias guard passed, API vocabulary
    generated and validate-only passed, domain-data product declarations validated, and unit tests
    passed with `808 passed in 54.79s`.
- Consequence:
  - Advisory execution posture is easier to audit, support, and explain in pre-sales or client
    settings without overstating `lotus-advise` ownership. The service records handoff and status
    reconciliation; downstream providers remain the execution systems of record.
- Documentation:
  - README, repository context, and repo-local wiki pages now describe the implementation-backed
    execution ownership evidence.
- Follow-Up:
  - Before PR closure, run wiki drift check and Git diff whitespace hygiene because this slice
    changes repo-local wiki source and generated API vocabulary.

## LA-REV-153

- Scope: Proposal evidence immutability
- Pattern: auditability hardening / lineage correctness
- Status: Hardened
- Finding Class: correctness risk
- Summary: Risk-lens extraction, proposal evidence-bundle assembly, version record construction,
  and version-detail projection preserved the right data but relied on shallow copies in several
  places. Nested risk, context, artifact, and replay-lineage objects could be mutated by later
  caller changes after evidence assembly, weakening the immutability expectation behind proposal
  versions and replay evidence.
- Evidence:
  - `src/core/advisory/risk_lens.py` now deep-copies upstream risk-lens evidence after validating
    source-service provenance.
  - `src/core/proposals/evidence.py` now deep-copies context-resolution and replay-lineage payloads
    before storing them in the evidence bundle.
  - `src/core/proposals/versions.py` now deep-copies artifact and evidence-bundle JSON into the
    persisted version record.
  - `src/core/proposals/projections.py` now deep-copies version result, artifact, evidence, and
    gate-decision JSON before building the API response DTO.
  - Focused validation passed:
    `python -m pytest tests/unit/advisory/engine/test_engine_risk_lens.py tests/unit/advisory/engine/test_engine_proposal_evidence.py tests/unit/advisory/engine/test_engine_proposal_versions.py tests/unit/advisory/engine/test_engine_proposal_projections.py -q`
    with `23 passed`.
  - Focused ruff check and format check passed for the changed modules and tests.
  - Repo-native feature lane passed with `make check`: ruff check passed, ruff format check passed
    for 334 files, monetary-float guard passed, mypy passed for 175 source files, OpenAPI quality
    gate passed, lifecycle OpenAPI docs tests passed, no-alias guard passed, API vocabulary
    generated and validate-only passed, domain-data product declarations validated, and unit tests
    passed with `810 passed in 54.61s`.
- Consequence:
  - Proposal versions and replay-facing evidence are better aligned with bank-grade lineage
    expectations: once evidence is assembled or projected, nested caller mutations cannot silently
    alter the captured advisory proof.
- Documentation:
  - No wiki change is required because this is internal evidence-integrity hardening, not a new
    public workflow, operator runbook, or capability claim.
- Follow-Up:
  - Include this evidence-integrity slice in the next PR merge gate; no API vocabulary semantic
    change is expected from this internal copying hardening.

## LA-REV-154

- Scope: PR dependency freshness gate
- Pattern: CI health / dependency governance
- Status: Hardened
- Finding Class: validation failure
- Summary: PR #120 initially failed the PR Merge Gate lint/typecheck governance job because the
  strict dependency freshness check detected `ruff 0.15.13 -> 0.15.14` after local feature-lane
  validation had passed.
- Evidence:
  - `requirements.txt` and `requirements-dev.txt` now pin `ruff==0.15.14`.
  - Installed and confirmed local `python -m ruff --version` reports `ruff 0.15.14`.
  - `make check-deps-strict` passed with `Known vulnerabilities: 0` and `Outdated packages
    (direct scope): 0`.
  - Reran `make check`: ruff check passed, ruff format check passed for 334 files,
    monetary-float guard passed, mypy passed for 175 source files, OpenAPI quality gate passed,
    lifecycle OpenAPI docs tests passed, no-alias guard passed, API vocabulary generated and
    validate-only passed, domain-data product declarations validated, and unit tests passed with
    `810 passed in 53.74s`.
- Consequence:
  - The branch is aligned with the same strict dependency-freshness posture enforced by the PR Merge
    Gate, keeping CI health controlled instead of bypassing the gate.
- Documentation:
  - No wiki change is required because this is dependency-governance maintenance, not a public
    capability or operator workflow change.
- Follow-Up:
  - Continue treating strict dependency freshness failures as fix-forward dependency hygiene rather
    than suppressing the gate.

## LA-REV-155

- Scope: Workflow audit projection immutability
- Pattern: auditability hardening / response-boundary correctness
- Status: Hardened
- Finding Class: correctness risk
- Summary: Workflow event reasons, approval details, and asynchronous operation result/error
  payloads were projected directly from mutable persistence-record JSON. That left audit and
  lineage-facing response DTOs relying on downstream model behavior instead of an explicit
  projection-boundary copy, which is too weak for banking-grade audit evidence.
- Evidence:
  - `src/core/proposals/projections.py` now deep-copies workflow event reason payloads, approval
    details, asynchronous result payloads, and asynchronous error payloads before constructing
    response DTOs.
  - `tests/unit/advisory/engine/test_engine_proposal_projections.py` now proves workflow event,
    approval, and asynchronous result projections stay isolated from later nested record mutation.
  - Focused validation passed:
    `python -m pytest tests/unit/advisory/engine/test_engine_proposal_projections.py -q`
    with `13 passed`.
  - Focused ruff check passed for the changed module and projection tests.
- Consequence:
  - Advisory workflow and async-operation read models now preserve append-only audit semantics at
    the response boundary: once a response projection is built, nested mutation of persistence
    records cannot silently alter the already projected audit or lineage payload.
- Documentation:
  - No wiki change is required because this is internal audit-projection hardening, not a public
    workflow, operator runbook, or capability-contract change.
- Follow-Up:
  - Include this response-boundary immutability slice in the next PR merge gate; no OpenAPI
    vocabulary semantic change is expected from this internal copying hardening.

## LA-REV-156

- Scope: Postgres write-return snapshot isolation
- Pattern: persistence boundary hardening / auditability correctness
- Status: Hardened
- Finding Class: correctness risk
- Summary: The Postgres proposal repository persisted async operations and workflow transitions
  correctly, but two write-return paths returned caller-owned mutable model instances. A caller
  could mutate nested payload, reason, approval, or proposal state after persistence and silently
  alter the object returned as repository evidence, even though the database row remained stable.
- Evidence:
  - `src/infrastructure/proposals/postgres.py` now deep-copies the non-idempotent async operation
    write result and workflow transition result before returning them to callers.
  - `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` now proves
    non-idempotent async operation write results and transition results remain isolated from later
    caller mutation while persisted reads remain stable.
- Consequence:
  - Postgres-backed advisory write paths now behave like persistence snapshots instead of passing
    mutable caller references across repository boundaries, strengthening audit and lineage
    semantics for bank-grade advisory workflows.
- Documentation:
  - No wiki change is required because this is internal persistence-boundary hardening, not a
    public workflow, operator runbook, or API capability change.
- Follow-Up:
  - Include the focused Postgres repository regression tests and repo-native feature lane in the
    PR evidence before merge.

## LA-REV-157

- Scope: Advisory event-builder audit payload isolation
- Pattern: auditability hardening / event-construction correctness
- Status: Hardened
- Finding Class: correctness risk
- Summary: Lifecycle, approval, execution-handoff, and execution-update event builders preserved
  request-supplied audit payloads with shallow dictionary copies. Nested reason, approval,
  execution notes, or execution details could therefore be mutated by a caller after event
  construction and alter the in-memory event before persistence or projection.
- Evidence:
  - `src/core/proposals/lifecycle_events.py` now deep-copies state-transition reasons and approval
    details before building workflow events and approval records.
  - `src/core/proposals/execution_handoff.py` now deep-copies execution handoff notes before
    embedding them in the append-only execution-requested event.
  - `src/core/proposals/execution_update.py` now deep-copies downstream execution details before
    embedding them in execution update events.
  - `tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py`,
    `tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py`, and
    `tests/unit/advisory/engine/test_engine_proposal_execution_update.py` now prove nested audit
    payloads remain isolated from later request mutation.
  - Focused validation passed:
    `python -m pytest tests/unit/advisory/engine/test_engine_proposal_lifecycle_events.py tests/unit/advisory/engine/test_engine_proposal_execution_handoff.py tests/unit/advisory/engine/test_engine_proposal_execution_update.py -q`
    with `44 passed`.
- Consequence:
  - Advisory lifecycle and execution events now behave like stable audit facts from construction
    onward, improving lineage integrity before repository persistence and response projection.
- Documentation:
  - No wiki change is required because this is internal audit-event construction hardening, not a
    public API, operator runbook, or capability-contract change.
- Follow-Up:
  - Include this event-builder immutability slice in the next PR merge gate; no OpenAPI vocabulary
    semantic change is expected.

## LA-REV-158

- Scope: Postgres proposal list pagination
- Pattern: hot-path DB query shape / pagination hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The Postgres proposal listing path applied portfolio, lifecycle state, advisor, date,
  cursor, and page-size semantics correctly, but fetched every filtered proposal row and built every
  `ProposalRecord` before slicing in application memory. That creates unbounded transfer and object
  construction cost for bank-scale advisory books with large proposal histories.
- Evidence:
  - `src/infrastructure/proposals/postgres.py` now applies keyset pagination in SQL using
    `(created_at, proposal_id)` and fetches only `limit + 1` rows to determine `next_cursor`.
  - Cursor handling now validates the cursor against the same filtered result set, preserving the
    previous empty-page behavior for missing or mismatched cursors without scanning all rows.
  - `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` now proves DB-side
    `LIMIT %s`, keyset cursor SQL shape, bounded `limit + 1` fetch behavior, and mismatched-filter
    cursor rejection.
- Consequence:
  - Proposal history reads are now bounded by page size rather than total matching history, reducing
    latency, database transfer, and service memory pressure for advisor and operations workflows.
- Documentation:
  - No wiki change is required because this is internal repository query-shape hardening with no
    public API, OpenAPI, operator workflow, or capability-contract change.
- Follow-Up:
  - Include the focused Postgres repository regression tests and repo-native feature lane in the PR
    evidence before merge.

## LA-REV-159

- Scope: Postgres proposal list index support
- Pattern: hot-path DB query shape / migration hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The proposal list repository path now uses SQL keyset pagination, but the schema did
  not yet include supporting proposal-record indexes for ordered keyset scans and common filtered
  advisor-book access. Without those indexes, larger bank datasets could still degrade into costly
  sorts or broad scans even though row transfer is page bounded.
- Evidence:
  - `src/infrastructure/postgres_migrations/proposals/0006_proposal_list_keyset_indexes.sql` now
    adds `idx_proposal_records_list_created` for unfiltered keyset ordering and
    `idx_proposal_records_list_portfolio_state_advisor` for common portfolio/state/advisor filtered
    advisory proposal history reads.
  - `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` now proves repository
    initialization applies both proposal-list indexes and records the `proposals:0006` migration.
- Consequence:
  - The bounded proposal list read path has schema-level support for predictable latency as
    proposal history grows, reducing operational risk for advisor workbench, audit, and operations
    list screens.
- Documentation:
  - No wiki change is required because this is internal Postgres schema-performance hardening with
    no public API, OpenAPI, operator workflow, or capability-contract change.
- Follow-Up:
  - Include repository migration smoke, focused repository tests, and repo-native feature-lane
    validation in the PR evidence before merge.

## LA-REV-160

- Scope: Async recovery startup batching
- Pattern: async orchestration / startup reliability hardening
- Status: Hardened
- Finding Class: query/performance risk
- Summary: FastAPI startup recovery invoked `recover_async_operations()` without a batch bound,
  causing the service to load and process every pending or expired async operation before readiness.
  That is functionally correct for small queues, but bank-scale backlogs can delay process startup,
  readiness, and deployment recovery.
- Evidence:
  - `ProposalRepository.list_recoverable_operations` now accepts an optional `limit`.
  - `InMemoryProposalRepository` and `PostgresProposalRepository` now apply the recoverable-operation
    limit; the Postgres path pushes the bound down to SQL with `LIMIT %s`.
  - `ProposalWorkflowService.recover_async_operations` now uses a bounded default recovery batch
    while retaining an override for tests and controlled maintenance runs.
  - Focused tests now prove read-model batch limiting, Postgres SQL limit behavior, zero-limit
    handling, and service-level max-operation recovery behavior.
- Consequence:
  - Advisory startup recovery remains deterministic and bounded under async backlog, reducing
    readiness risk while preserving repeatable recovery across subsequent startup or operator
    recovery passes.
- Documentation:
  - No wiki change is required because this is internal startup/recovery hardening with no public
    API, OpenAPI, operator workflow, or capability-contract change.
- Follow-Up:
  - Include focused async recovery tests and repo-native feature-lane validation in the PR evidence
    before merge.

## LA-REV-161

- Scope: Async exhausted-attempt guard
- Pattern: async orchestration / retry correctness hardening
- Status: Hardened
- Finding Class: correctness risk
- Summary: Non-terminal async operations whose `attempt_count` had already reached `max_attempts`
  could still enter `run_async_operation_until_terminal`, start another attempt, and invoke the
  executor. That could exceed the configured retry budget after restart or operator recovery,
  weakening bounded retry semantics.
- Evidence:
  - `src/core/proposals/async_operations.py` now exposes `has_exhausted_async_attempts` as an
    explicit domain predicate for retry-budget exhaustion.
  - `src/core/proposals/async_operation_runner.py` now fails exhausted non-terminal operations with
    `PROPOSAL_ASYNC_ATTEMPTS_EXHAUSTED` before leasing or invoking the executor.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operations.py` proves the retry-budget
    boundary.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operation_runner.py` proves exhausted
    operations fail without executor invocation or extra attempt-count mutation.
- Consequence:
  - Advisory async execution now enforces configured retry budgets consistently across direct
    execution, startup recovery, and operator recovery paths.
- Documentation:
  - No wiki change is required because this is internal retry correctness hardening with no public
    API, OpenAPI, operator workflow, or capability-contract change.
- Follow-Up:
  - Include focused async runner tests and repo-native feature-lane validation in the PR evidence
    before merge.

## LA-REV-162

- Scope: Lotus Risk enrichment retry policy
- Pattern: upstream integration resilience / bounded retry hardening
- Status: Hardened
- Finding Class: operational reliability risk
- Summary: The Lotus Risk enrichment client had timeout and transient retry handling, but retry
  attempts were fully environment-controlled and retry backoff was fixed in code. A misconfigured
  `LOTUS_RISK_RETRY_ATTEMPTS` value could therefore create excessive advisory latency, while
  operators had no documented knob to tune retry spacing for the risk-lens dependency.
- Evidence:
  - `src/integrations/lotus_risk/enrichment.py` now caps Lotus Risk retry attempts at `5`, exposes
    `LOTUS_RISK_RETRY_BACKOFF_SECONDS`, caps backoff at `2.0` seconds, and computes retry delay
    through a dedicated policy helper.
  - `tests/unit/advisory/api/test_lotus_risk_enrichment_client.py` now proves bounded retry
    attempts, configurable backoff, backoff capping, and no retry for non-retryable `4xx` failures.
  - `README.md`, `wiki/Getting-Started.md`, `wiki/Integrations.md`, and `wiki/Troubleshooting.md`
    now document the Lotus Risk timeout and bounded retry operator controls.
- Consequence:
  - Risk-lens enrichment has explicit, documented latency bounds under upstream failures, improving
    predictability for advisor workflows, production operations, and client-demo reliability.
- Documentation:
  - Repo-local wiki source was updated because operator-facing integration configuration changed.
- Follow-Up:
  - Include focused Lotus Risk client tests, repo-native `make check`, and repo wiki sync check in
    the PR evidence before merge.

## LA-REV-163

- Scope: RFC-0025 pre-policy suitability/context boundary
- Pattern: modularity hardening / duplicate logic cleanup
- Status: Hardened
- Finding Class: modularity problem
- Summary: Before adding RFC-0025 enterprise policy-pack behavior, the existing suitability scanner
  and proposal decision summary still interpreted advisory-policy context availability through raw
  string checks, and the suitability scanner carried a duplicate empty baseline-pack definition.
- Evidence:
  - `src/core/advisory/policy_context.py` now owns policy-context status vocabulary and accessors
    for client, mandate, and jurisdiction availability.
  - `src/core/common/suitability.py` and `src/core/advisory/decision_summary.py` now consume those
    accessors instead of reinterpreting raw status strings locally.
  - The duplicate empty `_GLOBAL_PRIVATE_BANKING_BASELINE_PACK` scanner wiring was removed so the
    suitability scanner has a single baseline-pack definition.
  - `tests/unit/advisory/engine/test_engine_policy_context.py` proves source-context projection and
    conservative unavailable behavior for missing or unknown context.
  - `tests/unit/test_rfc0025_slice2_cleanup_contract.py` pins the non-claiming RFC/wiki evidence
    and prevents scanner/decision-summary policy-context string re-interpretation from returning.
- Consequence:
  - Future RFC-0025 policy-pack implementation can build dedicated catalog/evaluation/persistence
    modules without stretching the existing suitability scanner or duplicating context-readiness
    interpretation.
- Documentation:
  - RFC-0025 Slice 2 evidence and repo-local wiki source were updated as non-claiming cleanup;
    no runtime policy-pack support, client-ready policy claim, or `/platform/capabilities`
    promotion was introduced.
- Follow-Up:
  - Include focused policy-context/suitability/decision-summary tests, docs contract tests,
    repo-native `make check`, and repo wiki sync check in the PR evidence before merge.

## LA-REV-164

- Scope: RFC-0025 policy-evaluation data-product boundary
- Pattern: mesh posture / unsupported capability claim prevention
- Status: Hardened
- Finding Class: product-truth risk
- Summary: RFC-0025 required an `AdvisoryPolicyEvaluationRecord:v1` data-product boundary before
  policy runtime work, but adding that product without explicit blocked telemetry and
  non-promotion tests would risk either invisible mesh planning truth or premature support claims.
- Evidence:
  - `contracts/domain-data-products/lotus-advise-products.v1.json` now declares
    `AdvisoryPolicyEvaluationRecord:v1` as `proposed`, blocked, and route-less.
  - `contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json` records
    blocked trust telemetry with unknown freshness, blocked completeness, unknown quality, and
    non-materialized lineage.
  - `tests/unit/test_trust_telemetry.py` now generates a current platform domain-product catalog
    from repo-native declarations before validating trust telemetry, and it pins the policy
    product as proposed, blocked, and not capability-promoted.
  - `tests/unit/advisory/api/test_api_integration_capabilities.py` asserts
    `/platform/capabilities` does not advertise policy evaluation support before runtime
    implementation exists.
- Consequence:
  - Mesh governance can see the intended policy-evaluation product boundary while business and
    front-office consumers remain protected from unsupported policy-pack claims.
- Documentation:
  - RFC-0025 Slice 3 evidence, trust-telemetry README, RFC index, supported-feature wiki source,
    and RFC README were updated as non-claiming data-product posture.
- Follow-Up:
  - After this repo-native declaration reaches `main`, refresh `lotus-platform` generated
    domain-product catalog, dependency graph, certification report, and maturity artifacts so
    platform publication truth includes the proposed policy-evaluation product.

## LA-REV-165

- Scope: RFC-0025 policy source-readiness evidence
- Pattern: source-owner boundary hardening / duplicate readiness scaffolding cleanup
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Before policy-pack evaluation exists, proposal evidence needed a policy-specific source
  readiness manifest so later slices cannot default missing `lotus-core` or `lotus-risk` facts into
  suitable, eligible, best-interest, disclosure-ready, consent-ready, or client-ready outcomes.
- Evidence:
  - `src/core/proposals/policy_source_readiness.py` now builds
    `rfc0025.policy-source-readiness.v1` over captured proposal evidence.
  - `src/core/proposals/evidence.py` attaches `policy_source_readiness` beside
    `memo_source_readiness` whenever proposal evidence is materialized.
  - `src/core/proposals/source_readiness_common.py` centralizes readiness section, overall-posture,
    and source-authority helpers shared by memo and policy readiness.
  - `tests/unit/advisory/engine/test_engine_policy_source_readiness.py` proves READY,
    PENDING_REVIEW, and BLOCKED source-owner paths without policy-evaluation claims.
  - `tests/unit/advisory/engine/test_engine_proposal_evidence.py` proves proposal evidence carries
    the policy source-readiness contract.
- Consequence:
  - Future policy catalog and evaluation slices can consume a stable source-readiness manifest
    instead of reinterpreting raw proposal evidence or duplicating source methodology.
- Documentation:
  - RFC-0025 Slice 4 evidence, repo context, RFC index, supported-feature wiki source, and RFC
    README were updated as source-readiness-only posture.
- Follow-Up:
  - Slice 5 should introduce policy-pack catalog/schema/activation without bypassing
    `rfc0025.policy-source-readiness.v1` for missing-source posture.

## LA-REV-166

- Scope: RFC-0025 policy-pack catalog and activation lifecycle
- Pattern: capability-boundary hardening / source-controlled reference-pack foundation
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Policy-pack support needed a real catalog and activation boundary before any proposal
  evaluation work, otherwise later slices could blur reference-pack metadata, policy activation,
  and unsupported evaluation into one broad claim.
- Evidence:
  - `src/core/policy_packs/catalog.py` now owns the `rfc0025.policy-pack-catalog.v1` reference-pack
    catalog for `GLOBAL_PRIVATE_BANKING_BASELINE` and `SG_PRIVATE_BANKING_REFERENCE`.
  - `src/api/proposals/routes_policy_packs.py` exposes list, detail, validate, and activate routes
    with hash-backed activation, maker-checker enforcement where configured, idempotency conflict
    protection, and audit-event projection.
  - `src/api/capabilities/service.py` advertises `advisory.policy_pack_catalog` while preserving
    the absence of proposal policy-evaluation support.
  - `tests/unit/advisory/engine/test_engine_policy_pack_catalog.py` proves validation, invalid-pack
    diagnostics, idempotency, content-hash enforcement, maker-checker control, and activation
    immutability.
  - `tests/unit/advisory/api/test_api_advisory_policy_packs.py` proves the canonical catalog API
    routes and absence of proposal policy-evaluation routes.
- Consequence:
  - Slice 6 can implement applicability and rule evaluation against a stable catalog contract
    without inventing pack metadata or activation posture inside the evaluator.
- Documentation:
  - RFC-0025 Slice 5 evidence, repo context, RFC index, supported-feature wiki source, and RFC
    README were updated as catalog-and-activation-only support.
- Follow-Up:
  - Slice 6 should consume only activated policy-pack versions and keep every rule result tied to
    `rfc0025.policy-source-readiness.v1` source posture.

## LA-REV-167

- Scope: RFC-0025 policy applicability and internal rule-evaluation engine
- Pattern: source-backed evaluator / non-promoted product boundary
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Policy evaluation needed a domain engine that consumes active policy packs and source
  readiness without jumping directly to persisted records, certified APIs, review queues, or UI
  claims.
- Evidence:
  - `src/core/policy_packs/evaluation.py` implements `rfc0025.policy-evaluation-engine.v1` as an
    internal evaluator for active policy packs only.
  - `src/core/policy_packs/models.py` now carries typed applicability, rule result, and evaluation
    response models with explicit source refs, missing evidence, reason codes, and required actions.
  - `src/core/proposals/policy_source_readiness.py` now records internal evaluator availability
    while preserving no-persisted-API and client-ready blocked posture.
  - `tests/unit/advisory/engine/test_engine_policy_pack_evaluation.py` proves ready, blocked,
    pending-review, missing-source, degraded-source, jurisdiction, client-segment, mandate,
    product, complex-product, conflict, disclosure, consent, and best-interest paths.
- Consequence:
  - Slice 7 can persist immutable evaluation records from a stable internal evaluator instead of
    inventing rule posture inside persistence or API code.
- Documentation:
  - RFC-0025 Slice 6 evidence, repo context, RFC index, supported-feature wiki source, and RFC
    README were updated as internal-engine-only support.
- Follow-Up:
  - Slice 7 should persist evaluation records idempotently and preserve policy version, content
    hash, source refs, rule result hashes, replay metadata, and append-only audit posture.

## LA-REV-168

- Scope: RFC-0025 policy evaluation persistence, replay, idempotency, and audit
- Pattern: immutable evidence record / append-only policy event boundary
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Policy evaluation needed durable finalized records with replayable hash evidence before
  certified APIs or front-office policy surfaces could truthfully expose the capability.
- Evidence:
  - `src/core/policy_packs/persistence.py` implements
    `rfc0025.policy-evaluation-persistence.v1` for finalized policy evaluation records,
    duplicate prevention, idempotent replay, append-only review/sign-off/report-archive events,
    and replay hash comparison.
  - `src/core/policy_packs/models.py` carries typed policy evaluation record, audit-event,
    persistence-result, and replay-response models.
  - `tests/unit/advisory/engine/test_engine_policy_pack_persistence.py` proves immutable
    hash-backed records, idempotency conflicts, duplicate request handling, append-only event
    posture, replay hash comparison, and disclosure/consent/approval dependency persistence.
  - `contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json` now narrows
    the blocked data-product reason to missing certified APIs, review queues, and product surfaces
    while recording Slice 7 internal persistence evidence.
- Consequence:
  - Slice 8 can expose certified policy APIs over an internal persistence boundary rather than
    combining route design with record immutability, replay, and audit concerns.
- Documentation:
  - RFC-0025 Slice 7 evidence, repo context, RFC index, supported-feature wiki source, trust
    telemetry README, and RFC README were updated as internal-persistence-only support.
- Follow-Up:
  - Slice 8 should expose certified policy evaluation APIs without bypassing the finalized-record
    store or promoting Gateway/Workbench/client-ready claims before their slices are complete.

## LA-REV-169

- Scope: RFC-0025 certified policy evaluation APIs and OpenAPI
- Pattern: thin route boundary over immutable policy evidence records
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Slice 8 needed to expose policy evaluation behavior without duplicating the Slice 6
  evaluator or mutating the Slice 7 finalized-record model.
- Evidence:
  - `src/api/proposals/routes_policy_evaluations.py` exposes create/replay, immutable read, replay,
    review queue, append-only event, lineage, and sign-off source-package endpoints.
  - `src/core/policy_packs/persistence.py` adds list, lineage, review-queue, and sign-off package
    projections over the existing `PolicyEvaluationRecordStore`.
  - `src/core/policy_packs/models.py` adds request and response contracts with field-level OpenAPI
    documentation.
  - `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py` proves idempotent
    finalization, conflict handling, replay hash comparison, event capture, lineage, review queue,
    and sign-off source-package behavior.
  - `tests/unit/test_rfc0025_slice8_policy_evaluation_api_contract.py` protects RFC/wiki/data
    product/trust telemetry indexing and prevents `/platform/capabilities` promotion.
- Consequence:
  - Advise now has a certified API source for policy evaluation records, but Gateway/Workbench
    policy support, report/render/archive realization, active data-product promotion, and
    client-ready publication remain blocked.
- Documentation:
  - RFC-0025 Slice 8 evidence, repo context, RFC index, supported-feature wiki source, data-product
    declaration, trust telemetry, and RFC README were updated.
- Follow-Up:
  - Slice 9 should attach approval, consent, disclosure, conflict, SLA, and sign-off workflow
    behavior to this API surface without turning source-package reads into client-ready claims.

## LA-REV-170

- Scope: RFC-0025 policy workflow and sign-off decision boundary
- Pattern: workflow projection over immutable policy evaluation records
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Slice 9 needed approval, disclosure, consent, conflict, SLA, and maker-checker posture
  without letting UI, report, or client-ready layers infer positive best-interest language.
- Evidence:
  - `src/core/policy_packs/workflow.py` implements
    `rfc0025.policy-sign-off-workflow.v1` over finalized policy evaluation records and append-only
    events.
  - `src/api/proposals/routes_policy_evaluations.py` exposes the workflow projection and sign-off
    decision command as thin API routes.
  - `src/core/policy_packs/models.py` carries the workflow, requirement, and sign-off decision
    contracts with OpenAPI field documentation.
  - `tests/unit/advisory/engine/test_engine_policy_pack_workflow.py` proves open requirement,
    maker-checker, conflict, and successful sign-off paths.
  - `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py` proves route-level workflow
    projection and sign-off requirement enforcement.
  - `tests/unit/test_rfc0025_slice9_policy_workflow_contract.py` protects RFC/wiki/data-product/
    trust-telemetry indexing and prevents `/platform/capabilities` promotion.
- Consequence:
  - Advise can now expose source-owned policy workflow posture and sign-off decisions, while
    Gateway/Workbench policy support, report/render/archive realization, active data-product
    promotion, and client-ready publication remain blocked.
- Documentation:
  - RFC-0025 Slice 9 evidence, repo context, RFC index, supported-feature wiki source,
    data-product declaration, trust telemetry, and RFC README were updated.
- Follow-Up:
  - Slice 10 should materialize typed policy/sign-off/disclosure packages through report, render,
    and archive only where source package, review posture, and lineage refs are implementation
    backed.

## LA-REV-171

- Scope: RFC-0025 policy report-package realization
- Pattern: signed-off source package handoff with lineage-recorded downstream refs
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Slice 10 needed report/render/archive materialization without treating a report job as
  Gateway/Workbench support, active data-product promotion, or client-ready publication.
- Evidence:
  - `src/core/policy_packs/reporting.py` implements
    `rfc0025.policy-report-package-realization.v1` over finalized policy evaluation records,
    workflow sign-off posture, idempotency keys, and append-only lineage events.
  - `src/integrations/lotus_report/adapter.py` submits `ADVISORY_POLICY_SIGN_OFF_PACKAGE` payloads
    to the existing portfolio-review report job contract and returns report/render/archive refs.
  - `src/api/proposals/routes_policy_evaluations.py` exposes
    `POST /advisory/policy-evaluations/{evaluation_id}/report-packages` as a thin API route.
  - `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py` proves unsigned blocking,
    signed-off handoff, lineage refs, idempotent replay, and client-ready release rejection.
  - `tests/unit/advisory/api/test_lotus_report_adapter.py` proves the downstream typed package
    payload and returned render/archive refs.
  - `tests/unit/test_rfc0025_slice10_policy_report_package_contract.py` protects RFC/wiki/
    data-product/trust-telemetry indexing and prevents `/platform/capabilities` promotion.
- Consequence:
  - Advise can now materialize signed-off policy evidence through lotus-report and retain returned
    report/render/archive refs in policy lineage. Gateway/Workbench policy support, live proof,
    active data-product promotion, AI policy-evidence consumption, and client-ready publication
    remain blocked.
- Documentation:
  - RFC-0025 Slice 10 evidence, repo context, RFC index, supported-feature wiki source,
    data-product declaration, trust telemetry, and RFC README were updated.
- Follow-Up:
  - Slice 11 should consume policy outcomes in AI workflow packs only as bounded evidence, without
    allowing AI to alter policy status, approvals, disclosures, consent posture, or client-ready
    claims.

## LA-REV-172

- Scope: RFC-0025 AI policy-evidence boundary
- Pattern: redacted evidence packet with non-authoritative AI lineage
- Status: Hardened
- Finding Class: product-truth risk
- Summary: Slice 11 needed AI-assisted policy explanation without allowing AI to approve, waive,
  mutate, certify, publish, or infer missing policy evidence.
- Evidence:
  - `src/core/policy_packs/ai.py` implements `rfc0025.policy-ai-evidence-boundary.v1` with
    source-hash validation, action allowlisting, forbidden-action rejection, redaction profile,
    idempotency, deterministic unavailable posture, and append-only AI lineage events.
  - `src/integrations/lotus_ai/policy_evidence.py` submits redacted structured context to
    `policy_evidence_summary.pack@v1` through the governed workflow-pack execution route.
  - `src/api/proposals/routes_policy_evaluations.py` exposes
    `POST /advisory/policy-evaluations/{evaluation_id}/ai-evidence`.
  - `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py` proves bounded AI lineage,
    forbidden-action rejection, stale-hash rejection, deterministic unavailable posture, and no
    policy-status mutation.
  - `tests/unit/advisory/api/test_lotus_ai_policy_evidence.py` proves the adapter sends redacted
    policy evidence without raw prompts or instructions and handles unavailable posture.
  - `tests/unit/test_rfc0025_slice11_policy_ai_evidence_contract.py` protects RFC/wiki/
    data-product/trust-telemetry indexing and prevents `/platform/capabilities` promotion.
- Consequence:
  - Advise can now send bounded policy evidence to lotus-ai for human-reviewed explanation.
    Gateway/Workbench policy support, live proof, active data-product promotion, and client-ready
    publication remain blocked.
- Documentation:
  - RFC-0025 Slice 11 evidence, repo context, RFC index, supported-feature wiki source,
    data-product declaration, trust telemetry, and RFC README were updated.
- Follow-Up:
  - Slice 12 should route policy evaluation, review queue, maker-checker, sign-off, report package,
    and AI evidence posture through Gateway and Workbench without local UI inference.

## LA-REV-173

- Scope: RFC-0027 advisory copilot proposal-version run history
- Pattern: query/performance risk / API contract hardening / test gap
- Status: Hardened
- Finding Class: query/performance risk
- Summary: The RFC-0027 proposal-version copilot run list exposed `next_cursor` but returned every
  matching run and always set the cursor to `null`; repeated canonical validation could therefore
  turn a proof-history read into an unbounded repository operation.
- Evidence:
  - `src/core/advisory_copilot/pagination.py` now owns opaque keyset cursor encode/decode logic.
  - `src/infrastructure/advisory_copilot/in_memory.py` and
    `src/infrastructure/advisory_copilot/postgres.py` now return newest-first bounded pages and
    next cursors from the repository boundary.
  - `src/infrastructure/postgres_migrations/advisory_copilot/0003_copilot_run_version_pagination_indexes.sql`
    adds proposal-version expression indexes for the production run-history path.
  - `src/api/proposals/routes_advisory_copilot.py` documents `limit` and `cursor`, bounds page size,
    and maps invalid cursors to validation errors.
  - `tests/unit/advisory/engine/test_advisory_copilot_persistence.py` and
    `tests/unit/advisory/api/test_api_advisory_copilot.py` prove bounded pagination, no duplicate
    pages, and invalid cursor rejection.
  - `tests/unit/shared/dependencies/test_production_cutover_contract.py` now pins migration `0003`
    as part of the cutover contract.
- Consequence:
  - Gateway, Workbench, and canonical validation can consume RFC-0027 copilot run history
    repeatably as proof runs accumulate, without rebuilding lineage in the UI or depending on
    unbounded read behavior.
- Documentation:
  - RFC-0027 Slice 8, Slice 9, the main RFC, and API vocabulary inventory were updated to reflect
    bounded run-history pagination.
- Follow-Up:
  - Continue reviewing the copilot route orchestration boundary; if it grows further, move
    proposal-version packet construction and AI run orchestration behind a dedicated application
    service rather than adding more controller-layer workflow logic.

## LA-REV-174

- Scope: RFC-0027 advisory copilot API orchestration boundary
- Pattern: controller business-logic cleanup / service-boundary hardening
- Status: Hardened
- Finding Class: modularity problem
- Summary: The RFC-0027 FastAPI route module still owned proposal-version packet assembly,
  policy-evaluation lookup, lotus-ai draft execution, run persistence, supportability construction,
  and run-history projection. That made the controller more than HTTP wiring and increased the
  risk of future Gateway/Workbench-facing behavior being patched in the route layer.
- Evidence:
  - `src/core/advisory_copilot/application.py` now owns the application-service boundary for
    evidence-packet creation, proposal-version evidence projection, evidence-packet reads,
    governed copilot action execution, run reads, review actions, supportability projection, and
    proposal-version run-history pages.
  - `src/api/proposals/routes_advisory_copilot.py` now stays focused on FastAPI routing,
    dependency assembly, request headers/path/query parameters, and product-safe HTTP error
    mapping.
  - The lotus-ai draft generator and policy-evaluation loader are injected into the application
    service instead of being called directly from route handlers.
  - `tests/unit/advisory/api/test_api_advisory_copilot.py` proves the public behavior still works
    after the extraction and adds coverage that supportability remains a static contract read that
    does not initialize copilot persistence.
- Consequence:
  - RFC-0027 copilot behavior is easier to test and extend without adding more business workflow
    logic to controllers, and supportability reads stay operationally safe when persistence is not
    configured.
- Documentation:
  - This ledger entry records the boundary hardening; public API and wiki truth are unchanged.
- Follow-Up:
  - If further orchestration growth appears, add focused unit tests for
    `AdvisoryCopilotApplicationService` rather than expanding controller tests.

## LA-REV-175

- Scope: RFC-0027 advisory copilot application-service idempotency boundary
- Pattern: idempotency / performance / test-quality hardening
- Status: Hardened
- Finding Class: reliability gap
- Summary: Direct application-service review found that idempotent copilot action replays were
  only resolved during run persistence, after the draft generator had already been invoked. That
  made retried advisor actions pay unnecessary AI-workflow cost and weakened the guarantee that
  replay handling is cheap and side-effect minimal.
- Evidence:
  - `src/core/advisory_copilot/application.py` now checks existing run idempotency before invoking
    the draft generator and returns the previously persisted run for matching replay requests.
  - `src/core/advisory_copilot/service.py` exposes the governed request-hash builder so the
    application service and persistence service use the same canonical replay fingerprint.
  - `tests/unit/advisory/engine/test_advisory_copilot_application.py` proves proposal-version
    evidence projection through injected loaders, raw-instruction redaction, conflict rejection,
    and replay short-circuiting without a second draft-generation call.
  - `tests/unit/advisory/api/test_api_advisory_copilot.py` continues to prove the public HTTP
    contract over the refactored service boundary.
- Consequence:
  - RFC-0027 copilot retries are now repeatable, cheaper, and safer: identical replays return the
    original run before AI orchestration, while changed payloads with the same idempotency key
    still fail with a contract-specific conflict.
- Documentation:
  - This ledger entry records the implementation-backed hardening; public API and wiki truth are
    unchanged.
- Follow-Up:
  - Keep future copilot orchestration behavior covered at the application-service boundary before
    adding or expanding controller-level assertions.

## LA-REV-176

- Scope: RFC-0024 through RFC-0027 proposal-route validation response constants
- Pattern: API compatibility / warning-free validation / regression guard
- Status: Hardened
- Finding Class: API quality gap
- Summary: RFC-focused validation exposed repeated `HTTP_422_UNPROCESSABLE_ENTITY` deprecation
  warnings from proposal-route OpenAPI response metadata and copilot validation error mapping. The
  repository already had a compatibility constant for modern FastAPI/Starlette versions, but the
  route modules bypassed it.
- Evidence:
  - `src/api/proposals/routes_lifecycle.py`, `routes_memo.py`,
    `routes_policy_evaluations.py`, `routes_policy_packs.py`, `routes_advisor_cockpit.py`, and
    `routes_advisory_copilot.py` now use `src.api.http_status.HTTP_422_UNPROCESSABLE`.
  - `tests/unit/advisory/api/test_http_status_compatibility.py` prevents proposal route modules
    from reintroducing the deprecated FastAPI constant outside the compatibility shim.
  - Targeted advisor-cockpit and advisory-copilot API tests pass after the route cleanup.
- Consequence:
  - RFC-0024 through RFC-0027 proposal APIs keep the same HTTP 422 behavior while avoiding
    framework-version deprecation noise in validation, OpenAPI generation, and CI logs.
- Documentation:
  - Public API semantics are unchanged; this ledger entry records the implementation-backed API
    compatibility hardening.
- Follow-Up:
  - Keep future route modules on shared status/error helpers rather than importing deprecated
    framework aliases directly.

## LA-REV-177

- Scope: RFC-0026 advisor cockpit acknowledgement idempotency
- Pattern: idempotency / correlation-id boundary hardening
- Status: Hardened
- Finding Class: reliability gap
- Summary: Advisor cockpit acknowledgement replay identity included `correlation_id` in the
  canonical request hash. A normal client retry with the same idempotency key but a new
  correlation id could therefore be rejected as a business conflict even though the acknowledged
  action, version, actor, and acknowledgement note were unchanged.
- Evidence:
  - `src/core/advisor_cockpit/service.py` now excludes observability metadata from the
    acknowledgement request hash while still persisting the original correlation id in the
    acknowledgement audit record.
  - `tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py` proves a same-business
    acknowledgement with a changed retry correlation id replays, preserves the original audit
    correlation id, and still rejects changed business payloads under the same idempotency key.
- Consequence:
  - RFC-0026 cockpit acknowledgements now have a cleaner idempotency boundary: correlation ids
    remain operational lineage, not part of the replay fingerprint, while real payload changes
    still fail closed.
- Documentation:
  - Public API semantics are unchanged; this ledger entry records the implementation-backed
    reliability hardening.
- Follow-Up:
  - Keep future idempotency hashes focused on business request identity and store trace/correlation
    fields as audit lineage unless a contract explicitly requires them in the replay fingerprint.

## LA-REV-178

- Scope: RFC-0026 through RFC-0028 supported-features ledger closure truth
- Pattern: documentation product truth / RFC closure governance
- Status: Hardened
- Finding Class: documentation quality gap
- Summary: RFC-0026 and RFC-0028 were marked implemented, and RFC-0027 carried implemented closure
  evidence, but the RFC-local supported-features ledgers still used pre-implementation
  `Proposed`/`Gated` wording for capabilities that had already passed implementation proof. That
  made the RFCs harder to use as product-truth artifacts for business, sales/pre-sales,
  operations, and engineering audiences.
- Evidence:
  - `docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md`,
    `docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md`, and
    `docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md` now use current support
    posture plus closure-evidence/boundary wording in their supported-features ledgers.
  - `tests/unit/test_rfc0026_implementation_readiness_contract.py`,
    `tests/unit/test_rfc0027_gold_standard_tightening_contract.py`, and
    `tests/unit/test_rfc0028_gold_standard_tightening_contract.py` prevent those ledgers from
    drifting back to stale `Proposed` rows for implemented capabilities.
- Consequence:
  - RFC-local product truth now matches README/wiki/supported-features posture: implemented
    capabilities are described as supported with explicit blocked boundaries for client-ready
    publication, external client communication, bank-specific attestations, and OMS execution.
- Documentation:
  - No wiki source change is required in this slice because `wiki/Supported-Features.md` and
    `wiki/RFC-Index.md` already carry the implemented RFC-0026 through RFC-0028 closure posture;
    this slice corrects the RFC-local ledgers and pins them with documentation-contract tests.
- Follow-Up:
  - When an implementation RFC reaches final closure, update the RFC-local supported-features
    ledger from promotion criteria to current support posture in the same closure PR.

## LA-REV-179

- Scope: RFC-0023/RFC-0024 advisor narrative and memo runtime copy
- Pattern: stale implementation-state language / business-facing API quality
- Status: Hardened
- Finding Class: documentation and API quality gap
- Summary: Advisor narrative and memo evidence still emitted or documented pre-closure wording such
  as policy packs "not implemented," narrative review "deferred," report/archive readiness blocked
  until "later slices," and memo conflict review blocked until policy packs were implemented. Those
  statements no longer matched the implemented RFC-0023 through RFC-0025 and RFC-0028 posture:
  advisor-review narrative, policy evaluation, advisor-use memo evidence, and report-package
  boundaries are implemented, while client-ready publication remains explicitly blocked.
- Evidence:
  - `src/core/advisory/narrative.py` now explains the actual client-ready blockers: completed
    mandate-policy approval/sign-off and explicit client-ready release authority are not
    supported, rather than claiming policy packs or advisor review are absent.
  - `src/core/advisory/narrative_policy.py` now returns
    `CLIENT_READY_NARRATIVE_RELEASE_NOT_SUPPORTED` for client-ready narrative requests.
  - `src/core/proposals/memo_policy_enrichment.py` and
    `src/core/proposals/memo_builder.py` now use current advisor-use memo/report-package language
    and review-required reason codes instead of stale implementation-state wording.
  - `src/core/advisory/narrative_models.py`, `src/core/advisory/artifact_models.py`, and
    `src/core/proposals/response_models.py` remove stale slice-number descriptions from OpenAPI
    schema text.
  - `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`,
    `tests/unit/advisory/engine/test_engine_proposal_memo_builder.py`, and
    `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` pin the lower-level
    API, domain, and OpenAPI wording boundaries.
- Consequence:
  - Business-facing runtime evidence and Swagger descriptions now stay truthful for private-banking
    users: implemented advisor/internal capabilities are acknowledged, while client-ready
    narrative, document publication, external communication, and execution authority remain
    blocked.
- Documentation:
  - `docs/rfcs/RFC-0023-slice-6-narrative-policy-disclosure-and-guardrail-framework.md` now uses
    the current client-ready narrative release blocker code. No wiki source change is required
    because public wiki support posture already states client-ready narrative publication remains
    gated.
- Follow-Up:
  - Avoid embedding RFC slice numbers or transient implementation-state wording in runtime
    messages and OpenAPI descriptions once the capability has moved past that slice.

## LA-REV-180

- Scope: Advisory golden-fixture regeneration and integration package import boundaries
- Pattern: stale automation / eager package barrel imports
- Status: Hardened
- Finding Class: stale code and import-boundary reliability gap
- Summary: The root `update_goldens.py` helper still targeted the pre-RFC-0014 golden fixture
  shape, scanned `tests/golden_data`, imported the deprecated `src.core.engine` shim, and called
  the removed `run_simulation` API. Repairing that helper exposed a second standalone reliability
  issue: importing `src.core.advisory.artifact` from a normal Python process could fail through
  eager `lotus_ai` and `lotus_core` package-barrel imports even though the path passed under the
  existing pytest import order.
- Evidence:
  - `update_goldens.py` now uses the current `tests/unit/advisory/golden_data` directory,
    `ProposalSimulateRequest`, `run_proposal_simulation`, artifact generation for RFC-0014E
    fixtures, deterministic request identifiers, and a `--check` mode for CI-friendly drift
    detection.
  - `src/integrations/lotus_ai/__init__.py` and `src/integrations/lotus_core/__init__.py` now use
    lazy package exports so importing a focused integration submodule does not pull unrelated
    workspace, proposal, copilot, or stateful-context paths into a circular initialization chain.
  - `tests/unit/scripts/test_update_goldens.py` pins proposal and artifact fixture check mode,
    drift repair behavior, the deprecated-engine-import boundary, and standalone artifact-module
    importability.
  - Local proof includes `python update_goldens.py --check`; full gate evidence is recorded in the
    PR once this slice passes repository-native validation.
- Consequence:
  - Advisory golden fixture automation is repeatable again, and import reliability now matches the
    way production scripts, operators, and CI helpers execute modules outside pytest's import-order
    side effects.
- Documentation:
  - No wiki source change is required. This slice hardens internal developer automation and
    integration import boundaries without changing supported product behavior, operator workflow,
    or business-facing feature posture.
- Follow-Up:
  - Keep future script-level automation covered by direct command tests or subprocess import tests
    when the failure mode only appears outside pytest's normal module graph.

## LA-REV-181

- Scope: Wiki demo and commercial proof navigation
- Pattern: documentation product truth / demo-readiness usability
- Status: Hardened
- Finding Class: documentation quality gap
- Summary: The RFC-0028 implementation-backed proof path had strong source material in README,
  API-surface, operations, supported-features, RFC, and commercial docs, but the wiki lacked a
  focused navigation page for business users, sales/pre-sales, operations, demo leads, and
  engineers. That made it harder to prepare client demos and RFP material from one
  implementation-backed wiki entry point without reading every RFC section.
- Evidence:
  - `wiki/Demo-and-Commercial-Proof.md` now summarizes current supported posture, proof flow,
    business flow, operator checklist, audience-specific next reads, blocked claims, and
    implementation references for the RFC-0028 bank-demo proof journey.
  - `wiki/Home.md`, `wiki/_Sidebar.md`, and `wiki/Supported-Features.md` now link the new page from
    the product-surface/demo navigation path.
  - `tests/unit/test_wiki_demo_commercial_proof_contract.py` protects navigation, canonical
    scenario/portfolio/proof-marker references, proof API references, commercial material
    references, blocked-claim language, and Mermaid diagram presence.
- Consequence:
  - Business, operations, sales/pre-sales, and engineering audiences now have a concise,
    implementation-backed wiki entry point for demo and commercial proof without promoting
    client-ready publication, external communication, bank attestations, legal/regulatory advice,
    completed approval/sign-off, AI authority, or OMS execution claims.
- Documentation:
  - Repo-local wiki source changed. Run the governed wiki sync check before merge and publish the
    `lotus-advise` wiki after this branch lands on `main`.
- Follow-Up:
  - Keep future demo-oriented wiki additions as navigation and interpretation layers over
    implementation-backed proof artifacts; do not duplicate long-form RFC or commercial-guide
    content.

## LA-REV-182

- Scope: Advisory copilot run pagination cursor validation
- Pattern: API validation boundary / keyset pagination hardening
- Status: Hardened
- Finding Class: validation and error-handling gap
- Summary: The advisory copilot run cursor decoder accepted decoded payloads without confirming the
  payload shape, typed fields, or timezone-aware `created_at` value. A client-supplied cursor with a
  naive timestamp could reach repository keyset comparison against timezone-aware run records and
  risk a runtime failure instead of the governed `COPILOT_RUN_CURSOR_INVALID` API response.
- Evidence:
  - `src/core/advisory_copilot/pagination.py` now validates opaque cursor JSON shape, string
    fields, non-empty run identifiers, and timezone-aware timestamps before repository filtering.
  - `tests/unit/advisory/engine/test_advisory_copilot_pagination.py` covers round-trip encoding,
    non-UTC aware offsets, invalid payload shapes, naive timestamps, and stable descending keyset
    ordering.
  - `tests/unit/advisory/api/test_api_advisory_copilot.py` now proves the API returns HTTP 422 with
    `COPILOT_RUN_CURSOR_INVALID` for naive timestamp cursors, matching the existing malformed-cursor
    contract.
- Consequence:
  - Invalid client cursors are rejected at the domain pagination boundary before in-memory or
    Postgres repositories evaluate the keyset predicate, preserving predictable API behavior and
    avoiding infrastructure-layer runtime failures.
- Documentation:
  - No wiki source change is required. This slice hardens an existing opaque cursor validation
    boundary without changing supported product behavior, operator workflow, or business-facing
    feature posture.
- Follow-Up:
  - Keep future keyset pagination helpers covered by direct decoder tests and at least one API-level
    malformed-cursor contract test.

## LA-REV-183

- Scope: Advisory copilot application idempotency refresh path
- Pattern: idempotency correctness / retryable dependency recovery
- Status: Hardened
- Finding Class: correctness and duplication gap
- Summary: The application-service replay fast path duplicated part of the persistence idempotency
  logic and returned an existing idempotent run before the persistence layer could apply its
  retryable-run refresh rule. That left dependency-unavailable or false-positive guardrail copilot
  runs at risk of being replayed as stale results even after the underlying lotus-ai dependency or
  guardrail condition recovered.
- Evidence:
  - `src/core/advisory_copilot/service.py` now exposes
    `can_attempt_advisory_copilot_run_refresh` as the shared retryability predicate used by the
    application layer and the persistence refresh rule.
  - `src/core/advisory_copilot/application.py` keeps normal idempotent replay efficient, but allows
    retryable existing runs to proceed through draft generation and persistence refresh.
  - `tests/unit/advisory/engine/test_advisory_copilot_application.py` now proves an unavailable
    copilot run refreshes on the same idempotency key, preserves the stable run identity and
    creation timestamp, and then reverts to efficient replay after the refreshed run is no longer
    retryable.
- Consequence:
  - RFC-0027 advisory copilot recovery behavior now matches its persistence contract at the API
    application boundary without forcing normal idempotent replays to call lotus-ai again.
- Documentation:
  - No wiki source change is required. This slice hardens internal idempotency and recovery
    semantics without changing supported product behavior, operator workflow, or business-facing
    feature posture.
- Follow-Up:
  - Keep application-layer replay shortcuts tied to shared domain predicates when persistence owns
    the authoritative recovery or idempotency rule.

## LA-REV-184

- Scope: Enterprise audit metadata redaction
- Pattern: sensitive-data handling / operational diagnostics hardening
- Status: Hardened
- Finding Class: security and observability gap
- Summary: The enterprise audit redaction helper only redacted exact lowercase field names and
  assumed dictionary keys were strings. Common audit metadata variants such as `apiToken`,
  `client-email`, `authorizationHeader`, `privateKey`, or `session_cookie` could avoid redaction,
  and non-string keys could make redaction brittle.
- Evidence:
  - `src/api/enterprise_readiness.py` now normalizes audit metadata field names, handles non-string
    keys safely, and redacts common token, authorization, cookie, password, secret, key, account,
    session, SSN, and client-email field-name variants.
  - `tests/unit/advisory/api/test_enterprise_readiness.py` covers nested dictionaries, lists,
    non-string keys, common camel-case and hyphenated sensitive names, safe business metadata, and
    non-mutating behavior.
- Consequence:
  - Enterprise audit logging is less likely to leak credentials or client-identifying metadata when
    callers use realistic field naming conventions in diagnostic metadata.
- Documentation:
  - No wiki source change is required. This slice hardens an internal security/diagnostic utility
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Keep future audit metadata expansions covered with direct redaction tests before adding new log
    fields or diagnostic payloads.

## LA-REV-185

- Scope: Enterprise write-authorization header validation
- Pattern: authorization/auditability hardening
- Status: Hardened
- Finding Class: security and validation gap
- Summary: Enterprise write authorization normalized header names but did not trim header values.
  Whitespace-only actor, tenant, role, correlation, service identity, or authorization values could
  be treated as present, weakening enforcement and audit lineage quality for write requests.
- Evidence:
  - `src/api/enterprise_readiness.py` now strips normalized header names and values before required
    header, service-identity, authorization, and capability checks.
  - `tests/unit/advisory/api/test_enterprise_readiness.py` now covers whitespace-only required
    headers, whitespace-only service identity, and trimmed valid header/capability values.
- Consequence:
  - Enterprise authorization checks now require meaningful identity and correlation values before
    allowing write requests under enforced authorization mode.
- Documentation:
  - No wiki source change is required. This slice hardens internal authorization validation without
    changing supported product behavior, operator workflow, or business-facing feature posture.
- Follow-Up:
  - Keep authorization-policy normalization covered when new enterprise headers or capability rules
    are added.

## LA-REV-186

- Scope: Enterprise capability-rule path matching
- Pattern: authorization boundary hardening
- Status: Hardened
- Finding Class: security and validation gap
- Summary: Enterprise capability rules used raw prefix matching for route paths. A configured rule
  for `/advisory/proposals` could also match sibling paths such as `/advisory/proposals-extra`,
  making capability requirements broader than intended.
- Evidence:
  - `src/api/enterprise_readiness.py` now matches capability rules only for the exact configured
    route path or a child path below it.
  - `tests/unit/advisory/api/test_enterprise_readiness.py` now proves child paths inherit the rule
    while sibling paths do not.
- Consequence:
  - Capability enforcement is now aligned to route boundaries instead of accidental string-prefix
    overlap, reducing over-broad authorization policy application.
- Documentation:
  - No wiki source change is required. This slice hardens internal authorization matching without
    changing supported product behavior, operator workflow, or business-facing feature posture.
- Follow-Up:
  - Keep capability-rule matching tests in place when wildcard or templated route policies are
    introduced.

## LA-REV-187

- Scope: Enterprise runtime JSON configuration validation
- Pattern: configuration hardening / startup safety
- Status: Hardened
- Finding Class: security and operational diagnostics gap
- Summary: Invalid `ENTERPRISE_FEATURE_FLAGS_JSON` and `ENTERPRISE_CAPABILITY_RULES_JSON` values
  were loaded as empty maps without surfacing configuration drift. In strict runtime-config mode,
  that could let a malformed capability or feature-flag configuration pass startup validation.
- Evidence:
  - `src/api/enterprise_readiness.py` now reports invalid or non-object JSON map configuration for
    feature flags and capability rules, and preserves fail-fast startup behavior when
    `ENTERPRISE_ENFORCE_RUNTIME_CONFIG=true`.
  - `tests/unit/advisory/api/test_enterprise_readiness.py` now covers issue reporting and strict
    fail-fast behavior for malformed enterprise JSON maps.
- Consequence:
  - Operators receive deterministic configuration issues instead of silent fallback to empty
    feature-flag or capability-rule maps.
- Documentation:
  - No wiki source change is required. This slice hardens runtime configuration validation without
    changing supported product behavior, operator workflow, or business-facing feature posture.
- Follow-Up:
  - Keep startup validation aligned with any future enterprise policy env vars before enabling
    production enforcement.

## LA-REV-188

- Scope: Advisor cockpit pagination boundary
- Pattern: modularity and duplicate cursor handling
- Status: Hardened
- Finding Class: modularity and validation gap
- Summary: Advisor cockpit page-size behavior lived in the pagination module while action and
  preparation-packet cursor resolution lived as duplicate service-local loops. That kept validation
  details inside the application service and made future cockpit paginated surfaces more likely to
  reimplement cursor handling.
- Evidence:
  - `src/core/advisor_cockpit/pagination.py` now owns reusable cockpit cursor resolution alongside
    page-size normalization.
  - `src/core/advisor_cockpit/service.py` now delegates action and preparation-packet cursor
    validation to the pagination module.
  - `tests/unit/advisory/engine/test_engine_advisor_cockpit_models.py` covers reusable cursor
    start, none-cursor behavior, valid cursor advancement, and invalid-cursor error code.
- Consequence:
  - The advisor cockpit service is narrower, cursor validation is centralized, and future RFC-0026
    cockpit pagination can reuse the same validated boundary.
- Documentation:
  - No wiki source change is required. This slice refactors internal pagination structure without
    changing supported product behavior, operator workflow, or business-facing feature posture.
- Follow-Up:
  - Prefer extending `advisor_cockpit.pagination` for future cockpit page tokens instead of adding
    service-local cursor loops.

## LA-REV-189

- Scope: Proposal async lifecycle payload resolution
- Pattern: idempotency, lineage, and validation hardening
- Status: Hardened
- Finding Class: validation and operational reliability gap
- Summary: Async proposal lifecycle payload resolution accepted whitespace-only idempotency keys and
  proposal identifiers as meaningful replay scope, and model validation used broad exception
  handling. That could degrade retry lineage quality and hide unexpected implementation defects
  behind a generic payload-invalid failure.
- Evidence:
  - `src/core/proposals/async_payloads.py` now resolves idempotency keys and proposal identifiers
    through a shared non-blank string helper, trims accepted values, falls back across persisted and
    request-scope sources only when values are meaningful, and catches Pydantic validation errors
    explicitly.
  - `tests/unit/advisory/engine/test_engine_proposal_async_payloads.py` covers trimmed fallback
    resolution and whitespace-only rejection for async create idempotency keys and async version
    proposal scope.
- Consequence:
  - Proposal async replay and retry paths now carry meaningful lifecycle identity before work is
    retried or marked failed, improving operational auditability and preventing blank replay
    scopes from being treated as valid state.
- Documentation:
  - No wiki source change is required. This slice hardens internal async lifecycle validation
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Keep future async lifecycle identity fields normalized through shared helpers before they are
    used for idempotency, persistence lookup, or audit lineage.

## LA-REV-190

- Scope: Target-generation solver dependency boundary
- Pattern: optional dependency and diagnostics hardening
- Status: Hardened
- Finding Class: validation and modularity gap
- Summary: Solver dependency loading was embedded directly in target generation with broad
  exception handling. That kept optional dependency behavior harder to test and could convert
  unexpected implementation defects into a generic `SOLVER_ERROR` diagnostic.
- Evidence:
  - `src/core/target_generation.py` now isolates cvxpy/numpy loading in
    `load_target_solver_dependencies`, catches only explicit import/runtime loader failures, and
    keeps target generation's unavailable-solver behavior unchanged.
  - `tests/unit/advisory/engine/test_engine_target_generation_dependencies.py` covers unavailable
    solver fallback, successful dependency resolution, and the `SOLVER_ERROR`/`BLOCKED` target
    generation outcome when the solver stack is not available.
- Consequence:
  - Optional solver availability is now a small tested boundary, while unexpected solver-path code
    defects are less likely to be silently masked during target-generation execution.
- Documentation:
  - No wiki source change is required. This slice hardens internal optional dependency behavior
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Keep additional optional analytics dependencies behind explicit loader boundaries with direct
    tests for unavailable and available dependency states.

## LA-REV-191

- Scope: Workspace session cache bounds
- Pattern: bounded in-memory runtime hardening
- Status: Hardened
- Finding Class: validation and operational reliability gap
- Summary: The Workspace session cache accepted invalid cache sizes and changing the cache size did
  not immediately evict existing sessions over the new limit. A zero or negative limit could make
  the next save fail at runtime rather than failing configuration deterministically.
- Evidence:
  - `src/api/services/workspace_store.py` now validates cache size at construction and resize time,
    rejects non-meaningful limits, centralizes over-capacity eviction, and applies eviction
    immediately when the cache size changes.
  - `tests/unit/advisory/api/test_workspace_store.py` now covers invalid cache sizes and immediate
    oldest-session eviction after reducing the cache limit.
- Consequence:
  - Workspace runtime memory bounds are deterministic, misconfiguration fails early, and cache
    resizing cannot leave the store temporarily above its configured capacity.
- Documentation:
  - No wiki source change is required. This slice hardens internal bounded-cache behavior without
    changing supported product behavior, operator workflow, or business-facing feature posture.
- Follow-Up:
  - Keep future in-memory fallback stores explicit about bounded capacity and deterministic
    validation before runtime traffic reaches them.

## LA-REV-192

- Scope: Workspace draft-action domain guards
- Pattern: domain validation and optimized-runtime safety
- Status: Hardened
- Finding Class: validation and reliability gap
- Summary: Workspace draft-action application relied on `assert` statements after request model
  validation. Optimized Python can remove asserts, and tests or internal callers can construct
  malformed request objects directly, turning domain validation failures into less predictable
  attribute errors or missing-state behavior.
- Evidence:
  - `src/core/workspace/draft_actions.py` now uses explicit domain guard helpers for required
    trade, cash-flow, row identifier, and replacement-option fields.
  - `tests/unit/advisory/api/test_workspace_draft_actions.py` covers malformed constructed draft
    action requests and verifies deterministic `WorkspaceDraftActionError` messages.
- Consequence:
  - Workspace draft mutation behavior no longer depends on Python assertion settings and remains
    deterministic even when internal callers bypass Pydantic construction.
- Documentation:
  - No wiki source change is required. This slice hardens internal workspace domain validation
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Avoid using `assert` for business or request-shape invariants in runtime domain mutation paths.

## LA-REV-193

- Scope: Proposal context-resolution request-shape guards
- Pattern: idempotency, policy-context, and optimized-runtime safety
- Status: Hardened
- Finding Class: validation and reliability gap
- Summary: Proposal context resolution relied on `assert` statements for stateful, stateless, and
  legacy request payload invariants before building simulation context, hashes, and policy
  selectors. Optimized Python can remove those checks, and malformed constructed payloads could
  fail with less deterministic errors.
- Evidence:
  - `src/core/proposals/context.py` now uses explicit helper guards that raise
    `ProposalContextResolutionError` for missing stateful input, stateless input, or legacy
    simulation request payloads.
  - `tests/unit/advisory/engine/test_engine_proposal_context.py` covers constructed malformed
    create, simulation, and version payloads for deterministic context-resolution errors.
- Consequence:
  - Proposal context resolution now fails predictably before request hashes, policy context, or
    lifecycle replay evidence are derived from malformed internal payload objects.
- Documentation:
  - No wiki source change is required. This slice hardens internal context-resolution validation
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Keep proposal context validation explicit because it feeds idempotency, replay, policy
    evaluation, and Gateway-facing advisory behavior.

## LA-REV-194

- Scope: Proposal async operation missing-work handling
- Pattern: async lifecycle and optimized-runtime safety
- Status: Hardened
- Finding Class: validation and operational reliability gap
- Summary: The async operation runner relied on an `assert` after loading an optional read model
  operation. Missing operations already represented a no-work condition, but the explicit runtime
  behavior was not pinned by tests and depended on assertion control flow.
- Evidence:
  - `src/core/proposals/async_operation_runner.py` now returns explicitly when the operation read
    model has no operation.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operation_runner.py` covers the
    missing-operation path and proves the executor is not called.
- Consequence:
  - Async operation runners now have deterministic no-work behavior under optimized Python and
    cannot accidentally execute work for an absent operation record.
- Documentation:
  - No wiki source change is required. This slice hardens internal async lifecycle control flow
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Keep async runner no-work, terminal, exhausted, retryable, and failed paths directly tested as
    lifecycle behavior evolves.

## LA-REV-195

- Scope: Proposal delivery execution projection guard
- Pattern: delivery projection and optimized-runtime safety
- Status: Hardened
- Finding Class: validation and reliability gap
- Summary: Delivery summary projection relied on an `assert` after selecting the latest execution
  status event or execution-request event. While normal control flow made the assertion redundant,
  optimized Python can remove it and the status-without-request behavior was not directly pinned.
- Evidence:
  - `src/core/proposals/delivery_summary.py` now guards the selected execution event explicitly
    instead of relying on assertion behavior.
  - `tests/unit/advisory/engine/test_engine_proposal_delivery_summary.py` covers projecting an
    execution status event when no execution-request event is present.
- Consequence:
  - Delivery summary projection remains deterministic for partial event histories and no longer
    depends on Python assertion settings.
- Documentation:
  - No wiki source change is required. This slice hardens internal delivery projection behavior
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Keep delivery projection tests focused on partial histories because report, execution, and
    archive events can arrive from independent downstream services.

## LA-REV-196

- Scope: Correlation and observability header normalization
- Pattern: audit lineage and operational diagnostics hardening
- Status: Hardened
- Finding Class: observability and lineage gap
- Summary: Correlation ID resolution and HTTP observability middleware accepted whitespace-only or
  padded correlation/request/trace headers as meaningful values. That could propagate low-quality
  lineage identifiers into logs, response headers, proposal workflow records, and downstream
  diagnostics.
- Evidence:
  - `src/core/proposals/correlation.py` now trims supplied correlation IDs and generates governed
    fallback IDs for blank values.
  - `src/api/observability.py` now trims inbound correlation, request, and traceparent headers,
    generates request IDs for blank values, and normalizes response correlation headers.
  - `tests/unit/advisory/engine/test_engine_proposal_correlation.py` and
    `tests/unit/advisory/api/test_api_observability_headers.py` cover trimmed and blank inbound
    identifiers.
- Consequence:
  - Advisory workflow and HTTP request lineage now carry meaningful identifiers, improving audit
    replay, support diagnostics, and cross-service trace consistency.
- Documentation:
  - No wiki source change is required. This slice hardens internal and API observability behavior
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Keep new externally supplied lineage headers normalized before they enter logs, workflow
    records, persistence, or downstream service calls.

## LA-REV-197

- Scope: Proposal create idempotency-key normalization
- Pattern: idempotency and audit lineage hardening
- Status: Hardened
- Finding Class: validation and operational reliability gap
- Summary: Proposal create and async-create commands accepted padded or whitespace-only
  idempotency keys. That could create distinct replay records for semantically identical client
  keys or allow blank replay identity to enter persistence.
- Evidence:
  - `src/core/proposals/idempotency.py` now exposes a required idempotency-key normalizer that
    trims meaningful values and rejects missing or blank keys.
  - `src/core/proposals/service.py` applies the normalizer before sync and async proposal-create
    persistence, mapping invalid keys to `ProposalValidationError`.
  - `src/api/proposals/routes_async.py` now maps async create idempotency-key validation failures
    through the standard proposal HTTP error model.
  - `tests/unit/advisory/engine/test_engine_proposal_idempotency.py` and
    `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` cover trimming,
    rejection, and repository lookup behavior.
- Consequence:
  - Proposal create replay identity is deterministic and cannot persist blank or padded
    idempotency keys as distinct lifecycle records.
- Documentation:
  - No wiki source change is required. This slice hardens API-adjacent idempotency behavior
    without changing supported product behavior, operator workflow, or business-facing feature
    posture.
- Follow-Up:
  - Completed by LA-REV-198 for lifecycle, memo, cockpit, and copilot idempotency scopes.

## LA-REV-198

- Scope: Advisory command idempotency-key normalization
- Pattern: idempotency and audit lineage hardening
- Status: Hardened
- Finding Class: validation, replay determinism, and API evidence gap
- Summary: Several advisory write commands accepted caller-supplied idempotency keys without
  normalizing whitespace. Padded keys could create separate replay identities from the same client
  retry, while whitespace-only optional keys could be persisted as misleading audit metadata.
- Evidence:
  - `src/core/common/idempotency.py` centralizes required and optional idempotency-key
    normalization for reuse across advisory domains.
  - Proposal lifecycle transitions, approval decisions, narrative reviews, memo creation and memo
    events, report-package requests, AI commentary requests, advisory copilot runs/reviews, and
    advisor cockpit acknowledgements normalize idempotency keys before replay lookup or
    persistence.
  - Advisor cockpit acknowledgement responses now return the normalized idempotency key in audit
    context, matching the documented response model and giving callers replay evidence without
    inspecting storage.
  - Focused tests cover padded-key replay and normalized persisted/audit evidence across proposal
    lifecycle, memo API, advisor cockpit, and advisory copilot paths.
- Consequence:
  - Advisory command replay identity is deterministic across HTTP and service callers, and optional
    whitespace-only keys no longer become persisted audit identity.
- Documentation:
  - No wiki source change is required. This is command-boundary hardening and response evidence
    alignment; supported product behavior and operator workflow are unchanged.
- Follow-Up:
  - None.

## LA-REV-199

- Scope: Policy-pack and policy-evaluation idempotency-key normalization
- Pattern: idempotency and audit lineage hardening
- Status: Hardened
- Finding Class: replay determinism and policy audit reliability gap
- Summary: RFC 25 policy-pack validation/activation, policy-evaluation finalization, workflow
  sign-off, report-package, and AI-evidence commands used caller-supplied idempotency keys without
  consistent normalization. Padded keys could create separate policy audit events for the same
  client retry, weakening replay determinism and audit supportability.
- Evidence:
  - `src/core/policy_packs/catalog.py` and `src/core/policy_packs/persistence.py` normalize
    required idempotency keys before validation, activation, and evaluation finalization.
  - `src/core/policy_packs/workflow.py`, `src/core/policy_packs/reporting.py`, and
    `src/core/policy_packs/ai.py` normalize optional idempotency keys before sign-off,
    report-package, and AI-evidence replay lookup.
  - Focused engine and API tests cover padded-key normalization across policy-pack validation,
    activation, evaluation finalization, append-only review events, sign-off, report-package, and
    AI-evidence paths.
- Consequence:
  - Policy audit lineage now records deterministic idempotency identity across RFC 25 and RFC 27
    policy evidence flows, reducing duplicate audit events and replay ambiguity.
- Documentation:
  - No wiki source change is required. This is policy command-boundary hardening and does not
    change product behavior, supported feature posture, or operator workflow.
- Follow-Up:
  - None.

## LA-REV-200

- Scope: Proposal simulation and workspace handoff idempotency-key normalization
- Pattern: idempotency and audit lineage hardening
- Status: Hardened
- Finding Class: replay determinism and lineage reliability gap
- Summary: Proposal simulation and workspace handoff entry points accepted caller-supplied
  idempotency keys before replay lookup and downstream lineage emission. Padded keys could produce
  duplicate simulation replay records or non-canonical proposal lineage for semantically identical
  retries.
- Evidence:
  - `src/api/services/advisory_simulation_service.py` normalizes required simulation
    idempotency keys before repository replay lookup, downstream orchestration, and persistence.
  - `src/api/services/workspace_lifecycle_handoff.py` normalizes the first-create handoff key before
    proposal creation.
  - `src/core/advisory/orchestration.py` and `src/core/advisory_engine.py` normalize optional
    idempotency keys before passing them into local fallback or result lineage.
  - Focused API tests cover padded-key replay for proposal artifact/simulation and workspace
    handoff lineage.
- Consequence:
  - Simulation, artifact, and workspace handoff lineage now carry deterministic replay identity
    across HTTP retries and local fallback paths.
- Documentation:
  - No wiki source change is required. This is replay/lineage hardening; supported feature posture
    and operator workflow are unchanged.
- Follow-Up:
  - None.

## LA-REV-201

- Scope: Shared Postgres migration cleanup and diagnostics
- Pattern: operational hardening and persistence infrastructure reliability
- Status: Hardened
- Finding Class: observability and migration failure-handling gap
- Summary: The shared Postgres migration runner suppressed rollback failures silently and allowed
  advisory-lock cleanup failures to mask the original migration error. That weakened operator
  diagnostics for proposal and advisory-copilot persistence migrations during cutover or startup.
- Evidence:
  - `src/infrastructure/postgres_migrations.py` now has explicit rollback and advisory-lock
    cleanup helpers with structured logging for cleanup failures.
  - Migration failures still attempt rollback and advisory unlock while preserving the original
    failure if cleanup also fails.
  - Successful migrations surface advisory-unlock failures as
    `POSTGRES_MIGRATION_UNLOCK_FAILED:<namespace>` instead of hiding lock-release problems.
  - `tests/unit/infrastructure/test_postgres_migrations.py` covers rollback/unlock behavior,
    original-error preservation when cleanup fails, and successful-migration unlock failures.
- Consequence:
  - Proposal and advisory-copilot Postgres migration startup behavior is more diagnosable and less
    likely to mislead operators during production cutover or incident triage.
- Documentation:
  - No wiki source change is required. This slice hardens shared persistence infrastructure
    behavior without changing supported feature posture, operator workflow, or business-facing
    documentation.
- Follow-Up:
  - None.

## LA-REV-202

- Scope: Proposal execution handoff idempotency-key normalization
- Pattern: idempotency and audit lineage hardening
- Status: Hardened
- Finding Class: replay determinism and execution-boundary audit gap
- Summary: Proposal execution handoff accepted optional caller idempotency keys without
  normalization before replay lookup or workflow-event persistence. Padded keys could produce
  duplicate execution handoff audit events for the same advisory handoff request.
- Evidence:
  - `src/core/proposals/execution_handoff_command.py` normalizes optional handoff idempotency keys
    before replay lookup and event creation.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` now covers padded-key
    execution handoff replay and confirms only one workflow event is recorded.
- Consequence:
  - RFC 26/RFC 28 execution handoff evidence remains deterministic without overclaiming OMS order,
    fill, settlement, or external execution completion.
- Documentation:
  - No wiki source change is required. This is execution-boundary replay hardening with no change
    to product feature posture or operator workflow.
- Follow-Up:
  - None.

## LA-REV-203

- Scope: Proposal async operation runner retry contract
- Pattern: async orchestration and runtime recovery hardening
- Status: Hardened
- Finding Class: test gap and service-boundary typing gap
- Summary: The async operation runner had lower-level tests for runtime exception state
  transitions, but the runner-level retry loop was not directly pinned. Its executor contract also
  accepted `Any`, weakening the boundary between orchestration and proposal-create result
  persistence.
- Evidence:
  - `src/core/proposals/async_operation_runner.py` now types async executors as returning
    `ProposalCreateResponse`.
  - `tests/unit/advisory/engine/test_engine_proposal_async_operation_runner.py` now covers a
    transient runtime exception followed by successful retry, verifying attempt count, terminal
    success, proposal lineage, and lease/error cleanup.
- Consequence:
  - RFC 23/RFC 26 asynchronous proposal creation has stronger regression coverage for runtime
    recovery behavior without relying only on lower-level state helper tests.
- Documentation:
  - No wiki source change is required. This is test and type-contract hardening with no change to
    product feature posture, API shape, or operator workflow.
- Follow-Up:
  - None.

## LA-REV-204

- Scope: RFC 26-28 no-deferred-wave documentation posture
- Pattern: documentation truth and supported-feature governance
- Status: Hardened
- Finding Class: documentation drift and product-claim clarity gap
- Summary: RFC 26/27 closure and wiki/index material still used "first-wave", "day-2", or
  "wave-2" phrasing in several places. That wording conflicted with the governed expectation that
  required implementation must be completed inside the RFC scope rather than implied as a later
  wave.
- Evidence:
  - RFC 26/27/28, relevant slice docs, `docs/rfcs/README.md`, and wiki source now use
    supported/implemented-scope language instead of deferred-wave terminology.
  - Contract tests for RFC 26 and RFC 27 documentation were updated to pin the no-deferred-wave
    posture.
  - Targeted documentation contract suite passed for RFC 26 and RFC 27 after the wording update.
- Consequence:
  - Product documentation is cleaner for enterprise review and no longer suggests staged deferral
    for requirements that are part of the implemented RFC business value.
- Documentation:
  - Wiki source changed and requires `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-advise`
    before merge and `-Publish` after merge to `main`.
- Follow-Up:
  - None.

## LA-REV-205

- Scope: Advisory copilot model-version vocabulary
- Pattern: private-banking API copy and model lineage hardening
- Status: Hardened
- Finding Class: documentation/API example quality gap
- Summary: Advisory copilot model-version examples and tests used `stub-advisory-copilot-v1`.
  That leaked test/prototype language into model lineage examples and weakened the business-facing
  polish expected for governed AI evidence.
- Evidence:
  - `src/core/advisory_copilot/records.py` now uses `lotus-ai-governed-model.v1` as the model
    lineage example.
  - Advisory copilot API, application, and persistence tests now use the same governed model
    vocabulary.
  - Focused copilot API/application/persistence tests, ruff, and mypy passed.
- Consequence:
  - RFC 27 copilot API/model examples now read as governed product lineage instead of prototype
    scaffolding, without changing runtime behavior or evidence semantics.
- Documentation:
  - No wiki source change is required. This slice improves API/model example vocabulary only.
- Follow-Up:
  - None.

## LA-REV-206

- Scope: Proposal artifact placeholder vocabulary
- Pattern: private-banking API copy and proposal artifact polish
- Status: Hardened
- Finding Class: API/documentation vocabulary quality gap
- Summary: Proposal artifact models and deterministic disclosure output still used "placeholder"
  and "later slices" language for advisor notes, product-document references, risk disclaimers, and
  generated intents. That wording made supported artifact evidence read like scaffolding instead
  of implementation-backed advisor material.
- Evidence:
  - `src/core/advisory/artifact_models.py` now describes advisor notes, disclosures, and product
    document references with business-facing terminology.
  - `src/core/advisory/artifact.py` now emits
    `KID/FactSheet reference pending source confirmation` instead of a placeholder label.
  - `src/core/advisory/alternatives_models.py` no longer describes generated intents as a later
    slice placeholder.
  - Focused proposal artifact and memo-builder tests, ruff, and mypy passed.
- Consequence:
  - RFC 23/24 proposal artifact evidence is cleaner for demos, API consumers, and downstream memo
    material without changing supported capability boundaries or overclaiming client-ready
    publication.
- Documentation:
  - No wiki source change is required. This slice improves API/model copy and deterministic
    artifact wording only.
- Follow-Up:
  - None.

## LA-REV-207

- Scope: RFC 23-28 supported-scope public vocabulary and cockpit action builder naming
- Pattern: public API copy, documentation truth, and domain-model vocabulary hardening
- Status: Hardened
- Finding Class: documentation/API vocabulary quality gap and stale internal naming
- Summary: Active RFC/wiki/OpenAPI/model surfaces still used wave-based or later-slice wording in
  current-state product copy, and the cockpit aggregate action builder was named
  `build_first_wave_cockpit_actions`. That weakened enterprise product language and made supported
  capability boundaries look like staged prototype scaffolding.
- Evidence:
  - Public RFC 23-28, wiki, OpenAPI tag descriptions, policy route descriptions, cockpit source
    model descriptions, and copilot model descriptions now use supported-scope and governed-gate
    language.
  - `src/core/advisor_cockpit/action_factory.py` now exposes
    `build_source_backed_cockpit_actions`, and source-read-model/tests use the source-backed name.
  - `tests/unit/test_rfc0023_0028_public_vocabulary_contract.py` now pins active public surfaces
    against stale wave/later-slice phrases.
  - Targeted RFC vocabulary, cockpit, copilot, advisor-cockpit API, advisory-copilot API, and
    OpenAPI contract tests passed with `66 passed`.
- Consequence:
  - RFC 23-28 current-state surfaces read as implementation-backed private-banking capabilities
    with explicit client-ready gates, without implying deferred waves or overclaiming external
    client publication.
- Documentation:
  - Wiki source changed and requires the repo wiki check with unpublished source changes allowed
    before merge, followed by wiki publication after merge to `main`.
- Follow-Up:
  - None.

## LA-REV-208

- Scope: Enterprise write-authorization capability-rule configuration
- Pattern: security posture and fail-closed authorization hardening
- Status: Hardened
- Finding Class: security configuration gap
- Summary: Runtime configuration validation reported malformed
  `ENTERPRISE_CAPABILITY_RULES_JSON`, but write authorization could still treat malformed
  capability rules as an empty rule map when `ENTERPRISE_ENFORCE_AUTHZ=true` and startup
  fail-fast was not enabled. Whitespace-padded capability-rule keys could also fail to match and
  behave like no rule. Those paths created fail-open posture for capability-specific write
  authorization.
- Evidence:
  - `src/api/enterprise_readiness.py` now rejects write authorization with
    `invalid_capability_rules_json` when capability rules are malformed.
  - Capability-rule keys and capability values are normalized before request matching.
  - `tests/unit/advisory/api/test_enterprise_readiness.py` now covers the fail-closed behavior.
  - Focused enterprise-readiness tests passed with `9 passed`.
- Consequence:
  - Enterprise write authorization no longer silently drops malformed or padded capability policy,
    improving bank-grade configuration safety without changing default non-enforcing local
    development behavior.
- Documentation:
  - No wiki source change is required. This is security posture hardening of existing middleware
    behavior and does not change product feature posture.
- Follow-Up:
  - None.

## LA-REV-209

- Scope: Advisor cockpit acknowledgement actor and note normalization
- Pattern: idempotency, audit lineage, and API DTO validation hardening
- Status: Hardened
- Finding Class: API validation and replay-determinism gap
- Summary: RFC-0026 cockpit acknowledgement normalized the idempotency key, but the request DTO did
  not normalize `acknowledged_by` or support-safe acknowledgement notes. Padded actor values or
  multiline notes could create dirty audit lineage and avoidable request-hash drift; blank actor
  values were not rejected at the DTO boundary.
- Evidence:
  - `src/core/advisor_cockpit/api_models.py` now trims and validates `acknowledged_by`, normalizes
    acknowledgement notes, and treats blank notes as absent.
  - Advisor cockpit service tests now verify normalized actor/note persistence and replay.
  - Advisor cockpit API tests now verify blank actors return HTTP 422.
  - Focused advisor-cockpit service, API, and RFC-0026 API-contract tests passed with `17 passed`.
- Consequence:
  - Cockpit acknowledgement audit records are cleaner, replay hashes are less brittle, and invalid
    business actors are blocked before persistence.
- Documentation:
  - No wiki source change is required. This is DTO/audit-lineage hardening with no product posture
    change.
- Follow-Up:
  - None.

## LA-REV-210

- Scope: Advisory copilot actor normalization
- Pattern: RFC-0027 API DTO validation, idempotency, and audit-lineage hardening
- Status: Hardened
- Finding Class: API validation and audit hygiene gap
- Summary: Governed advisory copilot requests accepted actor fields without DTO-level
  normalization. Padded `created_by`, `requested_by`, or review `actor_id` values could create
  dirty audit records and avoidable idempotency hash drift, while blank review actors were not
  rejected before service execution.
- Evidence:
  - `src/core/advisory_copilot/api_models.py` now trims and validates copilot actor fields.
  - Advisory copilot application tests now verify normalized packet/run audit actors.
  - Advisory copilot API tests now verify padded review actor replay and blank actor rejection.
  - Focused advisory-copilot application, API, and RFC-0027 certified API tests passed with
    `17 passed`.
- Consequence:
  - RFC-0027 copilot audit lineage is cleaner, replay hashes are less brittle, and invalid review
    actors are blocked at the API model boundary.
- Documentation:
  - No wiki source change is required. This is DTO/audit-lineage hardening with no product posture
    change.
- Follow-Up:
  - None.

## LA-REV-211

- Scope: Shared actor and support-note normalization
- Pattern: duplicate DTO validation cleanup and shared core helper extraction
- Status: Hardened
- Finding Class: duplication and maintainability gap
- Summary: RFC-0026 cockpit acknowledgement and RFC-0027 copilot APIs both implemented local
  actor normalization after audit-lineage hardening. Keeping separate validators would invite
  drift in actor trimming, blank actor rejection, and support-safe note normalization across
  advisor workflow surfaces.
- Evidence:
  - `src/core/common/actors.py` now provides reusable `normalize_required_actor_id` and
    `normalize_optional_support_note` helpers.
  - Cockpit and copilot API DTOs now delegate to the shared helpers while preserving their
    existing domain-specific error codes.
  - `tests/unit/core/test_actor_normalization.py` covers helper behavior directly.
  - Focused actor-normalization, advisor-cockpit API/service, and advisory-copilot API/application
    tests passed with `31 passed`.
- Consequence:
  - Actor/audit normalization is reusable across Advise modules, reducing duplicate DTO logic and
    making future advisory workflow APIs easier to keep consistent.
- Documentation:
  - No wiki source change is required. This is internal shared-helper refactoring with no product
    posture or operator workflow change.
- Follow-Up:
  - None.

## LA-REV-212

- Scope: RFC-0027 correlation-id normalization across copilot and audit boundaries
- Pattern: audit lineage, API boundary hygiene, and observability consistency
- Status: Hardened
- Finding Class: API validation and audit hygiene gap
- Summary: Advisory copilot application methods and enterprise audit emission accepted raw
  correlation ids even though request observability already normalized response headers. Padded
  `X-Correlation-ID` values could therefore leak into persisted copilot lineage or enterprise
  audit records, while blank values did not consistently fall back to the deterministic copilot
  correlation identifiers used by replayable workflows.
- Evidence:
  - `src/core/proposals/correlation.py` now exposes reusable optional correlation-id
    normalization while preserving generated fallback behavior for observability.
  - `src/core/advisory_copilot/application.py` now normalizes optional correlation ids and keeps
    deterministic fallback ids for packet, run, and review persistence.
  - `src/api/enterprise_readiness.py` now normalizes correlation ids before audit emission.
  - Focused correlation, copilot application/API, observability, and enterprise-readiness tests
    passed with `32 passed`.
- Consequence:
  - Persisted copilot lineage and enterprise audit records no longer carry padded correlation
    identifiers, and blank inbound values use governed fallbacks instead of dirty audit values.
- Documentation:
  - No wiki source change is required. This is audit-lineage and boundary normalization hardening
    with no product posture or operator workflow change.
- Follow-Up:
  - None.

## LA-REV-213

- Scope: Advisory copilot run-list page-size normalization
- Pattern: pagination hardening and service-boundary consistency
- Status: Hardened
- Finding Class: API/service boundary validation gap
- Summary: The RFC-0027 copilot run-list route bounded `limit` through FastAPI query validation,
  but direct application-service callers could still pass invalid or oversized page sizes to the
  repositories. That left repository behavior dependent on Python slicing or database `LIMIT`
  semantics rather than a shared domain pagination rule.
- Evidence:
  - `src/core/advisory_copilot/pagination.py` now defines default and maximum run-list page sizes
    and rejects non-positive service-level page sizes.
  - `src/core/advisory_copilot/application.py` now normalizes run-list page sizes before calling
    the repository.
  - Copilot pagination and application-service tests now pin page-size normalization and invalid
    service-call rejection.
- Consequence:
  - RFC-0027 run history pagination is consistently bounded for API and non-API callers, reducing
    avoidable performance risk and eliminating ambiguous repository behavior for invalid limits.
- Documentation:
  - No wiki source change is required. This preserves the existing API contract and strengthens
    service-boundary enforcement.
- Follow-Up:
  - None.

## LA-REV-214

- Scope: Integration dependency readiness URL sanitization
- Pattern: sensitive-data handling and operational diagnostics hardening
- Status: Hardened
- Finding Class: security and observability hygiene gap
- Summary: Dependency readiness state exposed configured base URLs directly. A misconfigured
  runtime URL containing credentials, query tokens, or fragments could therefore leak sensitive
  material through readiness/capability diagnostics even when runtime probing legitimately needed
  the configured URL.
- Evidence:
  - `src/integrations/base.py` now sanitizes the public dependency `base_url` returned in
    readiness state while preserving the configured URL for runtime probes.
  - Integration dependency tests now verify credentials, query strings, and fragments are stripped
    from public state and invalid URL ports are not surfaced.
- Consequence:
  - Operational readiness APIs remain useful for support and pre-sales diagnostics without
    exposing credential-bearing dependency URLs.
- Documentation:
  - No wiki source change is required. This strengthens existing sensitive-data handling without
    changing supported product capabilities.
- Follow-Up:
  - None.

## LA-REV-215

- Scope: Integration dependency health probe target hardening
- Pattern: operational diagnostics and security posture hardening
- Status: Hardened
- Finding Class: security and runtime resilience gap
- Summary: Dependency health probes accepted any configured URL shape and followed redirects.
  Misconfigured dependency URLs could therefore trigger unnecessary non-http probe attempts or
  redirect-driven probe behavior that is not needed for Lotus readiness decisions.
- Evidence:
  - `src/integrations/base.py` now fails closed for non-http(s) or invalid-port probe targets
    before creating an HTTP client.
  - Dependency probes now run with redirects disabled.
  - Integration base tests verify redirect disabling and fail-closed behavior for invalid probe
    targets.
- Consequence:
  - Runtime readiness probing is more predictable and avoids probing unexpected schemes or
    redirect targets from misconfigured dependency URLs.
- Documentation:
  - No wiki source change is required. This is internal operational hardening with no product
    posture change.
- Follow-Up:
  - None.

## LA-REV-216

- Scope: Lotus-core stateful-context base URL derivation sanitization
- Pattern: sensitive configuration handling and upstream integration hardening
- Status: Hardened
- Finding Class: security and configuration hygiene gap
- Summary: Stateful-context query/control-plane URL derivation preserved embedded credentials
  from `LOTUS_CORE_BASE_URL` or `LOTUS_CORE_QUERY_BASE_URL`. Those derived URLs are reused across
  upstream source reads, making credential-bearing URL propagation an avoidable security and
  diagnostics risk.
- Evidence:
  - `src/integrations/lotus_core/stateful_context_routes.py` now strips URL credentials, query
    strings, and fragments while preserving host, path, scheme, and query/control-plane port
    derivation.
  - Stateful-context tests now verify explicit query URLs and derived query/control-plane URLs do
    not retain credentials or sensitive URL components.
- Consequence:
  - Lotus-core stateful context reads use cleaner derived service URLs and no longer propagate
    embedded URL credentials through Advise integration routing.
- Documentation:
  - No wiki source change is required. This is runtime configuration hardening with no supported
    feature posture change.
- Follow-Up:
  - None.

## LA-REV-217

- Scope: Lotus-core simulation base URL sanitization
- Pattern: sensitive configuration handling and upstream integration hardening
- Status: Hardened
- Finding Class: security and configuration hygiene gap
- Summary: The direct lotus-core simulation adapter still constructed upstream request URLs from
  raw `LOTUS_CORE_BASE_URL` even after stateful-context routing was hardened. Credential-bearing
  URLs, query tokens, fragments, or non-http schemes could therefore reach the simulation call
  path.
- Evidence:
  - `src/integrations/base.py` now provides reusable `sanitized_http_base_url` for integration
    runtime URL handling.
  - `src/integrations/lotus_core/simulation.py` now strips credentials, query strings, and
    fragments from the configured base URL and rejects non-http(s) values before opening a client.
  - Lotus-core simulation tests now prove sanitized request URL construction and fail-closed
    behavior for invalid configured schemes.
- Consequence:
  - Advise no longer propagates embedded URL credentials through the direct lotus-core simulation
    execution path, and invalid schemes fail before network activity.
- Documentation:
  - No wiki source change is required. This is runtime configuration hardening with no supported
    feature posture change.
- Follow-Up:
  - None.

## LA-REV-218

- Scope: Lotus AI adapter base URL sanitization
- Pattern: sensitive configuration handling, duplicate integration setup, and fail-closed adapter
  configuration
- Status: Hardened
- Finding Class: security and maintainability gap
- Summary: The Lotus AI adapters resolved `LOTUS_AI_BASE_URL` independently across proposal
  narrative, proposal memo commentary, policy evidence, workspace rationale, and advisory copilot
  paths. The duplicated parsing accepted raw configured URLs, which made it easier for
  credential-bearing URLs, query tokens, fragments, or unsupported schemes to leak into workflow
  pack calls.
- Evidence:
  - `src/integrations/lotus_ai/runtime_config.py` centralizes Lotus AI base URL resolution through
    the shared sanitized HTTP URL helper.
  - The five Lotus AI workflow-pack adapters now use the shared resolver instead of local
    environment parsing.
  - `tests/unit/advisory/api/test_lotus_ai_runtime_config.py` proves every adapter strips
    credentials, query strings, and fragments while rejecting invalid schemes with the
    adapter-specific unavailable error.
- Consequence:
  - AI-assisted advisory paths now fail closed on invalid runtime configuration and no longer
    propagate embedded URL secrets through workflow-pack endpoints.
- Documentation:
  - No wiki source change is required. This is runtime configuration hardening with no supported
    feature posture change.
- Follow-Up:
  - None.

## LA-REV-219

- Scope: Lotus Risk and Lotus Report adapter base URL sanitization
- Pattern: sensitive configuration handling and upstream integration hardening
- Status: Hardened
- Finding Class: security and configuration hygiene gap
- Summary: The direct lotus-risk enrichment and lotus-report package adapters still constructed
  upstream request URLs from raw `LOTUS_RISK_BASE_URL` and `LOTUS_REPORT_BASE_URL`. This left two
  RFC 23-28 integration paths able to propagate embedded URL credentials, query tokens, fragments,
  or unsupported schemes into outbound service calls.
- Evidence:
  - `src/integrations/lotus_risk/enrichment.py` now sanitizes and validates the configured base URL
    before opening an HTTP client and reuses the resolved URL across retry attempts.
  - `src/integrations/lotus_report/adapter.py` now sanitizes and validates the configured base URL
    before report-package requests.
  - Risk and report adapter tests prove sanitized request URL construction and fail-closed behavior
    for invalid configured schemes without opening an HTTP client.
- Consequence:
  - Advise integration calls to risk and report services no longer propagate embedded URL secrets,
    and invalid schemes fail before network activity.
- Documentation:
  - No wiki source change is required. This is runtime configuration hardening with no supported
    feature posture change.
- Follow-Up:
  - None.

## LA-REV-220

- Scope: Dependency health probe URL sanitization
- Pattern: sensitive configuration handling and operational diagnostics hardening
- Status: Hardened
- Finding Class: security and observability hygiene gap
- Summary: Dependency readiness probing validated that configured service URLs were HTTP(S), but
  still built `/health/ready` and `/health` requests from the raw configured value. A
  credential-bearing URL, query token, or fragment could therefore leak into probe URLs even though
  public dependency state already used sanitized values.
- Evidence:
  - `src/integrations/base.py` now resolves a sanitized HTTP probe base URL once and uses that
    value for readiness checks.
  - `tests/unit/advisory/api/test_integrations_base.py` proves probe calls strip embedded
    credentials, query strings, and fragments while preserving scheme, host, port, and path.
- Consequence:
  - Operational readiness checks no longer propagate embedded URL secrets through diagnostic
    health-probe requests.
- Documentation:
  - No wiki source change is required. This is internal operational hardening with no supported
    feature posture change.
- Follow-Up:
  - None.

## LA-REV-221

- Scope: Dependency readiness invalid-configuration posture
- Pattern: API truthfulness, operational diagnostics, and configuration validation
- Status: Hardened
- Finding Class: readiness overclaim and API semantics gap
- Summary: Dependency readiness treated any non-empty base URL configuration as
  `configuration_only` ready when runtime probes were disabled, even when the configured value was
  not a usable HTTP(S) base URL. This could overstate `/platform/capabilities` readiness for
  malformed service configuration.
- Evidence:
  - `src/integrations/base.py` now marks configured but invalid dependency URLs as
    `invalid_configuration`, keeps `operational_ready=false`, and avoids runtime probing.
  - Dependency readiness probes now receive sanitized base URLs instead of raw configured values.
  - `src/api/capabilities/models.py` documents the new readiness basis in the response contract.
  - Integration and `/platform/capabilities` tests prove invalid configured URLs remain configured
    but fail closed without making dependent features or workflows ready.
- Consequence:
  - Operator and API readiness output no longer overclaims bank-runtime readiness when dependency
    URLs are malformed.
- Documentation:
  - No wiki source change is required. This is API readiness-contract hardening; the OpenAPI
    response model carries the implementation-backed contract truth.
- Follow-Up:
  - None.

## LA-REV-222

- Scope: Enterprise audit structured log serialization
- Pattern: auditability and operational diagnostics hardening
- Status: Hardened
- Finding Class: audit evidence serialization gap
- Summary: Enterprise audit events attached audit details to log records through
  `extra={"audit": ...}`, but the JSON log formatter only serialized `extra_fields`. This left
  audit details visible to in-process `caplog` assertions while risking loss from actual structured
  JSON log output.
- Evidence:
  - `src/api/observability.py` now emits an `audit` object when a log record carries structured
    audit data.
  - `tests/unit/advisory/api/test_enterprise_readiness.py` now formats an emitted enterprise audit
    event through the production JSON formatter and proves normalized correlation IDs plus redacted
    sensitive metadata are present in the JSON payload.
- Consequence:
  - Enterprise authorization and write-path audit events remain machine-readable in production log
    pipelines instead of only being available inside Python log records.
- Documentation:
  - No wiki source change is required. This is observability serialization hardening with no
    supported feature posture change.
- Follow-Up:
  - None.

## LA-REV-223

- Scope: Correlation and request ID boundary hardening
- Pattern: response-header safety, log hygiene, and operational diagnostics hardening
- Status: Hardened
- Finding Class: reflected diagnostic identifier validation gap
- Summary: Inbound correlation and request identifiers were trimmed but otherwise trusted before
  being reflected into response headers and structured logs. Oversized or control-character-bearing
  identifiers could therefore degrade log quality or produce unsafe diagnostic headers.
- Evidence:
  - `src/core/proposals/correlation.py` now rejects oversized and control-character-bearing
    correlation IDs before preserving caller values.
  - `src/api/observability.py` now applies the same boundary to request IDs and response-provided
    correlation IDs before reflecting them.
  - Unit and API tests prove oversized inbound IDs are replaced by generated Lotus IDs.
- Consequence:
  - Diagnostic identifiers remain bounded and safe for response headers, logs, and cross-service
    tracing while preserving valid caller-supplied IDs.
- Documentation:
  - No wiki source change is required. This is operational boundary hardening with no supported
    feature posture change.
- Follow-Up:
  - None.

## LA-REV-224

- Scope: Enterprise audit identity normalization
- Pattern: auditability, response-header safety, and operational diagnostics hardening
- Status: Hardened
- Finding Class: audit identity hygiene gap
- Summary: Enterprise audit events normalized correlation IDs but emitted actor, tenant, and role
  values directly from caller headers. Padded, blank, oversized, or control-character-bearing audit
  identity fields could therefore degrade machine-readable audit records.
- Evidence:
  - `src/api/enterprise_readiness.py` now normalizes audit actor, tenant, and role values before
    structured audit emission, with bounded fallbacks for invalid values.
  - Enterprise readiness tests prove trimmed actor/role values are preserved and invalid tenant
    identity falls back to `default`.
- Consequence:
  - Authorization and write-path audit records use bounded, clean identity fields suitable for
    production log indexing and review.
- Documentation:
  - No wiki source change is required. This is audit serialization hardening with no supported
    feature posture change.
- Follow-Up:
  - None.

## LA-REV-225

- Scope: Workspace rationale Lotus AI tenant context
- Pattern: domain vocabulary, private-banking tenant posture, and configuration consistency
- Status: Hardened
- Finding Class: stale hardcoded tenant context gap
- Summary: The workspace rationale Lotus AI adapter still sent a hardcoded `tenant-us-002`
  workflow caller context while the rest of the advisory AI integration used the Singapore private
  banking default or the `LOTUS_ADVISE_TENANT_ID` runtime setting. This created inconsistent
  tenant context for RFC 27 workspace rationale flows.
- Evidence:
  - `src/integrations/lotus_ai/rationale.py` now uses `LOTUS_ADVISE_TENANT_ID` with the governed
    `tenant-sg-001` default.
  - Lotus AI rationale tests prove both the default private-banking tenant context and runtime
    tenant override behavior.
- Consequence:
  - Workspace rationale workflow-pack calls now carry consistent private-banking tenant context
    across advisory AI paths.
- Documentation:
  - No wiki source change is required. This aligns runtime configuration behavior with existing
    advisory AI tenant posture and does not change supported feature scope.
- Follow-Up:
  - None.

## LA-REV-226

- Scope: Enterprise write-denial audit middleware
- Pattern: auditability, operational diagnostics, and security posture
- Status: Hardened
- Finding Class: unaudited payload-size denial gap
- Summary: Oversized write requests were denied with `413 payload_too_large` before the normal
  response path, which meant the denial did not emit an enterprise audit event and did not include
  the enterprise policy-version response header. This weakened supportability for blocked write
  attempts on advisory RFC 23-28 APIs.
- Evidence:
  - `src/api/enterprise_readiness.py` now emits a structured `DENY <method> <path>` audit event
    for payload-size denials with bounded metadata for content length and configured maximum.
  - Enterprise middleware tests prove the 413 denial audit payload and policy-version header.
  - Authorization-denial middleware tests prove the 403 path also carries the policy-version
    header.
- Consequence:
  - Security, compliance, and operations can correlate rejected write attempts without inspecting
    request bodies or relying on infrastructure-only logs.
- Documentation:
  - No wiki source change is required. This tightens existing enterprise middleware behavior
    without changing supported feature scope.
- Follow-Up:
  - None.

## LA-REV-227

- Scope: Lotus Report outbound identity headers
- Pattern: outbound integration hardening, private-banking tenant posture, and duplication removal
- Status: Hardened
- Finding Class: duplicated and weakly bounded downstream identity context
- Summary: Lotus Report adapter calls built outbound identity headers separately in each report
  path, defaulted tenant context to `default`, and passed raw `requested_by` values through
  headers and report options. This created inconsistent private-banking tenant posture and avoidable
  downstream header hygiene risk.
- Evidence:
  - `src/integrations/lotus_report/adapter.py` now uses one shared report-header builder across
    portfolio review, memo package, and policy sign-off package calls.
  - Outbound report calls use the governed `LOTUS_ADVISE_TENANT_ID` setting with `tenant-sg-001`
    default and bounded actor identity values for headers and report options.
  - Lotus Report adapter tests prove default tenant context, tenant override, invalid tenant
    fallback, and malformed actor fallback without opening new downstream contracts.
- Consequence:
  - Reporting integration calls carry consistent private-banking context and avoid propagating
    malformed actor identifiers into downstream report audit or render/archive jobs.
- Documentation:
  - No wiki source change is required. This tightens existing integration behavior without changing
    supported feature scope.
- Follow-Up:
  - None.

## LA-REV-228

- Scope: Lotus Core and Lotus Risk outbound correlation headers
- Pattern: integration boundary hardening, observability, and downstream diagnostics
- Status: Hardened
- Finding Class: weak outbound correlation-id normalization
- Summary: Lotus Core simulation and Lotus Risk enrichment clients passed caller-provided
  correlation identifiers directly into downstream headers. API entrypoints already normalize
  request IDs, but the integration clients lacked defensive boundary normalization for direct
  service use and tests.
- Evidence:
  - `src/integrations/lotus_core/simulation.py` now resolves outbound correlation IDs before
    calling Lotus Core.
  - `src/integrations/lotus_risk/enrichment.py` now resolves one outbound correlation ID per
    enrichment request and reuses it across retry attempts.
  - Integration client tests prove malformed correlation IDs are not propagated downstream.
- Consequence:
  - Downstream Core and Risk logs receive bounded correlation identifiers even when an internal
    caller bypasses normal API ingress validation.
- Documentation:
  - No wiki source change is required. This tightens existing observability hygiene without
    changing supported feature scope.
- Follow-Up:
  - None.

## LA-REV-229

- Scope: Lotus Report status retrieval path
- Pattern: outbound integration hardening and downstream URL trust boundary
- Status: Hardened
- Finding Class: weak downstream status-url constraint
- Summary: Lotus Report memo and policy package flows consumed the downstream `status_url`
  response value directly when retrieving render/archive status. The call still used the configured
  Lotus Report base URL, but the adapter did not explicitly constrain the response path to the
  expected report-job route.
- Evidence:
  - `src/integrations/lotus_report/adapter.py` now retrieves status only for clean relative
    `/reports/jobs/...` paths.
  - Lotus Report adapter tests prove valid status paths are fetched and untrusted absolute status
    URLs are ignored without losing the accepted report job posture.
- Consequence:
  - Advise no longer follows unexpected report status paths from downstream response payloads,
    keeping render/archive polling inside the documented Lotus Report job route.
- Documentation:
  - No wiki source change is required. This is boundary hardening for an existing integration path.
- Follow-Up:
  - None.

## LA-REV-230

- Scope: Lotus AI workflow-pack tenant context
- Pattern: private-banking tenant posture, outbound integration consistency, and runtime
  configuration hardening
- Status: Hardened
- Finding Class: inconsistent workflow-pack caller tenant context
- Summary: Lotus AI advisory copilot and workspace rationale calls carried tenant context, but
  proposal memo commentary, proposal narrative, and policy evidence workflow-pack calls did not.
  The tenant resolution was also duplicated and not bounded for invalid environment values.
- Evidence:
  - `src/integrations/lotus_ai/runtime_config.py` now exposes one bounded
    `resolve_lotus_ai_tenant_id()` helper with the governed `tenant-sg-001` default.
  - Advisory copilot, workspace rationale, proposal memo commentary, proposal narrative, and policy
    evidence adapters all use the shared tenant resolver in workflow-pack caller context.
  - Lotus AI runtime-config tests prove default, override, and invalid tenant fallback behavior.
  - Workflow-pack request tests prove memo, narrative, and policy evidence calls include the
    private-banking tenant context.
- Consequence:
  - All Advise-to-Lotus-AI workflow-pack calls now carry consistent bounded private-banking tenant
    context for downstream audit, review, and operational diagnostics.
- Documentation:
  - No wiki source change is required. This aligns existing AI integration calls with the already
    documented advisory AI tenant posture.
- Follow-Up:
  - None.

## LA-REV-231

- Scope: Lotus Report returned artifact URL boundary
- Pattern: output sanitization, downstream URL trust boundary, and client-safe metadata
- Status: Hardened
- Finding Class: untrusted downstream status URL echo
- Summary: After constraining report status polling to `/reports/jobs/...`, Advise still returned
  the raw downstream `status_url` as report `artifact_url` and explanation metadata. A malformed
  downstream value would not be fetched, but it could still leak into caller-visible report
  metadata.
- Evidence:
  - `src/integrations/lotus_report/adapter.py` now derives returned report status URLs from the
    same constrained report-job path helper used for polling.
  - Lotus Report adapter tests prove valid report-job paths are returned and untrusted absolute
    status URLs are omitted from `artifact_url` and explanation metadata.
- Consequence:
  - Advise callers only receive clean Lotus Report job paths for report artifacts and do not see
    malformed downstream status URLs.
- Documentation:
  - No wiki source change is required. This is integration output hardening for the existing report
    package path.
- Follow-Up:
  - None.

## LA-REV-232

- Scope: Cross-service idempotency key header boundary
- Pattern: input normalization, outbound header safety, replay-key governance
- Status: Hardened
- Finding Class: malformed idempotency key propagation
- Summary: The shared idempotency key normalizer trimmed whitespace and rejected blanks, but it did
  not reject control characters or oversized values. Downstream Core simulation could therefore
  receive a caller-provided malformed idempotency key in an outbound HTTP header if invoked below
  the route layer.
- Evidence:
  - `src/core/common/idempotency.py` now bounds idempotency keys to 128 characters and rejects
    control characters.
  - `src/integrations/lotus_core/simulation.py` normalizes the outbound idempotency key before
    adding the `Idempotency-Key` header.
  - Unit tests cover shared normalizer rejection and prove malformed Core simulation idempotency
    keys are omitted from outbound headers.
- Consequence:
  - Advisory write paths now share a safer replay-key boundary, and cross-service simulation calls
    cannot propagate malformed caller keys as HTTP metadata.
- Documentation:
  - No wiki source change is required. This is defensive header and replay-key hardening for
    existing contracts.
- Follow-Up:
  - None.

## LA-REV-233

- Scope: OpenAPI idempotency header contract
- Pattern: API documentation consistency, shared header governance, Swagger accuracy
- Status: Hardened
- Finding Class: API documentation drift
- Summary: Idempotency key handling is now bounded in shared runtime normalization, but OpenAPI
  parameter documentation still described replay keys only generically. That left Swagger weaker
  than the implemented API boundary and forced each route family to remember the same wording.
- Evidence:
  - `src/api/openapi_enrichment.py` centrally enriches every `Idempotency-Key` header with the
    shared 128-character boundary and business-clear replay-key wording.
  - OpenAPI contract tests assert every documented `Idempotency-Key` header carries the bounded
    schema and non-technical replay-key description.
- Consequence:
  - Swagger consumers see one consistent idempotency-key contract across RFC 23-28 proposal,
    memo, policy, cockpit, and copilot write paths.
- Documentation:
  - No wiki source change is required. This updates generated API contract truth for existing
    endpoints.
- Follow-Up:
  - None.

## LA-REV-234

- Scope: Governed advisory copilot AI output boundary
- Pattern: fail-closed AI output mapping, bounded advisor-facing content, RFC-0027 supportability
- Status: Hardened
- Finding Class: unbounded or empty AI draft output
- Summary: The RFC-0027 Lotus AI copilot adapter treated a completed workflow-pack execution as
  review-required output even when every returned section was invalid. It also accepted unbounded
  section and review-guidance counts and string lengths from downstream AI output.
- Evidence:
  - `src/integrations/lotus_ai/advisory_copilot.py` now fails closed with
    `LOTUS_AI_ADVISORY_COPILOT_INVALID_OUTPUT` when no valid bounded section remains.
  - The adapter bounds advisor-facing section count, section identifiers, titles, text, and review
    guidance before returning draft content.
  - Unit tests prove invalid/oversized output is not surfaced and valid output is bounded
    deterministically.
- Consequence:
  - RFC-0027 copilot output remains advisor-review only and cannot surface empty, malformed, or
    oversized downstream AI text as a usable advisory draft.
- Documentation:
  - No wiki source change is required. This hardens existing RFC-0027 runtime semantics without
    changing user-facing capability scope.
- Follow-Up:
  - None.

## LA-REV-235

- Scope: Proposal memo AI commentary output boundary
- Pattern: bounded advisor-use AI commentary, fail-closed output mapping, RFC-0024/RFC-0027 reuse
- Status: Hardened
- Finding Class: unbounded downstream AI commentary
- Summary: The memo commentary adapter already failed closed when no valid section remained, but it
  accepted unbounded downstream AI section counts, text sizes, and review-guidance payloads before
  returning advisor-use commentary.
- Evidence:
  - `src/integrations/lotus_ai/proposal_memo.py` now bounds memo AI section count, section
    identifiers, titles, text, and review guidance.
  - Unit tests prove oversized memo commentary is unavailable and valid multi-section output is
    capped deterministically.
- Consequence:
  - Memo commentary stays review-gated, advisor-use only, and safe for downstream API/UI consumers
    without accepting unbounded AI text.
- Documentation:
  - No wiki source change is required. This hardens existing memo AI commentary semantics.
- Follow-Up:
  - None.

## LA-REV-236

- Scope: Proposal narrative AI draft output boundary
- Pattern: bounded advisor-review AI narrative, fail-closed output mapping, RFC-0023 supportability
- Status: Hardened
- Finding Class: unbounded downstream AI narrative draft
- Summary: The proposal narrative AI adapter validated section keys and failed closed when no valid
  sections remained, but it still accepted unbounded downstream section counts and text sizes.
- Evidence:
  - `src/integrations/lotus_ai/proposal_narrative.py` now bounds narrative AI section count,
    section titles, and section text before returning advisor-review draft sections.
  - Unit tests prove oversized narrative output is unavailable and repeated valid sections are
    capped deterministically.
- Consequence:
  - RFC-0023 AI-assisted narrative remains advisor-review only and safe for downstream artifact,
    report, API, and UI surfaces without accepting unbounded AI text.
- Documentation:
  - No wiki source change is required. This hardens existing proposal narrative AI draft semantics.
- Follow-Up:
  - None.

## LA-REV-237

- Scope: Lotus AI output-safety reuse and policy evidence hardening
- Pattern: duplicate adapter parsing removal, bounded AI output mapping, policy-evidence safety
- Status: Hardened
- Finding Class: duplicated unbounded AI output handling
- Summary: Copilot, memo commentary, and narrative adapters duplicated bounded section parsing
  after recent hardening, while the policy-evidence adapter still used its older unbounded
  section and review-guidance mapping.
- Evidence:
  - `src/integrations/lotus_ai/output_safety.py` now owns reusable bounded review-section and
    guidance mapping.
  - Copilot, memo commentary, proposal narrative, and policy-evidence adapters consume the shared
    helper while preserving their domain-specific fail-closed behavior.
  - Policy-evidence tests now prove oversized AI evidence sections are rejected and valid output is
    capped deterministically; helper tests cover invalid item filtering and guidance bounds.
- Consequence:
  - Lotus AI adapters share one bounded output policy, reducing drift and making future RFC AI
    surfaces easier to harden consistently.
- Documentation:
  - No wiki source change is required. This is internal adapter modularity and safety hardening.
- Follow-Up:
  - None.

## LA-REV-238

- Scope: Workspace rationale Lotus AI output boundary
- Pattern: bounded AI assistant output, bounded workflow-pack run metadata, governed review actions
- Status: Hardened
- Finding Class: unbounded downstream AI output handling
- Summary: The workspace rationale adapter failed closed on missing AI output, but it accepted
  unbounded assistant text, review-action summaries, allowed-action strings, and workflow-pack
  supportability findings from lotus-ai.
- Evidence:
  - `src/integrations/lotus_ai/rationale.py` now bounds assistant output, review summaries,
    workflow-pack identifiers, run state fields, owner fields, and supportability findings.
  - Allowed review actions are constrained to the governed workspace rationale action set and
    de-duplicated before being returned to API consumers.
  - Unit tests prove oversized assistant output fails closed, review summaries are capped, and
    workflow-pack run metadata is bounded and filtered.
- Consequence:
  - RFC-0026/RFC-0027 workspace assistance remains evidence-grounded and review-gated without
    surfacing malformed, oversized, or non-governed lotus-ai metadata as trusted API output.
- Documentation:
  - No wiki source change is required. This hardens an existing internal AI adapter contract.
- Follow-Up:
  - None.

## LA-REV-239

- Scope: Workspace assistant request-boundary validation
- Pattern: API input bounds, advisor instruction normalization, review-action lineage validation
- Status: Hardened
- Finding Class: validation gap
- Summary: Workspace assistant output was bounded, but inbound advisor instructions and
  workflow-pack review-action text were not consistently normalized or length-bounded before
  reaching the Lotus AI integration seam.
- Evidence:
  - `src/core/workspace/models.py` now trims and bounds assistant requester ids, advisor
    instructions, workflow-pack run ids, reviewer ids, review reasons, and replacement run ids.
  - Workspace assistant schema exposes max-length bounds for request bodies.
  - Contract tests prove normalization, empty-value rejection, oversize rejection, and replacement
    lineage requirements.
- Consequence:
  - RFC-0026/RFC-0027 workspace assistance has a stronger API boundary before AI execution or
    review-action forwarding.
- Documentation:
  - No wiki source change is required. This is API contract hardening aligned with existing
    endpoint semantics.
- Follow-Up:
  - None.

## LA-REV-240

- Scope: Workspace rationale review-action lineage forwarding
- Pattern: cross-service lineage, review-action correlation, workspace-scoped AI handoff
- Status: Hardened
- Finding Class: auditability gap
- Summary: The workspace rationale review-action route was workspace-scoped in Advise, but the
  forwarded Lotus AI review-action request did not carry workspace context, source refs, or an
  Advise correlation id.
- Evidence:
  - `src/api/services/workspace_ai_service.py` passes the path workspace id into the Lotus AI
    review-action adapter.
  - `src/integrations/lotus_ai/rationale.py` forwards workflow-pack identity, workflow surface,
    workspace review context, workspace source refs, and a deterministic Advise correlation id.
  - API tests prove the workspace-scoped review action forwards the context and preserves
    replacement lineage.
- Consequence:
  - RFC-0026/RFC-0027 workspace AI review actions now retain clearer cross-service audit and
    lineage context at the Lotus AI boundary.
- Documentation:
  - No wiki source change is required. This strengthens existing internal review-action handoff
    evidence without changing the user-facing capability.
- Follow-Up:
  - None.

## LA-REV-241

- Scope: Advisory copilot action request-boundary validation
- Pattern: API input bounds, advisor instruction normalization, guardrail input hygiene
- Status: Hardened
- Finding Class: validation gap
- Summary: RFC-0027 copilot action requests described requested outputs, requested intents, and
  advisor instructions as bounded, but the API model did not enforce item counts, item lengths, or
  whitespace normalization before guardrail evaluation and Lotus AI execution.
- Evidence:
  - `src/core/advisory_copilot/api_models.py` now bounds requested outputs, requested intents,
    actor ids, and optional user instructions.
  - Action request validators trim and de-duplicate output and intent keys before request hashing
    and guardrail evaluation.
  - Application tests prove normalization plus empty, oversized-output, oversized-instruction, and
    oversized-review-actor rejection.
- Consequence:
  - RFC-0027 copilot execution receives cleaner bounded advisor input and preserves deterministic
    idempotency hashing without storing raw prompt text.
- Documentation:
  - No wiki source change is required. This is API model hardening aligned with existing copilot
    semantics.
- Follow-Up:
  - None.

## LA-REV-242

- Scope: Advisory copilot evidence-packet request identifiers
- Pattern: API identifier bounds, source-projection input hygiene, persistence key normalization
- Status: Hardened
- Finding Class: validation gap
- Summary: RFC-0027 copilot evidence-packet request models accepted unbounded packet, portfolio,
  and proposal identifiers before source projection and persistence.
- Evidence:
  - `src/core/advisory_copilot/api_models.py` now trims and bounds evidence-packet ids,
    portfolio ids, and proposal ids across direct packet creation, proposal-version source
    projection, and action execution requests.
  - Application tests prove identifier normalization and oversized or blank identifier rejection.
- Consequence:
  - Copilot evidence-packet persistence and source-projection requests have consistent bounded
    identifier hygiene before hashing, storage, and downstream action execution.
- Documentation:
  - No wiki source change is required. This is API model hardening aligned with existing copilot
    semantics.
- Follow-Up:
  - None.

## LA-REV-243

- Scope: Advisory copilot structured payload safety
- Pattern: persistence payload bounds, recursive guardrail hardening, direct service-call safety
- Status: Hardened
- Finding Class: validation and performance risk
- Summary: The RFC-0027 copilot service rejected raw AI storage keys in structured reason,
  lineage, and output payloads, but the recursive safety check did not bound depth, item count, or
  string length.
- Evidence:
  - `src/core/advisory_copilot/service.py` now enforces maximum structured payload depth, item
    count, and string length while preserving raw prompt key rejection.
  - Persistence tests prove oversized strings and oversized nested collections are rejected before
    run persistence.
- Consequence:
  - Direct service callers cannot bypass API model limits to persist arbitrarily large copilot
    reason, lineage, or output-section structures.
- Documentation:
  - No wiki source change is required. This is internal persistence safety hardening.
- Follow-Up:
  - None.

## LA-REV-244

- Scope: Advisory copilot evidence-section model bounds
- Pattern: source-evidence input hygiene, bounded evidence packet projection, API model safety
- Status: Hardened
- Finding Class: validation gap
- Summary: Direct RFC-0027 evidence-packet creation accepted source refs and source section
  summary items without model-level bounds, leaving direct API callers able to submit oversized
  evidence section payloads before packet hashing and persistence.
- Evidence:
  - `src/core/advisory_copilot/models.py` now trims and bounds source-ref identifiers, content
    hashes, section keys, section titles, source-ref counts, and summary item counts/lengths.
  - Evidence-section tests prove source evidence normalization plus empty source-ref, oversized
    summary text, and oversized summary-list rejection.
- Consequence:
  - Copilot evidence packets now apply consistent source-evidence bounds before role projection,
    hashing, persistence, and downstream AI action execution.
- Documentation:
  - No wiki source change is required. This is API/model hardening aligned with existing RFC-0027
    evidence-packet semantics.
- Follow-Up:
  - None.

## LA-REV-245

- Scope: Advisory copilot proposal-version source projection
- Pattern: source-projection hygiene, bounded generated evidence, repeatable RFC-0027 validation
- Status: Hardened
- Finding Class: validation and performance risk
- Summary: RFC-0027 proposal-version source projection could assemble oversized packet ids,
  lineage ids, source refs, hashes, and business summary strings from valid upstream proposal,
  memo, policy, and report data before evidence-packet model validation.
- Evidence:
  - `src/core/advisory_copilot/source_projection.py` now compacts oversized generated packet,
    source, lineage, and content-hash references deterministically and bounds generated business
    summary items before packet construction.
  - Application tests seed oversized proposal, memo, policy, report, and archive evidence and
    prove packet creation remains bounded without relying on full live validation to catch the
    issue.
- Consequence:
  - Canonical and expanded RFC-0027 validation can tolerate unusually verbose source evidence
    while preserving bounded audit references, deterministic packet identifiers, and downstream
    AI action safety.
- Documentation:
  - No wiki source change is required. This is internal source-projection hardening aligned with
    existing copilot evidence-packet semantics.
- Follow-Up:
  - None.

## LA-REV-246

- Scope: Advisory copilot evidence-packet domain model audit fields
- Pattern: domain-model boundary enforcement, audit reference bounds, direct service-call safety
- Status: Hardened
- Finding Class: validation gap
- Summary: RFC-0027 API request models bounded copilot evidence-packet identifiers, but the
  core evidence-packet model still accepted oversized packet ids, hashes, portfolio/proposal ids,
  lineage refs, unsupported-evidence messages, and oversized audit collections from direct
  service callers.
- Evidence:
  - `src/core/advisory_copilot/models.py` now trims and bounds packet identifiers, packet hashes,
    portfolio/proposal ids, lineage refs, unsupported-evidence advisor messages, and lineage or
    unsupported-evidence collection sizes.
  - Foundation tests prove normalization and rejection for oversized packet ids, hashes, lineage
    ids, unsupported-evidence messages, and oversized audit collections.
- Consequence:
  - RFC-0027 evidence packets now enforce bounded audit and persistence fields in the domain model
    itself, not only through API request DTOs or source-projection callers.
- Documentation:
  - No wiki source change is required. This is internal model hardening aligned with existing
    copilot packet semantics.
- Follow-Up:
  - None.

## LA-REV-247

- Scope: Advisory copilot persistence record audit fields
- Pattern: persistence DTO bounds, correlation fallback safety, direct record validation
- Status: Hardened
- Finding Class: validation and observability risk
- Summary: RFC-0027 persistence records had descriptive audit fields but did not enforce the
  same bounded identifier, hash, idempotency-key, correlation-id, actor, tenant, and workflow
  reference contracts that API and domain models now enforce.
- Evidence:
  - `src/core/advisory_copilot/records.py` now trims and bounds copilot run, evidence-packet,
    idempotency, and review record audit fields.
  - `src/core/advisory_copilot/application.py` now compacts generated correlation fallbacks when
    long packet or run identifiers would exceed the governed correlation-id limit.
  - Persistence and application tests prove record normalization, oversized audit-field rejection,
    and bounded generated correlation ids for maximum-length packet ids.
- Consequence:
  - Copilot persistence, replay, and review audit records now enforce bounded diagnostics and
    idempotency contracts even for direct service or repository-adjacent callers.
- Documentation:
  - No wiki source change is required. This is internal persistence-record hardening aligned with
    existing RFC-0027 copilot audit semantics.
- Follow-Up:
  - None.

## LA-REV-248

- Scope: Advisory copilot HTTP edge parameter bounds
- Pattern: API contract hardening, OpenAPI validation metadata, fail-fast request validation
- Status: Hardened
- Finding Class: validation and API quality gap
- Summary: RFC-0027 route path, header, and cursor parameters described governed identifiers
  but did not consistently expose or enforce the same length bounds already present in API
  request bodies, domain models, and persistence records.
- Evidence:
  - `src/api/proposals/routes_advisory_copilot.py` now applies explicit bounds to copilot
    evidence-packet ids, run ids, proposal/version path ids, idempotency headers, correlation
    headers, and pagination cursors.
  - API tests prove oversized path identifiers, review idempotency keys, correlation headers, and
    cursors fail with HTTP 422 before service/repository execution.
- Consequence:
  - Gateway and Workbench callers receive clearer RFC-0027 HTTP contract behavior, and generated
    OpenAPI documents now carry the same bounded-identifier posture as the backend models.
- Documentation:
  - No wiki source change is required. This is API contract metadata and validation hardening for
    existing copilot endpoints.
- Follow-Up:
  - None.

## LA-REV-249

- Scope: Advisory copilot lotus-ai adapter outbound context
- Pattern: integration boundary hardening, prompt-leak prevention, bounded downstream payloads
- Status: Hardened
- Finding Class: validation and security risk
- Summary: RFC-0027 service and API paths bounded copilot inputs, but direct lotus-ai adapter
  calls could still forward overlong generated correlation ids, duplicate/oversized requested
  output keys, overlong actor text, or raw prompt-like reason fields in the workflow-pack request.
- Evidence:
  - `src/integrations/lotus_ai/advisory_copilot.py` now compacts generated caller correlation
    ids, bounds outbound requested outputs and actor text, filters raw prompt/provider keys from
    reason payloads, bounds reason text/list values, caps source refs, and bounds workflow/model
    lineage values extracted from lotus-ai responses.
  - Adapter tests prove maximum-length packet ids, duplicated/oversized requested outputs,
    overlong actor text, overlong reason values, and raw prompt-like reason keys are handled
    before an outbound workflow-pack request is built.
- Consequence:
  - RFC-0027 copilot execution no longer relies solely on API/service callers for outbound safety;
    the lotus-ai adapter enforces bounded, business-safe payloads at the integration boundary.
- Documentation:
  - No wiki source change is required. This is integration-boundary hardening aligned with the
    existing governed copilot semantics.
- Follow-Up:
  - None.

## LA-REV-250

- Scope: Advisory copilot evidence-packet business-safe unsupported evidence
- Pattern: domain-model business-language guardrails, packet-size bounds, direct model safety
- Status: Hardened
- Finding Class: validation and documentation-quality risk
- Summary: RFC-0027 evidence-packet section text was checked for technical-copy leakage, but
  direct unsupported-evidence advisor messages and direct packet section collections were not
  explicitly bounded at the packet model boundary.
- Evidence:
  - `src/core/advisory_copilot/models.py` now rejects technical terms in unsupported-evidence
    advisor messages and caps direct evidence-packet section collections.
  - Foundation tests prove technical unsupported-evidence messages and oversized packet section
    collections are rejected before persistence or API serialization.
- Consequence:
  - Advisor-facing unsupported-evidence posture stays business-facing, and direct packet creation
    cannot create oversized evidence packets that bypass source-projection limits.
- Documentation:
  - No wiki source change is required. This is domain-model hardening for existing RFC-0027 packet
    semantics.
- Follow-Up:
  - None.

## LA-REV-251

- Scope: RFC-0028 bank-demo proof capture API metadata
- Pattern: proof-pack API contract hardening, metadata hygiene, correlation-id bounds
- Status: Hardened
- Finding Class: validation and security risk
- Summary: RFC-0028 proof-pack capture sanitized local artifact refs, but optional runtime
  metadata and the proof-pack correlation header were not explicitly bounded or screened for
  sensitive fragments before proof metadata construction.
- Evidence:
  - `src/api/routers/bank_demo_proof.py` now bounds repository SHA, service version, environment,
    and correlation-id metadata, normalizes blank optional metadata to fallback behavior, and
    rejects sensitive metadata fragments.
  - API tests prove oversized repository metadata, sensitive environment metadata, and oversized
    correlation headers fail with HTTP 422 before proof-pack construction.
- Consequence:
  - RFC-0028 proof bundles remain sanitized not only for artifact paths, but also for the metadata
    that Gateway, Workbench, wiki, and commercial proof materials consume.
- Documentation:
  - No wiki source change is required. This is API request-contract hardening for existing
    RFC-0028 proof-pack semantics.
- Follow-Up:
  - None.

## LA-REV-252

- Scope: RFC-0028 supported-claim wording model
- Pattern: business-facing documentation governance, claim-copy bounds, sensitive-term rejection
- Status: Hardened
- Finding Class: documentation-quality and security risk
- Summary: RFC-0028 supported-claim copy feeds README, wiki, demo, RFP, and commercial material,
  but the model did not enforce bounded claim identifiers or reject technical/sensitive terms in
  business-facing claim wording.
- Evidence:
  - `src/core/bank_demo_proof/models.py` now bounds supported-claim ids, proof requirement refs,
    titles, and claim text, normalizes claim copy, and rejects sensitive technical terms such as
    raw prompts, provider responses, credentials, secrets, and tokens.
  - Model tests prove unsafe claim wording and oversized claim identifiers are rejected before
    supported-claim registers can be used by documentation or proof-pack generation.
- Consequence:
  - RFC-0028 commercial and documentation outputs have stronger source-level controls over what
    can be promoted into business, sales, pre-sales, RFP, and client-demo material.
- Documentation:
  - No wiki source change is required. This is model-level governance for existing supported-claim
    semantics.
- Follow-Up:
  - None.

## LA-REV-253

- Scope: RFC-0028 proof-pack asset index model
- Pattern: proof asset sanitization, canonical hash validation, proof-pack metadata bounds
- Status: Hardened
- Finding Class: validation and security risk
- Summary: RFC-0028 proof-pack capture sanitized API request artifact references, but direct
  proof-pack and proof-asset model construction still accepted unsafe artifact paths, non-canonical
  content hashes, unbounded proof asset collections, and sensitive repository metadata.
- Evidence:
  - `src/core/bank_demo_proof/models.py` now bounds proof-pack identifiers, repository evidence,
    evidence/source-product reference lists, proof asset indexes, asset URIs, evidence refs, and
    content hashes at the domain model boundary.
  - Model tests prove URL/query artifact references, invalid content hashes, and sensitive
    repository SHA metadata are rejected before proof packs can be serialized for Gateway,
    Workbench, wiki, RFP, or commercial-material use.
- Consequence:
  - RFC-0028 proof-pack material now has a second line of defense below the API request model, so
    automation and future internal callers cannot bypass artifact and metadata hygiene controls.
- Documentation:
  - No wiki source change is required. This is source-level hardening for the existing RFC-0028
    proof-pack contract.
- Follow-Up:
  - None.

## LA-REV-254

- Scope: RFC-0028 commercial material model
- Pattern: business-facing material governance, source-ref hygiene, audience typing
- Status: Hardened
- Finding Class: documentation-quality and security risk
- Summary: RFC-0028 commercial material records drive sales, pre-sales, RFP, demo, architecture,
  and operations material, but the model still accepted loose string audiences, unsafe repository
  source references, unbounded material fields, and duplicate material identifiers.
- Evidence:
  - `src/core/bank_demo_proof/commercial_materials.py` now types material audiences with the
    supported-claim audience vocabulary, bounds identifiers/titles/source refs/lists, rejects
    sensitive technical copy, normalizes repository-local source references, and enforces unique
    material ids.
  - Commercial material tests prove the generated pack remains business usable while unsafe source
    refs, raw-prompt wording, unsupported audiences, and duplicate material ids are rejected.
- Consequence:
  - RFC-0028 commercial, RFP, demo, and wiki-facing material inventory has domain-model controls
    that match its client-facing use rather than relying only on generated docs remaining clean.
- Documentation:
  - No wiki source change is required. This hardens the source model behind existing RFC-0028
    commercial documentation and proof-pack output.
- Follow-Up:
  - None.

## LA-REV-255

- Scope: RFC-0028 document proof model
- Pattern: document-proof status bounds, output-format validation, duplicate-proof prevention
- Status: Hardened
- Finding Class: validation and documentation-quality risk
- Summary: RFC-0028 document proof rows demonstrate advisor-use memo and policy report posture,
  archive controls, and blocked client-ready publication, but the row model still accepted loose
  status strings, unsafe output-format values, sensitive degraded reasons, and duplicate document
  family rows.
- Evidence:
  - `src/core/bank_demo_proof/document_proof.py` now bounds document statuses, validates
    deterministic output formats, rejects sensitive degraded reason text, and requires unique
    document proof families in the summary.
  - Document proof tests prove unsafe output formats, raw-prompt degraded reasons, and duplicate
    document-family rows are rejected while the canonical proof summary remains valid.
- Consequence:
  - RFC-0028 document evidence is safer to promote into proof packs, commercial material, wiki
    content, and demo scripts without implying unsupported client-ready document release.
- Documentation:
  - No wiki source change is required. This is source-level validation for existing RFC-0028
    document-proof semantics.
- Follow-Up:
  - None.

## LA-REV-256

- Scope: RFC-0028 journey integration proof model
- Pattern: AI/policy proof status bounds, panel uniqueness, rule-count consistency
- Status: Hardened
- Finding Class: validation and overclaim risk
- Summary: RFC-0028 journey integration proof rows establish that AI, policy, and cockpit evidence
  remain advisor-assistive and source-owned, but several status fields, required-panel lists, and
  policy rule counts were still loosely validated at direct model construction.
- Evidence:
  - `src/core/bank_demo_proof/integration_proof.py` now bounds AI, policy, and summary status
    fields, rejects sensitive technical status text, caps panel/AI-row/unsupported-claim lists,
    requires unique Workbench panel ids, and prevents pending policy rule counts from exceeding
    material policy rule counts.
  - Integration proof tests prove canonical evidence still builds while provider-response status
    leakage, impossible rule counts, and duplicate panel requirements are rejected at model level.
- Consequence:
  - RFC-0028 proof material can rely on stronger source-level controls before journey evidence is
    used by Gateway, Workbench, commercial material, or wiki/demo proof packs.
- Documentation:
  - No wiki source change is required. This is source-level hardening for existing RFC-0028
    integration-proof semantics.
- Follow-Up:
  - None.

## LA-REV-257

- Scope: RFC-0028 material field review model
- Pattern: live-proof review sanitization, scalar observed-value validation, claim-ref bounds
- Status: Hardened
- Finding Class: validation and proof-quality risk
- Summary: RFC-0028 material field reviews are the lowest-level bridge from live runtime payloads
  to supported-claim promotion, but direct review construction still accepted structured observed
  payloads, sensitive observed text, and loose claim reference lists.
- Evidence:
  - `src/core/bank_demo_proof/capture.py` now bounds material review identifiers/source paths,
    expected posture text, observed scalar values, and claim refs while rejecting sensitive runtime
    fragments and structured observed payloads.
  - Capture tests prove raw-prompt observed values and structured observed payloads are rejected at
    the material-review boundary, while the canonical review path still passes.
- Consequence:
  - RFC-0028 proof automation has stronger lower-level protection before live evidence can be used
    to promote claims into proof packs, commercial material, or documentation.
- Documentation:
  - No wiki source change is required. This is source-level hardening for existing RFC-0028 proof
    capture semantics.
- Follow-Up:
  - None.

## LA-REV-258

- Scope: RFC-0026 advisor cockpit domain models
- Pattern: cockpit evidence bounds, business-safe copy validation, acknowledgement-state integrity
- Status: Hardened
- Finding Class: validation and supportability risk
- Summary: RFC-0026 cockpit models are source-owned and reused by Advise APIs, Gateway, Workbench,
  trust telemetry, and demo material, but direct model construction still accepted unbounded
  source/evidence text, sensitive technical copy, inconsistent unacknowledged acknowledgement
  details, and invalid negative action-count values.
- Evidence:
  - `src/core/advisor_cockpit/models.py` now bounds caller/action/evidence/lineage/dependency/
    readiness/snapshot identifiers and lists, rejects sensitive technical terms in support-safe
    copy, normalizes optional blank references to absent values, prevents unacknowledged states
    from carrying acknowledgement detail, and rejects negative snapshot action counts.
  - `src/core/advisor_cockpit/action_factory.py` now projects oversized upstream source
    identifiers, evidence references, lineage references, source refs, and summaries into bounded
    cockpit-safe references before constructing UI/API-facing action items.
  - Advisor cockpit model tests prove sensitive evidence summaries, oversized action ids,
    inconsistent acknowledgement state, and negative action counts are rejected at the core model
    boundary.
  - Advisor cockpit action-factory tests prove oversized policy source projections remain
    traceable and bounded before the broader copilot evidence-packet service consumes them.
- Consequence:
  - RFC-0026 cockpit output is safer for Gateway, Workbench, OpenAPI, wiki, and demo usage without
    relying on UI or route-layer filtering to keep advisor-facing source evidence business-safe.
- Documentation:
  - No wiki source change is required. This is source-level model hardening for existing RFC-0026
    cockpit semantics.
- Follow-Up:
  - Continue auditing cockpit construction input DTOs and source-read-model projections for the
    same direct-boundary guarantees.

## LA-REV-259

- Scope: RFC-0026 advisor cockpit preparation packet projection
- Pattern: shared cockpit projection bounds and preparation packet safety
- Status: Hardened
- Finding Class: API stability and source-projection risk
- Summary: Advisor cockpit action items now bounded oversized upstream identifiers through the
  action factory, but meeting-preparation packets were built separately in the service layer. A long
  proposal-derived preparation id or context ref could still fail the bounded packet model after
  the read model had already accepted the source projection.
- Evidence:
  - `src/core/advisor_cockpit/projection_bounds.py` centralizes stable bounded reference,
    optional-reference, content-hash, and business-summary projection helpers for cockpit outputs.
  - `src/core/advisor_cockpit/action_factory.py` now uses the shared projection-bound helpers
    instead of local helper copies.
  - `src/core/advisor_cockpit/service.py` now applies the same bounded reference and summary
    projection to meeting-preparation packet ids, context refs, evidence refs, and section
    source refs.
  - Advisor cockpit service tests prove preparation packets remain valid and traceable when
    source proposals carry oversized identifiers.
- Consequence:
  - RFC-0026 preparation packet APIs have the same source-projection safety posture as cockpit
    action APIs, reducing Gateway and Workbench failure risk from upstream identifier drift.
- Documentation:
  - No wiki source change is required. This is implementation-backed API stability hardening for
    existing RFC-0026 semantics.
- Follow-Up:
  - Continue auditing source read-model collection bounds and supportability metadata for runaway
    source batches.

## LA-REV-260

- Scope: RFC-0026 advisor cockpit source read-model batch boundary
- Pattern: governed source batch limit alignment
- Status: Hardened
- Finding Class: performance and direct-boundary risk
- Summary: `AdvisorCockpitService` loaded source records with a 100-record governed limit, but
  direct `AdvisorCockpitSourceBatch` construction did not encode that same boundary. Tests and
  internal callers could bypass the service limit and build runaway read-model batches.
- Evidence:
  - `src/core/advisor_cockpit/source_read_model.py` now owns
    `COCKPIT_SOURCE_BATCH_MAX_ITEMS` and applies it to every preloaded source collection in
    `AdvisorCockpitSourceBatch`.
  - `src/core/advisor_cockpit/service.py` now derives `COCKPIT_SOURCE_LIMIT` from the read-model
    batch contract rather than duplicating the numeric limit.
  - Source read-model tests prove oversized source batches are rejected at construction time and
    the exported limit remains the governed 100-record boundary.
- Consequence:
  - RFC-0026 cockpit read-model construction is consistent across service and direct usage,
    reducing runaway memory, latency, and unbounded-source risk before Gateway or Workbench reads.
- Documentation:
  - No wiki source change is required. This is a source-level operational hardening of existing
    RFC-0026 behavior.
- Follow-Up:
  - Continue auditing cockpit supportability metadata for bounded, business-facing output.

## LA-REV-261

- Scope: RFC-0026 advisor cockpit snapshot identity projection
- Pattern: bounded snapshot identifiers
- Status: Hardened
- Finding Class: API stability risk
- Summary: Cockpit action items and preparation packets were protected against oversized source
  references, but snapshot ids were still assembled directly from caller scope. A long portfolio or
  advisor scope could exceed the bounded snapshot model and fail an otherwise valid empty snapshot.
- Evidence:
  - `src/core/advisor_cockpit/service.py` now applies shared cockpit projection bounds when
    constructing `AdvisorCockpitOperatingSnapshot.snapshot_id`.
  - Advisor cockpit service tests prove oversized portfolio scopes produce stable bounded snapshot
    identifiers instead of failing model validation.
- Consequence:
  - RFC-0026 snapshot APIs remain stable for Gateway and Workbench even when upstream route or
    caller scope identifiers are unusually long.
- Documentation:
  - No wiki source change is required. This is source-level API stability hardening for existing
    RFC-0026 behavior.
- Follow-Up:
  - Continue auditing supportability and acknowledgement metadata for bounded business-facing
    output.

## LA-REV-262

- Scope: RFC-0026 advisor cockpit API response DTOs
- Pattern: bounded page and supportability response models
- Status: Hardened
- Finding Class: API contract and supportability risk
- Summary: The service enforced bounded cockpit pagination and supportability shapes, but the
  preparation-packet and supportability response DTOs did not encode those constraints directly.
  Direct model construction could accept oversized pages, invalid counts, oversized posture text,
  or unbounded supportability context.
- Evidence:
  - `src/core/advisor_cockpit/api_models.py` now bounds preparation packet pages, cursors,
    page sizes, counts, supportability dictionaries, acknowledgement audit dictionaries, posture
    identifiers, and unsupported capability lists.
  - Advisor cockpit API model tests prove oversized preparation pages, invalid page/count values,
    oversized supportability posture text, oversized supportability context, and oversized
    unsupported capability lists are rejected at the DTO boundary.
- Consequence:
  - RFC-0026 API responses now carry service-level pagination and supportability guarantees in
    the OpenAPI-backed DTOs themselves, improving Gateway, Workbench, and generated-client safety.
- Documentation:
  - No wiki source change is required. This is DTO-level contract hardening for existing
    RFC-0026 API semantics.
- Follow-Up:
  - Continue auditing acknowledgement persistence metadata and idempotency records for bounded
    support-safe fields.

## LA-REV-263

- Scope: RFC-0026 advisor cockpit acknowledgement persistence
- Pattern: bounded acknowledgement and idempotency metadata
- Status: Hardened
- Finding Class: persistence and API stability risk
- Summary: Cockpit action ids are bounded, but acknowledgement ids were derived as `ack_` plus the
  action id. Boundary-length action ids could therefore create acknowledgement ids that later fail
  API-facing acknowledgement-state validation. Persistence records also lacked direct bounds for
  acknowledgement, idempotency, correlation, and support-note metadata.
- Evidence:
  - `src/core/advisor_cockpit/persistence.py` now bounds acknowledgement records, idempotency
    records, request hashes, correlation ids, reason metadata, actor ids, and support-safe notes.
  - `src/core/advisor_cockpit/service.py` now derives acknowledgement ids through the shared
    cockpit projection-bound helper.
  - Advisor cockpit service tests prove direct persistence records bound oversized metadata and
    service acknowledgements remain valid when action ids are already at the model boundary.
- Consequence:
  - RFC-0026 acknowledgement replay and audit paths remain stable for Gateway and Workbench without
    relying on shorter canonical action ids.
- Documentation:
  - No wiki source change is required. This is persistence/API stability hardening for existing
    RFC-0026 acknowledgement semantics.
- Follow-Up:
  - Continue auditing route-level path/query inputs for bounded, support-safe service entry.

## LA-REV-264

- Scope: RFC-0026 advisor cockpit route input contract
- Pattern: route-level bounded path, query, and header inputs
- Status: Hardened
- Finding Class: API contract and validation risk
- Summary: Core models, service projections, and persistence records were bounded, but the FastAPI
  cockpit routes still accepted oversized portfolio, advisor, cursor, action id, idempotency, and
  correlation values before handing them to the service. Some oversized inputs could be rejected
  downstream or projected later, but the OpenAPI contract did not advertise the route boundary.
- Evidence:
  - `src/api/proposals/routes_advisor_cockpit.py` now applies max-length constraints to cockpit
    route path parameters, query parameters, and headers, and uses the shared cockpit page-size
    maximum for route-level pagination.
  - Advisor cockpit API tests prove oversized query, cursor, path, and idempotency-header values
    fail with HTTP 422 at the route boundary.
  - OpenAPI tests prove advisor id, preparation cursor, limit, and 128-character idempotency
    header constraints are published in the schema.
- Consequence:
  - RFC-0026 route contracts now fail invalid inputs consistently before service execution and are
    clearer for Gateway, Workbench, generated clients, and operational runbooks.
- Documentation:
  - No wiki source change is required. This is OpenAPI-backed route contract hardening for existing
    RFC-0026 API behavior.
- Follow-Up:
  - Continue auditing RFC-0027/RFC-0028 route contracts for the same boundary consistency where
    implementation-backed APIs already exist.

## LA-REV-265

- Scope: RFC-0027 governed advisory copilot response DTOs
- Pattern: bounded run-page and supportability response contracts
- Status: Hardened
- Finding Class: API contract and generated-client safety risk
- Summary: The copilot list route bounded page size to 100 and supportability was static, but the
  response DTOs did not encode the same bounds directly. Direct model construction and generated
  client schemas could therefore miss page-size, cursor, support-status, and unsupported-boundary
  limits already expected by the service contract.
- Evidence:
  - `src/core/advisory_copilot/api_models.py` now bounds copilot run pages, cursors,
    supportability status text, client-ready publication posture, action-family lists, and
    unsupported-boundary messages.
  - Advisory copilot API tests prove boundary-size run pages and cursors are accepted while
    oversized pages, oversized cursors, oversized support statuses, and oversized boundary lists
    are rejected at the DTO boundary.
- Consequence:
  - RFC-0027 response contracts now publish service-level limits through OpenAPI-backed models,
    improving Gateway, Workbench, and generated-client safety without changing supported
    business behavior.
- Documentation:
  - No wiki source change is required. This is DTO-level contract hardening for existing
    RFC-0027 API semantics.
- Follow-Up:
  - Continue auditing RFC-0027 persistence and source-projection boundaries before moving to
    RFC-0028 route and report-proof contracts.

## LA-REV-266

- Scope: RFC-0027 governed advisory copilot evidence source inputs
- Pattern: bounded source-section and audience projection contracts
- Status: Hardened
- Finding Class: API validation, performance, and projection safety risk
- Summary: Evidence-packet output models bounded projected packet sections, but the create-request
  DTO did not directly bound inbound source sections and source-section audience lists were not
  normalized or deduplicated at the domain boundary. Oversized source projections could therefore
  be accepted before being narrowed by the packet builder.
- Evidence:
  - `src/core/advisory_copilot/models.py` now publishes the packet-section limit, bounds supported
    and allowed audience lists, and normalizes source-section audiences with duplicate removal.
  - `src/core/advisory_copilot/api_models.py` now bounds inbound evidence-packet source sections
    to the same domain packet-section limit.
  - Advisory copilot API and domain tests prove valid boundary inputs pass while oversized source
    sections, empty audiences, and oversized/invalid audience lists fail at the correct boundary.
- Consequence:
  - RFC-0027 evidence packet creation now fails invalid or excessive source projections before
    service execution, reducing avoidable runtime work and keeping Gateway/Workbench contracts
    aligned with the domain projection model.
- Documentation:
  - No wiki source change is required. This is input-boundary hardening for existing RFC-0027
    evidence-packet semantics.
- Follow-Up:
  - Continue auditing RFC-0027 persistence JSON payload sizing and source-projection reference
    helpers for any remaining duplicated or weak boundary rules.

## LA-REV-267

- Scope: RFC-0027 governed advisory copilot persistence records
- Pattern: bounded persisted JSON/list payload contracts
- Status: Hardened
- Finding Class: persistence, auditability, and generated-schema safety risk
- Summary: The copilot service rejects oversized nested structured payloads before persistence,
  but durable record DTOs did not encode top-level JSON/list bounds for packet, request, output,
  guidance, guardrail, lineage, or review reason fields. Direct record construction could therefore
  bypass limits that the service relies on for safe audit replay and generated schemas.
- Evidence:
  - `src/core/advisory_copilot/records.py` now bounds top-level JSON dictionaries, output section
    lists, review guidance lists, and guardrail result lists on copilot run, packet, and review
    records.
  - Persistence tests prove review guidance and guardrail reason lists are normalized and that
    oversized output sections, lineage dictionaries, packet reasons, review reasons, guidance
    lists, and guardrail reason text are rejected at the record boundary.
- Consequence:
  - RFC-0027 durable audit records now reflect the service's bounded-payload contract more
    directly, reducing replay, storage, and generated-client drift risk.
- Documentation:
  - No wiki source change is required. This is persistence contract hardening for existing
    RFC-0027 copilot audit semantics.
- Follow-Up:
  - Continue auditing RFC-0027 source-projection helpers and then move to RFC-0028 route/report
    proof contracts.

## LA-REV-268

- Scope: RFC-0028 bank-demo proof runtime posture contract
- Pattern: bounded runtime endpoint and base-url evidence
- Status: Hardened
- Finding Class: API contract, proof-pack safety, and generated-schema risk
- Summary: Runtime posture evidence sanitized endpoint summaries, but the model did not publish
  explicit endpoint path, base URL, or endpoint-inventory bounds. Gateway, Workbench, and generated
  clients therefore could not rely on the schema to reject oversized runtime-proof metadata before
  proof-pack construction.
- Evidence:
  - `src/core/bank_demo_proof/runtime_posture.py` now bounds endpoint paths, runtime base URLs,
    and endpoint inventories while preserving existing summary redaction/truncation behavior.
  - RFC-0028 backend proof tests prove sensitive runtime summary fields are redacted and oversized
    endpoint paths, base URLs, and endpoint inventories are rejected.
  - Bank-demo proof API OpenAPI tests prove the new runtime posture bounds are published in the
    schema used by Gateway and Workbench.
- Consequence:
  - RFC-0028 proof-pack capture now has a clearer machine-readable runtime evidence envelope and
    fails malformed runtime posture before material-field review or proof-pack assembly.
- Documentation:
  - No wiki source change is required. This is schema-level hardening for existing RFC-0028
    runtime-proof semantics.
- Follow-Up:
  - Continue auditing RFC-0028 proof-capture request payload bounds, metadata normalization, and
    proof bundle list/dictionary limits.

## LA-REV-269

- Scope: RFC-0028 bank-demo proof capture envelope
- Pattern: bounded proof metadata, live payload, and material-review projections
- Status: Hardened
- Finding Class: API contract, auditability, and proof-pack safety risk
- Summary: The proof-pack route sanitized runtime content before material assembly, but request
  payloads and capture metadata did not publish complete size and sensitivity constraints at every
  boundary. Oversized live-runtime dictionaries, non-UTC metadata timestamps, or sensitive
  metadata labels could therefore reach proof-pack construction before being rejected or obscured.
- Evidence:
  - `src/api/routers/bank_demo_proof.py` now bounds live runtime payload top-level keys in the
    request schema used by Gateway and generated clients.
  - `src/core/bank_demo_proof/capture.py` now bounds proof metadata identifiers and labels,
    enforces timezone-aware UTC capture timestamps, and limits proof-bundle runtime summaries and
    material field review rows.
  - RFC-0028 API and engine tests prove oversized request payloads, sensitive metadata, overlong
    metadata labels, and non-UTC timestamps fail at the correct boundary while normal proof
    capture still succeeds.
- Consequence:
  - RFC-0028 proof-pack generation now has a tighter repeatable evidence envelope, reducing
    storage, replay, and client-contract drift risk without changing supported bank-demo claims.
- Documentation:
  - No wiki source change is required. This is envelope hardening for existing RFC-0028 proof
    capture semantics.
- Follow-Up:
  - Continue auditing RFC-0028 report/export contracts and any remaining canonical automation
    evidence gaps before claiming RFC closure.

## LA-REV-270

- Scope: RFC-0028 commercial material governance
- Pattern: exact blocked-claim coverage and duplicate-proof prevention
- Status: Hardened
- Finding Class: client-facing material governance and wording-drift risk
- Summary: The commercial material pack declared blocked claims that must remain excluded from
  every product, demo, RFP, security, architecture, ROI, and operator asset, but validation only
  checked for a loose client-ready substring. A material could therefore omit other blocked claims
  or pass a misleading substring while still appearing governed.
- Evidence:
  - `src/core/bank_demo_proof/commercial_materials.py` now requires every material to exclude the
    exact blocked-claim set declared by the pack and rejects duplicate claim references and
    audiences.
  - Commercial material tests prove the generated pack excludes all blocked claims in every
    material, rejects duplicate references/audiences, and fails substring-only or incomplete
    blocked-claim coverage.
- Consequence:
  - RFC-0028 commercial/RFP material governance now prevents accidental overclaiming across
    client-ready publication, external communication, approval/sign-off, legal advice, bank-specific
    attestation, and OMS/order/fill/settlement boundaries.
- Documentation:
  - No wiki source change is required. This tightens validation for the existing RFC-0028
    commercial material contract without changing supported feature truth.
- Follow-Up:
  - Continue auditing proof-pack writer artifacts, manifest shape, and local output references for
    any remaining repeatability or disclosure gaps.

## LA-REV-271

- Scope: RFC-0028 backend proof writer manifest
- Pattern: portable bundle-local artifact references
- Status: Hardened
- Finding Class: evidence portability and local-path disclosure risk
- Summary: `manifest.json` recorded artifact paths using the concrete output directory. When
  operators wrote proof evidence to an absolute temporary or workstation path, the manifest could
  leak machine-specific filesystem locations into otherwise sanitized proof evidence.
- Evidence:
  - `scripts/capture_rfc0028_backend_proof.py` now writes manifest artifact references relative to
    the proof bundle root.
  - The proof-capture writer test now uses an absolute pytest temp directory and proves manifest
    artifact references stay bundle-local and do not include the temp path.
- Consequence:
  - RFC-0028 proof bundles are more portable for review, archive, and client-demo preparation while
    preserving the generated proof asset content and supported-claim posture.
- Documentation:
  - No wiki source change is required. This is evidence-manifest hardening for the existing
    proof-capture script behavior.
- Follow-Up:
  - Continue auditing runtime probe configuration, CLI validation, and proof-pack summary copy for
    remaining operator-experience or disclosure issues.

## LA-REV-272

- Scope: RFC-0028 runtime probe configuration
- Pattern: pre-probe base URL validation
- Status: Hardened
- Finding Class: runtime configuration and sensitive URL disclosure risk
- Summary: Runtime posture models rejected base URLs containing credentials, query strings, or
  fragments, but the proof-capture script normalized that posture after probe calls were assembled.
  An unsafe operator-provided URL could therefore be used in an HTTP request before the final
  posture model rejected it.
- Evidence:
  - `src/core/bank_demo_proof/runtime_posture.py` now exposes a reusable
    `normalize_runtime_base_url(...)` helper used by the model validator and proof-capture script.
  - `scripts/capture_rfc0028_backend_proof.py` validates the base URL before probed and
    not-probed runtime posture construction.
  - Proof-capture script tests prove credential/query/fragment URLs fail before capture and that
    safe runtime paths are normalized consistently.
- Consequence:
  - RFC-0028 runtime proof capture fails unsafe runtime configuration before any HTTP probe,
    strengthening operator safety and keeping proof evidence free of sensitive URL material.
- Documentation:
  - No wiki source change is required. This is runtime-capture validation hardening for the
    existing RFC-0028 proof workflow.
- Follow-Up:
  - Continue auditing proof-pack summary copy and script source-path handling before RFC-0028
    closure review.

## LA-REV-273

- Scope: RFC-0028 demo scenario contract
- Pattern: bounded scenario steps and source/evidence references
- Status: Hardened
- Finding Class: contract drift, generated-schema, and proof-governance risk
- Summary: RFC-0028 proof packs were tightly bounded, but the upstream scenario contract still
  allowed weakly bounded scenario step fields, duplicated step evidence references, duplicated
  step ids, and sensitive technical wording in scenario titles or unsupported-boundary text.
- Evidence:
  - `src/core/bank_demo_proof/models.py` now bounds scenario step identifiers, titles, owner
    repositories, evidence references, Workbench panel references, source products, evidence
    markers, unsupported boundaries, and step inventories.
  - Scenario contract validation now rejects duplicate step ids, duplicate step reference lists,
    and sensitive technical wording before proof-pack construction.
  - RFC-0028 proof model tests cover sensitive titles, duplicate refs, duplicate step ids, and
    unsafe unsupported-boundary wording.
- Consequence:
  - RFC-0028 scenario contracts now provide a stronger source-of-truth envelope for Advise,
    Gateway, Workbench, and platform canonical automation without allowing duplicated or unsafe
    scenario evidence to pass into proof packs.
- Documentation:
  - No wiki source change is required. This strengthens the existing scenario contract rather than
    changing the documented RFC-0028 feature posture.
- Follow-Up:
  - Continue auditing supported-claim register list bounds and wording rules before RFC-0028
    closure review.

## LA-REV-274

- Scope: RFC-0028 supported-claim register
- Pattern: bounded claim taxonomy, wording, and artifact policy lists
- Status: Hardened
- Finding Class: supported-claim governance and generated-schema risk
- Summary: The supported-claim register enforced classification/evidence rules, but claim
  audience/material/reference lists, wording guardrails, claim inventories, and artifact policy
  access-class lists did not consistently encode size and uniqueness constraints. This left room
  for duplicated or oversized claim governance data to flow into demo, RFP, and proof material.
- Evidence:
  - `src/core/bank_demo_proof/models.py` now bounds claim audiences, allowed materials,
    evidence refs, proof requirements, wording rules, claim inventories, artifact policy classes,
    sensitive-material rules, and register identifiers.
  - Claim and artifact policy validators now reject duplicated taxonomy lists, duplicated wording
    rules, duplicated access classes, duplicated sensitive-material rules, and sensitive claim refs.
  - RFC-0028 proof model tests cover duplicate audiences, duplicate wording, duplicate access
    classes, and duplicate sensitive-material policy rules.
- Consequence:
  - RFC-0028 supported claims now have a tighter machine-readable governance envelope for
    commercial material generation and front-office canonical proof, reducing wording drift and
    generated-client ambiguity.
- Documentation:
  - No wiki source change is required. This strengthens the existing supported-claim contract
    without changing documented supported-feature truth.
- Follow-Up:
  - Continue auditing proof-pack asset uniqueness and repository-SHA metadata before RFC-0028
    closure review.

## LA-REV-275

- Scope: RFC-0028 proof-pack audit record
- Pattern: UTC proof timestamps, unique assets, and normalized repository evidence
- Status: Hardened
- Finding Class: audit replay, lineage, and proof-pack integrity risk
- Summary: The proof-pack model required canonical markers and blocked client-ready approval, but
  direct proof-pack construction did not enforce UTC generation timestamps, duplicate proof-asset
  ids, sensitive repository names, or repository-name collisions after normalization.
- Evidence:
  - `src/core/bank_demo_proof/models.py` now requires timezone-aware UTC proof-pack timestamps,
    rejects sensitive or oversized repository names, detects repository-name collisions after
    normalization, and rejects duplicate proof-pack asset ids.
  - RFC-0028 proof model tests cover non-UTC timestamps, sensitive repository names,
    normalization collisions, and duplicate asset ids.
- Consequence:
  - RFC-0028 proof packs are safer to replay, compare, archive, and present because their core
    audit identity cannot silently contain ambiguous repository evidence or duplicate assets.
- Documentation:
  - No wiki source change is required. This is proof-pack integrity hardening for existing
    RFC-0028 output.
- Follow-Up:
  - Continue auditing document and integration proof source-payload validation before RFC-0028
    closure review.

## LA-REV-276

- Scope: RFC-0028 document proof source projection
- Pattern: governed missing/invalid source-field failures
- Status: Hardened
- Finding Class: live-validation diagnosability and source-payload safety risk
- Summary: Document proof projection relied on direct dictionary indexing for required report,
  render, archive, and client-ready fields, and treated `requested_output_formats` as iterable
  without first proving it was a list. Malformed live-runtime payloads could therefore surface raw
  `KeyError` failures or character-by-character format validation instead of governed RFC-0028
  source-field errors.
- Evidence:
  - `src/core/bank_demo_proof/document_proof.py` now validates required source fields through
    governed `RFC0028_DOCUMENT_PROOF_FIELD_MISSING` errors and rejects non-list output format
    payloads through `RFC0028_DOCUMENT_PROOF_FIELD_INVALID`.
  - Document proof tests cover missing render-reference source fields and invalid scalar output
    format payloads while preserving normal proof-capture behavior.
- Consequence:
  - RFC-0028 live validation and proof capture now fail malformed document source payloads at the
    document-proof boundary with repeatable, test-covered diagnostics.
- Documentation:
  - No wiki source change is required. This is source-payload validation hardening for existing
    document proof semantics.
- Follow-Up:
  - Continue auditing integration proof source-field validation before RFC-0028 closure review.

## LA-REV-277

- Scope: RFC-0028 journey integration proof source projection
- Pattern: governed missing/invalid AI and policy source-field failures
- Status: Hardened
- Finding Class: source-payload coercion and live-validation diagnosability risk
- Summary: Journey integration proof projection used direct dictionary indexing and Python truthy
  coercion for AI, policy, and copilot source fields. Malformed live-runtime payloads could surface
  raw `KeyError` failures, treat string booleans as true, or accept boolean rule counts before the
  proof model had enough context to reject the source shape.
- Evidence:
  - `src/core/bank_demo_proof/integration_proof.py` now uses governed required-value, boolean, and
    integer source helpers that emit `RFC0028_INTEGRATION_PROOF_FIELD_MISSING` and
    `RFC0028_INTEGRATION_PROOF_FIELD_INVALID` diagnostics.
  - Integration proof tests cover missing policy-pack ids, invalid string boolean fields, invalid
    boolean rule counts, and normal proof-capture behavior.
- Consequence:
  - RFC-0028 integration proof capture now rejects malformed AI/policy/cockpit source payloads at
    the projection boundary with repeatable diagnostics instead of relying on Python coercion or
    ungoverned exceptions.
- Documentation:
  - No wiki source change is required. This is source-payload validation hardening for existing
    integration proof semantics.
- Follow-Up:
  - Continue auditing script CLI/output handling and then run RFC-0028 closure reconciliation.

## LA-REV-278

- Scope: RFC-0028 proof-capture CLI artifact references
- Pattern: separate filesystem output from proof asset references
- Status: Hardened
- Finding Class: operator experience, portability, and local-path disclosure risk
- Summary: The proof-capture CLI used `--output-dir` as both the filesystem write location and
  proof-pack asset reference prefix. Relative output directories worked, but absolute operator
  paths could either fail proof-asset validation or risk coupling proof references to local
  workstation paths.
- Evidence:
  - `scripts/capture_rfc0028_backend_proof.py` now supports an explicit `--artifact-ref-prefix`
    and derives a safe relative default when `--output-dir` is absolute.
  - Script tests prove absolute output directories fall back to the governed default artifact ref
    prefix, custom relative prefixes are preserved, and sensitive prefixes are rejected.
- Consequence:
  - RFC-0028 proof capture can write evidence to operator-selected filesystem locations while
    preserving portable, sanitized proof-pack asset references for review and archive.
- Documentation:
  - No wiki source change is required. The CLI behavior is backward compatible for the governed
    default output path and strengthens absolute-output handling.
- Follow-Up:
  - Run RFC-0028 closure reconciliation and decide whether this branch is ready for the next PR
    checkpoint.

## LA-REV-279

- Scope: RFC-0028 proof-capture operator documentation
- Pattern: implementation-backed CLI/runbook alignment
- Status: Hardened
- Finding Class: documentation drift and operator misuse risk
- Summary: The proof-capture CLI gained `--artifact-ref-prefix` so operators can write evidence to
  absolute filesystem locations while keeping proof-pack asset references portable, but README,
  RFC, and wiki runbook text still described only `--output-dir`.
- Evidence:
  - `README.md`, `docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md`, and
    `wiki/Operations-Runbook.md` now explain when to use `--artifact-ref-prefix` and why proof-pack
    references must remain local-relative and sanitized.
- Consequence:
  - Operators, reviewers, and demo-prep users have implementation-backed instructions that prevent
    local path leakage and artifact-reference drift in RFC-0028 proof packs.
- Documentation:
  - Wiki source changed in this slice; run `Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-advise`
    before merge and publish after merge to `main`.
- Follow-Up:
  - Run RFC-0028 closure reconciliation and repo wiki check before PR handoff.

## LA-REV-280

- Scope: Lotus Report integration request mapping
- Pattern: adapter boundary separation and safe report-status follow-up URLs
- Status: Hardened
- Finding Class: service-boundary modularity, sensitive-data handling, and test gap
- Summary: The Lotus Report adapter mixed HTTP transport with Advise-to-Report request/header
  projection, output-format normalization, status-path filtering, and fail-closed source-field
  validation. The same adapter also accepted same-path report status URLs with query material,
  which could allow token-like data to appear in follow-up requests or response evidence.
- Evidence:
  - `src/integrations/lotus_report/request_mapping.py` now owns report request/header mapping,
    source date/currency extraction, output-format normalization, bounded actor/tenant identity,
    status-path filtering, and response-status normalization.
  - `src/integrations/lotus_report/adapter.py` now keeps the HTTP transport and dependency
    handling while translating mapping failures into the existing
    `LOTUS_REPORT_REQUEST_UNAVAILABLE` fail-closed posture.
  - `tests/unit/advisory/api/test_lotus_report_request_mapping.py` covers direct mapping,
    boundary preservation for memo and policy packages, bounded headers, output formats, trusted
    status paths, and missing source identity failures.
  - `tests/unit/advisory/api/test_lotus_report_adapter.py` now proves status URLs with query
    material are not followed and are not returned as artifact URLs.
- Consequence:
  - Lotus Report handoff mapping is reusable and testable outside the HTTP adapter, while
    follow-up status evidence remains local-path-only and sanitized.
- Documentation:
  - No README or wiki source change is required. This is an internal service-boundary hardening
    slice with unchanged public API semantics.
- Follow-Up:
  - Continue separating response projection from transport if future report-package changes add
    more explanation or lineage mapping complexity.

## LA-REV-281

- Scope: Lotus Report integration response projection
- Pattern: transport orchestration separated from advisory evidence-envelope construction
- Status: Hardened
- Finding Class: service-boundary modularity, lineage projection, and test gap
- Summary: After request mapping was extracted, the Lotus Report adapter still constructed
  portfolio-review, memo-package, and policy sign-off response explanations inline with HTTP
  transport. That kept report/render/archive lineage projection harder to test without fake HTTP
  clients and made future explanation changes more likely to couple to transport code.
- Evidence:
  - `src/integrations/lotus_report/response_projection.py` now owns
    `ProposalReportResponse` construction for portfolio review, advisor memo report packages, and
    policy sign-off report packages.
  - `src/integrations/lotus_report/adapter.py` now orchestrates override handling, base URL
    resolution, HTTP calls, status fetches, and fail-closed translation while delegating
    evidence-envelope projection to the response projection module.
  - `tests/unit/advisory/api/test_lotus_report_response_projection.py` proves bounded reviewed
    narrative summaries, blocked client-ready posture for memo and policy packages, render/archive
    refs, and fail-closed missing report-job identity behavior without HTTP fakes.
- Consequence:
  - Report response lineage is independently testable and the adapter is materially smaller,
    clearer, and less coupled to business evidence projection.
- Documentation:
  - No README or wiki source change is required. This is internal integration-boundary hardening
    with unchanged public API semantics.
- Follow-Up:
  - Continue auditing other large adapters for the same request mapping / transport / response
    projection separation pattern.

## LA-REV-282

- Scope: Lotus Risk concentration request mapping
- Pattern: risk-enrichment transport separated from concentration payload construction
- Status: Hardened
- Finding Class: service-boundary modularity and test gap
- Summary: The Lotus Risk enrichment client mixed retrying HTTP transport, upstream response
  validation, stateless concentration payload construction, stateful simulation payload
  construction, cash-position projection, security-trade change mapping, issuer mapping, and
  response application in one module. That made the concentration request contract harder to test
  without fake HTTP clients and made future risk-contract changes more likely to couple to retry
  behavior.
- Evidence:
  - `src/integrations/lotus_risk/concentration_request.py` now owns stateless and stateful
    concentration request construction, including cash positions, projected positions, simulation
    changes, issuer mappings, and enrichment-policy selection.
  - `src/integrations/lotus_risk/enrichment.py` now keeps runtime configuration, retrying HTTP
    transport, upstream response validation, and risk-lens application.
  - `tests/unit/advisory/api/test_lotus_risk_concentration_request.py` proves stateless
    position/cash projection and stateful simulation-change/issuer-mapping projection without
    using HTTP fakes.
- Consequence:
  - Risk enrichment request mapping is reusable and directly testable, while transport retry
    behavior remains isolated from concentration-payload business mapping.
- Documentation:
  - No README or wiki source change is required. This is internal integration-boundary hardening
    with unchanged public API semantics.
- Follow-Up:
  - Continue auditing the remaining risk enrichment response-application and retry diagnostics
    boundaries if later slices touch risk-lens behavior.

## LA-REV-283

- Scope: Lotus Risk concentration response projection
- Pattern: upstream risk contract and risk-lens application separated from HTTP retry transport
- Status: Hardened
- Finding Class: service-boundary modularity and test gap
- Summary: After concentration request mapping was extracted, the Lotus Risk enrichment client
  still owned upstream response DTOs and risk-lens explanation projection alongside retrying HTTP
  transport. That made the canonical `proposal.explanation.risk_lens` envelope harder to test
  directly and kept upstream contract validation coupled to HTTP fakes.
- Evidence:
  - `src/integrations/lotus_risk/concentration_response.py` now owns the
    `LotusRiskConcentrationResponse` DTO family and `apply_concentration_response`.
  - `src/integrations/lotus_risk/enrichment.py` now keeps runtime configuration, retrying HTTP
    transport, upstream JSON validation, and orchestration.
  - `tests/unit/advisory/api/test_lotus_risk_concentration_response.py` proves canonical risk-lens
    projection, preservation of existing explanation fields, decimal JSON projection, and
    rejection of wrong upstream source-service identity without HTTP fakes.
- Consequence:
  - The risk-lens evidence envelope is independently testable and the enrichment transport module
    is smaller, clearer, and less coupled to risk-domain projection.
- Documentation:
  - No README or wiki source change is required. This is internal integration-boundary hardening
    with unchanged public API semantics.
- Follow-Up:
  - Continue auditing retry diagnostics and other integration adapters for similarly separable
    request/response contracts.

## LA-REV-284

- Scope: Lotus AI workflow-pack response parsing
- Pattern: duplicated provider response normalization extracted from individual adapters
- Status: Hardened
- Finding Class: service-boundary modularity and test gap
- Summary: The advisory copilot, proposal narrative, proposal memo commentary, policy evidence,
  and workspace rationale adapters each repeated defensive dict extraction, provider detail
  handling, workflow-run id extraction, and model-version extraction. That duplication made
  fail-closed behavior easier to drift across AI-assisted advisory surfaces and kept lineage
  parsing tied to each adapter's transport code.
- Evidence:
  - `src/integrations/lotus_ai/workflow_response.py` now owns shared provider response
    normalization for safe object extraction, workflow-run id, model version, bounded provider
    detail, and optional bounded text.
  - The Lotus AI adapters now delegate common response parsing while retaining domain-specific
    output validation, lineage construction, guardrails, and review guidance.
  - `tests/unit/advisory/api/test_lotus_ai_workflow_response.py` proves fail-closed handling for
    malformed provider payloads, trimmed lineage values, default unavailable details, and bounded
    provider text.
- Consequence:
  - Lotus AI integration behavior is more consistent and easier to harden without changing public
    API semantics or weakening human-review gates.
- Documentation:
  - No README or wiki source change is required. This is internal integration-boundary hardening
    with unchanged public API semantics.
- Follow-Up:
  - Continue separating Lotus AI workflow-pack request construction from adapter transport where
    future slices identify material duplication or test gaps.

## LA-REV-285

- Scope: Lotus AI workflow-pack execute request envelope
- Pattern: shared governed request envelope separated from domain payload construction
- Status: Hardened
- Finding Class: duplication, tenant/caller consistency, and contract drift risk
- Summary: The Lotus AI execute adapters duplicated the same pack id/version/environment,
  caller-identity, task-request, tenant, context, source-reference, and expected-output envelope
  construction. Domain payloads were different, but the shared wrapper was platform contract
  plumbing that could drift across advisory copilot, proposal narrative, memo commentary, policy
  evidence, and workspace rationale integrations.
- Evidence:
  - `src/integrations/lotus_ai/workflow_request.py` now owns the governed workflow-pack execute
    envelope for Lotus Advise callers.
  - Lotus AI adapters now retain domain-specific payload and source-reference construction while
    delegating common caller/environment/tenant/context wrapping to the shared helper.
  - `tests/unit/advisory/api/test_lotus_ai_workflow_request.py` proves the governed caller
    envelope, configured environment and tenant propagation, and default local development posture.
- Consequence:
  - Lotus AI execute requests now use one consistent Advise-owned envelope, reducing drift risk in
    caller identity, tenant routing, source context, and expected-output metadata.
- Documentation:
  - No README or wiki source change is required. This is internal integration-boundary hardening
    with unchanged public API semantics.
- Follow-Up:
  - Continue auditing Lotus AI workflow-pack run review-action mapping separately because it uses a
    different endpoint contract than execute requests.

## LA-REV-286

- Scope: Advisory copilot Lotus AI request safety
- Pattern: outbound request hygiene extracted from adapter orchestration
- Status: Hardened
- Finding Class: module size, sensitive-data handling, and request-boundary test gap
- Summary: `advisory_copilot.py` still mixed transport orchestration and output guardrails with
  outbound request hygiene: caller correlation id hashing, source-reference bounding, requested
  output de-duplication, and raw-prompt/provider-response reason redaction. Those controls are
  security and governance boundaries, so keeping them as private helpers inside the transport
  adapter made them harder to test directly and easier to regress during future copilot changes.
- Evidence:
  - `src/integrations/lotus_ai/advisory_copilot_request.py` now owns advisory-copilot workflow-pack
    request construction, workflow surface naming, caller correlation id bounding, source refs,
    requested outputs, and safe reason projection.
  - `src/integrations/lotus_ai/advisory_copilot.py` now keeps orchestration, guardrail decisions,
    Lotus AI response handling, lineage projection, and fallback behavior.
  - `tests/unit/advisory/api/test_lotus_ai_advisory_copilot_request.py` proves source-ref bounding,
    oversized correlation-id hashing, requested-output de-duplication, and raw prompt/provider
    material redaction before Advise calls lotus-ai.
- Consequence:
  - Advisory copilot request safety is now independently testable, the adapter is materially
    smaller, and outbound Lotus AI calls remain bounded to governed evidence rather than raw prompt
    or provider material.
- Documentation:
  - No README or wiki source change is required. This is internal integration-boundary hardening
    with unchanged public API semantics.
- Follow-Up:
  - Continue separating advisory copilot lineage helpers only if future slices need to extend
    proposal-version lineage behavior.

## LA-REV-287

- Scope: RFC-0028 backend proof runtime summary projection
- Pattern: sanitized demo-evidence projection separated from proof-pack orchestration
- Status: Hardened
- Finding Class: module size, demo-proof contract clarity, and missing direct tests
- Summary: `capture.py` owned both proof-pack orchestration and the sanitized live-runtime summary
  projection. The summary projection is a durable RFC-0028 evidence contract used by proof-pack
  assets, scripts, and demo material, so keeping it inside the orchestrator made it harder to test
  missing-field behavior and safe-field selection independently.
- Evidence:
  - `src/core/bank_demo_proof/runtime_summary.py` now owns sanitized runtime summary projection,
    dotted-path lookup, dictionary contract lookup, and fixed-shape field selection.
  - `src/core/bank_demo_proof/capture.py` now composes the runtime summary instead of owning the
    projection internals.
  - `tests/unit/advisory/engine/test_engine_bank_demo_runtime_summary.py` proves demo-safe field
    projection, source-hash exclusion, fail-closed missing contract sections, dotted-path error
    reporting, and fixed-shape selection.
- Consequence:
  - RFC-0028 proof capture is smaller and the sanitized runtime evidence contract is directly
    testable without constructing a full proof pack.
- Documentation:
  - No README or wiki source change is required. This is internal proof-capture modularity
    hardening with unchanged public API semantics.
- Follow-Up:
  - Continue separating proof asset construction from capture orchestration if later RFC-0028
    slices need to add additional asset families.

## LA-REV-288

- Scope: RFC-0028 backend proof asset construction
- Pattern: proof asset inventory separated from capture orchestration
- Status: Hardened
- Finding Class: proof-boundary clarity, commit/local evidence controls, and direct test gap
- Summary: `capture.py` still constructed the full proof asset list inline, including commit-safe
  summaries, local-only runtime bundle evidence, customer-consumable commercial material, and
  canonical content hashes. That asset inventory is a durable RFC-0028 proof contract and should
  be testable without building the full capture bundle.
- Evidence:
  - `src/core/bank_demo_proof/proof_assets.py` now owns backend proof asset construction, content
    hashes, commit permissions, access classes, retention classes, and source live-runtime bundle
    URI precedence.
  - `src/core/bank_demo_proof/capture.py` now delegates asset construction while retaining proof
    bundle orchestration and material review enforcement.
  - `tests/unit/advisory/engine/test_engine_bank_demo_proof_assets.py` proves asset inventory,
    customer-consumable vs local-only boundaries, content hashes, and source bundle precedence.
- Consequence:
  - RFC-0028 proof-pack evidence boundaries are easier to audit and less likely to drift when
    proof capture adds new assets or commercial material changes.
- Documentation:
  - No README or wiki source change is required. This is internal proof-capture modularity
    hardening with unchanged public API semantics.
- Follow-Up:
  - Continue auditing proof-pack metadata and supported-claim register construction for additional
    separable contracts if future slices change client-demo material.

## LA-REV-289

- Scope: RFC-0028 material field review gate
- Pattern: supported-claim material review separated from proof-capture orchestration
- Status: Hardened
- Finding Class: claim-gate modularity and validation reuse
- Summary: Material field reviews are the lowest-layer supported-claim gate for RFC-0028, but the
  review DTO, expected field matrix, sensitive-text validation, and review builder lived inside
  `capture.py`. That kept a durable claim-control contract coupled to proof-pack orchestration and
  duplicated validation concerns that metadata also needed.
- Evidence:
  - `src/core/bank_demo_proof/material_review.py` now owns `MaterialFieldReview`, the material
    field matrix, and `review_material_fields`.
  - `src/core/bank_demo_proof/validation.py` now owns shared proof-capture text normalization and
    sensitive-term detection for metadata and material review fields.
  - `src/core/bank_demo_proof/capture.py` now imports the material review contract and composes it
    during proof capture.
  - Existing RFC-0028 proof-capture tests continue to prove material review pass/block behavior,
    sensitive observed-value rejection, and full proof-pack enforcement.
- Consequence:
  - Supported-claim gating is easier to audit and extend, and proof capture is further reduced to
    orchestration rather than owning every proof sub-contract.
- Documentation:
  - No README or wiki source change is required. This is internal proof-capture modularity
    hardening with unchanged public API semantics.
- Follow-Up:
  - Continue auditing supported-claim register construction if future slices add claim families or
    demo audiences.

## LA-REV-290

- Scope: RFC-0028 scenario and supported-claim contract construction
- Pattern: durable demo contracts separated from proof-capture orchestration
- Status: Hardened
- Finding Class: contract modularity, claim-control drift risk, and direct test gap
- Summary: `capture.py` still owned the RFC-0028 scenario contract, source-product inventory,
  unsupported boundaries, and supported-claim register. Those are durable governance contracts
  used by proof capture, commercial material, and demo documentation, so keeping them inside the
  orchestrator made claim wording, audience posture, and Workbench panel identifiers harder to
  review independently.
- Evidence:
  - `src/core/bank_demo_proof/scenario_contract.py` now owns the canonical scenario reference,
    source products, unsupported boundaries, and ordered scenario-step construction.
  - `src/core/bank_demo_proof/supported_claim_register.py` now owns the supported-claim register
    reference, artifact policy, claim posture, audience mapping, and wording guardrails.
  - `src/core/bank_demo_proof/capture.py` now composes these contracts during proof-pack
    construction instead of owning their internals.
  - `tests/unit/advisory/engine/test_engine_bank_demo_scenario_contract.py` proves canonical
    identity, source products, unsupported boundaries, and governed Workbench panel identifiers.
  - `tests/unit/advisory/engine/test_engine_bank_demo_supported_claim_register.py` proves claim
    posture, UI-pending screenshot exclusion, commercial material permissions, and artifact
    policy boundaries.
- Consequence:
  - RFC-0028 claim-control and scenario-governance changes are now reviewed in focused modules
    with direct tests, while proof capture remains a smaller orchestration layer.
- Documentation:
  - No README or wiki source change is required. This is internal proof-contract modularity
    hardening with unchanged public API semantics.
- Follow-Up:
  - Continue auditing proof-capture metadata and CLI writer boundaries only where additional
    RFC-0028 proof evidence or operator behavior changes.

## LA-REV-291

- Scope: RFC-0028 backend proof-pack contract construction
- Pattern: proof-pack marker and boundary construction separated from capture orchestration
- Status: Hardened
- Finding Class: contract modularity, overclaim prevention, and direct test gap
- Summary: `capture.py` still assembled the proof-pack header inline, including proof id,
  evidence markers, scenario/register references, source products, unsupported boundaries,
  repository SHA lineage, and blocked client-ready posture. Those values are part of the
  machine-readable RFC-0028 proof contract and should be testable without building every source
  proof summary first.
- Evidence:
  - `src/core/bank_demo_proof/proof_pack.py` now owns backend proof-pack construction and the
    canonical RFC-0028 evidence marker inventory.
  - `src/core/bank_demo_proof/capture.py` now builds proof assets, then delegates proof-pack
    construction to the proof-pack contract module.
  - `tests/unit/advisory/engine/test_engine_bank_demo_proof_pack.py` proves canonical proof-pack
    identifiers, contract references, evidence markers, source products, unsupported boundaries,
    repository lineage, and client-ready blocking posture.
- Consequence:
  - RFC-0028 proof-pack contract changes now fail close to the contract boundary, and capture
    orchestration no longer owns the scenario, claim-register, asset, material-review, runtime
    summary, and proof-pack internals at once.
- Documentation:
  - No README or wiki source change is required. This is internal proof-contract modularity
    hardening with unchanged public API semantics.
- Follow-Up:
  - Continue auditing metadata and CLI writer behavior if operator-facing proof capture changes.

## LA-REV-292

- Scope: RFC-0028 backend proof artifact writer
- Pattern: artifact writing and summary rendering separated from proof-capture CLI orchestration
- Status: Hardened
- Finding Class: operator automation modularity and evidence-output drift risk
- Summary: `scripts/capture_rfc0028_backend_proof.py` owned CLI parsing, live-suite loading,
  runtime probing, proof-bundle assembly, artifact writing, manifest construction, JSON encoding,
  and Markdown summary rendering. The artifact writer is the repeatable operator evidence-output
  contract, so keeping it inside the CLI made it harder to test and reuse without invoking the
  runtime probe and live-suite orchestration path.
- Evidence:
  - `scripts/rfc0028_backend_proof_writer.py` now owns sanitized artifact paths, manifest
    artifact references, JSON output, and business-facing capture-summary rendering.
  - `scripts/capture_rfc0028_backend_proof.py` now delegates artifact writing while retaining CLI,
    live-suite source selection, runtime probing, and metadata assembly.
  - `tests/unit/scripts/test_capture_rfc0028_backend_proof.py` now imports the writer directly
    and continues to prove sanitized artifact output, relative manifest refs, no raw source hashes,
    runtime latency presentation, and blocked client-ready posture.
- Consequence:
  - RFC-0028 proof-output behavior is easier to audit independently from CLI/runtime behavior, and
    future writer changes have a smaller blast radius.
- Documentation:
  - No README or wiki source change is required. The public capture command and artifact names are
    unchanged.
- Follow-Up:
  - Continue auditing runtime probe orchestration only if additional endpoint families or operator
    CLI options are added.

## LA-REV-293

- Scope: RFC-0028 runtime probe orchestration
- Pattern: runtime probe collection separated from proof-capture CLI orchestration
- Status: Hardened
- Finding Class: operational diagnostics modularity and security-boundary clarity
- Summary: `scripts/capture_rfc0028_backend_proof.py` still owned runtime endpoint probing,
  latency capture, health/capability summary projection, skipped-probe posture, and base-url
  validation alongside CLI parsing and live-suite source selection. Runtime probing is an
  operational diagnostics boundary with sensitive URL and summary redaction expectations, so it
  should be directly testable without executing the proof-capture CLI.
- Evidence:
  - `scripts/rfc0028_runtime_probe.py` now owns runtime posture probing, individual endpoint
    probing, skipped-probe posture construction, health summaries, capability summaries, and
    latency capture.
  - `scripts/capture_rfc0028_backend_proof.py` delegates runtime posture collection to the runtime
    probe module and keeps CLI/source-selection responsibilities.
  - `tests/unit/scripts/test_capture_rfc0028_backend_proof.py` imports runtime probe functions
    directly and continues to prove sensitive material redaction, latency capture, unsafe base-url
    rejection, and skipped-probe normalization.
- Consequence:
  - RFC-0028 operator diagnostics are easier to audit and extend without coupling runtime probing
    to live-suite execution or artifact writing.
- Documentation:
  - No README or wiki source change is required. The public capture command and runtime posture
    artifact behavior are unchanged.
- Follow-Up:
  - Continue auditing live-suite source loading only if additional source modes or bundle layouts
    are added.

## LA-REV-294

- Scope: RFC-0028 live-suite proof source loading
- Pattern: live-suite source selection separated from proof-capture CLI orchestration
- Status: Hardened
- Finding Class: repeatability boundary clarity and direct test gap
- Summary: `scripts/capture_rfc0028_backend_proof.py` still owned existing `result.json` loading,
  bundle resolution, optional live-suite execution, bundle reference calculation, and no-source
  failure behavior. This source-selection logic is the repeatability boundary for RFC-0028 proof
  capture, so it should be directly testable without invoking runtime probes, metadata assembly,
  or artifact writing.
- Evidence:
  - `scripts/rfc0028_live_suite_source.py` now owns existing result loading, latest bundle
    resolution, optional live-suite execution, source artifact references, and repeatable-source
    failure behavior.
  - `scripts/capture_rfc0028_backend_proof.py` now delegates live-suite source selection while
    retaining CLI parsing and proof orchestration.
  - `tests/unit/scripts/test_capture_rfc0028_backend_proof.py` now proves existing result loading,
    latest bundle resolution, and the explicit source-required error.
- Consequence:
  - RFC-0028 proof-capture repeatability is now covered at the source-selection layer, reducing
    reliance on full live-suite execution to catch source artifact regressions.
- Documentation:
  - No README or wiki source change is required. The public capture command and source modes are
    unchanged.
- Follow-Up:
  - Continue auditing proof-capture metadata and artifact-reference behavior only when operator
    options or evidence artifact semantics change.

## LA-REV-295

- Scope: RFC-0028 bank-demo proof API request boundary
- Pattern: API request validation and runtime metadata normalization separated from route handlers
- Status: Hardened
- Finding Class: controller thinness, metadata validation reuse, and direct test gap
- Summary: `src/api/routers/bank_demo_proof.py` still owned the request DTO, artifact-reference
  validation, runtime metadata defaults, environment fallbacks, correlation-id derivation, and
  sensitive-fragment rejection. That kept route handlers coupled to request-normalization details
  and made metadata behavior harder to test without driving the whole FastAPI endpoint.
- Evidence:
  - `src/api/routers/bank_demo_proof_request.py` now owns `BankDemoProofCaptureRequest`,
    artifact-reference validators, runtime repository SHA/service-version/environment defaults,
    correlation-id normalization, and sensitive metadata rejection.
  - `src/api/routers/bank_demo_proof.py` now focuses on OpenAPI route declaration, metadata
    composition, proof-pack invocation, and HTTP 409 material-drift mapping.
  - `tests/unit/advisory/api/test_api_bank_demo_proof_request.py` proves sensitive artifact ref
    rejection, request-vs-environment metadata precedence, governed fallbacks, context correlation
    id use, and sensitive correlation-id rejection.
- Consequence:
  - RFC-0028 proof API request behavior is easier to audit and less likely to accrete business
    logic in the controller layer.
- Documentation:
  - No README or wiki source change is required. The public API path, request schema name, and
    behavior are unchanged.
- Follow-Up:
  - Continue auditing the route only if API behavior or OpenAPI semantics change.

## LA-REV-296

- Scope: RFC-0028 document proof business-safe text validation
- Pattern: shared RFC-0028 proof text normalization reused by document proof contracts
- Status: Hardened
- Finding Class: duplicate validation logic and sensitive-detail drift risk
- Summary: `src/core/bank_demo_proof/document_proof.py` carried its own required-text
  normalization and sensitive technical-term filter even though proof capture already had the same
  guarded vocabulary. That duplication made report/document proof behavior easier to drift from the
  canonical RFC-0028 proof-pack safety boundary.
- Evidence:
  - `src/core/bank_demo_proof/validation.py` now exposes shared required-text and business-safe
    text normalization helpers while keeping the existing proof-capture helper behavior intact.
  - `src/core/bank_demo_proof/document_proof.py` reuses the shared helpers for status, degraded
    reason, summary identifier, and requested-output-format normalization.
  - `tests/unit/advisory/engine/test_engine_bank_demo_document_proof.py` now covers hyphenated
    sensitive provider-response wording so document proof validation cannot leak technical detail
    through presentation-safe fields.
- Consequence:
  - RFC-0028 document proof safety is more consistent with proof capture and easier to extend
    across commercial/report proof modules without local sensitive-term variants.
- Documentation:
  - No README or wiki source change is required. The public proof API, CLI, and generated proof
    artifact behavior are unchanged.
- Follow-Up:
  - Continue reducing duplicate validation in commercial-material and integration-proof modules
    where it can be done without changing public proof contracts.

## LA-REV-297

- Scope: RFC-0028 commercial-material proof validation
- Pattern: commercial material proof contracts reuse shared RFC-0028 text-safety helpers
- Status: Hardened
- Finding Class: duplicate sensitive-fragment handling and repository-ref safety drift
- Summary: `src/core/bank_demo_proof/commercial_materials.py` carried a second sensitive-fragment
  vocabulary for business titles, claim refs, pack ids, and repository source references. The list
  used underscore variants while document/proof capture used space and hyphen normalization, making
  the proof-pack safety boundary harder to reason about consistently.
- Evidence:
  - `src/core/bank_demo_proof/validation.py` now normalizes underscores, hyphens, and spaces before
    matching RFC-0028 sensitive terms.
  - `src/core/bank_demo_proof/commercial_materials.py` now reuses shared required-text,
    business-safe text, and sensitive-term helpers while retaining repository-local source-ref
    validation.
  - `tests/unit/advisory/engine/test_engine_bank_demo_commercial_materials.py` now covers sensitive
    repository source fragments such as `raw_prompt`.
- Consequence:
  - Commercial proof materials now share the same sensitive-detail boundary as proof capture and
    document proof, reducing the chance that RFP/demo material metadata can drift into technical
    leakage.
- Documentation:
  - No README or wiki source change is required. The commercial material inventory and public proof
    behavior are unchanged.
- Follow-Up:
  - Continue the same consolidation in integration-proof validation if focused tests show no public
    contract drift.

## LA-REV-298

- Scope: RFC-0028 journey integration proof validation
- Pattern: source integration proof status fields reuse shared RFC-0028 text-safety helpers
- Status: Hardened
- Finding Class: duplicate status validation and blocked-boundary wording risk
- Summary: `src/core/bank_demo_proof/integration_proof.py` carried another local sensitive-term
  tuple and status normalizer for AI, policy, panel, and proof identifiers. Reusing the shared RFC
  28 text-safety helper reduces duplicate validation, but unsupported-claim boundary statements must
  still be allowed to name blocked concepts such as raw prompts when explaining what is excluded.
- Evidence:
  - `src/core/bank_demo_proof/integration_proof.py` now delegates status and identifier validation
    to the shared business-safe helper while using required-text normalization for unsupported-claim
    boundary statements.
  - `tests/unit/advisory/engine/test_engine_bank_demo_integration_proof.py` now covers
    underscore-form sensitive provider-response status text.
  - Focused proof-capture tests continue to prove the canonical integration proof summary can state
    raw-prompt exclusion without leaking raw material.
- Consequence:
  - RFC-0028 AI/policy/cockpit integration proof fields now share the same sensitive-detail
    boundary as document and commercial proof fields while keeping business-facing blocked-claim
    language truthful.
- Documentation:
  - No README or wiki source change is required. The integration proof contract and generated proof
    artifact semantics are unchanged.
- Follow-Up:
  - Continue auditing larger proof model contracts for reusable validators only where the change
    preserves externally visible proof wording.

## LA-REV-299

- Scope: RFC-0028 proof model sensitive-term vocabulary
- Pattern: proof model contracts reuse the shared RFC-0028 sensitive-term matcher
- Status: Hardened
- Finding Class: duplicate sensitive-term vocabulary and underscore-drift risk
- Summary: `src/core/bank_demo_proof/models.py` still had a model-local sensitive technical-term
  tuple used by scenario, supported-claim, proof-asset, and proof-pack validators. That duplicated
  the same vocabulary now shared by document, commercial, integration, and capture proof modules
  and did not cover underscore variants consistently.
- Evidence:
  - `src/core/bank_demo_proof/models.py` now delegates sensitive-term matching to the shared RFC-0028
    validation helper while preserving its custom required-field error messages.
  - `tests/unit/advisory/engine/test_engine_bank_demo_proof_models.py` now covers underscore-form
    provider-response text in supported-claim wording.
  - Focused RFC-0028 proof model, integration, commercial, document, and capture tests pass.
- Consequence:
  - RFC-0028 proof model contracts now use the same sensitive-detail vocabulary as the rest of the
    proof-pack stack without widening model error-message churn.
- Documentation:
  - No README or wiki source change is required. Public proof models and generated proof artifacts
    retain the same schema and business meaning.
- Follow-Up:
  - Continue extracting model submodules only where a complete domain boundary can be moved with
    focused tests; avoid broad churn in the central proof contract module.

## LA-REV-300

- Scope: RFC-0028 supported-claim register vocabulary
- Pattern: claim register wording avoids implementation-process language in proof material
- Status: Hardened
- Finding Class: business-facing language quality and commercial-proof leakage risk
- Summary: `src/core/bank_demo_proof/supported_claim_register.py` still used implementation-process
  terms such as "report seam" and "Slice 5" in claim text or wording rules. The supported-claim
  register feeds RFC-0028 proof and commercial material governance, so it should use private-banking
  and product-proof language rather than internal implementation phrasing.
- Evidence:
  - Supported-claim wording now uses "report-package handoff", "proof scope", and "Gateway and
    Workbench validation" instead of seam/slice phrasing.
  - `tests/unit/advisory/engine/test_engine_bank_demo_supported_claim_register.py` now prevents
    `seam` and `slice` from appearing in claim text or wording rules.
  - Focused supported-claim, proof-capture, and RFC-0028 documentation-contract tests pass.
- Consequence:
  - RFC-0028 proof material is less likely to leak engineering process language into business,
    sales, pre-sales, or client-demo audiences.
- Documentation:
  - No README or wiki source change is required. This is a source-of-truth claim-register wording
    correction and does not change public behavior or commands.
- Follow-Up:
  - Continue scanning generated proof summaries and commercial docs for implementation-process
    wording before final RFC-0028 closure.

## LA-REV-301

- Scope: README and wiki public integration vocabulary
- Pattern: public documentation uses business-facing integration-boundary language
- Status: Hardened
- Finding Class: documentation polish, audience fit, and implementation-shorthand leakage
- Summary: Public README/wiki pages still described report and AI integration points as "seams".
  That shorthand is useful during engineering discussions but reads like implementation jargon in
  material intended for business users, operations, sales, pre-sales, and client-demo preparation.
- Evidence:
  - `README.md` now describes Lotus Report, Lotus AI, and adjacent app relationships as integration
    boundaries.
  - `wiki/Advisory-Workspace.md`, `wiki/Proposal-Lifecycle.md`, `wiki/Integrations.md`, and
    `wiki/Supported-Features.md` use integration-boundary terminology in prose, tables, and
    diagrams.
  - `tests/unit/test_public_docs_vocabulary.py` prevents `seam` wording from returning to the
    target public docs.
- Consequence:
  - Public documentation better matches enterprise buyer and bank stakeholder expectations without
    changing any API or runtime behavior.
- Documentation:
  - Repo-local wiki source changed and must pass wiki sync check before merge.
- Follow-Up:
  - Continue broader wiki/RFC vocabulary cleanup only where it changes current product truth or
    buyer-facing clarity; avoid rewriting historical RFC implementation notes for cosmetics.

## LA-REV-302

- Scope: RFC-0028 proof-pack API error classification
- Pattern: distinguish material-proof conflict from malformed source evidence
- Status: Hardened
- Finding Class: API error-model precision and caller remediation clarity
- Summary: `POST /advisory/bank-demo-proof/proof-packs` mapped every proof-build `ValueError` to
  HTTP 409. Material-field drift is a real conflict because it means the provided evidence does not
  match the canonical proof posture, but malformed source evidence is a 422 request/source-evidence
  validation failure. Treating both as 409 made Gateway, Workbench, and automation remediation less
  precise.
- Evidence:
  - `src/api/routers/bank_demo_proof.py` now maps
    `RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED` to HTTP 409 and other proof-build validation
    failures to HTTP 422.
  - The OpenAPI 422 response description now includes source-evidence validation failure.
  - `tests/unit/advisory/api/test_api_bank_demo_proof.py` proves material drift remains 409 while
    missing nested source evidence returns 422 with the bounded proof-field diagnostic.
- Consequence:
  - RFC-0028 proof automation and product consumers can distinguish stale/materially conflicting
    proof state from invalid source evidence without inspecting fragile response text alone.
- Documentation:
  - No README or wiki source change is required. The API behavior is clarified in OpenAPI and
    covered by endpoint tests.
- Follow-Up:
  - Continue tightening error models only where consumers need different remediation behavior.

## LA-REV-303

- Scope: RFC-0028 proof-pack OpenAPI response examples
- Pattern: documented API error examples distinguish proof conflict from source-evidence validation
- Status: Hardened
- Finding Class: OpenAPI usability and integration contract clarity
- Summary: After the RFC-0028 proof-pack endpoint started classifying material drift as 409 and
  malformed source evidence as 422, the OpenAPI response descriptions named the statuses but did
  not provide concrete examples. Gateway, Workbench, and automation integrators benefit from stable
  examples for the two remediation paths.
- Evidence:
  - `src/api/routers/bank_demo_proof.py` now includes response examples for 409 material-review
    conflict and 422 missing source-evidence diagnostics.
  - `tests/unit/advisory/api/test_api_bank_demo_proof.py` asserts those examples remain present in
    the generated OpenAPI operation.
  - Focused OpenAPI lifecycle docs tests and `scripts/openapi_quality_gate.py` pass.
- Consequence:
  - RFC-0028 proof API consumers can understand expected error payloads from the OpenAPI document
    without relying only on code or test fixtures.
- Documentation:
  - No README or wiki source change is required. The API contract is documented in OpenAPI.
- Follow-Up:
  - If Gateway or Workbench needs typed problem-details bodies later, introduce that as a dedicated
    cross-repo API-contract slice rather than a local response-description edit.

## LA-REV-304

- Scope: RFC-0028 runtime proof summary sanitization
- Pattern: sanitized runtime evidence redacts sensitive values even when upstream services place
  them in neutral summary fields
- Status: Hardened
- Finding Class: evidence-leakage prevention and operational diagnostics hardening
- Summary: Runtime proof summaries already redacted sensitive keys, but a neutral health or
  readiness field such as `detail`, `message`, or `error` could still carry bearer credentials,
  token assignments, or traceback text returned by a dependency. RFC-0028 proof material must
  remain useful for operational posture without carrying credentials, prompts, raw payload/source
  markers, trace/correlation identifiers, or stack traces.
- Evidence:
  - `src/core/bank_demo_proof/runtime_posture.py` now redacts sensitive string values matching
    bearer/basic credentials, token/secret/password/cookie/API-key assignments, trace/correlation
    identifiers, raw prompt/payload/source assignments, and traceback text.
  - `tests/unit/advisory/engine/test_engine_bank_demo_proof_models.py` proves neutral runtime
    summary fields are redacted while business-useful degraded-readiness wording remains intact.
  - Focused proof-model tests and touched-file Ruff checks pass.
- Consequence:
  - Runtime evidence remains operationally meaningful while reducing the chance that upstream
    health/readiness diagnostics leak secret or stack details into RFC-0028 proof artifacts.
- Documentation:
  - No README or wiki source change is required. Existing RFC-0028 public docs already state that
    runtime proof summaries redact credentials, tokens, raw payload/prompt/source material, and
    trace/correlation identifiers.
- Follow-Up:
  - Continue checking generated proof artifacts for business-facing vocabulary and secret-free
    summaries during final RFC-0028 closure.

## LA-REV-305

- Scope: Public RFC/wiki/commercial integration-boundary vocabulary
- Pattern: buyer-facing documentation avoids engineering shorthand for cross-service boundaries
- Status: Hardened
- Finding Class: documentation product quality and private-banking audience fit
- Summary: The previous public-document vocabulary guard covered README and only selected wiki
  pages. Additional public wiki pages, the RFC index, RFC README, and active RFC-0028 source still
  used "seam" wording for report, AI, and handoff integration points. That shorthand weakens
  documentation intended for business, operations, sales, pre-sales, and client-demo audiences.
- Evidence:
  - `wiki/Home.md`, `wiki/Overview.md`, `wiki/Security-and-Governance.md`,
    `wiki/Architecture.md`, and `wiki/RFC-Index.md` now use integration-boundary language.
  - `docs/rfcs/README.md` and
    `docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md` now use report-package and
    handoff boundary wording where those documents are current source truth.
  - `tests/unit/test_public_docs_vocabulary.py` now covers all repo wiki pages, commercial
    material, the RFC index, and active RFC-0028.
- Consequence:
  - Public Lotus Advise documentation is more consistent, business-facing, and less likely to leak
    implementation shorthand into client-demo or sales-support material.
- Documentation:
  - Repo-local wiki source changed and must pass wiki sync check before merge, then publish after
    merge to `main`.
- Follow-Up:
  - Keep future documentation edits tied to implementation-backed truth or buyer-facing clarity;
    do not rewrite historical RFC records purely for style.

## LA-REV-306

- Scope: RFC-0028 proof-pack API validation-error redaction
- Pattern: endpoint error details must not echo sensitive nested source-evidence values
- Status: Hardened
- Finding Class: API security, evidence hygiene, and consumer-safe diagnostics
- Summary: `POST /advisory/bank-demo-proof/proof-packs` already prevented request-shape
  validation errors from echoing sensitive artifact references, but proof-build validation errors
  were returned with `str(exc)`. If nested live-runtime source evidence carried a sensitive value in
  a material field, Pydantic validation text could include the rejected input. That is not suitable
  for Gateway, Workbench, automation logs, or proof-pack diagnostics.
- Evidence:
  - `src/api/routers/bank_demo_proof.py` now classifies status from the raw proof error but returns
    a sanitized detail when the error contains credentials, tokens, secrets, raw prompt/payload/
    source terms, provider responses, authorization, or cookies.
  - Material-review conflicts still preserve the 409 remediation path when details are safe.
  - `tests/unit/advisory/api/test_api_bank_demo_proof.py` proves sensitive nested source evidence
    returns a bounded 422 `RFC0028_PROOF_PACK_VALIDATION_FAILED` detail without echoing the token or
    rejected value.
- Consequence:
  - RFC-0028 proof API consumers keep actionable HTTP classification without exposing sensitive
    source-evidence values in API responses or logs.
- Documentation:
  - No README or wiki source change is required. Existing API/wiki proof-boundary docs already
    state that HTTP 422 validation responses must not echo rejected sensitive input.
- Follow-Up:
  - Consider typed problem-detail models only as a coordinated cross-repo API-contract slice if
    Gateway or Workbench needs machine-readable remediation codes beyond current stable strings.

## LA-REV-307

- Scope: RFC-0028 proof-pack client-ready posture schema
- Pattern: public API schemas must not advertise unsupported client-ready approval states
- Status: Hardened
- Finding Class: API contract truthfulness and overclaim prevention
- Summary: `ClientReadyProofPosture` exposed `CLIENT_READY_APPROVED` in the model literal while a
  later proof-pack validator rejected it. That kept runtime behavior conservative, but OpenAPI
  could still advertise an approval posture that RFC-0028 does not currently support. Unsupported
  client-ready approval must not appear as a valid current proof-pack API value.
- Evidence:
  - `src/core/bank_demo_proof/models.py` now limits `ClientReadyProofPosture` to
    `CLIENT_READY_REVIEW_REQUIRED` and `CLIENT_READY_PUBLICATION_BLOCKED`.
  - `tests/unit/advisory/api/test_api_bank_demo_proof.py` asserts
    `CLIENT_READY_APPROVED` is absent from the generated `AdvisoryBankDemoProofPack` schema.
  - `docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md` now states that
    `CLIENT_READY_APPROVED` is not part of the current proof-pack API contract before publication
    controls exist.
- Consequence:
  - Gateway, Workbench, and external API readers cannot infer unsupported client-ready publication
    approval from the proof-pack schema.
- Documentation:
  - RFC-0028 source truth changed; no wiki change was required for this specific API enum
    correction.
- Follow-Up:
  - Any future client-ready approval posture must arrive with implementation-backed publication
    controls, API tests, OpenAPI examples, and wiki/supported-feature updates in the same slice.

## LA-REV-308

- Scope: RFC-0028 supported-claim taxonomy documentation
- Pattern: RFC source truth must match the implemented supported-claim classification contract
- Status: Hardened
- Finding Class: RFC/API contract alignment and unsupported-state removal
- Summary: RFC-0028 listed `REMOVED_OR_SUPERSEDED` as a supported-claim classification, but the
  implemented `SupportedClaimClassification` contract exposes only
  `IMPLEMENTATION_BACKED`, `BACKEND_BACKED_UI_PENDING`, `DEGRADED_SUPPORTED`, `PLANNED_RFC`, and
  `UNSUPPORTED`. Adding an unused public state would increase API surface without a current
  product need, so the RFC now documents removed or superseded claims as unsupported migration
  wording rather than a separate classification.
- Evidence:
  - `docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md` no longer lists
    `REMOVED_OR_SUPERSEDED` as a current classification.
  - `tests/unit/test_rfc0028_gold_standard_tightening_contract.py` asserts the active RFC source
    does not reintroduce the unsupported classification.
  - Focused RFC contract and proof-model tests pass.
- Consequence:
  - The RFC, model taxonomy, and OpenAPI schema remain aligned, reducing integration ambiguity for
    Gateway, Workbench, documentation, and proof automation.
- Documentation:
  - RFC-0028 source truth changed. No wiki change was required because the wiki did not advertise
    the removed classification.
- Follow-Up:
  - Keep any future claim-classification addition platform-backed and schema-tested before adding
    it to RFC, README, wiki, or commercial material.

## LA-REV-309

- Scope: RFC-0027 advisory copilot human-review posture documentation
- Pattern: RFC review-state vocabulary must match the implemented copilot contract
- Status: Hardened
- Finding Class: RFC/API contract alignment and client-ready overclaim prevention
- Summary: RFC-0027 still listed older human-review postures such as
  `APPROVED_FOR_ADVISOR_USE`, `APPROVED_FOR_CLIENT_DRAFT_USE`,
  `REJECTED_UNSUPPORTED_EVIDENCE`, and `REJECTED_POLICY_OR_GUARDRAIL`. The implemented copilot
  contract exposes `APPROVED_FOR_INTERNAL_USE`, `REJECTED`, `UNSUPPORTED`,
  `GUARDRAIL_REJECTED`, and `UNAVAILABLE` instead, with client-ready publication blocked. The RFC
  now matches the shipped contract vocabulary.
- Evidence:
  - `docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md` now lists the implemented review
    postures from `src/core/advisory_copilot/models.py`.
  - `tests/unit/test_rfc0027_gold_standard_tightening_contract.py` asserts the implemented
    postures are documented and the superseded names do not return.
  - Focused RFC-0027 contract tests pass.
- Consequence:
  - Engineers, Gateway/Workbench consumers, and demo/support documentation readers see the same
    copilot review-state vocabulary that the API and persistence layers actually use.
- Documentation:
  - RFC-0027 source truth changed. No wiki change was required because wiki/supported-feature truth
    already describes governed internal advisor/reviewer copilot interactions.
- Follow-Up:
  - Keep any future review posture addition tied to model, API, OpenAPI, persistence, and RFC tests
    in the same slice.

## LA-REV-310

- Scope: RFC-0026 cockpit business-facing vocabulary
- Pattern: Workbench-facing action copy and public docs use private-banking boundary language
- Status: Hardened
- Finding Class: business-language quality and product-surface clarity
- Summary: Advisor-cockpit action copy and public/RFC documentation still used internal shorthand
  such as `DPM` and `seam` for portfolio-management and handoff boundaries. Those terms are
  acceptable in engineering conversation but weaker in Workbench-facing action text, wiki, README,
  and active RFC source truth intended for business, operations, sales, pre-sales, and client-demo
  readers.
- Evidence:
  - `src/core/advisor_cockpit/action_factory.py` and `src/core/advisor_cockpit/service.py` now use
    discretionary portfolio-management wording in tactical house-view action text and summaries.
  - `README.md`, `wiki/Architecture.md`, `wiki/Integrations.md`, `wiki/Mesh-Data-Products.md`,
    `wiki/RFC-Index.md`, `wiki/Supported-Features.md`, `docs/rfcs/README.md`, RFC-0026, and
    RFC-0028 use portfolio-management and handoff-boundary wording instead of `DPM`/`seam`
    shorthand.
  - `tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py` asserts the updated
    Workbench-facing tactical house-view action copy.
  - `tests/unit/test_public_docs_vocabulary.py` prevents `DPM` and `seam` wording from returning
    to public docs.
- Consequence:
  - The advisor cockpit reads more like a private-banking product surface while preserving the
    source-of-record boundaries with `lotus-manage`, CRM, report, archive, and execution services.
- Documentation:
  - Repo-local wiki source changed and must pass wiki sync check before merge, then publish after
    merge to `main`.
- Follow-Up:
  - Continue replacing implementation shorthand only where it affects product-surface, wiki, RFC,
    README, or commercial-material clarity.

## LA-REV-311

- Scope: Active RFC 26-28 public-source vocabulary and closure wording
- Pattern: Active RFC source truth must not leak placeholders or describe completed proof slices as
  deferred work
- Status: Hardened
- Finding Class: RFC/product documentation quality and closure-truth alignment
- Summary: A follow-up active-RFC scan found stale implementation shorthand in RFC-0027, a `todo`
  cell in the RFC-0026 vocabulary table, and RFC-0028 closure wording that still referred to
  completed Gateway, Workbench, commercial, and owner-repo slices as "later" work. The wording has
  been tightened to business-facing integration-boundary and relationship-follow-up language while
  preserving truthful unsupported boundaries for client-ready publication, external client
  communication, approvals, and OMS/order/fill/settlement.
- Evidence:
  - RFC-0026 now avoids the placeholder `todo` vocabulary in the advisor-cockpit domain table.
  - RFC-0027 now uses advisory-to-discretionary portfolio-management and integration-boundary
    language instead of `DPM`/`seam` shorthand.
  - RFC-0028 no longer describes already-completed proof gates as "later" work.
  - `tests/unit/test_public_docs_vocabulary.py` now includes RFC-0026 and RFC-0027 in the public
    documentation vocabulary guard.
  - `tests/unit/test_rfc0028_gold_standard_tightening_contract.py` blocks stale "later" closure
    phrases from returning.
  - Focused RFC/public-doc tests passed:
    `python -m pytest tests/unit/test_public_docs_vocabulary.py tests/unit/test_rfc0027_gold_standard_tightening_contract.py tests/unit/test_rfc0028_gold_standard_tightening_contract.py`.
- Consequence:
  - RFCs 26-28 are better aligned with implementation-backed closure truth and safer for
    business, operations, sales, pre-sales, and client-demo readers.
- Documentation:
  - Active RFC source truth changed. Repo-local wiki source did not require a separate update in
    this slice because wiki vocabulary had already been hardened and this change tightens RFC
    wording plus regression coverage.
- Follow-Up:
  - Keep active RFC closure wording tied to current implementation evidence and avoid using
    "later" to describe already-completed gates.

## LA-REV-312

- Scope: Legacy advisory simulation database dependency
- Pattern: Delete dead infrastructure placeholders once concrete repository/runtime ownership
  exists elsewhere
- Status: Hardened
- Finding Class: dead-code removal and API dependency clarity
- Summary: `src/api/dependencies.py` still exposed a `get_db_session` generator documented as a
  database-session stub from older RFC-0005 scaffolding. The only remaining consumers were legacy
  simulation route parameters and test overrides; persisted proposal, cockpit, memo, policy, and
  copilot behavior now use repository/runtime wiring instead of this dependency. Keeping the stub
  made the API layer look less production-ready and suggested an unimplemented persistence path.
- Evidence:
  - Removed `src/api/dependencies.py`.
  - Removed unused `db: Depends(get_db_session)` parameters from the advisory simulation and
    artifact endpoints.
  - Removed test harness overrides for the deleted dependency.
  - `tests/unit/advisory/api/test_api_internal_guards.py` now asserts simulation endpoints do not
    reintroduce the legacy `db` dependency.
  - Focused regression proof passed:
    `python -m pytest tests/unit/advisory/api/test_api_internal_guards.py tests/unit/advisory/api/test_api_advisory_proposal_simulate.py tests/e2e/demo/test_demo_scenarios.py`.
- Consequence:
  - API dependency flow is clearer: deterministic simulation remains stateless while persisted
    workflow paths use the proposal/advisory repositories and runtime readiness gates.
- Documentation:
  - No README/wiki change is required because this removes misleading internal scaffolding without
    changing public endpoint behavior or supported-feature truth.
- Follow-Up:
  - Continue removing stale scaffolding only when references prove it is no longer part of a
    supported extension point.

## LA-REV-313

- Scope: RFC-0026 advisor cockpit action construction modularity
- Pattern: Separate source DTOs from action-builder behavior in large domain modules
- Status: Hardened
- Finding Class: maintainability and service-boundary clarity
- Summary: `src/core/advisor_cockpit/action_factory.py` had grown into a large mixed module that
  defined source input DTOs, source-reference DTOs, and action-builder behavior together. The
  source-read-model and service layers only need source DTOs in some paths, so coupling them to the
  full action-builder module made the cockpit package harder to reason about and extend.
- Evidence:
  - Added `src/core/advisor_cockpit/action_sources.py` for source-backed cockpit action DTOs.
  - Kept `src/core/advisor_cockpit/action_factory.py` focused on action construction,
    evidence/readiness helpers, and deterministic ordering.
  - Updated source-read-model/service imports to depend on `action_sources.py` where they only need
    source DTOs.
  - Kept package-level exports stable through `src/core/advisor_cockpit/__init__.py`.
  - RFC/index source truth now names both `action_sources.py` and `action_factory.py`.
  - `tests/unit/test_rfc0026_slice4_domain_action_factory_contract.py` now asserts source DTOs live
    outside the action factory.
  - Focused regression proof passed:
    `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py tests/unit/test_rfc0026_slice4_domain_action_factory_contract.py tests/unit/test_rfc0026_slice5_source_read_model_contract.py`.
- Consequence:
  - RFC-0026 cockpit source projection and action construction boundaries are clearer, with less
    import coupling and a smaller action-factory behavior surface.
- Documentation:
  - RFC/index/wiki source truth changed because the package structure is durable implementation
    evidence for RFC-0026 Slice 4.
- Follow-Up:
  - Continue splitting large cockpit modules only along domain boundaries that reduce coupling or
    duplicate reasoning.

## LA-REV-314

- Scope: RFC-0023 narrative review client-ready status contract
- Pattern: Remove unsupported client-ready approval states from API-visible enums
- Status: Hardened
- Finding Class: API contract overclaim prevention and OpenAPI accuracy
- Summary: `ProposalNarrativeClientReadyStatus` still advertised
  `APPROVED_FOR_CLIENT_READY` even though RFC-0023 only supports advisor-review narrative evidence
  and the service deliberately returns blocked posture for client-ready release requests. Keeping
  the enum value in the model/OpenAPI contract made the API look more capable than the
  implementation and proof evidence support.
- Evidence:
  - Removed `APPROVED_FOR_CLIENT_READY` from `ProposalNarrativeClientReadyStatus`.
  - Tightened `client_ready_release_requested` wording to separately approved publication controls
    rather than vague future scope.
  - Updated RFC/wiki/index wording to keep client-ready narrative and publication separately gated.
  - `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` now asserts the
    narrative review schema does not expose `APPROVED_FOR_CLIENT_READY`.
  - Focused regression proof passed:
    `python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py tests/unit/advisory/engine/test_engine_proposal_workflow_service.py::test_narrative_client_ready_release_requires_positive_review_and_clear_policy tests/unit/advisory/engine/test_engine_proposal_workflow_service.py::test_narrative_client_ready_release_stays_gated_for_clean_advisor_review_narrative tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py::test_narrative_review_blocks_client_ready_release_without_approval tests/unit/test_rfc0023_slice13_14_closure_hardening_contract.py tests/unit/test_rfc0023_slice3_documentation_contract.py`.
- Consequence:
  - RFC-0023 OpenAPI and model contracts now match the proven behavior: advisor-review approval is
    not client-ready publication approval.
- Documentation:
  - RFC and wiki source truth changed because an API-visible status contract was tightened.
- Follow-Up:
  - Any future client-ready status addition must arrive with implementation, policy/disclosure
    gates, report/render/archive controls, OpenAPI examples, live evidence, and documentation in
    the same implementation slice.

## LA-REV-315

- Scope: API-facing integration-boundary vocabulary
- Pattern: OpenAPI and runtime supportability descriptions use business-facing boundary language
- Status: Hardened
- Finding Class: API documentation quality and product-language consistency
- Summary: A source scan found `seam` terminology in API-visible descriptions for integration
  capabilities, report delivery, advisory copilot, workspace rationale, workspace AI review, and
  proposal report status. The wording was technically understandable but weaker for banking
  audiences and inconsistent with the hardened RFC/wiki/commercial language.
- Evidence:
  - Replaced API/runtime descriptions with `integration boundary`, `boundary`, or
    `dependency boundary` wording in capabilities, delivery, copilot, workspace, and proposal
    response models.
  - Updated the integration capabilities test fixture wording.
  - Added an OpenAPI guard in
    `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` that prevents
    `seam` from returning to the generated OpenAPI surface.
  - Focused regression proof passed:
    `python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py tests/unit/advisory/api/test_api_integration_capabilities.py tests/unit/advisory/contracts/test_contract_openapi_workspace_docs.py`.
- Consequence:
  - API consumers, operators, and client-facing technical readers see consistent
    integration-boundary language across generated contracts and supportability payloads.
- Documentation:
  - No README/wiki update was required because this slice changes generated API contract wording
    and the API vocabulary inventory records the updated descriptions.
- Follow-Up:
  - Keep OpenAPI wording business-facing and avoid engineering shorthand in generated contracts.

## LA-REV-316

- Scope: Tactical house-view portfolio-management API wording
- Pattern: Public route descriptions and examples prefer private-banking terminology over internal
  abbreviations
- Status: Hardened
- Finding Class: API documentation quality and private-banking vocabulary
- Summary: The tactical house-view route and request model still used `DPM` in API descriptions and
  examples. The source product may continue to accept source-owned portfolio type values, but the
  public contract should explain the capability in discretionary portfolio-management language.
- Evidence:
  - Updated tactical house-view request model descriptions/examples to use discretionary
    portfolio-management wording.
  - Updated the route description to say downstream discretionary portfolio-management workflows.
  - Updated tactical house-view API/engine tests to use `DISCRETIONARY` in example requests.
  - Added an OpenAPI assertion that prevents the route description from returning to `DPM`
    workflow wording.
  - Focused regression proof passed:
    `python -m pytest tests/unit/advisory/api/test_tactical_house_view_api.py tests/unit/advisory/engine/test_tactical_house_view.py tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py`.
- Consequence:
  - Tactical house-view API docs now read as a private-banking capability while preserving
    downstream portfolio-management ownership boundaries.
- Documentation:
  - No README/wiki change was required because this slice changes generated API contract wording
    and examples only.
- Follow-Up:
  - Keep source-owned codes compatible where needed, but prefer business-facing examples in public
    API contracts.

## LA-REV-317

- Scope: Advisor cockpit owner-role vocabulary and compatibility
- Pattern: Business-facing labels are exposed without breaking legacy cross-repo role values
- Status: Hardened
- Finding Class: API design, integration compatibility, and private-banking vocabulary
- Summary: Advisor cockpit house-view actions still relied on the legacy `DPM_OWNER` role as the
  only portfolio-management projection value. Gateway and Workbench currently consume that value,
  so removing it would break live canonical integration. Advise now accepts the business-facing
  `PORTFOLIO_MANAGER` caller role and emits `owner_role_label` for display while preserving the
  legacy role value for existing consumers.
- Evidence:
  - Added `PORTFOLIO_MANAGER` to `AdvisorCockpitOwnerRole` and projected it to the same visible
    action set as the legacy role.
  - Added `owner_role_label` to `AdvisoryActionItem` so UI/reporting consumers can render
    "Portfolio manager" instead of showing machine role codes.
  - Updated cockpit house-view API and service tests to seed `DISCRETIONARY` portfolio examples,
    query through `PORTFOLIO_MANAGER`, and prove legacy `DPM_OWNER` callers still see the action.
  - Added an OpenAPI guard that requires the business-facing owner-role label contract.
- Consequence:
  - Advise improves private-banking vocabulary without introducing a breaking contract change for
    Gateway or Workbench during their parallel refactors.
- Documentation:
  - RFC-0026 Slice 16 proof language was updated from internal abbreviated wording to
    portfolio-manager / portfolio-management wording.
- Follow-Up:
  - Superseded by LA-REV-325, which removed the legacy owner-role value from the Advise source
    contract after the surrounding RFC-0026/RFC-0028 proof boundary had stabilized.

## LA-REV-318

- Scope: Tactical house-view portfolio-type compatibility
- Pattern: Canonical defaults with explicit legacy alias normalization
- Status: Hardened
- Finding Class: Domain modeling and API compatibility
- Summary: The tactical house-view request default still included the legacy `DPM` source code even
  after the public API descriptions and tests moved to discretionary portfolio-management
  vocabulary. This kept the live source model tied to an internal abbreviation. The default now
  uses canonical `DISCRETIONARY` and `MANAGED` values while normalizing legacy `DPM` input to
  `DISCRETIONARY` for backward-compatible repeatability.
- Evidence:
  - Replaced the default eligible portfolio types with `DISCRETIONARY` and `MANAGED`.
  - Added bounded portfolio-type alias normalization in the cohort builder.
  - Added a regression test proving a legacy `DPM` candidate remains eligible under the canonical
    defaults.
- Consequence:
  - Tactical house-view defaults now use private-banking portfolio-management language without
    breaking existing seeded or integration payloads that still carry the legacy source code.
- Documentation:
  - No README/wiki update was required because this is a source-model compatibility hardening
    change covered by generated API vocabulary and tests.
- Follow-Up:
  - Remove the legacy alias only through a coordinated public-contract migration after downstream
    consumers have moved to canonical portfolio-type values.

## LA-REV-319

- Scope: RFC-0028 proof asset commit policy
- Pattern: Commit-safe proof assets are enforced at the model boundary
- Status: Hardened
- Finding Class: Security posture and proof-artifact governance
- Summary: `ProofAsset` blocked local-only and secret assets from being committed, but it did not
  require committed assets to use a commit-safe/customer-consumable access class, `COMMIT_SOURCE`
  retention, or an immutable content hash. That left room for a restricted evidence summary to be
  accidentally marked commit-allowed even though the default supported-claim artifact policy would
  not permit it.
- Evidence:
  - Added model-level validation that `commit_allowed=True` requires `COMMIT_SAFE_SUMMARY` or
    `CUSTOMER_CONSUMABLE_SUMMARY`, `COMMIT_SOURCE` retention, and a canonical `content_hash`.
  - Added regression tests for restricted commit attempts, local-retention commit attempts, and
    missing content hashes.
  - Updated RFC-0028 and wiki security-governance truth to describe the commit-allowed proof asset
    policy.
- Consequence:
  - RFC-0028 proof-pack artifacts now enforce the same safety posture in code, tests, RFC truth,
    and wiki governance material.
- Documentation:
  - RFC-0028 and `wiki/Security-and-Governance.md` changed because proof-artifact policy truth
    changed.
- Follow-Up:
  - Keep any future proof asset access class changes synchronized with the supported-claim
    register, proof model validation, and wiki governance text.

## LA-REV-320

- Scope: RFC-0024/RFC-0025 supported-feature closure truth after RFC-0028
- Pattern: Documentation reflects current implemented owner RFC instead of stale planned wording
- Status: Hardened
- Finding Class: Documentation truth and commercial-claim governance
- Summary: Supported-feature and RFC-index wording still described client-ready memo claims and
  full bank-demo/RFP package claims as planned or gated until RFC-0028 owned them. RFC-0028 now owns
  bank-demo/RFP proof through supported-claim governance, while client-ready memo publication and
  external client communication remain gated. Leaving the old wording would confuse business and
  pre-sales readers about what RFC-0028 proved versus what remains blocked.
- Evidence:
  - Updated `wiki/Supported-Features.md` for RFC-0024 to state that RFC-0028 governs bank-demo/RFP
    proof through supported claims without promoting client-ready memo publication.
  - Updated the RFC index rows for RFC-0024 and RFC-0025 to point bank-demo/RFP proof to RFC-0028
    instead of describing it as a future/gated claim inside those RFCs.
  - Updated RFC-0024 documentation contract tests and trust-telemetry documentation assertions to
    pin the current gated client-ready memo publication wording.
- Consequence:
  - Business-facing supported-feature truth now distinguishes implemented RFC-0028 proof from
    still-gated client-ready memo publication and external communication.
- Documentation:
  - Wiki supported-features source and RFC index source changed; wiki check/publish is required
    before/after merge.
- Follow-Up:
  - Keep cross-RFC closure language current when a later RFC implements a previously gated package
    while still blocking narrower client-ready publication or communication claims.

## LA-REV-321

- Scope: RFC-0027 copilot business-copy leakage controls
- Pattern: Guardrail invariants must live at the model and persistence boundary, not only in the
  packet builder
- Status: Hardened
- Finding Class: Security posture and test gap
- Summary: The copilot evidence-packet builder rejected raw prompt/provider/trace/correlation
  wording before projection, but direct evidence-section model construction and persisted
  structured payloads did not enforce the same low-level invariant. That left API, replay, or test
  fixture paths able to bypass the intended business-copy redaction rule.
- Evidence:
  - Added shared copilot business-copy technical-detail detection in the domain model.
  - Applied the rule to business projections, unsupported-evidence messages, evidence-section
    titles, evidence-section summaries, and persisted structured payload string values.
  - Added regression tests for direct evidence-section construction and persisted output-section
    leakage, plus RFC/wiki contract assertions for the governance wording.
- Consequence:
  - RFC-0027 copilot evidence now rejects sensitive technical copy at the lowest useful layer across
    UI, API, persistence, and replay paths instead of depending on one builder path.
- Documentation:
  - RFC-0027 Slice 14 acceptance evidence and `wiki/Security-and-Governance.md` changed; wiki
    check/publish is required before/after merge.
- Follow-Up:
  - Keep any future copilot projection fields wired through the shared business-copy guard before
    they are exposed through Gateway, Workbench, or persisted replay evidence.

## LA-REV-322

- Scope: RFC-0027/RFC-0028 current-state documentation boundary
- Pattern: Current feature truth must distinguish owner-RFC runtime authority from RFC-0028
  supported-claim proof
- Status: Hardened
- Finding Class: Documentation drift
- Summary: Current README, RFC index, supported-features, and wiki text still said full RFC-0028
  demo/RFP claims were gated in RFC-0026/RFC-0027 context. RFC-0028 now owns bank-demo/RFP proof
  through supported claims and claim-controlled commercial material, while client-ready
  publication, external client communication, bank-specific attestations, legal advice, completed
  sign-off/approval, and OMS/order/fill/settlement remain blocked.
- Evidence:
  - Updated current README wording for advisor-cockpit and bank-demo proof boundaries.
  - Updated RFC-0027 index and RFC body wording to say RFC-0028 governs bank-demo/RFP proof through
    supported claims rather than RFC-0027 runtime authority.
  - Updated supported-features and wiki RFC-index current-state sections for memo, policy,
    cockpit, and copilot boundaries.
  - Updated documentation contract tests pinning the current supported-claim wording.
- Consequence:
  - Business, pre-sales, operations, and engineering readers now see RFC-0028 as the implemented
    proof owner without interpreting RFC-0026 or RFC-0027 as granting client-ready, execution, or
    bank-specific attestation authority.
- Documentation:
  - README, RFC index, RFC-0027, supported-features, and wiki RFC index changed; wiki check/publish
    is required before/after merge.
- Follow-Up:
  - Keep historical slice records audit-friendly, but update current-state README/wiki/index truth
    whenever a later RFC implements a previously gated supported-claim package.

## LA-REV-323

- Scope: RFC-0028 proof-pack correlation header contract
- Pattern: RFC-0028 proof endpoints should use the same correlation-id header spelling as the
  surrounding Advise RFC APIs
- Status: Hardened
- Finding Class: API contract consistency
- Summary: The proof-pack endpoint accepted and documented `X-Correlation-Id`, while the RFC-0026
  and RFC-0027 Advise APIs expose `X-Correlation-ID`. HTTP header matching is case-insensitive at
  runtime, but OpenAPI consumers and generated clients should see one consistent contract.
- Evidence:
  - Updated the RFC-0028 proof-pack route header alias to `X-Correlation-ID`.
  - Updated API tests to send the canonical header and assert the OpenAPI parameter name,
    location, and max-length contract.
- Consequence:
  - Gateway, Workbench, automation, and client SDK consumers now see a consistent correlation-id
    contract across the implemented RFC-0026 through RFC-0028 Advise APIs.
- Documentation:
  - No wiki source change is required. This is an OpenAPI contract consistency fix for an existing
    runtime behavior boundary.
- Follow-Up:
  - Continue final RFC-0028 closure review across proof automation, documentation truth, and
    branch hygiene before PR handoff.

## LA-REV-324

- Scope: RFC-0026 through RFC-0028 baseline-gap wording
- Pattern: Closed RFCs should distinguish pre-implementation baseline gaps from current product
  posture
- Status: Hardened
- Finding Class: Documentation truth
- Summary: The implemented RFC-0026, RFC-0027, and RFC-0028 documents still used "Current gaps"
  wording in baseline sections. The gap lists were historically useful, but after implementation
  they could make readers believe supported cockpit, copilot, or bank-demo proof features were
  still missing.
- Evidence:
  - Renamed the RFC-0026 baseline section to "Pre-RFC Implementation Baseline".
  - Reworded RFC-0026, RFC-0027, and RFC-0028 gap lists as baseline gaps closed or explicitly
    classified by the RFC.
  - Added documentation contract assertions so the stale "Current gaps" wording cannot reappear in
    those implemented RFCs.
- Consequence:
  - Business, pre-sales, operations, and engineering readers get current implementation truth
    without losing the original baseline rationale for the work.
- Documentation:
  - RFC source changed. No wiki source change is required because the wiki already carries current
    implemented support posture.
- Follow-Up:
  - Keep baseline/audit sections in future RFCs clearly labeled once the RFC moves from planning to
    implemented closure.

## LA-REV-325

- Scope: RFC-0026 advisor cockpit owner-role vocabulary
- Pattern: Product-facing cockpit contracts should use private-banking role language, not legacy
  discretionary-portfolio-management abbreviations
- Status: Hardened
- Finding Class: Domain vocabulary and API quality
- Summary: House-view impact actions used `DPM_OWNER` as the machine-readable owner role while
  rendering "Portfolio manager" as the label. That leaked legacy/internal wording into the Advise
  API contract and tests even though RFC-0026 current product language uses portfolio-management
  boundaries.
- Evidence:
  - Replaced the house-view impact owner role with `PORTFOLIO_MANAGER`.
  - Removed `DPM_OWNER` from emitted advisor-cockpit owner roles and mapped the legacy caller
    alias to `PORTFOLIO_MANAGER` visibility.
  - Updated API, service, action-factory, and RFC slice tests/docs to assert the private-banking
    owner role.
- Consequence:
  - RFC-0026 cockpit contracts now use clean private-banking vocabulary for house-view impact
    queues while preserving the `lotus-manage` source-of-record boundary.
- Documentation:
  - RFC-0026 slice docs changed. No wiki source change is required because current wiki pages
    already use portfolio-management language rather than `DPM_OWNER`.
- Follow-Up:
  - Watch adjacent Gateway/Workbench refactors for any stale copied examples; Advise remains the
    source-owned contract for the cleaned role.

## LA-REV-327

- Scope: RFC-0026 cockpit legacy caller-role compatibility
- Pattern: Clean emitted domain contracts can preserve bounded inbound compatibility during
  cross-repo refactors
- Status: Hardened
- Finding Class: Integration compatibility
- Summary: Read-only Gateway and Workbench pulse showed canonical Workbench validation still sends
  `DPM_OWNER` as a cockpit caller role while Gateway refactors are in flight. Removing that inbound
  value from Advise would break live proof even though Advise should no longer emit it as an action
  owner role.
- Evidence:
  - Split caller-role validation from emitted action-owner-role validation.
  - Kept `DPM_OWNER` as an inbound caller alias only, projecting it to `PORTFOLIO_MANAGER` actions.
  - Added service and API regression tests proving legacy caller compatibility returns
    `PORTFOLIO_MANAGER` in response payloads.
- Consequence:
  - RFC-0026 Advise output stays clean while the current Gateway/Workbench canonical validation
    path remains repeatable during adjacent refactors.
- Documentation:
  - No wiki source change is required. This is a bounded compatibility rule for the existing
    source-owned cockpit API.
- Follow-Up:
  - Once Gateway and Workbench migrate their query examples and validators, remove the inbound
    legacy caller alias in a coordinated contract-cleanup slice.

## LA-REV-328

- Scope: RFC-0026 cockpit caller-role OpenAPI regression coverage
- Pattern: Compatibility exceptions need API-contract tests that prove both allowed input and clean
  output
- Status: Hardened
- Finding Class: Test quality and API governance
- Summary: The legacy caller-role compatibility fix had runtime API and service tests, but the
  OpenAPI contract also needed an explicit assertion that `DPM_OWNER` remains input-only and does
  not return to emitted action owner roles.
- Evidence:
  - Added OpenAPI assertions that action payload owner-role enums include `PORTFOLIO_MANAGER` and
    exclude `DPM_OWNER`.
  - Added OpenAPI assertions that the action-list query-role parameter documents the legacy alias
    and accepts both `DPM_OWNER` and `PORTFOLIO_MANAGER`.
- Consequence:
  - Generated clients and cross-repo validators get a pinned compatibility contract while response
    payloads stay on clean private-banking vocabulary.
- Documentation:
  - No wiki source change is required. This is test coverage for a documented API compatibility
    exception.
- Follow-Up:
  - Remove both the alias and this compatibility assertion once Gateway and Workbench no longer
    send the legacy caller role.

## LA-REV-329

- Scope: RFC-0023 through RFC-0028 public documentation vocabulary
- Pattern: Current RFC source should use private-banking portfolio-management language rather than
  legacy abbreviations
- Status: Hardened
- Finding Class: Documentation quality and business vocabulary
- Summary: Current RFC-0023/RFC-0024 source-map and handoff sections still used `DPM` wording for
  portfolio-management boundaries. The implementation is already advisory-first and
  `lotus-manage`-owned for discretionary portfolio-management workflows, so the public RFC wording
  should not preserve legacy abbreviations outside explicit compatibility exceptions.
- Evidence:
  - Reworded RFC-0023 and RFC-0024 main/slice documentation to use advisory-to-portfolio-management
    and discretionary portfolio-management language.
  - Added a public documentation vocabulary contract covering RFC-0023 through RFC-0028 source files.
  - Focused public-doc vocabulary tests pass.
- Consequence:
  - Business, pre-sales, and implementation readers see consistent private-banking vocabulary
    across the implemented RFC crown-jewel sequence.
- Documentation:
  - RFC source changed. No wiki source change is required because wiki pages already used
    portfolio-management wording.
- Follow-Up:
  - Keep explicit `DPM_OWNER` wording limited to the inbound caller-role compatibility exception
    until Gateway/Workbench migration removes it.

## LA-REV-330

- Scope: Mesh data-product wiki boundary for RFC-0023/RFC-0024/RFC-0028
- Pattern: Current wiki truth must not imply client-ready publication or stale bank-demo gating
- Status: Hardened
- Finding Class: Documentation truth and commercial-claim governance
- Summary: The mesh data-product operating rule still described proposal narrative truth as
  advisor-review only "until" client-draft and client-ready publication slices were implemented,
  and memo truth still said full bank-demo/RFP package claims remained gated. That wording was easy
  to misread after RFC-0028 implemented supported-claim demo/RFP proof while client-ready
  publication remains blocked.
- Evidence:
  - Updated `wiki/Mesh-Data-Products.md` to state that narrative evidence remains advisor-review
    only and that compliance-review, client-draft, client-ready publication, and external client
    communication remain unsupported unless a later source-owned RFC proves those controls.
  - Updated the same page to route bank-demo/RFP proof truth to RFC-0028 supported claims without
    promoting client-ready memo publication.
  - Added a wiki contract test that rejects the stale client-ready-publication and full-demo-gating
    wording.
- Consequence:
  - Business, pre-sales, and operations readers get the current implemented proof boundary without
    interpreting mesh data-product status as client-ready publication or obsolete RFC-0028 gating.
- Documentation:
  - Wiki source changed; wiki check/publish is required before/after merge.
- Follow-Up:
  - Continue reviewing public wiki operating rules for stale pre-RFC-0028 language before PR
    handoff.

## LA-REV-331

- Scope: RFC-0023 through RFC-0026 current documentation and closure records
- Pattern: Current RFC truth must route bank-demo/RFP proof to RFC-0028 without reviving stale
  pre-RFC-0028 gating language
- Status: Hardened
- Finding Class: Documentation truth and commercial-claim governance
- Summary: Current RFC bodies, RFC index material, and durable RFC-0024/RFC-0025 closure records
  still contained phrasing that full RFC-0028 bank-demo/RFP claims remained gated. That was true
  before RFC-0028 completion, but after supported-claim proof shipped it understated the supported
  demo/RFP proof boundary and could confuse business readers.
- Evidence:
  - Updated current RFC-0023/RFC-0024/RFC-0025/RFC-0026 source pages, RFC index source, and wiki
    RFC index source to route broader bank-demo/RFP proof to RFC-0028 supported claims.
  - Removed stale RFC-0025 wording that described client-ready policy publication and external
    client communication as blocked only until final closure, because final closure is complete and
    those controls remain blocked unless a later source-owned RFC proves them.
  - Preserved the stronger blocked wording for client-ready publication, external communication,
    policy approval authority, OMS/order lifecycle, and execution/settlement claims.
  - Updated RFC-0024/RFC-0025 final-closure contract tests and added a public-doc vocabulary
    guard against stale RFC-0028 gating phrases in current public documentation.
  - Full `make check` passed with 1555 unit tests after formatting.
- Consequence:
  - Implementation-backed commercial proof can be described accurately without promoting
    client-ready publication or approval authority.
- Documentation:
  - RFC and wiki source changed; wiki check/publish is required before/after merge.
- Follow-Up:
  - Keep historical slice records audit-friendly, but keep current RFC and wiki summaries aligned
    with the implemented RFC-0028 supported-claim boundary.

## LA-REV-332

- Scope: RFC-0028 proof-pack logical contract references
- Pattern: Proof-pack references should be bounded Lotus logical refs, not arbitrary URL-shaped
  strings
- Status: Hardened
- Finding Class: Security posture and API model validation
- Summary: `AdvisoryBankDemoProofPack` normalized `scenario_contract_ref` and
  `supported_claim_register_ref` as generic required text. That preserved normal output but did
  not reject external URLs, query strings, fragments, credentials, or sensitive path fragments in
  those contract-reference fields.
- Evidence:
  - Added `normalize_lotus_advise_contract_ref` for RFC-0028 Lotus Advise logical contract refs.
  - Applied the validator to proof-pack scenario-contract and supported-claim-register refs.
  - Added model regression tests for external URLs, query/token leakage, path traversal, and
    sensitive contract reference fragments.
  - Focused proof-model tests, `python -m compileall src/core/bank_demo_proof`, and full
    `make check` passed with 1555 unit tests.
- Consequence:
  - Proof-pack API payloads cannot smuggle arbitrary external references or sensitive material
    through contract-ref fields while preserving the governed `lotus-advise://...` contract ids.
- Documentation:
  - Review ledger updated. No public README/wiki change is required because the supported public
    contract shape did not change.
- Follow-Up:
  - Keep future proof-pack reference fields wired through explicit logical-ref or artifact-ref
    validators instead of generic string normalization.

## LA-REV-333

- Scope: RFC-0027 advisory copilot route error boundary
- Pattern: Controller error mapping should preserve status semantics without leaking sensitive
  lower-layer detail
- Status: Hardened
- Finding Class: Security posture and API error handling
- Summary: Advisory copilot routes mapped controlled `ValueError` codes to HTTP 404/409/422, but
  returned the raw exception text. Current domain/service paths usually emit bounded error codes,
  yet the route boundary should still fail closed if a lower layer accidentally includes raw prompt,
  provider, token, or credential detail in a validation error.
- Evidence:
  - Added route-level sensitive-detail detection for copilot error mapping.
  - Sensitive copilot route errors now return `ADVISORY_COPILOT_REQUEST_VALIDATION_FAILED` with
    HTTP 422 instead of echoing raw lower-layer detail.
  - Added API regression coverage proving raw prompt/token detail is redacted while existing route
    status-code mapping remains intact.
  - Focused `tests/unit/advisory/api/test_api_advisory_copilot.py` and full `make check` passed
    with 1556 unit tests.
- Consequence:
  - RFC-0027 API consumers get stable error semantics without exposing sensitive AI/provider
    details through route-level exception handling.
- Documentation:
  - Review ledger updated. No public README/wiki change is required because this hardens an
    existing supported boundary without changing the documented feature posture.
- Follow-Up:
  - Keep future copilot route errors constrained to bounded codes or sanitized business-safe
    messages.

## LA-REV-343

- Scope: Runtime readiness probe error detail
- Pattern: Readiness probes should expose controlled operational posture without leaking
  configuration, credential, or driver details
- Status: Hardened
- Finding Class: Security posture and operational diagnostics
- Summary: `_readiness_probe` returned raw `RuntimeError` text from runtime persistence or proposal
  repository initialization. Controlled operational codes are useful for operators, but raw driver
  or configuration failures can include DSNs, passwords, tokens, or other sensitive detail.
- Evidence:
  - Added safe readiness error-detail projection in `src/api/main.py`.
  - Controlled readiness failures still return their existing detail.
  - Sensitive runtime failures now return `READINESS_CHECK_FAILED`.
  - Focused `ruff`, format check, health tests, and internal guard tests passed with 9 tests.
- Consequence:
  - `/health/ready` remains useful for operations while failing closed on sensitive runtime
    initialization errors.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is defensive
    runtime diagnostics hardening.
- Follow-Up:
  - Keep health/readiness error bodies bounded and route deeper diagnostics to logs/telemetry.

## LA-REV-342

- Scope: Lotus Core simulation exception handler
- Pattern: Global exception handlers for upstream dependencies must preserve useful contract errors
  without echoing sensitive provider or request detail
- Status: Hardened
- Finding Class: Security posture and API error handling
- Summary: The `LotusCoreSimulationUnavailableError` exception handler returned `str(exc)` directly
  in problem-details responses. Current Lotus Core errors are usually controlled, and contract
  mismatch details are useful, but an upstream problem payload could include bearer tokens,
  credentials, raw payloads, or provider response detail.
- Evidence:
  - Added safe Lotus Core simulation error-detail projection in `src/api/main.py`.
  - Non-sensitive upstream contract errors still return their original status and detail.
  - Sensitive upstream simulation details now return `LOTUS_CORE_SIMULATION_UNAVAILABLE`.
  - Focused `ruff`, format check, core simulation error tests, and internal guard tests passed with
    7 tests.
- Consequence:
  - Proposal simulation problem-details responses stay operationally useful while failing closed for
    sensitive upstream detail.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is defensive API
    exception-handler hardening.
- Follow-Up:
  - Apply the same fail-closed rule to any new global exception handler for external dependencies.

## LA-REV-341

- Scope: RFC-0028 bank-demo proof API sensitive-detail detector
- Pattern: API routes should share one sensitive-error detector instead of maintaining duplicate
  fragment lists per route family
- Status: Hardened
- Finding Class: Duplication reduction and security posture
- Summary: The bank-demo proof router carried its own sensitive-error fragment list even though the
  API layer now has a shared detector used by proposal, workspace, report, and copilot routes.
- Evidence:
  - Replaced the route-local fragment list in `src/api/routers/bank_demo_proof.py` with the shared
    `src/api/sensitive_error_details.py` detector.
  - Existing RFC-0028 proof-pack API tests continued to cover sensitive source-evidence redaction.
  - Focused `ruff`, format check, and bank-demo proof API tests passed with 8 tests.
- Consequence:
  - RFC-0028 proof-pack route behavior stays unchanged while the API layer has less duplicated
    security-sensitive matching logic.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is internal
    defensive code consolidation.
- Follow-Up:
  - Keep domain-specific proof-field validators separate when they validate business payloads, but
    use the shared API detector for route error-detail redaction.

## LA-REV-340

- Scope: Legacy proposal simulation idempotency cache export
- Pattern: Repository-backed runtime should not retain unused in-memory idempotency cache exports or
  tests that reset dead state
- Status: Hardened
- Finding Class: Dead code and test reliability
- Summary: `src/api/services/advisory_simulation_service.py` still declared
  `PROPOSAL_IDEMPOTENCY_CACHE` and `MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE`, and `src/api/main.py`
  re-exported them. The simulation path now persists idempotency through the proposal repository;
  the cache was only being cleared by tests and no longer influenced behavior.
- Evidence:
  - Removed the unused cache and max-size constant from the simulation service and main exports.
  - Updated unit and integration test setup to reset the actual proposal repository/service boundary
    instead of clearing dead state.
  - Added an internal guard test preventing `src.api.main` from re-exporting the legacy cache.
  - Focused `ruff`, format check, lifecycle API tests, memo API tests, and internal guard tests
    passed with 102 tests.
- Consequence:
  - Proposal idempotency ownership is clearer: persistence is repository-backed, and tests no
    longer imply a non-production in-memory cache is authoritative.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this removes stale
    internal implementation residue.
- Follow-Up:
  - Continue removing test-only compatibility exports when they no longer match runtime ownership.

## LA-REV-339

- Scope: Proposal memo report-package OpenAPI description
- Pattern: Public API descriptions must reflect implemented report handoff behavior and not carry
  stale slice-history language into business-facing contracts
- Status: Hardened
- Finding Class: API documentation quality and implementation truth
- Summary: The memo report-package event endpoint still described report/render/archive realization
  as later scope. That was stale now that the adjacent memo report-package request endpoint requests
  Lotus Report materialization and records returned report, render, and archive references.
- Evidence:
  - Updated the report-package event endpoint description to distinguish lineage event recording
    from the Lotus Report materialization request endpoint.
  - Added an OpenAPI contract assertion that the endpoint references the reporting owner, points to
    the report-package request endpoint, and does not reintroduce `later scope` language.
  - Focused `ruff`, format check, and OpenAPI lifecycle contract test passed.
- Consequence:
  - Swagger/OpenAPI now presents current memo reporting behavior without leaking implementation-slice
    history or underclaiming the supported report-package flow.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because the durable user-facing
    API contract text is the changed truth.
- Follow-Up:
  - Keep stale implementation-phase phrases out of OpenAPI descriptions when RFC slices are promoted.

## LA-REV-338

- Scope: Lotus Report integration API error boundaries
- Pattern: Report materialization routes should return a stable unavailable posture without
  exposing upstream report/render/archive error detail
- Status: Hardened
- Finding Class: Security posture and API error handling
- Summary: Delivery report requests, memo report packages, and policy evaluation report packages
  each mapped `LotusReportUnavailableError` directly to `detail=str(exc)`. The current adapter uses
  a controlled `LOTUS_REPORT_REQUEST_UNAVAILABLE` code, but a future integration error could carry
  provider response, bearer token, credential, or raw payload detail.
- Evidence:
  - Added shared Lotus Report unavailable HTTP mapping in
    `src/api/proposals/report_errors.py`.
  - Delivery, memo, and policy evaluation report routes now use the shared mapper.
  - Added a route test that proves sensitive Lotus Report unavailable detail is redacted.
  - Confirmed no remaining `detail=str(exc)` mappings under `src/api`.
  - Focused `ruff`, format check, lifecycle report-route tests, memo API tests, and policy
    evaluation API tests passed with 21 tests.
  - Full repository `make check` passed with 1,568 unit tests after the API boundary hardening
    sequence.
- Consequence:
  - Report integration routes keep stable service-unavailable semantics while preventing upstream
    report/render/archive details from leaking through Advise API responses.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is defensive API
    boundary hardening for existing report behavior.
- Follow-Up:
  - Keep future integration-unavailable mappings behind bounded-detail helpers.

## LA-REV-337

- Scope: Advisory copilot repository startup boundary
- Pattern: Copilot route startup failures should preserve controlled repository posture while
  sharing the platform API sensitive-detail detector
- Status: Hardened
- Finding Class: Security posture and API error handling
- Summary: The copilot route module had its own sensitive-fragment list and returned raw
  repository startup `RuntimeError` text through a 503 response. Controlled repository failures
  should remain visible, but DSN, password, token, or driver detail should fail closed.
- Evidence:
  - Copilot route validation now uses the shared API sensitive-detail detector.
  - Copilot repository startup failures redact sensitive detail to
    `ADVISORY_COPILOT_REPOSITORY_UNAVAILABLE`.
  - Added a repository dependency test for sensitive startup failures.
  - Focused `ruff`, format check, and copilot API tests passed with 17 tests.
- Consequence:
  - Copilot API diagnostics remain stable for controlled Lotus error codes while reducing the risk
    of configuration or credential detail leaking during startup failure.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is defensive API
    boundary hardening for existing copilot behavior.
- Follow-Up:
  - Continue converging route-local error mappings onto shared bounded-detail helpers.

## LA-REV-336

- Scope: Advisory proposal simulation API validation boundaries
- Pattern: Simulation validation and context-resolution errors should preserve controlled proposal
  error codes without leaking lower-layer request, credential, or upstream context detail
- Status: Hardened
- Finding Class: Security posture and API error handling
- Summary: `src/api/services/advisory_simulation_service.py` returned raw exception text for
  idempotency validation, simulation-gate validation, alternatives normalization, and proposal
  context resolution. Most present exceptions are controlled domain codes, but the service also
  wraps lower-layer context-resolution and normalization failures where future raw payload, token,
  or provider detail could otherwise reach the API response body.
- Evidence:
  - Simulation validation details now use the shared proposal error-detail redaction helper.
  - Controlled simulation errors such as `PROPOSAL_SIMULATION_DISABLED` and
    `IDEMPOTENCY_KEY_CONFLICT` keep their existing status and business-facing behavior.
  - Added route tests for sensitive idempotency validation and context-resolution errors.
  - Focused `ruff`, format check, proposal simulation API tests, and proposal HTTP error tests
    passed with 51 tests.
- Consequence:
  - Proposal simulation remains operationally diagnosable through bounded Lotus error codes while
    reducing the chance of sensitive advisory context or upstream details leaking into client HTTP
    bodies.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is defensive API
    boundary hardening for existing proposal simulation behavior.
- Follow-Up:
  - Continue applying the same bounded-detail rule to remaining route modules that still raise
    `HTTPException(... detail=str(exc))`.

## LA-REV-335

- Scope: Advisory workspace API error boundaries
- Pattern: Workspace routes should preserve controlled business error codes without echoing
  sensitive upstream or lower-layer exception details
- Status: Hardened
- Finding Class: Security posture and API error handling
- Summary: Workspace route handlers returned `str(exc)` directly for not-found, conflict, and
  assistant-unavailable paths. The current domain services usually raise controlled codes, but
  several paths wrap lower-layer failures. A future upstream failure could accidentally expose
  authorization headers, tokens, raw payloads, raw prompts, provider responses, or credentials in
  the HTTP response body.
- Evidence:
  - Added shared sensitive API error-detail detection in `src/api/sensitive_error_details.py`.
  - Moved proposal route redaction to the shared detector instead of duplicating fragment logic.
  - Added workspace-specific bounded API details in `src/api/workspaces/errors.py`.
  - Workspace route handlers now use the shared workspace error mapper for 404, 409, and assistant
    unavailable paths while preserving `LOTUS_AI_RATIONALE_UNAVAILABLE` as the controlled 503
    integration posture.
  - Focused `ruff` and workspace/proposal API tests passed with 54 tests.
- Consequence:
  - Advisory workspace, proposal, and AI-assistant route families now share the same sensitive-detail
    detection baseline while retaining private-banking business error vocabulary for supported
    client workflows.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is defensive API
    boundary hardening for existing workspace behavior.
- Follow-Up:
  - Continue removing direct `detail=str(exc)` mappings in service-facing API helpers where a
    controlled Lotus API error detail is more appropriate.

## LA-REV-334

- Scope: Shared proposal API error mapper
- Pattern: Proposal route error mapping should preserve domain status codes without echoing
  sensitive lower-layer detail
- Status: Hardened
- Finding Class: Security posture and API error handling
- Summary: `raise_proposal_http_exception` was the shared mapper for proposal, memo, policy,
  cockpit, delivery, async, and workspace API errors, but it returned `str(exc)` for every domain
  exception. Most current domain exceptions use controlled codes, but the shared route boundary
  should fail closed if a validation or idempotency path accidentally carries a token, raw prompt,
  provider response, credential, or similar sensitive detail.
- Evidence:
  - Added shared proposal error-detail sanitization in `src/api/proposals/errors.py`.
  - Normal controlled proposal error text is still preserved for 404, 409, and 422 mappings.
  - Sensitive proposal error text now returns bounded details: `PROPOSAL_NOT_FOUND`,
    `PROPOSAL_CONFLICT`, or `PROPOSAL_REQUEST_VALIDATION_FAILED`.
  - Focused tests covering proposal HTTP errors, internal guards, advisor cockpit, and policy
    evaluation APIs passed with 33 tests.
  - Full repository `make check` passed with 1,561 unit tests.
- Consequence:
  - Broad proposal-family API routes retain stable status semantics while reducing the chance of
    sensitive source evidence leaking through exception text.
- Documentation:
  - Review ledger updated. No README/wiki source change is required because this is defensive API
    error-boundary hardening for existing behavior.
- Follow-Up:
  - Keep new proposal-family domain errors as controlled codes, and use the shared mapper rather
    than route-local `detail=str(exc)` when adding API routes.

## LA-REV-326

- Scope: OpenAPI enrichment portfolio-id example vocabulary
- Pattern: Generated API examples should use the canonical private-banking proof portfolio rather
  than legacy demo identifiers
- Status: Hardened
- Finding Class: API documentation quality and private-banking vocabulary
- Summary: The generic OpenAPI enrichment helper still emitted `DEMO_DPM_EUR_001` as the default
  portfolio-id example. That legacy identifier could leak into generated endpoint examples even
  though the governed RFC-0023 through RFC-0028 proof path uses `PB_SG_GLOBAL_BAL_001`.
- Evidence:
  - Replaced the generic portfolio-id OpenAPI example with `PB_SG_GLOBAL_BAL_001`.
  - Updated the OpenAPI enrichment unit test to pin the canonical private-banking example.
- Consequence:
  - Generated Advise API examples align with the governed front-office proof dataset and avoid
    legacy discretionary-portfolio-management abbreviations.
- Documentation:
  - No README/wiki source change is required. This is generated API contract example hygiene.
- Follow-Up:
  - Continue scanning generated docs and examples for stale non-private-banking vocabulary before
    PR handoff.
