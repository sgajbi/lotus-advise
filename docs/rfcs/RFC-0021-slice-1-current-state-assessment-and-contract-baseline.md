# RFC-0021 Slice 1: Current-State Assessment and Contract Baseline

- RFC: `RFC-0021`
- Slice: `Slice 1`
- Status: COMPLETED
- Created: 2026-04-12
- Owners: lotus-advise

## Purpose

This document is the Slice 1 evidence artifact for RFC-0021.

Its role is to make the current proposal contract explicit before implementation begins on the new `proposal_decision_summary` contract.

Slice 1 is complete only if:

1. current behavior is evidence-backed,
2. current gaps are explicit,
3. the minimum additive contract is defined,
4. UI and artifact inference to remove in later slices is identified,
5. no unnecessary implementation work leaks in from Slice 2 or later.

## Executive Summary

`lotus-advise` already has the raw ingredients needed for a strong decision-summary capability:

1. canonical proposal simulation through `lotus-core`,
2. canonical risk enrichment through `lotus-risk`,
3. top-level proposal status,
4. deterministic workflow gate output,
5. deterministic suitability output,
6. persisted proposal versions and replay evidence,
7. workspace evaluation, save, and handoff flows,
8. artifact generation and lifecycle delivery evidence.

The current gap is not lack of raw evidence. The gap is lack of one backend-owned decision object that:

1. explains the advisory posture,
2. consolidates approvals and material changes,
3. distinguishes insufficient evidence from actual suitability failure,
4. stays identical across simulate, lifecycle, workspace, artifact, and replay surfaces.

Current implementation already exposes enough evidence to build that layer without adding duplicate portfolio or risk calculation logic.

## Current Behavior Inventory

### Current Top-Level Proposal Outcome

Current top-level proposal status is:

1. `READY`
2. `PENDING_REVIEW`
3. `BLOCKED`

Evidence:

1. `src/core/common/simulation_shared.py`
   `derive_status_from_rules`
2. `src/core/models.py`
   `ProposalResult.status`
3. `tests/unit/advisory/engine/test_engine_advisory_proposal_simulation.py`
4. `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`

Current behavior:

1. hard rule failure drives `BLOCKED`,
2. soft rule failure drives `PENDING_REVIEW`,
3. otherwise status is `READY`.

Assessment:

1. this is a necessary coarse workflow signal,
2. it is not rich enough to explain the advisor-facing decision posture.

### Current Workflow Gate Output

Current workflow gate output is a separate structure from top-level status.

Evidence:

1. `src/core/common/workflow_gates.py`
2. `src/core/models.py`
   `GateDecision`, `GateDecisionSummary`, `GateReason`
3. `src/core/proposals/service.py`
   persistence of `gate_decision_json`
4. `src/core/advisory/artifact.py`
   artifact fallback logic and next-step inference
5. `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`
6. `tests/unit/advisory/engine/test_engine_workflow_gates.py`

Current gate values:

1. `BLOCKED`
2. `RISK_REVIEW_REQUIRED`
3. `COMPLIANCE_REVIEW_REQUIRED`
4. `CLIENT_CONSENT_REQUIRED`
5. `EXECUTION_READY`
6. `NONE`

Current next-step values:

1. `FIX_INPUT`
2. `RISK_REVIEW`
3. `COMPLIANCE_REVIEW`
4. `REQUEST_CLIENT_CONSENT`
5. `EXECUTE`
6. `NONE`

Current gate precedence:

1. blocked status or hard rule failure,
2. new high-severity suitability issue,
3. soft rule failure or new medium-severity suitability issue,
4. client consent already obtained,
5. client consent required by policy,
6. execution ready.

Assessment:

1. current gate output is deterministic and useful,
2. it is workflow-oriented rather than advisor-decision-oriented,
3. it does not consolidate missing evidence, material changes, or approval requirements into one stable contract.

### Current Suitability Output

Current suitability output is concentrated on advisory scanner logic already implemented in `RFC-0010`.

Evidence:

1. `src/core/common/suitability.py`
2. `src/core/models.py`
   `SuitabilityResult`, `SuitabilityIssue`, `SuitabilitySummary`
3. `tests/unit/advisory/engine/test_engine_suitability_scanner.py`
4. `tests/unit/advisory/golden/test_golden_advisory_proposal_scenarios.py`

Current suitability dimensions:

1. concentration,
2. issuer exposure,
3. liquidity tier exposure,
4. governance shelf posture,
5. cash band,
6. data quality.

Current issue status classes:

1. `NEW`
2. `RESOLVED`
3. `PERSISTENT`

Current suitability recommendation:

1. `NONE`
2. `RISK_REVIEW`
3. `COMPLIANCE_REVIEW`

Assessment:

1. current suitability logic is real and reusable,
2. it is not yet an enterprise suitability policy,
3. client profile, mandate, objective, time horizon, product complexity, jurisdiction, and preference context are not first-class inputs yet.

### Current Risk Output

Current risk evidence is already integrated from `lotus-risk`.

Evidence:

1. `src/core/advisory/risk_lens.py`
2. `src/core/advisory/orchestration.py`
3. `src/core/advisory/artifact.py`
4. `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`
5. live validation and cross-service parity coverage described in `docs/architecture/CODEBASE-REVIEW-LEDGER.md`

Current posture:

1. risk evidence is available as a risk-lens explanation/evidence field,
2. risk evidence already has canonical upstream lineage,
3. degraded risk behavior is explicit when enrichment is unavailable.

Assessment:

1. this is the correct authority model,
2. RFC-0021 must classify risk evidence into decision posture but must not calculate risk locally.

### Current Persistence, Replay, and Workspace Behavior

Current lifecycle and replay posture is already strong.

Evidence:

1. `src/core/proposals/service.py`
2. `src/core/replay/service.py`
3. `src/api/services/workspace_service.py`
4. `src/core/proposals/models.py`
5. `tests/unit/advisory/api/test_workspace_service.py`
6. `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`
7. `docs/architecture/CODEBASE-REVIEW-LEDGER.md`

Current persisted decision-adjacent evidence includes:

1. `proposal_result_json`,
2. `gate_decision_json`,
3. `evidence_bundle_json`,
4. replay continuity,
5. workspace replay evidence,
6. artifact evidence bundle,
7. risk-lens replay evidence.

Assessment:

1. persistence infrastructure is ready for `proposal_decision_summary`,
2. the main missing piece is the normalized decision-summary projector and its persisted contract.

## Current Contract Surfaces

### Direct Simulation

Surface:

1. `POST /advisory/proposals/simulate`

Current relevant fields:

1. `status`,
2. `suitability`,
3. `gate_decision`,
4. `allocation_lens`,
5. `diagnostics`,
6. `explanation`,
7. `lineage`.

Assessment:

1. raw evidence exists,
2. no backend-owned `proposal_decision_summary` exists.

### Artifact Generation

Surface:

1. `POST /advisory/proposals/artifact`

Current relevant fields:

1. artifact-level `status`,
2. artifact-level `gate_decision`,
3. artifact summary `recommended_next_step`,
4. suitability summary and highlights,
5. risk-lens summary,
6. evidence bundle.

Assessment:

1. artifact currently infers some advisor-facing meaning through `_resolve_next_step`,
2. this logic should move behind the future backend decision-summary contract rather than staying artifact-specific.

### Proposal Lifecycle Detail and Version Detail

Surfaces:

1. proposal detail,
2. current version detail,
3. replay evidence,
4. delivery summary,
5. async replay.

Current relevant fields:

1. `proposal_result`,
2. `gate_decision`,
3. `evidence_bundle`,
4. replay continuity,
5. risk-lens evidence.

Assessment:

1. these are the preferred first consumers for persisted decision summary,
2. a dedicated `decision-summary` endpoint is not required for Slice 1.

### Workspace

Surfaces:

1. evaluate workspace,
2. save workspace version,
3. resume,
4. compare,
5. handoff to lifecycle,
6. replay saved version.

Current relevant fields:

1. evaluation `status`,
2. evaluation `gate_decision`,
3. impact summary,
4. review and blocking issue counts,
5. replay evidence continuity,
6. latest proposal result.

Assessment:

1. workspace already surfaces a compact advisor-facing summary,
2. it still depends on distributed fields rather than one decision-summary contract.

## Current Gaps Relative To RFC-0021

### Gap 1: No Single Backend-Owned Decision Object

Current state:

1. status lives in `ProposalResult.status`,
2. workflow advice lives in `gate_decision`,
3. suitability detail lives in `suitability`,
4. artifact-specific next step is inferred in artifact code,
5. workspace cards summarize counts rather than advisory posture.

Required future state:

1. a single `proposal_decision_summary` contract owned by backend code.

### Gap 2: Missing Evidence Is Not First-Class Enough

Current state:

1. data-quality issues and degraded authority posture exist,
2. but there is no consolidated `missing_evidence` collection for the advisor.

Required future state:

1. explicit missing-evidence contract independent from pass/fail semantics.

### Gap 3: Material Changes Are Not Normalized

Current state:

1. before/after states and allocation deltas exist,
2. drift analytics exist,
3. risk-lens before/after exists,
4. but no normalized material-change classification exists.

Required future state:

1. stable `material_changes` contract that is business-readable and reusable across UI, replay, and narrative.

### Gap 4: Approval Requirements Are Not Consolidated

Current state:

1. gate output implies review steps,
2. lifecycle states and approvals exist,
3. but there is no explicit `approval_requirements` object at proposal-evaluation time.

Required future state:

1. deterministic approval requirement classification inside `proposal_decision_summary`.

### Gap 5: Client and Mandate Context Are Not Yet First-Class Decision Inputs

Current state:

1. mandate id and jurisdiction can appear in metadata and stateful context,
2. but suitability policy does not yet consume true client and mandate context as a first-class policy input set.

Required future state:

1. explicit client and mandate posture integrated without duplicating upstream ownership.

## Minimum Additive Contract For Slice 2

The first implementation must treat these fields as required:

1. `decision_status`,
2. `top_level_status`,
3. `primary_reason_code`,
4. `primary_summary`,
5. `recommended_next_action`,
6. `decision_policy_version`,
7. `confidence`,
8. `approval_requirements`,
9. `material_changes`,
10. `missing_evidence`,
11. `advisor_action_items`,
12. `evidence_refs`.

The first implementation may keep these nested structures shallow, but should reserve them in the contract:

1. `suitability_posture`,
2. `risk_posture`,
3. `client_and_mandate_posture`.

## Mapping From Current Gate Semantics To Target Decision Status Semantics

This is the Slice 1 baseline recommendation.

| Current condition | Current fields | Target `decision_status` |
| --- | --- | --- |
| Hard rule failure or blocked data quality | `status=BLOCKED`, `gate_decision.gate=BLOCKED` | `BLOCKED_REMEDIATION_REQUIRED` |
| New high-severity suitability issue | `gate_decision.gate=COMPLIANCE_REVIEW_REQUIRED` | `REQUIRES_COMPLIANCE_REVIEW` |
| Soft failure or medium-severity suitability issue | `gate_decision.gate=RISK_REVIEW_REQUIRED` | `REQUIRES_RISK_REVIEW` |
| Client consent required | `gate_decision.gate=CLIENT_CONSENT_REQUIRED` | `REQUIRES_CLIENT_CONSENT` |
| Ready and workflow-clear | `gate_decision.gate=EXECUTION_READY` with advisory review context | `READY_FOR_CLIENT_REVIEW` |
| Required context missing but proposal not hard blocked | degraded authority posture, missing client/mandate/product context | `INSUFFICIENT_EVIDENCE` |
| Proposal should be changed before progressing | no stable current field; inferred from distributed evidence | `REVISION_RECOMMENDED` |

## UI And Artifact Inference To Delete In Later Slices

Once `proposal_decision_summary` exists, these local inferences should be removed or reduced:

1. artifact `_resolve_next_step` in `src/core/advisory/artifact.py`,
2. artifact takeaway text that reconstructs decision posture from raw fields,
3. workspace review/blocking count reliance as a proxy for advisory decision posture,
4. any future UI badge logic that derives decision state from `status` and `gate_decision` separately,
5. any future narrative/reporting logic that rebuilds approval posture from gate reasons instead of consuming one backend summary.

## Naming And Vocabulary Baseline

The proposed field vocabulary is aligned with current repo and platform standards:

1. `proposal_decision_summary`, not `status_details`,
2. `approval_requirements`, not `tasks`,
3. `material_changes`, not `diffs`,
4. `missing_evidence`, not generic `warnings`,
5. `advisor_action_items`, not `todos`,
6. `decision_status`, not another top-level status family.

## Recommended Initial Implementation Defaults

Unless Slice 2 code evidence forces a different choice:

1. use current proposal detail and version detail surfaces as the first persisted consumers,
2. defer a dedicated `GET /advisory/proposals/{proposal_id}/decision-summary` endpoint until a real consumer proves it is needed,
3. start with a global private-banking baseline policy pack,
4. defer jurisdiction overlays until policy truth is actually available,
5. project the new decision summary first in shadow mode beside current `gate_decision`.

## Repository Review Notes From Slice 1

### Current Code Quality Observations

1. current logic is reasonably modular across simulation, suitability, workflow gates, artifact, lifecycle, and replay,
2. the largest risk is distributed advisor-facing interpretation rather than one giant monolith,
3. `src/core/advisory/artifact.py` already contains decision-adjacent inference that should eventually shrink once RFC-0021 is implemented,
4. current persistence and replay design is strong enough to support the next slice without structural rework.

### Slice 1 Improvement Applied

Slice 1 added targeted baseline workflow-gate tests so current gate semantics are explicitly pinned before introducing `proposal_decision_summary`.

Evidence:

1. `tests/unit/advisory/engine/test_engine_workflow_gates.py`

## Exit Criteria Review

Slice 1 acceptance criteria from RFC-0021 are satisfied:

1. assessment document exists,
2. current behavior is backed by code and test evidence,
3. proposed field names are reconciled with current vocabulary and RFC conventions,
4. baseline gaps are explicit,
5. no Slice 2 implementation leaked into production code.

## Recommended Next Slice

Proceed to `Slice 2: Decision Summary Models and Pure Projector`.

Guardrails for Slice 2:

1. do not recalculate upstream portfolio or risk truth,
2. keep current top-level status vocabulary stable,
3. ship the minimum required contract first,
4. prove alignment between current gate output and new decision summary before expanding scope.
