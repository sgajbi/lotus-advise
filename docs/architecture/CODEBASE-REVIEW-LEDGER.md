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
