# RFC-0024 Slice 7 - Certified APIs and OpenAPI

## Implemented Behavior

Slice 7 exposes the first canonical `lotus-advise` memo API surface for the persisted
`AdvisoryProposalMemoEvidencePack:v1` created by Slices 5 and 6.

Implemented endpoints:

| Endpoint | Behavior |
| --- | --- |
| `POST /advisory/proposals/{proposal_id}/versions/{version_no}/memo` | Creates or idempotently replays a persisted memo for an immutable proposal version. |
| `GET /advisory/proposals/{proposal_id}/versions/{version_no}/memo` | Reads the exact persisted memo record, projection policy, audit events, and replay links. |
| `GET /advisory/proposals/{proposal_id}/versions/{version_no}/memo/projection` | Returns read-only memo projection policy and optional audience-filtered sections. |
| `POST /advisory/proposals/{proposal_id}/versions/{version_no}/memo/review` | Records idempotent append-only memo review events against the inspected memo hash. |
| `POST /advisory/proposals/{proposal_id}/versions/{version_no}/memo/report-package-events` | Records append-only report-package posture events without creating report/render/archive artifacts. |
| `GET /advisory/proposals/{proposal_id}/memos/lineage` | Returns proposal-level memo lineage with memo hashes, source hashes, lifecycle status, and event counts. |
| `GET /advisory/proposals/{proposal_id}/versions/{version_no}/memo/replay-evidence` | Returns memo replay evidence with proposal source hashes, memo hashes, replay metadata, projection posture, and audit events. |

The API surface is intentionally Advise-owned only. Slice 7 does not add Gateway routes, Workbench
surfaces, report rendering, archive realization, active data-product support, or client-ready memo
publication.

The primary OpenAPI contracts are `ProposalMemoCreateRequest`, `ProposalMemoResponse`,
`ProposalMemoProjectionResponse`, `ProposalMemoReviewRequest`,
`ProposalMemoReportPackageEventRequest`, `ProposalMemoLineageResponse`, and
`ProposalMemoReplayEvidenceResponse`.

## Design Review

Memo API logic lives in `src/core/proposals/memo_api.py` instead of expanding
`ProposalWorkflowService`. The route module `src/api/proposals/routes_memo.py` remains a thin
controller over the repository and core memo commands. This keeps memo behavior modular and avoids
re-coupling proposal lifecycle orchestration to memo review/report-package event rules.

The route family is canonical and version-scoped:

1. memo creation is anchored to immutable proposal versions,
2. review and report-package writes are hash-guarded by `source_memo_hash`,
3. idempotent event writes detect payload drift using a canonical request hash,
4. replay evidence exposes the same source hashes persisted by Slice 6,
5. client-ready publication remains blocked in every response posture.

## Acceptance Review

Slice 7 acceptance criteria:

| Criterion | Evidence |
| --- | --- |
| OpenAPI gate passes with endpoint guidance, examples, response docs, and header docs | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` validates memo schemas, canonical route family, response refs, `Idempotency-Key` headers, error docs, and tag ownership. |
| Endpoint certification covers behavior and material returned fields | `tests/unit/advisory/api/test_api_advisory_proposal_memo.py` validates create/replay, read, projection, review idempotency/conflict, stale hash rejection, client-ready release blocking, report-package events, lineage, and replay evidence fields. |
| Broken or retired downstream contract is migrated in the same RFC | No Gateway, Workbench, report/render/archive, or downstream contract is changed in this slice; those remain explicitly blocked future scope. |

## API Boundary

Supported now:

1. `lotus-advise` memo create/read/projection/review/report-package-event/lineage/replay endpoints,
2. OpenAPI/Swagger contract exposure under the `Advisory Proposal Memo` tag,
3. idempotency for memo creation, review events, and report-package events,
4. stale-hash protection for review and report-package event writes,
5. read-only projection and replay evidence.

Still not supported:

1. Gateway and Workbench memo product surfaces,
2. report rendering, archive storage, and client document generation,
3. active `AdvisoryProposalMemoEvidencePack:v1` data-product support,
4. client-ready memo approval, publication, or external client communication.

## Wiki And README Decision

Repo-local wiki source and RFC index are updated because Slice 7 changes public Advise API truth.
README remains unchanged because the existing repository command and orientation surface is still
accurate.

## Remaining Gates

Later RFC-0024 slices still need policy/fees/conflicts enrichment, report/render/archive
realization, AI narrative integration, Gateway/Workbench product realization, live front-office
proof, documentation/demo enablement, and closure hardening before client-ready memo claims can be
made.
