# Lotus Advise Work To Be Done

This ledger records follow-up work discovered during `lotus-advise` hardening. Other Lotus
repositories remain read-only for this refactor program; upstream or downstream issues must be
recorded here with enough detail for later owner-specific slices.

## WTBD-001: Continue Proposal Service Decomposition

- Owning repository: `lotus-advise`
- Finding class: modularity problem
- Current evidence:
  - `src/core/proposals/service.py` remains a large orchestration module.
  - `src/core/proposals/models.py` remains a large contract module.
- Progress:
  - Async create/version submission hashing and replay metadata extraction now live in
    `src/core/proposals/async_payloads.py`.
  - Workflow transition, approval-transition, execution-update, execution-status, and
    state-correlation rules now live in `src/core/proposals/workflow_rules.py`.
  - Delivery-summary projection now reuses the shared execution-status vocabulary from
    `src/core/proposals/workflow_rules.py`.
  - Proposal summary, version detail, workflow event, and approval record projections now live in
    `src/core/proposals/projections.py`.
  - Execution-status projection and latest execution event selection now live in
    `src/core/proposals/execution_status.py`.
  - Report-request workflow event construction now lives in `src/core/proposals/reporting.py`.
  - Async operation attempt, success, failure, retry, and replay-lineage state helpers now live in
    `src/core/proposals/async_operations.py`.
  - Async create/version payload recovery and failure outcomes now live in
    `src/core/proposals/async_payloads.py`.
  - Immutable proposal version-record construction now lives in `src/core/proposals/versions.py`.
  - Create-version eligibility policy now lives in `src/core/proposals/versions.py`, keeping
    terminal-state, expected-version, and portfolio-context validation out of the workflow service.
  - New proposal-version lifecycle state mutation now lives in
    `src/core/proposals/versions.py`, keeping current-version increment, draft reset, and
    last-event timestamp mutation out of the workflow service.
  - Lifecycle-origin validation now lives in `src/core/proposals/lifecycle.py`.
  - Create response and async operation response DTO projections now live in
    `src/core/proposals/projections.py`.
  - Proposal lineage response assembly now lives in `src/core/proposals/projections.py`, including
    immutable version item projection, latest-version selection, and missing-version detection.
  - Proposal lineage read-model loading now lives in
    `src/core/proposals/lineage_read_model.py`, keeping proposal/version-list repository loading
    out of the workflow service.
  - Proposal workflow timeline and approval-history response assembly now live in
    `src/core/proposals/projections.py`, keeping lifecycle read-model projection out of the
    workflow service.
  - Proposal delivery summary and delivery-history response assembly now live in
    `src/core/proposals/delivery_summary.py`, alongside the existing delivery event selection and
    execution/reporting posture extraction.
  - Proposal idempotency lookup response projection now lives in
    `src/core/proposals/projections.py`, keeping audit timestamp formatting out of the workflow
    service.
  - Idempotency replay create-response referent validation now lives in
    `src/core/proposals/projections.py`, keeping response assembly and missing-referent detection
    out of the workflow service's repository read path.
  - Proposal execution handoff replay response, requested-event construction, and accepted response
    projection now live in `src/core/proposals/execution_handoff.py`, while the workflow service
    retains lookup, idempotency replay detection, expected-state validation, and persistence.
  - Proposal execution handoff aggregate timestamp mutation now lives in
    `src/core/proposals/execution_handoff.py`, keeping handoff event-time state mutation out of the
    workflow service.
  - Proposal execution handoff readiness validation now lives in
    `src/core/proposals/execution_handoff.py`, keeping the execution-ready domain rule out of the
    workflow service while preserving API error mapping.
  - Proposal execution update event construction now lives in
    `src/core/proposals/execution_update.py`, while the workflow service retains handoff identity
    matching, terminal-state rejection, timestamp ordering, replay detection, and persistence.
  - Proposal execution update handoff identity validation now lives in
    `src/core/proposals/execution_update.py`, keeping execution request/provider reconciliation
    vocabulary out of the workflow service while preserving API error mapping.
  - Proposal execution update terminal-state validation now lives in
    `src/core/proposals/execution_update.py`, keeping terminal lifecycle rejection out of the
    workflow service while preserving API error mapping.
  - Proposal execution update handoff timestamp ordering now lives in
    `src/core/proposals/execution_update.py`, keeping execution update event-time validation out of
    the workflow service while preserving API error mapping.
  - Proposal execution update event-time resolution now lives in
    `src/core/proposals/execution_update.py`, keeping payload-versus-service-clock timestamp
    selection out of the workflow service.
  - Proposal execution update idempotency-key construction now lives in
    `src/core/proposals/execution_update.py`, keeping replay lookup identity and event lineage
    identity aligned.
  - Proposal execution update canonical request hashing now lives in
    `src/core/proposals/execution_update.py`, keeping replay hash and event lineage hash
    construction beside update replay identity.
  - Generic proposal state-transition event construction and transition response projection now
    live in `src/core/proposals/lifecycle_events.py`, while the workflow service retains proposal
    lookup, replay detection, expected-state validation, transition-rule resolution, and persistence.
  - Generic lifecycle transition aggregate state mutation now lives in
    `src/core/proposals/lifecycle_events.py`, keeping state and last-event timestamp mutation out of
    the workflow service for state transitions and approvals.
  - Generic proposal state-transition canonical request hashing now lives in
    `src/core/proposals/lifecycle_events.py`, keeping transition replay hash construction beside
    transition event construction.
  - Proposal approval canonical request hashing now lives in
    `src/core/proposals/lifecycle_events.py`, keeping approval replay hash construction beside
    approval record and approval event construction.
  - Proposal approval replay response assembly now lives in
    `src/core/proposals/lifecycle_events.py`, keeping replay referent projection beside approval
    response projection.
  - Proposal state-transition replay response assembly now lives in
    `src/core/proposals/lifecycle_events.py`, keeping idempotency replay projection beside normal
    state-transition response projection.
  - Execution-update replay detection now uses the already-loaded workflow event stream through
    `src/core/proposals/execution_update.py`, avoiding duplicate event reads on idempotent replay
    while preserving replay hash conflict behavior.
  - Execution-handoff canonical request hashing now lives in
    `src/core/proposals/execution_handoff.py`, keeping handoff replay hash construction beside
    handoff event and replay response construction.
  - Proposal create and version canonical request hashing now lives in
    `src/core/proposals/context.py`, keeping request identity beside resolved advisory-context
    canonicalization instead of workflow service orchestration.
  - Advisory proposal simulation execution now lives in
    `src/core/proposals/simulation_execution.py`, keeping correlation ID resolution and advisory
    orchestration invocation out of the workflow service.
  - The stale service-private simulation execution wrapper has been removed; create and version
    flows now call the proposal-domain simulation execution boundary directly.
  - Proposal artifact and evidence-bundle materialization now lives in
    `src/core/proposals/materialization.py`, removing duplicated create/version artifact and
    evidence assembly from the workflow service.
  - Proposal lineage now uses a repository-native ordered version list instead of one
    `get_version` read per version number, reducing N+1 read shape while preserving gap detection.
  - Async operation replay referent loading now lives in `src/core/proposals/async_replay.py`,
    keeping version-selection and event-loading rules out of the workflow service.
  - Proposal version replay referent loading now lives in `src/core/proposals/proposal_replay.py`,
    reusing one tested boundary for version replay and idempotent create-response reconstruction.
  - Proposal version read-model loading now lives in
    `src/core/proposals/version_read_model.py`, keeping direct version-detail repository loading
    out of the workflow service.
  - Proposal activity read-model loading now lives in
    `src/core/proposals/activity_read_model.py`, reducing repeated proposal/event loading across
    workflow timeline, execution status, delivery summary/history, and execution-update replay
    paths.
  - Proposal approval read-model loading now lives in
    `src/core/proposals/approval_read_model.py`, keeping approval posture repository loading out of
    the workflow service.
  - Proposal detail read-model loading now lives in
    `src/core/proposals/detail_read_model.py`, keeping proposal/current-version repository loading
    out of the workflow service.
  - Idempotent replay event and approval lookups now live in
    `src/core/proposals/idempotency.py`, keeping replay repository loading next to replay matching
    rules.
  - Proposal idempotency read-model loading now lives in
    `src/core/proposals/idempotency_read_model.py`, keeping replay-audit key lookup repository
    loading out of the workflow service.
  - Proposal async-operation status read-model loading now lives in
    `src/core/proposals/async_operation_read_model.py`, keeping operation-id and correlation-id
    status lookup repository loading out of the workflow service.
  - Report-request event creation and aggregate timestamp mutation now live behind
    `build_report_request_event_and_apply_state` in `src/core/proposals/reporting.py`, keeping
    report command state logic out of the workflow service.
  - Execution handoff event creation and aggregate timestamp mutation now live behind
    `build_execution_handoff_event_and_apply_state` in
    `src/core/proposals/execution_handoff.py`, keeping handoff command state logic out of the
    workflow service.
  - State-transition event creation and aggregate state mutation now live behind
    `build_state_transition_event_and_apply_state` in
    `src/core/proposals/lifecycle_events.py`, keeping transition command state logic out of the
    workflow service.
  - Approval record creation, approval transition event creation, and aggregate state mutation now
    live behind `build_approval_command_state_and_apply_transition` in
    `src/core/proposals/lifecycle_events.py`, keeping approval command state logic out of the
    workflow service.
  - Execution update event creation and aggregate state mutation now live behind
    `build_execution_update_event_and_apply_state` in
    `src/core/proposals/execution_update.py`, keeping execution update command state logic out of
    the workflow service.
  - New-version lifecycle event creation and aggregate version-state mutation now live behind
    `build_new_version_created_event_and_apply_state` in `src/core/proposals/versions.py`, keeping
    create-version command state logic out of the workflow service.
  - Initial proposal aggregate, `CREATED` lineage event, and proposal-create idempotency record
    assembly now live behind `build_proposal_create_command_state` in
    `src/core/proposals/records.py`, keeping create command state referent construction out of the
    workflow service.
  - Execution-update aggregate state mutation now lives in
    `src/core/proposals/execution_update.py`, keeping execution update state and last-event
    timestamp mutation out of the workflow service.
  - Report-request aggregate timestamp mutation now lives in
    `src/core/proposals/reporting.py`, keeping report lineage event-time policy out of the
    workflow service.
  - Proposal approval record construction, approval workflow-event construction, and approval
    transition response projection now live in `src/core/proposals/lifecycle_events.py`, while the
    workflow service retains approval replay referent checks, expected-state validation,
    approval-transition rule resolution, and persistence.
  - Proposal evidence-bundle enrichment now lives in `src/core/proposals/evidence.py`, consolidating
    context-resolution override handling, risk-lens extraction, and replay-lineage attachment across
    proposal create and version create paths.
  - Proposal `CREATED` and `NEW_VERSION_CREATED` lifecycle event construction now lives in
    `src/core/proposals/lifecycle_events.py`, keeping create/version workflow event assembly
    consistent with the other lifecycle command helpers.
  - Initial proposal aggregate construction and proposal-create idempotency record construction now
    live in `src/core/proposals/records.py`, keeping default lifecycle state and replay identity
    construction out of the workflow service.
  - Async create-proposal and create-version operation record construction now lives in
    `src/core/proposals/async_operations.py`, keeping persisted operation payload shape,
    submission hash lineage, retry counters, and initial status defaults out of the workflow
    service.
  - Async create-proposal replay identity validation now lives in
    `src/core/proposals/async_operations.py`, keeping operation-type, idempotency-key, and
    submission-hash matching out of the workflow service.
  - Async create-version replay identity validation now lives in
    `src/core/proposals/async_operations.py`, keeping operation-type, proposal-scope, and
    submission-hash matching out of the workflow service.
  - Recoverable async operation kind classification now lives in
    `src/core/proposals/async_operations.py`, keeping supported recovery operation vocabulary out of
    the workflow service.
  - Async operation terminal-run skip handling now lives in
    `src/core/proposals/async_operations.py`, keeping missing/terminal operation retry-loop
    vocabulary out of the workflow service.
  - Async operation result-version extraction now lives in
    `src/core/proposals/async_operations.py`, keeping replay-evidence version selection parsing out
    of the workflow service.
  - Async create-submission outcome counters now live behind
    `AsyncCreateSubmissionStatsTracker` in `src/core/proposals/async_operations.py`, keeping
    thread-safe accepted/replayed/conflict bookkeeping out of the workflow service.
  - Stale service-private projection wrappers have been removed; `ProposalWorkflowService` now calls
    projection helpers directly.
  - Stale module-level `utc_now` helper has been removed from
    `src/core/proposals/async_operations.py`; async operation state transitions receive explicit
    timestamps from the workflow service.
  - Stale async replay-lineage service wrapper and unused time helper have been removed.
  - Stale service-private version-record wrapper has been removed; create paths call the version
    builder directly.
  - The wiki architecture page now documents the implementation-backed proposal module boundaries
    and lineage flow with diagrams.
  - Workflow event and approval replay idempotency lookup now lives in
    `src/core/proposals/idempotency.py`.
  - Expected-state optimistic concurrency validation now lives in
    `src/core/proposals/concurrency.py`.
  - Proposal simulation enablement validation now lives in
    `src/core/proposals/simulation_gate.py` and is reused by lifecycle and direct simulation
    service paths.
  - Proposal fallback correlation ID resolution now lives in
    `src/core/proposals/correlation.py` and is reused by lifecycle, async, and direct simulation
    paths.
  - Proposal-domain identifier factories now live in `src/core/proposals/identifiers.py` and cover
    proposal, version, workflow event, async operation, execution request, approval, and report
    request identifiers.
  - Stale service-private async submission hash wrappers have been removed; async create/version
    submission hashing is called directly from `src/core/proposals/async_payloads.py`.
- Follow-up:
  - Split lifecycle command handling, async operation handling, delivery projection, report request
    projection, and execution handoff helpers into smaller domain modules.
  - Keep API contracts stable while moving business rules out of controller and persistence seams.
  - Add characterization tests around each extracted rule before or during extraction.
  - Publish repo-local wiki updates after merge to `main`.

## WTBD-002: Continue Stateful Context Adapter Decomposition

- Owning repository: `lotus-advise`
- Finding class: query/performance risk
- Current evidence:
  - `src/integrations/lotus_core/stateful_context.py` remains a large upstream adapter that mixes
    source reads, translation, enrichment, caching, and supportability mapping.
- Follow-up:
  - Split portfolio source reads, instrument enrichment, market-data hydration, request translation,
    and cache policy into explicit submodules.
  - Preserve RFC-0082 authority boundaries: source facts stay in `lotus-core`; advisory context
    translation stays in `lotus-advise`.

## WTBD-003: Continue Workspace Service Decomposition

- Owning repository: `lotus-advise`
- Finding class: modularity problem
- Current evidence:
  - `src/api/services/workspace_service.py` remains a large API service that mixes workspace draft
    mutation, evaluation orchestration, replay evidence, saved-version handling, lifecycle handoff,
    and identifier generation.
- Progress:
  - Workspace identifier factories now live in `src/core/workspace/identifiers.py` and cover
    workspace session, trade draft, cash-flow draft, and saved-version identifiers.
  - Workspace reevaluation now uses the shared proposal correlation resolver so workspace-originated
    proposal simulations follow the same correlation ID policy as proposal-originated simulations.
  - Workspace replay evidence, draft-state hashing, saved-version matching, and handoff continuity
    now live in `src/core/workspace/replay.py`.
  - Workspace saved-version summary refresh and saved-version lookup now live in
    `src/core/workspace/versions.py`.
  - Workspace draft-state projection and simulation-request reconstruction now live in
    `src/core/workspace/draft_state.py`.
  - Workspace draft action mutation now lives in `src/core/workspace/draft_actions.py`.
  - Workspace lifecycle handoff metadata, proposal request assembly, simulate-request guards, and
    handoff context-resolution evidence now live in `src/core/workspace/handoff.py`.
  - Workspace evaluation summary construction, issue counts, and portfolio delta formatting now
    live in `src/core/workspace/evaluation.py`.
  - Workspace session cache state and LRU eviction now live in
    `src/api/services/workspace_store.py`.
  - Workspace saved-version comparison projection and diff-summary calculation now live in
    `src/core/workspace/compare.py`.
  - Workspace saved-version record construction, replay-evidence fallback, and defensive snapshot
    copying now live in `src/core/workspace/versions.py`.
  - Workspace saved-version resume snapshot application now lives in
    `src/core/workspace/versions.py`.
  - Workspace saved-version list projection now lives in
    `src/core/workspace/versions.py`.
  - Workspace session DTO construction now lives in `src/core/workspace/sessions.py`.
  - Workspace stateless resolved-context construction now lives in
    `src/core/workspace/sessions.py`, and stale stateful resolved-context service helper code has
    been removed.
  - Workspace lifecycle handoff completion, lifecycle-link assignment, and replay-continuity
    mutation now live in `src/core/workspace/handoff.py`.
  - Workspace reevaluation context assembly, policy selectors, context-resolution evidence, and
    request hashing now live in `src/core/workspace/reevaluation.py`.
- Follow-up:
  - Continue extracting workspace orchestration support only where behavior can be pinned outside
    the API service without duplicating upstream context resolution semantics.
  - Preserve existing workspace API contracts and lifecycle handoff semantics while reducing service
    size.

## WTBD-004: Keep Gateway And Workbench Capability Consumers Aligned

- Owning repositories: `lotus-gateway`, `lotus-workbench`
- Current action: read-only observation only; no issue has been confirmed in those repositories in
  this slice.
- Follow-up trigger:
  - If future `GET /platform/capabilities` fields change, verify `lotus-gateway` and
    `lotus-workbench` consume the capability contract without inferring advisory supportability
    locally.
  - Record the exact downstream file paths and expected payload deltas before making any
    cross-repository change.
