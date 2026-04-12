# RFC-0021 Slice 2: Decision Summary Models and Pure Projector Evidence

- RFC: `RFC-0021`
- Slice: `Slice 2`
- Status: IMPLEMENTED
- Created: 2026-04-12
- Owners: lotus-advise

## Scope

Slice 2 implemented the minimum additive `proposal_decision_summary` contract on:

1. direct simulation responses,
2. proposal artifact responses.

It did not implement:

1. persisted lifecycle storage of `proposal_decision_summary`,
2. replay projection of persisted decision summaries,
3. workspace persistence of decision summaries,
4. enterprise client or mandate integration,
5. full material-change classification.

Those remain in later slices by design.

## What Was Added

### New Model Layer

Added:

1. `src/core/advisory/decision_summary_models.py`

This defines:

1. `ProposalDecisionSummary`,
2. approval requirement models,
3. missing-evidence models,
4. advisor action item models,
5. suitability, risk, and client/mandate posture summaries.

### New Pure Projector

Added:

1. `src/core/advisory/decision_summary.py`

This projector derives a first-pass decision summary from existing evidence:

1. top-level proposal status,
2. workflow gate decision,
3. suitability output,
4. diagnostics/data-quality evidence,
5. authority-resolution posture,
6. risk-lens availability.

### Response Surface Integration

Updated:

1. `src/core/models.py`
   `ProposalResult` now includes optional `proposal_decision_summary`
2. `src/core/advisory/orchestration.py`
   decision summary is projected after authority-resolution enrichment
3. `src/core/advisory/artifact_models.py`
   `ProposalArtifact` now includes optional `proposal_decision_summary`
4. `src/core/advisory/artifact.py`
   artifact response now exposes the decision summary

### Slice Boundary Protection

Updated:

1. `src/core/proposals/service.py`

Current lifecycle persistence intentionally excludes `proposal_decision_summary` from stored `proposal_result_json` so Slice 2 does not silently implement Slice 3.

## Current Decision Summary Behavior

### Implemented Decision Status Projection

Current projector supports:

1. `READY_FOR_CLIENT_REVIEW`,
2. `REQUIRES_RISK_REVIEW`,
3. `REQUIRES_COMPLIANCE_REVIEW`,
4. `REQUIRES_CLIENT_CONSENT`,
5. `BLOCKED_REMEDIATION_REQUIRED`,
6. `INSUFFICIENT_EVIDENCE`,
7. `REVISION_RECOMMENDED`.

### Implemented First-Pass Fields

Current projector fills:

1. `decision_status`,
2. `top_level_status`,
3. `primary_reason_code`,
4. `primary_summary`,
5. `recommended_next_action`,
6. `decision_policy_version`,
7. `suitability_policy_version` when suitability exists,
8. `confidence`,
9. `approval_requirements`,
10. `material_changes` as an empty list in this slice,
11. `suitability_posture`,
12. `missing_evidence`,
13. `risk_posture`,
14. `client_and_mandate_posture`,
15. `advisor_action_items`,
16. `evidence_refs`.

### Deliberate Limits In This Slice

Current projector deliberately does not yet:

1. calculate real material changes,
2. consume client profile or mandate policy,
3. persist summary into proposal versions,
4. expose summary through replay surfaces,
5. replace existing workflow-gate logic.

## Tests Added Or Updated

Added:

1. `tests/unit/advisory/engine/test_engine_proposal_decision_summary.py`
2. `tests/unit/advisory/engine/test_engine_workflow_gates.py`

Updated:

1. `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py`
2. `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

Validated behaviors:

1. ready decision-summary projection,
2. compliance-review projection,
3. blocked-remediation projection,
4. insufficient-evidence projection,
5. revision-recommended projection,
6. direct simulation response includes `proposal_decision_summary`,
7. degraded risk posture is reflected as missing evidence,
8. artifact response includes `proposal_decision_summary`,
9. lifecycle create does not persist `proposal_decision_summary` yet.

## Review Notes

### What Improved

1. advisor-facing decision semantics now live in one backend-owned projector instead of being scattered across raw fields,
2. simulation and artifact surfaces now share the same decision-summary source,
3. slice boundaries are explicit and protected by tests,
4. no duplicate portfolio or risk calculation logic was introduced.

### What Still Needs Improvement In Later Slices

1. client and mandate context must become real policy inputs,
2. missing-evidence classification needs richer domain coverage,
3. approval requirements need deeper policy backing,
4. material changes need a real classifier,
5. persisted and replayed surfaces must gain the same summary once Slice 3 begins,
6. artifact-specific next-step inference should shrink over time as consumers trust the decision summary more directly.

## Exit Criteria Review

Slice 2 acceptance criteria are satisfied:

1. `ProposalDecisionSummary` and nested models exist,
2. a pure projector over existing evidence exists,
3. simulation and artifact paths expose additive decision-summary fields,
4. top-level status vocabulary remains stable,
5. focused unit and API tests cover ready, review, blocked, insufficient-evidence, and revision-recommended outcomes.

## Recommended Next Slice

Proceed to `Slice 3: Persistence, Replay, Workspace, and Async Evidence`.

Guardrails for Slice 3:

1. persist exactly the projected decision summary, not a recomputed copy,
2. keep replay stable from persisted evidence,
3. preserve current slice-boundary tests while extending lifecycle and workspace surfaces.
