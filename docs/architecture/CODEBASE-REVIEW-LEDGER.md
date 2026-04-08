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
