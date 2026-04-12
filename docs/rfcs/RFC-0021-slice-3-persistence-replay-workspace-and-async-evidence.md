# RFC-0021 Slice 3 Evidence: Persistence, Replay, Workspace, and Async Evidence

- RFC: `docs/rfcs/RFC-0021-proposal-decision-summary-and-enterprise-suitability-policy.md`
- Slice Status: IMPLEMENTED
- Date: 2026-04-12
- Owner: `lotus-advise`

## Scope Delivered

Slice 3 closed the persistence and continuity gap left intentionally open in Slice 2.

Implemented outcomes:

1. persisted `proposal_decision_summary` inside immutable proposal version records,
2. returned the persisted summary through create, version, detail, and async-success surfaces via existing version payloads,
3. exposed the persisted summary explicitly in proposal replay evidence and async replay evidence,
4. preserved the decision summary through workspace evaluation, save, resume, and handoff continuity,
5. kept the optional standalone decision-summary endpoint deferred because existing persisted surfaces remain sufficient for the current consumers.

## Code Changes

### Version Persistence

`src/core/proposals/service.py`

1. removed the temporary Slice 2 exclusion that stripped `proposal_decision_summary` from `proposal_result_json`,
2. kept version persistence append-only and deterministic,
3. preserved the existing hashing contract over the persisted proposal-result payload after correlation/idempotency stripping.

Result:

1. proposal create now persists the summary with version 1,
2. proposal version creation persists a freshly computed summary for the new version,
3. stale decision posture no longer risks being inferred from older version payloads.

### Replay Surfaces

`src/core/replay/service.py`

1. proposal version replay evidence now includes `evidence.proposal_decision_summary`,
2. async replay inherits the same persisted summary from the linked proposal version replay response,
3. workspace saved-version replay evidence includes the saved decision summary when workspace evaluation existed at save time.

Result:

1. replay consumers no longer need to search inside raw payloads to find the canonical decision object,
2. replay and async evidence now expose the same backend-owned summary used by lifecycle consumers,
3. workspace-to-lifecycle continuity can be checked directly at the decision-summary layer.

## Tests Added Or Tightened

### Proposal Workflow Service

`tests/unit/advisory/engine/test_engine_proposal_workflow_service.py`

1. create persists a non-null `proposal_decision_summary`,
2. new proposal version recomputes the summary and does not bleed the previous version posture forward.

### Proposal Replay And Async Replay

`tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py`

1. proposal version replay includes `proposal_decision_summary`,
2. async replay includes the same persisted decision summary,
3. proposal replay and async replay remain aligned on the same decision-summary payload,
4. risk-enriched replay preserves both risk lens and decision-summary risk posture.

### Workspace Continuity

`tests/unit/advisory/api/test_api_workspace.py`

1. saved workspace replay evidence includes `proposal_decision_summary`,
2. workspace replay and proposal replay remain aligned on the same decision-summary payload after handoff,
3. risk-enriched workspace replay preserves both risk lens and decision-summary risk posture.

`tests/unit/advisory/api/test_workspace_service.py`

1. saved workspace versions retain a non-null decision summary after save and reload,
2. workspace handoff continuity preserves the saved version carrying the same decision evidence.

## Validation

Targeted slice validation:

```powershell
python -m pytest tests\unit\advisory\engine\test_engine_proposal_workflow_service.py tests\unit\advisory\api\test_api_advisory_proposal_lifecycle.py tests\unit\advisory\api\test_api_workspace.py tests\unit\advisory\api\test_workspace_service.py -q
```

Result:

1. `154 passed`

Full repository gate was rerun after the slice changes and passed before commit in the implementation loop.

## Review Pass

The post-implementation review focused on whether Slice 3 needed a new endpoint.

Decision:

1. do not introduce `GET /advisory/proposals/{proposal_id}/decision-summary` yet,
2. existing persisted proposal detail, version detail, async status, replay evidence, and workspace replay surfaces already expose the canonical summary cleanly,
3. adding a dedicated endpoint now would increase API surface without a consumer-driven need.

## Remaining Work For Next Slice

Slice 4 can now build the enterprise suitability policy engine on top of a stable persisted decision-summary contract.

Next implementation focus:

1. policy pack registry,
2. richer suitability issue model,
3. deterministic policy-versioned advisory classifications,
4. stronger missing-evidence posture beyond current gate-derived projection.
