# RFC-0025 Slice 10 - Policy Report, Render, And Archive Realization

Status: IMPLEMENTED - ADVISE REPORT-PACKAGE REALIZATION ONLY; GATEWAY, WORKBENCH, LIVE PROOF, ACTIVE DATA-PRODUCT PROMOTION, AND CLIENT-READY PUBLICATION REMAIN GATED

## Scope Boundary

This slice materializes signed-off policy evaluation evidence into a governed report-package handoff
from `lotus-advise` to `lotus-report`. It is intentionally narrower than the full RFC-0025 product
surface: Advise can now request deterministic report/render/archive handling for a signed-off policy
evaluation, record returned refs in policy lineage, and fail closed on client-ready document release.
client-ready document requests fail closed in this slice.

Implemented scope:

1. signed-off policy evaluation report-package request API,
2. source-hash validation against the immutable policy evaluation record,
3. workflow validation that requires completed policy sign-off and no open blockers,
4. typed `ADVISORY_POLICY_SIGN_OFF_PACKAGE` payload handoff to `lotus-report`,
5. returned report, render, archive, retention, and access-audit refs recorded as append-only
   policy lineage evidence,
6. replay-safe idempotency for report-package requests,
7. fail-closed client-ready document request handling.

This slice does not implement Gateway routes, Workbench policy screens, active mesh publication,
canonical `PB_SG_GLOBAL_BAL_001` front-office proof, AI policy-evidence consumption, or external
client communication.

## Implementation

The report-package boundary lives in `src/core/policy_packs/reporting.py`.

Canonical route added to `src/api/proposals/routes_policy_evaluations.py`:

1. `POST /advisory/policy-evaluations/{evaluation_id}/report-packages`

The request requires:

1. `requested_by`,
2. `portfolio_id`,
3. reviewed `source_evaluation_hash`,
4. supported `requested_output_formats`,
5. `client_ready_document_requested = false`.

The service rejects:

1. stale source hashes,
2. unsupported or empty output formats,
3. unsigned policy evaluations,
4. open approval, disclosure, consent, conflict, or source-readiness blockers,
5. client-ready document requests.

The `lotus-report` adapter path is implemented in `src/integrations/lotus_report/adapter.py` as
`request_policy_sign_off_report_package_with_lotus_report`. It submits the policy sign-off package
to the portfolio-review report job contract with `source_report_type =
ADVISORY_POLICY_SIGN_OFF_PACKAGE`. The package includes the immutable policy evaluation record,
workflow posture, audit events, source lineage, approval dependencies, disclosure requirements,
consent requirements, and the explicit `client_ready_publication = BLOCKED` boundary.

## Lineage Event

Successful materialization records `POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED` as append-only
policy lineage. The event reason stores:

1. `rfc0025.policy-report-package-realization.v1`,
2. request hash and report request id,
3. source evaluation hash and portfolio id,
4. report package id and report job status,
5. report service and status URL,
6. render refs returned by report/render,
7. archive refs returned by report/archive, including retention and access-audit metadata when the
   downstream status payload supplies them,
8. policy sign-off package summary,
9. `client_ready_publication = BLOCKED`.

Idempotent replays with the same request hash return the existing lineage event and report refs.
Reusing an idempotency key with different policy package inputs returns a conflict.

## Data Product Posture

`AdvisoryPolicyEvaluationRecord:v1` remains proposed and blocked after this slice.

The product now has Advise-local report-package realization for signed-off policy evaluations. It
remains blocked because Gateway/Workbench policy consumption, canonical live proof, supportability
promotion, active data-product promotion, and client-ready publication are not implemented.
`/platform/capabilities` must not advertise policy evaluation support until the product surface is
implementation-backed.

## Acceptance Evidence

Tests:

1. `tests/unit/advisory/api/test_api_advisory_policy_evaluations.py`
2. `tests/unit/advisory/api/test_lotus_report_adapter.py`
3. `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py`
4. `tests/unit/test_rfc0025_slice10_policy_report_package_contract.py`
5. `tests/unit/test_trust_telemetry.py`
6. `tests/unit/test_rfc0025_slice3_data_product_contract.py`

Covered paths:

1. unsigned evaluations cannot request policy report packages,
2. signed-off evaluations can request a typed policy report package from `lotus-report`,
3. render and archive refs are retained in the returned event and lineage,
4. idempotent report-package replays do not call the downstream adapter again,
5. client-ready document release fails closed,
6. OpenAPI docs expose the route, request/response contracts, idempotency header, and error
   posture,
7. data-product and trust telemetry posture remains proposed/blocked rather than promoted.

## Wiki And README Decision

Repo RFC index, repo context, codebase review ledger, data-product declaration, trust telemetry, API
vocabulary, and wiki source are updated because implementation truth changed. Wiki publication is
required after merge.
