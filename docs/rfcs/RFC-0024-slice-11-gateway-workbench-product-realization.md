# RFC-0024 Slice 11: Gateway and Workbench Product Realization

## Status

Implemented for Gateway-routed advisor-use memo posture and Workbench product-surface visibility.

Client-ready memo release, active `AdvisoryProposalMemoEvidencePack:v1` data-product promotion,
commercial/demo/RFP claims, and final RFC-0024 closure remain gated later RFC-0024 scope.

## Implemented Behavior

Slice 11 exposes the implemented proposal memo value through product-facing surfaces:

1. `lotus-gateway` routes proposal memo create/read/projection/review/report-package/AI-commentary,
   lineage, and replay-evidence calls through canonical `lotus-advise` memo endpoints.
2. Gateway response envelopes preserve source-owned memo payloads without recomputing suitability,
   supportability, readiness, render posture, archive refs, or client-ready publication posture.
3. `lotus-workbench` adds a Gateway-only advisor memo product panel on proposal detail pages.
4. Workbench reads memo posture, audience projection, report-package posture, archive references,
   AI commentary posture, lineage, and replay evidence from Gateway/BFF APIs.
5. Workbench actions create/replay memos, approve memos for advisor use, request advisor-use memo
   report packages, and request review-gated AI commentary through Gateway only.
6. Workbench explicitly keeps client-ready release and send-to-client controls absent.

## Gateway Boundary

Gateway remains an experience API, not memo authority. It forwards:

1. `POST /api/v1/proposals/{proposal_id}/versions/{version_no}/memo`,
2. `GET /api/v1/proposals/{proposal_id}/versions/{version_no}/memo`,
3. `GET /api/v1/proposals/{proposal_id}/versions/{version_no}/memo/projection`,
4. `POST /api/v1/proposals/{proposal_id}/versions/{version_no}/memo/review`,
5. `POST /api/v1/proposals/{proposal_id}/versions/{version_no}/memo/report-packages`,
6. `POST /api/v1/proposals/{proposal_id}/versions/{version_no}/memo/ai-commentary`,
7. `GET /api/v1/proposals/{proposal_id}/memos/lineage`,
8. `GET /api/v1/proposals/{proposal_id}/versions/{version_no}/memo/replay-evidence`.

The routes use typed request contracts for write operations and opaque source-preserving response
envelopes for memo payloads that are still owned by `lotus-advise`.

## Workbench Boundary

Workbench consumes only Gateway/BFF memo APIs. The new product panel displays advisor, compliance,
operations, client-draft, degraded, and blocked posture from Gateway responses. It does not derive
memo facts from raw proposal data and does not infer supportability or readiness locally.

## Acceptance Review

Implementation evidence:

1. `../lotus-gateway/src/app/clients/advise_client.py`
2. `../lotus-gateway/src/app/contracts/proposals.py`
3. `../lotus-gateway/src/app/services/proposal_service.py`
4. `../lotus-gateway/src/app/routers/proposals.py`
5. `../lotus-gateway/tests/unit/test_proposal_service.py`
6. `../lotus-gateway/tests/contract/test_proposals_contract.py`
7. `../lotus-workbench/src/features/proposals/api.ts`
8. `../lotus-workbench/src/features/proposals/types.ts`
9. `../lotus-workbench/src/features/proposals/components/proposal-memo-posture-panel.tsx`
10. `../lotus-workbench/src/features/proposals/components/proposal-detail-view.tsx`
11. `../lotus-workbench/tests/unit/proposals-api.test.ts`
12. `../lotus-workbench/tests/unit/proposal-memo-posture-panel.test.tsx`
13. `../lotus-workbench/tests/integration/proposal-detail-view.test.tsx`
14. `../lotus-workbench/tests/e2e/proposal-memo-posture.spec.ts`

Validation evidence:

1. `lotus-gateway`: `python -m pytest tests/unit/test_proposal_service.py tests/contract/test_proposals_contract.py -q`
2. `lotus-gateway`: `python -m ruff check src/app/clients/advise_client.py src/app/contracts/proposals.py src/app/routers/proposals.py src/app/services/proposal_service.py tests/unit/test_proposal_service.py tests/contract/test_proposals_contract.py`
3. `lotus-workbench`: `npm run test -- --run tests/unit/proposals-api.test.ts tests/unit/proposal-memo-posture-panel.test.tsx tests/integration/proposal-detail-view.test.tsx`
4. `lotus-workbench`: `npm run typecheck`
5. `lotus-workbench`: `npm run lint`
6. `lotus-workbench`: `npx playwright test tests/e2e/proposal-memo-posture.spec.ts`

## Wiki And README Decision

Repo-local wiki source and the RFC index are updated because supported-feature truth changed:
Gateway and Workbench memo product realization is now implemented for advisor-use posture.

README/RFC index truth is updated to point at this slice evidence. This slice does not require a
new Advise runtime endpoint because the canonical memo endpoints were implemented in prior slices.

## Remaining Gates

Slice 11 does not promote:

1. client-ready memo publication,
2. client-ready report package release,
3. active `AdvisoryProposalMemoEvidencePack:v1` data-product support,
4. commercial/demo/RFP claims,
5. final RFC-0024 closure.
