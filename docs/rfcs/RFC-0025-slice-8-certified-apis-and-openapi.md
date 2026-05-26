# RFC-0025 Slice 8 - Certified Policy Evaluation APIs And OpenAPI

Status: IMPLEMENTED - CERTIFIED ADVISE API SURFACE ONLY; GATEWAY, WORKBENCH, REPORT REALIZATION, AND CLIENT-READY PUBLICATION REMAIN GATED

## Scope Boundary

This slice exposes the RFC-0025 policy evaluation record through canonical `lotus-advise` APIs.
It builds directly on Slice 7 persistence and does not create a second policy workflow engine.

Implemented API scope:

1. create or replay a finalized policy evaluation record for a proposal version,
2. read a finalized evaluation record,
3. replay and compare pinned policy/source/evaluation hashes,
4. read a policy review queue projection,
5. record append-only review, sign-off, and report/archive reference events,
6. read policy lineage with finalization and later audit events,
7. read the Advise source sign-off package for policy review.

This slice does not implement Gateway routes, Workbench policy panels, report/render/archive package
realization, AI policy-evidence packets, active data-product promotion, or client-ready publication.
Those remain later RFC-0025 slices.

## Implementation

The API boundary lives in `src/api/proposals/routes_policy_evaluations.py`.

Canonical routes:

1. `POST /advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations`
2. `GET /advisory/policy-evaluations/review-queue`
3. `GET /advisory/policy-evaluations/{evaluation_id}`
4. `POST /advisory/policy-evaluations/{evaluation_id}/replay`
5. `POST /advisory/policy-evaluations/{evaluation_id}/events`
6. `GET /advisory/policy-evaluations/{evaluation_id}/lineage`
7. `GET /advisory/policy-evaluations/{evaluation_id}/sign-off-package`

Core support added in `src/core/policy_packs/persistence.py`:

1. list finalized records by aggregate policy posture,
2. list audit events for a record,
3. project lineage from immutable hashes and append-only events,
4. project a review queue response without inventing workflow state,
5. project an Advise source sign-off package without claiming report realization.

OpenAPI support added:

1. dedicated `Advisory Policy Evaluation` tag,
2. request and response models with field descriptions and examples,
3. documented idempotency headers,
4. explicit 404, 409, and 422 response descriptions where applicable,
5. route summaries and descriptions that preserve the unsupported Gateway, Workbench, report, and
   client-ready boundaries.

## Data Product Posture

`AdvisoryPolicyEvaluationRecord:v1` remains proposed and blocked for mesh publication after this
slice.

The data product now has Advise-local current routes because the source API exists. It remains
blocked because the product is not yet consumable through Gateway/Workbench, report/render/archive
sign-off package realization is not implemented, live canonical proof is not complete, and
`/platform/capabilities` must not advertise policy evaluation support until the product surface is
implementation-backed.

## Acceptance Evidence

Tests:

1. `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py`
2. `tests/unit/advisory/api/test_api_advisory_policy_packs.py`
3. `tests/unit/advisory/engine/test_engine_policy_pack_persistence.py`
4. `tests/unit/advisory/engine/test_engine_policy_pack_evaluation.py`
5. `tests/unit/test_rfc0025_slice8_policy_evaluation_api_contract.py`
6. `tests/unit/test_trust_telemetry.py`

Covered paths:

1. policy evaluation create is idempotent and hash-backed,
2. idempotency drift is rejected with conflict semantics,
3. record read returns material hashes and supportability boundaries,
4. replay compares matching and changed source evidence,
5. review events are append-only and lineage-visible,
6. review queue filters `PENDING_REVIEW` records,
7. sign-off package returns the Advise source package while keeping report realization blocked,
8. OpenAPI exposes the certified routes with the dedicated tag and idempotency header docs,
9. data-product and trust telemetry posture remains proposed/blocked rather than promoted.

## Wiki And README Decision

Repo RFC index, repo context, codebase review ledger, data-product declaration, trust telemetry, and
wiki source are updated because implementation truth changed. Wiki publication is required after
merge.
