# RFC-0025 Slice 9 - Policy Approval, Consent, Disclosure, Conflict, And Sign-Off Workflow

Status: IMPLEMENTED - ADVISE SOURCE WORKFLOW ONLY; REPORT REALIZATION, GATEWAY, WORKBENCH, AND CLIENT-READY PUBLICATION REMAIN GATED

## Scope Boundary

This slice connects finalized policy evaluation outcomes to an Advise-owned workflow projection and
sign-off decision boundary.

Implemented scope:

1. approval dependency projection from policy rule outcomes,
2. disclosure and consent requirement projection that remains visible for memo and later report
   preparation,
3. conflict posture and blocker projection from material policy rule outcomes,
4. SLA aging for open policy review requirements,
5. maker-checker enforcement for policy sign-off,
6. sign-off decision recording against the immutable evaluation hash,
7. explicit blockers preventing unresolved source gaps, disclosures, consents, conflicts, or stale
   hashes from being converted into positive best-interest or client-ready wording.

This slice does not implement report/render/archive realization, Gateway routes, Workbench policy
screens, AI policy-evidence packets, active data-product promotion, or client-ready publication.

## Implementation

The workflow boundary lives in `src/core/policy_packs/workflow.py`.

Canonical routes added to `src/api/proposals/routes_policy_evaluations.py`:

1. `GET /advisory/policy-evaluations/{evaluation_id}/workflow`
2. `POST /advisory/policy-evaluations/{evaluation_id}/sign-off-decisions`

The workflow projection returns:

1. approval dependencies with owner role, SLA, due time, and open/satisfied posture,
2. disclosure requirements with open/satisfied posture,
3. consent requirements with open/satisfied posture,
4. conflict posture and conflict blockers,
5. SLA posture and overdue requirement identifiers,
6. sign-off readiness and blockers,
7. latest sign-off event where one exists,
8. client-ready publication boundary as `BLOCKED`.

The sign-off decision command:

1. requires the caller to supply the reviewed `source_evaluation_hash`,
2. rejects stale hash decisions,
3. rejects approval by the evaluation creator,
4. rejects approval while approval, disclosure, consent, conflict, or blocked-evaluation
   requirements remain open,
5. records approved sign-off as an append-only `POLICY_EVALUATION_SIGN_OFF_RECORDED` event,
6. records non-approval decisions as append-only review events,
7. preserves report/render/archive realization as `NOT_IMPLEMENTED`.

## Data Product Posture

`AdvisoryPolicyEvaluationRecord:v1` remains proposed and blocked for mesh publication after this
slice.

The product now has source workflow and sign-off decision APIs in Advise. It remains blocked because
the policy product is not yet consumable through Gateway/Workbench, report/render/archive sign-off
package realization is not implemented, live canonical proof is not complete, and
`/platform/capabilities` must not advertise policy evaluation support until the product surface is
implementation-backed.

## Acceptance Evidence

Tests:

1. `tests/unit/advisory/engine/test_engine_policy_pack_workflow.py`
2. `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py`
3. `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py`
4. `tests/unit/test_rfc0025_slice9_policy_workflow_contract.py`
5. `tests/unit/test_trust_telemetry.py`

Covered paths:

1. workflow projection exposes approval, disclosure, consent, conflict, SLA, and sign-off posture,
2. maker-checker sign-off is enforced,
3. open requirements block policy sign-off,
4. material conflict blocks sign-off until explicit conflict review outcome is recorded,
5. successful sign-off records an append-only sign-off event,
6. sign-off response keeps client-ready publication blocked and report realization unimplemented,
7. OpenAPI docs cover the new workflow and sign-off decision contracts,
8. data-product and trust telemetry posture remains proposed/blocked rather than promoted.

## Wiki And README Decision

Repo RFC index, repo context, codebase review ledger, data-product declaration, trust telemetry, API
vocabulary, and wiki source are updated because implementation truth changed. Wiki publication is
required after merge.
