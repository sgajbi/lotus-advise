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
  - Lifecycle-origin validation now lives in `src/core/proposals/lifecycle.py`.
  - Create response and async operation response DTO projections now live in
    `src/core/proposals/projections.py`.
  - Stale service-private projection wrappers have been removed; `ProposalWorkflowService` now calls
    projection helpers directly.
- Follow-up:
  - Split lifecycle command handling, async operation handling, delivery projection, report request
    projection, and execution handoff helpers into smaller domain modules.
  - Keep API contracts stable while moving business rules out of controller and persistence seams.
  - Add characterization tests around each extracted rule before or during extraction.

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

## WTBD-003: Keep Gateway And Workbench Capability Consumers Aligned

- Owning repositories: `lotus-gateway`, `lotus-workbench`
- Current action: read-only observation only; no issue has been confirmed in those repositories in
  this slice.
- Follow-up trigger:
  - If future `GET /platform/capabilities` fields change, verify `lotus-gateway` and
    `lotus-workbench` consume the capability contract without inferring advisory supportability
    locally.
  - Record the exact downstream file paths and expected payload deltas before making any
    cross-repository change.
