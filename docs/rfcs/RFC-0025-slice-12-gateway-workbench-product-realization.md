# RFC-0025 Slice 12: Gateway and Workbench Product Realization

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0025: Enterprise Suitability and Best-Interest Policy Packs |
| **Slice** | 12 |
| **Status** | Implemented |
| **Date** | 2026-05-26 |
| **Primary repos** | `lotus-gateway`, `lotus-workbench`, `lotus-advise` |

## Outcome

Slice 12 exposes the implemented Advise policy-pack and policy-evaluation surface through Gateway
and the first Workbench Suitability Review product surface.

The slice is intentionally bounded. It proves advisor and supervisory review posture, sign-off
source-package posture, workflow posture, and one evidence-review request action through Gateway.
It does not promote client-ready publication, approval/waiver authority, completed policy sign-off,
or active data-product publication.

## Implementation Evidence

### Gateway

`lotus-gateway` now routes the RFC-0025 policy-pack and policy-evaluation BFF surface to canonical
`lotus-advise` APIs:

1. policy-pack list, detail, validate, and activate,
2. policy evaluation create/read/replay/events/lineage,
3. policy review queue,
4. sign-off source package,
5. workflow posture,
6. sign-off decision recording,
7. report-package request,
8. AI-evidence request.

Evidence:

1. `lotus-gateway/src/app/routers/advisory_policy.py`
2. `lotus-gateway/src/app/clients/advise_client.py`
3. `lotus-gateway/tests/integration/test_advisory_policy_router.py`
4. `lotus-gateway/tests/contract/test_advise_gateway_route_coverage.py`
5. `lotus-gateway/wiki/Supported-Features.md`

### Workbench

`lotus-workbench` consumes the Gateway/BFF policy review surface in
`/proposals?mode=suitability`.

Implemented Workbench posture:

1. loads policy review queue through Gateway only,
2. loads selected policy evaluation detail through Gateway only,
3. loads sign-off source-package posture through Gateway only,
4. loads policy workflow posture through Gateway only,
5. renders advisor-facing policy status, source gaps, approval dependencies, disclosure reviews,
   consent evidence, source references, maker-checker posture, SLA posture, sign-off blockers, and
   next action,
6. records a bounded request for more evidence through Gateway using the source evaluation hash.

Evidence:

1. `lotus-workbench/src/features/proposals/api.ts`
2. `lotus-workbench/src/features/proposals/proposal-policy-review-view-model.ts`
3. `lotus-workbench/src/features/proposals/components/proposal-lifecycle-workspace.tsx`
4. `lotus-workbench/tests/unit/proposals-api.test.ts`
5. `lotus-workbench/tests/unit/proposal-policy-review-view-model.test.ts`
6. `lotus-workbench/tests/integration/proposal-lifecycle-workspace.test.tsx`
7. `lotus-workbench/wiki/Supported-Features.md`
8. `lotus-workbench/wiki/Validation-and-CI.md`

## Product Boundaries

Supported after Slice 12:

1. Gateway-backed advisor/compliance/supervisory review of source-owned policy evaluations,
2. Gateway-backed policy workflow posture,
3. Gateway-backed sign-off source-package posture,
4. Gateway-backed request for more evidence against an immutable source evaluation hash.

Still gated:

1. active data-product publication for `AdvisoryPolicyEvaluationRecord:v1`,
2. `/platform/capabilities` promotion for a fully supported advisory policy data product,
3. canonical live front-office proof for the full policy-pack journey,
4. policy commercial/demo/RFP material,
5. second-last hardening and final closure review,
6. client-ready publication,
7. external client communication,
8. Workbench-local suitability calculation,
9. Workbench approval, waiver, or completed policy sign-off authority.

## Validation Evidence

Workbench PR #380 merged to `main` at:

1. `5a8a110740cbd822068b358c7b60469169d1261a`

Workbench validation:

1. focused proposal API/view-model/lifecycle tests passed,
2. `npm run typecheck` passed,
3. `npm run lint` passed,
4. `git diff --check` passed,
5. `make check` passed,
6. PR checks passed,
7. Main Releasability Gate `26438597740` passed,
8. Workbench wiki was published and check-only drift returned to zero.

Gateway validation was completed in the preceding Gateway Slice 12 BFF work and remains referenced
by Gateway route coverage and integration tests listed above.

## Closure Decision

Slice 12 is complete for Gateway and Workbench product realization. RFC-0025 remains open because
the active data-product promotion, canonical live proof, commercial material, final hardening,
closure notes, and post-completion communication slices are not complete.
