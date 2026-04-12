# RFC-0022 Slice 1: Current-State Assessment and Alternatives Contract Baseline

- RFC: `RFC-0022`
- Slice: `Slice 1`
- Status: COMPLETED
- Created: 2026-04-13
- Owners: lotus-advise

## Purpose

This document is the Slice 1 evidence artifact for RFC-0022.

Its role is to make the current proposal, lifecycle, artifact, workspace, and replay contract explicit before implementation begins on backend-owned proposal alternatives.

Slice 1 is complete only if:

1. current behavior is evidence-backed,
2. the surfaces that must eventually carry `proposal_alternatives` are explicit,
3. the minimum first-implementation scope is frozen,
4. cross-RFC ownership boundaries are reconciled with RFC-0020 and RFC-0021,
5. no Slice 2 or later implementation leaks into the assessment artifact.

## Executive Summary

`lotus-advise` already has the core evidence spine needed for proposal alternatives:

1. canonical proposal simulation through `lotus-core`,
2. canonical proposal allocation lens from RFC-0020,
3. canonical proposal concentration risk lens from RFC-0020,
4. canonical `proposal_decision_summary` from RFC-0021,
5. persisted proposal versions with replay-safe evidence bundles,
6. workspace evaluation, save, replay, and handoff flows,
7. deterministic artifact generation,
8. async proposal create/version replay continuity.

The current gap is not lack of upstream authority or lack of persisted lifecycle infrastructure. The gap is the absence of one backend-owned alternatives contract and orchestration layer that:

1. accepts explicit advisor objectives and constraints,
2. generates bounded candidate alternatives,
3. evaluates each candidate through canonical simulation, risk, and decision posture,
4. ranks and explains alternatives deterministically,
5. persists accepted, rejected, and selected alternatives across lifecycle and replay surfaces.

Current implementation is therefore ready for alternatives as an orchestration and contract-extension program. It is not ready for alternatives if that work tries to introduce new advisory-local calculation logic, a second decision-summary schema, or broader risk optimization claims than RFC-0020 currently supports.

## Current Surface Inventory

### Direct Simulation

Surface:

1. `POST /advisory/proposals/simulate`

Evidence:

1. `src/api/routers/advisory_simulation.py`
2. `src/api/services/advisory_simulation_service.py`
3. `src/core/advisory/orchestration.py`
4. `src/core/models.py`
   `ProposalResult`

Current relevant fields already returned on `ProposalResult`:

1. `before`
2. `after_simulated`
3. `explanation`
4. `diagnostics`
5. `suitability`
6. `gate_decision`
7. `proposal_decision_summary`
8. `allocation_lens`
9. `lineage`

Assessment:

1. direct simulation already returns the canonical ingredients alternatives must reuse,
2. there is no `alternatives_request` input block,
3. there is no `proposal_alternatives` response object,
4. there is no candidate-generation or ranking contract in the simulation response today.

### Proposal Artifact

Surface:

1. `POST /advisory/proposals/artifact`

Evidence:

1. `src/api/routers/advisory_simulation.py`
2. `src/core/advisory/artifact.py`
3. `src/core/advisory/artifact_models.py`

Current relevant artifact behavior:

1. artifact generation already consumes the same proposal simulation contract used by lifecycle flows,
2. artifact output already carries `proposal_decision_summary`,
3. artifact output already carries a normalized `risk_lens` summary,
4. artifact evidence bundles already persist request inputs and engine outputs.

Assessment:

1. artifacts are structurally ready to project alternatives later,
2. there is no artifact-level alternatives section yet,
3. artifact logic must not become the place where alternatives ranking or tradeoff inference is invented.

### Proposal Lifecycle Detail and Version Detail

Surfaces:

1. `POST /advisory/proposals`
2. `GET /advisory/proposals/{proposal_id}`
3. `GET /advisory/proposals/{proposal_id}/versions/{version_no}`
4. `POST /advisory/proposals/{proposal_id}/versions`
5. async create/version paths under `/advisory/proposals/async` and `/advisory/proposals/{proposal_id}/versions/async`

Evidence:

1. `src/api/proposals/routes_lifecycle.py`
2. `src/core/proposals/models.py`
   `ProposalVersionDetail`, `ProposalDetailResponse`, `ProposalCreateResponse`
3. `src/core/proposals/service.py`

Current relevant lifecycle behavior:

1. immutable version detail already persists full `proposal_result`,
2. immutable version detail already persists full `artifact`,
3. immutable version detail already persists `evidence_bundle`,
4. proposal service already stores `risk_lens` in `evidence_bundle_json`,
5. proposal service already stores replay lineage when present.

Assessment:

1. lifecycle persistence is ready to carry alternatives evidence once the model exists,
2. no proposal summary, version detail, or create response currently exposes alternatives,
3. there is no persisted selected-alternative contract today,
4. there is no alternatives-specific projection endpoint today.

### Replay Surfaces

Surfaces:

1. `GET /advisory/proposals/{proposal_id}/versions/{version_no}/replay-evidence`
2. `GET /advisory/proposals/operations/{operation_id}/replay-evidence`
3. workspace saved-version replay evidence surface

Evidence:

1. `src/api/proposals/routes_support.py`
2. `src/core/replay/models.py`
3. `src/core/replay/service.py`
4. `src/api/workspaces/router.py`
5. `src/api/services/workspace_service.py`

Current relevant replay behavior:

1. replay responses already expose normalized persisted evidence,
2. replay evidence already carries `risk_lens`,
3. replay evidence already carries `proposal_decision_summary`,
4. replay continuity already links workspace handoff and async execution back into persisted lifecycle evidence.

Assessment:

1. replay architecture already enforces the right persistence-first posture for alternatives,
2. alternatives must be added as persisted evidence and replayed from storage,
3. replay must not become a recomputation path for alternatives.

### Workspace Evaluation, Save, Resume, Compare, and Handoff

Surfaces:

1. `POST /advisory/workspaces`
2. `GET /advisory/workspaces/{workspace_id}`
3. `POST /advisory/workspaces/{workspace_id}/evaluate`
4. `POST /advisory/workspaces/{workspace_id}/save`
5. `POST /advisory/workspaces/{workspace_id}/resume`
6. `POST /advisory/workspaces/{workspace_id}/compare`
7. `POST /advisory/workspaces/{workspace_id}/handoff`

Evidence:

1. `src/api/workspaces/router.py`
2. `src/api/services/workspace_service.py`
3. `src/core/workspace/models.py`

Current relevant workspace behavior:

1. workspace sessions already retain `latest_proposal_result`,
2. workspace replay evidence already retains `risk_lens`,
3. workspace handoff already bridges into persisted proposal lifecycle without duplicating lifecycle ownership,
4. workspace metadata already retains `mandate_id` where available.

Assessment:

1. workspace is a natural alternatives consumer because selection is likely to happen there before handoff,
2. no workspace contract currently carries alternatives state,
3. no workspace save/handoff path currently persists a selected alternative id,
4. alternatives selection must therefore be designed as an additive lifecycle/workspace contract change, not a local UI/session-only behavior.

## Existing Upstream Evidence Available Today

### Canonical Simulation and Allocation Authority

Evidence:

1. `src/integrations/lotus_core/simulation.py`
2. `src/core/models.py`
   `ProposalAllocationLens`, `ProposalResult`
3. `src/core/advisory/orchestration.py`
4. RFC-0020 implementation references in `docs/rfcs/RFC-0020-canonical-allocation-and-risk-lens-convergence.md`

Available today:

1. `lotus-core` remains the normal simulation authority,
2. `ProposalResult` already carries `allocation_lens`,
3. proposal before/after states already expose canonical RFC-0020 allocation evidence,
4. the current authoritative proposal allocation scope is the curated RFC-0020 front-office subset: `asset_class`, `currency`, `sector`, `country`, `region`, `product_type`, and `rating`.

Assessment:

1. alternatives must reuse this allocation lens,
2. alternatives must not create a second advisory-local allocation or AUM calculation path,
3. alternatives comparison should stay within the RFC-0020 proposal allocation subset for first implementation.

### Canonical Risk Lens Authority

Evidence:

1. `src/integrations/lotus_risk/enrichment.py`
2. `src/core/advisory/risk_lens.py`
3. `src/core/advisory/decision_material_changes.py`
4. RFC-0020 implementation references in `docs/rfcs/RFC-0020-canonical-allocation-and-risk-lens-convergence.md`

Available today:

1. proposal risk evidence already flows from `lotus-risk`,
2. current implemented production proposal risk scope is concentration lensing,
3. shelf issuer metadata is already assembled for changed instruments during risk enrichment,
4. degraded risk behavior is already explicit.

Assessment:

1. first alternatives implementation can truthfully compare concentration improvement,
2. first alternatives implementation must not imply optimization across broader unavailable risk methodologies,
3. any future broader risk objective must be gated by a later RFC or later authoritative upstream support.

### Canonical Decision Posture

Evidence:

1. `src/core/advisory/decision_summary.py`
2. `src/core/advisory/decision_summary_models.py`
3. `src/core/advisory/orchestration.py`
4. `src/core/advisory/artifact.py`
5. `src/core/replay/service.py`

Available today:

1. every evaluated proposal can carry a backend-owned `proposal_decision_summary`,
2. artifact and replay already preserve that summary,
3. decision posture already incorporates risk, suitability, approvals, material changes, and missing evidence.

Assessment:

1. alternatives should reuse this exact contract per feasible alternative,
2. alternatives must not introduce a second decision-summary shape,
3. ranking policy may compare canonical decision posture outputs, but must not fork RFC-0021 vocabulary.

### Shelf and Mandate Inputs

Evidence:

1. `src/integrations/lotus_core/stateful_context.py`
2. `src/core/models.py`
   `ShelfEntry`
3. `src/core/proposals/models.py`
4. `src/core/workspace/models.py`
5. `src/core/advisory/policy_context.py`
6. `src/core/common/suitability.py`

Available today:

1. proposal requests already carry shelf entries,
2. stateful context resolution can build shelf entries from Lotus Core query data,
3. lifecycle and workspace flows already carry `mandate_id` when available,
4. suitability already has restricted-product and mandate-context logic.

Assessment:

1. first alternatives implementation can rely on governed held positions plus current shelf evidence,
2. mandate and client-preference evidence remain partially available and should be treated as explicit evidence inputs rather than assumed truth,
3. `AVOID_RESTRICTED_PRODUCTS` can ship only if Slice 1 discovery confirms the restricted-product evidence path is stable enough for truthful alternatives behavior.

## What Does Not Exist Yet

Repository inspection found no implementation of alternatives-specific request or response contracts outside RFC docs.

Evidence:

1. no `proposal_alternatives` fields in `src/core/models.py`, `src/core/proposals/models.py`, `src/core/workspace/models.py`, or `src/core/advisory/artifact_models.py`
2. no `alternatives_request` request fields in proposal, lifecycle, or workspace contracts
3. no `selected_alternative_id` lifecycle or workspace field
4. no alternatives-specific strategy, ranking, or persistence module under `src/core/advisory/`
5. no alternatives-specific replay projection in `src/core/replay/service.py`
6. no alternatives capability key in `src/api/routers/integration_capabilities.py`
7. no alternatives vocabulary entries in `docs/standards/api-vocabulary/lotus-advise-api-vocabulary.v1.json`

Assessment:

1. Slice 2 must begin with additive contracts and internal models,
2. Slice 3 and later must wire those models into existing simulation, lifecycle, artifact, workspace, and replay surfaces,
3. there is currently no hidden partial alternatives implementation to reconcile or migrate.

## First-Implementation Scope Freeze

This scope is intentionally frozen before implementation begins.

### Objectives in Scope

1. `REDUCE_CONCENTRATION`
2. `RAISE_CASH`
3. `LOWER_TURNOVER`
4. `IMPROVE_CURRENCY_ALIGNMENT`

### Objective Conditionally in Scope

1. `AVOID_RESTRICTED_PRODUCTS`
   Ship only if current restricted-product and mandate-context evidence is proven sufficient during implementation.

### Objectives Explicitly Deferred

1. `IMPROVE_RISK_ALIGNMENT` beyond the currently implemented concentration-lens scope
2. `REBALANCE_TO_REFERENCE_MODEL`
3. `MINIMIZE_APPROVAL_REQUIREMENTS`
4. `PRESERVE_CLIENT_PREFERENCES`
5. `LOWER_COST_AND_FRICTION`

### Constraints in Scope

1. `cash_floor`
2. `max_turnover_pct`
3. `max_trade_count`
4. `preserve_holdings`
5. `restricted_instruments`
6. `do_not_buy`
7. `do_not_sell`
8. `allow_fx`
9. `allowed_currencies`

### Candidate-Universe Scope

First implementation candidate generation is limited to:

1. currently held positions,
2. canonical shelf-backed instruments already available in the resolved proposal context,
3. deterministic modifications of the current governed proposal intent set.

Not allowed in first implementation:

1. unrestricted market search,
2. advisory-local security discovery,
3. hidden AI-generated trade proposals.

### Persistence and Selection Scope

1. alternatives remain opt-in through `alternatives_request.enabled`,
2. first implementation default `max_alternatives` is `3`,
3. `include_rejected_candidates` defaults to `true`,
4. `selected_alternative_id` is absent on first-time generation requests,
5. `selected_alternative_id` is used only on lifecycle or workspace writes that confirm a backend-issued alternative selection.

## Minimum Additive Contract Baseline

### Request Surfaces That Need an Alternatives Input

The additive request block must align to existing proposal request shapes and reuse existing simulation ownership.

Primary request families:

1. `POST /advisory/proposals/simulate`
2. `POST /advisory/proposals/artifact`
3. `POST /advisory/proposals`
4. `POST /advisory/proposals/{proposal_id}/versions`
5. workspace evaluation or handoff request shapes that already embed or derive proposal simulation inputs

Assessment:

1. create and version flows should reuse the same alternatives request semantics through the nested simulation request rather than inventing lifecycle-only variants,
2. workspace flows should reuse the same semantics where they trigger a fresh evaluation,
3. selected-alternative persistence may require additive workspace or lifecycle metadata fields beyond the evaluation request itself.

### Response and Persistence Surfaces That Must Eventually Carry Alternatives

These surfaces are the authoritative target set for `proposal_alternatives` once implementation begins:

1. `ProposalResult` in `src/core/models.py`
2. `ProposalArtifact` in `src/core/advisory/artifact_models.py`
3. `ProposalVersionDetail` and proposal detail responses in `src/core/proposals/models.py`
4. replay evidence built in `src/core/replay/service.py`
5. workspace session and saved-version responses in `src/core/workspace/models.py`

Assessment:

1. alternatives should be introduced once in the core simulation contract and then reused downstream,
2. lifecycle, artifact, replay, and workspace surfaces should project persisted alternatives evidence rather than regenerating it independently,
3. if a dedicated alternatives read endpoint is required, it must remain a projection over persisted version evidence.

## Cross-RFC Reconciliation

### RFC-0020 Alignment

RFC-0022 must inherit these implemented truths from RFC-0020:

1. canonical proposal allocation remains sourced from `lotus-core`,
2. proposal allocation comparison remains within the curated RFC-0020 proposal dimensions,
3. canonical proposal risk comparison remains limited to the implemented concentration lens,
4. replay-safe proposal risk evidence is already persisted and must remain the authoritative source.

### RFC-0021 Alignment

RFC-0022 must inherit these implemented truths from RFC-0021:

1. `proposal_decision_summary` is already the canonical advisor-facing decision contract,
2. decision posture must remain replay-safe and persistence-first,
3. alternatives may compare decision posture outputs but must not fork the schema or vocabulary,
4. UI consumers must continue to receive backend-owned decision evidence rather than recomputing advisory posture locally.

## Open Implementation Questions Remaining After Slice 1

These remain valid implementation questions, but they are now narrowed:

1. What exact canonical eligible-instrument source should govern shelf expansion beyond directly held positions?
2. Is the current restricted-product and mandate-context posture sufficient to truthfully ship `AVOID_RESTRICTED_PRODUCTS` in Slice 4?
3. Which exact workspace or lifecycle write surface should persist `selected_alternative_id` first?
4. What final latency budget should apply to alternatives mode on canonical seeded portfolios once the enrichment path is implemented?

## Slice 1 Exit Decision

Slice 1 is complete.

Evidence-backed conclusion:

1. the repository already has the authoritative simulation, allocation, risk, decision-summary, artifact, lifecycle, workspace, and replay seams needed for alternatives,
2. no hidden alternatives implementation exists today,
3. the first implementation scope is now intentionally frozen,
4. RFC-0022 can move to Slice 2 without contract ambiguity about domain authority or current risk scope.
