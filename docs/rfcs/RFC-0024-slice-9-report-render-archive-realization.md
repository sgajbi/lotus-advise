# RFC-0024 Slice 9: Report, Render, and Archive Realization

## Status

Implemented for advisor-use memo report package materialization.

Client-ready memo document generation, Gateway exposure, Workbench exposure, AI commentary, and active
`AdvisoryProposalMemoEvidencePack:v1` data-product promotion remain gated later RFC-0024 scope.

## Implemented Scope

Slice 9 adds the implementation-backed report/render/archive path for persisted advisor proposal memo
evidence packs:

1. `lotus-advise` exposes
   `POST /advisory/proposals/{proposal_id}/versions/{version_no}/memo/report-packages`.
2. The Advise command requires exact `source_memo_hash` continuity and a prior
   `APPROVE_FOR_ADVISOR_USE` memo review event.
3. Client-ready document requests are rejected with `MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED`.
4. Advise submits a typed `proposal_memo_package` to `lotus-report` through the existing
   portfolio-review report job seam.
5. `lotus-report` validates the typed memo package, preserves it in the immutable report snapshot,
   projects it into the deterministic render package as `advisor_proposal_memo`, and carries memo
   lineage/disclosure refs.
6. `lotus-report` includes support-safe `advisor_proposal_memo` archive metadata in archive handoff.
7. `lotus-archive` validates and stores the support-safe advisor proposal memo archive summary and
   exposes it in metadata/source-event artifact refs without raw memo reconstruction.
8. Advise records returned report, render, and archive refs in append-only memo audit events and
   memo lineage.

## Evidence

Implementation and tests:

1. `src/core/proposals/memo_api.py`
2. `src/api/proposals/routes_memo.py`
3. `src/integrations/lotus_report/adapter.py`
4. `../lotus-report/src/app/reporting_jobs/models.py`
5. `../lotus-report/src/app/reporting_render/package_builder.py`
6. `../lotus-report/src/app/reporting_render/service.py`
7. `../lotus-archive/src/app/archive/models.py`
8. `../lotus-archive/src/app/archive/api_models.py`
9. `../lotus-archive/src/app/archive/source_events.py`
10. `tests/unit/advisory/api/test_api_advisory_proposal_memo.py`
11. `tests/unit/advisory/api/test_lotus_report_adapter.py`
12. `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py`
13. `../lotus-report/tests/unit/reporting_jobs/test_report_job_ledger.py`
14. `../lotus-report/tests/unit/reporting_render/test_service.py`
15. `../lotus-archive/tests/unit/test_archive_metadata_model.py`
16. `../lotus-archive/tests/unit/test_migration_contract.py`

## Non-Promotion Boundary

Slice 9 does not promote client-ready memo publication. The supported document path is advisor-use
materialization after memo review. Gateway, Workbench, AI commentary, active data-product support,
commercial/demo claims, and final RFC closure remain later slices.
