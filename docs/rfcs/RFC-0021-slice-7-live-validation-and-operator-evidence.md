# RFC-0021 Slice 7 Evidence: Live Validation and Operator Evidence

- RFC: `docs/rfcs/RFC-0021-proposal-decision-summary-and-enterprise-suitability-policy.md`
- Slice: `Slice 7`
- Commit Target: `feat(advisory): validate live decision summary evidence`
- Status: `implemented`

## Scope

Slice 7 closes the live-validation gap that remained after the decision-summary policy, persistence,
and classifier slices were completed.

This slice:

1. extends the live runtime suite to validate decision-summary posture directly,
2. proves ready, review, blocked, and insufficient-evidence paths on operator-facing runtime flows,
3. strengthens persisted proposal read-surface validation so decision summary presence is checked
   on lifecycle endpoints, and
4. upgrades the machine-readable evidence bundle and PR summary outputs so operator handoff records
   carry decision status, primary reason, next action, and approval requirement posture.

## Code Changes

### 1. Reusable live decision snapshot helper

Added `scripts/live_runtime_decision_summary.py`.

The helper introduces one normalized runtime-evidence shape:

1. `path_name`
2. `top_level_status`
3. `decision_status`
4. `primary_reason_code`
5. `recommended_next_action`
6. `approval_requirement_types`

This keeps parity validation, degraded-runtime validation, and operator evidence rendering aligned
 on one representation instead of duplicating ad hoc field extraction.

### 2. Live parity suite now validates decision-summary paths

Updated `scripts/validate_cross_service_parity_live.py`.

The suite now validates three explicit decision-summary paths:

1. `ready_path`
   canonical stateful no-op proposal still returns a backend-owned decision summary with ready
   posture and stable next-step fields.
2. `review_path`
   deterministic stateless review scenario returns risk or compliance review posture with explicit
   approval requirements.
3. `blocked_path`
   missing-FX stateless scenario returns blocked remediation posture and explicit
   `DATA_REMEDIATION` approval requirements.

The parity result payload now persists these snapshots for downstream evidence rendering.

### 3. Degraded-runtime suite now proves insufficient evidence

Updated `scripts/validate_degraded_runtime_live.py`.

The `lotus-risk` unavailable drill now validates:

1. the simulation still degrades cleanly without inventing a false positive risk posture,
2. the decision summary returns `INSUFFICIENT_EVIDENCE`,
3. the primary reason is `MISSING_RISK_LENS`, and
4. the degraded-runtime result carries the same insufficient-evidence snapshot used by evidence
   writers.

### 4. Persisted proposal read surfaces now assert decision-summary continuity

Updated `_assert_persisted_read_surfaces(...)` in
`scripts/validate_cross_service_parity_live.py`.

The live suite now checks that:

1. proposal detail and version endpoints expose the same persisted decision summary,
2. `decision_status` and `primary_reason_code` remain present on persisted reads, and
3. `approval_requirements` remains a stable list contract on operator-facing read surfaces.

This closes the gap where lifecycle endpoints were validated heavily for state lineage but not for
the backend-owned advisory decision evidence they are supposed to deliver.

### 5. Operator evidence bundle now includes decision posture

Updated:

1. `scripts/validate_live_runtime_suite.py`
2. `scripts/live_runtime_suite_artifacts.py`
3. `scripts/run_live_runtime_evidence_bundle.py`

The evidence bundle markdown and PR-ready summary now include:

1. ready-path decision posture,
2. review-path decision posture,
3. blocked-path decision posture, and
4. degraded insufficient-evidence posture.

That makes the live bundle materially more useful in PR review, release sign-off, and future
regression triage.

## Test Coverage

Updated `tests/unit/advisory/api/test_live_runtime_suite.py`.

The test suite now proves:

1. machine-readable runtime artifacts serialize decision-path evidence deterministically,
2. markdown summaries include decision-path sections,
3. PR summaries include ready, review, blocked, and insufficient-evidence posture, and
4. skip-degraded behavior still returns an explicit placeholder snapshot rather than omitting the
   shape.

Updated `tests/e2e/live/test_live_runtime_suite.py`.

The live E2E contract now asserts:

1. parity runtime includes explicit review posture,
2. degraded runtime includes explicit insufficient-evidence posture.

Regression protection remains in:

1. `tests/unit/advisory/engine/test_engine_proposal_decision_summary.py`
2. `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

Those tests already cover the underlying policy behavior and continue to protect the runtime suite
from drifting away from backend truth.

## Validation

Local targeted validation completed:

1. `python -m pytest tests/unit/advisory/api/test_live_runtime_suite.py -q`
2. `python -m pytest tests/unit/advisory/engine/test_engine_proposal_decision_summary.py tests/unit/advisory/engine/test_engine_proposal_workflow_service.py -q`

Planned final gate for this slice:

1. `make check`

## Review Pass

This slice received an explicit review pass before moving forward.

Review conclusions:

1. the new decision-path extraction was pushed into a reusable helper instead of being duplicated in
   both live validators,
2. persisted operator surfaces are now checked for decision-summary continuity, not just workflow
   state continuity,
3. evidence output is stronger without changing decision-policy authority or moving logic into the
   wrong layer, and
4. no new local calculators or duplicated business rules were introduced.

## Next Slice

Slice 8 should complete:

1. RFC status and index updates,
2. repository and agent-context assessment,
3. API and workflow documentation tightening where runtime truth changed,
4. full PR loop, merge preparation, and branch hygiene.
