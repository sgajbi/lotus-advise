# RFC-0024 Slice 5: Memo Domain Model and Pure Builder

Status: Implemented on 2026-05-23.

## Purpose

Slice 5 introduces the first RFC-0024 memo domain implementation without promoting memo support as
a product capability. The slice adds a deterministic, side-effect-free builder for
`AdvisoryProposalMemoEvidencePack:v1` so later persistence, API, report, Gateway, Workbench, and
client-ready slices have a clean domain boundary to build on.

This slice deliberately does not add memo routes, persistence, report packages, archive records,
Gateway contracts, Workbench screens, active data-product support, or client-ready memo claims.

## Implemented Behavior

1. `src/core/proposals/memo_models.py` defines typed memo evidence-pack, section, material-claim,
   audience, section-status, and source-authority manifest models.
2. `src/core/proposals/memo_builder.py` builds a deterministic pure
   `AdvisoryProposalMemoEvidencePack` from immutable proposal artifact JSON and the persisted
   RFC-0024 `memo_source_readiness` manifest.
3. The builder emits all 17 RFC-required memo sections in stable order:
   `EXECUTIVE_SUMMARY`, `CLIENT_AND_HOUSEHOLD_CONTEXT`,
   `ADVISORY_OBJECTIVE_AND_CONSTRAINTS`, `RECOMMENDATION`, `REJECTED_ALTERNATIVES`,
   `PORTFOLIO_IMPACT`, `RISK_AND_SCENARIO_CONTEXT`, `SUITABILITY_AND_BEST_INTEREST`,
   `FEES_COSTS_TAX_AND_FRICTIONS`, `CONFLICTS_AND_DISCLOSURES`,
   `APPROVALS_CONSENTS_AND_MAKER_CHECKER`, `REPORT_ARCHIVE_AND_DELIVERY_READINESS`,
   `EXECUTION_HANDOFF_BOUNDARY`, `EVIDENCE_AND_LINEAGE_APPENDIX`, `COMPLIANCE_APPENDIX`,
   `OPERATIONS_APPENDIX`, and `SUPPORTABILITY_APPENDIX`.
4. Each section carries status, audience visibility, summary, material claims, claim refs, evidence
   refs, source-authority refs, missing evidence, degraded evidence, reason codes,
   review-required posture, owner role, material input hash, and section hash.
5. Material claims are emitted only when evidence refs and source-authority refs exist. Missing
   source-owner evidence remains `PENDING_REVIEW` or `BLOCKED` instead of being rendered as a
   positive memo claim.
6. Report/render/archive readiness remains `BLOCKED` with explicit reason codes until later
   RFC-0024 slices implement typed package, render, archive, retention, and access-audit support.
7. The memo pack exposes deterministic `source_input_hash`, `memo_hash`, and `memo_id` values.

## Design Review

The implementation keeps memo logic out of `ProposalWorkflowService`, API routers, persistence, and
report handoff modules. The builder consumes existing immutable evidence and source-readiness
truth, then returns a typed domain object. That keeps later Slice 6 persistence and Slice 7 API work
thin and avoids re-expanding the proposal service.

The builder does not duplicate source methodology. It projects:

1. `lotus-core` source posture from the Slice 4 source-readiness manifest,
2. `lotus-risk` concentration and missing extended-risk posture from the manifest,
3. `lotus-advise` decision summary, alternatives, gate decision, suitability summary, trades, and
   execution-boundary posture from immutable proposal artifact evidence.

## Acceptance Review

| Gate | Status | Evidence |
| --- | --- | --- |
| Pure deterministic builder | Pass | Repeated builds over equivalent evidence return identical `memo_hash` and `memo_id`. |
| Required memo sections exist | Pass | Unit tests assert all 17 RFC-required sections in stable order. |
| Source-backed material claims | Pass | Unit tests prove every material claim has evidence refs and source-authority refs. |
| Missing evidence remains explicit | Pass | Unit tests prove missing positions flow into `BLOCKED` section posture and reason codes. |
| Report/archive not over-promoted | Pass | Report/archive section remains `BLOCKED` with `MEMO_REPORT_RENDER_ARCHIVE_NOT_IMPLEMENTED`. |
| Public product claim not promoted | Pass | No API routes, persistence, Gateway/Workbench support, or supported-feature promotion is added. |

## Local Validation

1. `python -m pytest tests/unit/advisory/engine/test_engine_proposal_memo_builder.py -q`
2. `python -m ruff check src/core/proposals/memo_models.py src/core/proposals/memo_builder.py tests/unit/advisory/engine/test_engine_proposal_memo_builder.py`
3. `python -m mypy --config-file mypy.ini src/core/proposals/memo_models.py src/core/proposals/memo_builder.py`

## Wiki And README Decision

The repo RFC index and authored wiki source are updated because this slice changes durable RFC
state. The supported-features page records Slice 5 as pure builder foundation only. It deliberately
does not mark advisor proposal memo, client-ready memo publication, or
`AdvisoryProposalMemoEvidencePack:v1` as supported product capability.

## Remaining Gates

1. Slice 6 must add persistence, replay, idempotency, and audit behavior before any memo can become
   durable product truth.
2. Slice 7 must certify APIs and OpenAPI before Gateway or Workbench consumption.
3. Slice 9 must implement report/render/archive realization before client-ready memo publication
   can be considered.
4. Supported features and `/platform/capabilities` must remain non-claiming until implementation
   proof closes later slices.
