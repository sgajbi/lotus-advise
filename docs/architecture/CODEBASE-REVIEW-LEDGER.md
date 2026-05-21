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
- Summary: The proposal workflow service still owned async operation retry-loop mechanics,
  execution handoff command persistence, execution update command persistence, and report-request
  command persistence inline with high-level create, version, lifecycle, approval, execution,
  query, and replay coordination.
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
  - `src/core/proposals/service.py` delegates to those helpers while keeping the public workflow
    service API and existing exception behavior stable.
  - `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` continues to prove async
    create/version execution, lifecycle failure handling, runtime retry behavior, recovery of
    pending/expired operations, execution handoff replay/conflict behavior, execution update
    replay/conflict behavior, report request event recording, and proposal command compatibility.
- Consequence:
  - WTBD-001 is narrowed further: async runtime mechanics, execution handoff writes, execution
    update writes, and report command writes are now named proposal-domain boundaries rather than
    service-private branches. The remaining WTBD-001 work is concentrated in lifecycle/approval
    command orchestration and the large API contract module, which should be split only with
    explicit schema-compatibility safeguards.
- Follow-Up:
  - Continue WTBD-001 in small command-oriented slices; do not split `models.py` mechanically
    without a compatibility/export plan and OpenAPI regression proof.
