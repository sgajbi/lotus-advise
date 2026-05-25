# RFC-0024 Slice 15: Final Hardening and Review

Date: 2026-05-25

## Status

Implemented for final advisor-use hardening. This slice does not promote client-ready memo
publication, external client communication, or full RFC-0028 bank-demo/RFP package claims.

## Live Evidence

Canonical Workbench validation passed for `PB_SG_GLOBAL_BAL_001` after the Core front-office seed
readiness path reached a clean state.

Evidence location:

- `lotus-workbench/output/playwright/live-canonical/live-validation-summary.json`
- `lotus-workbench/output/playwright/live-canonical/proposal-memo-evidence-pack-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-overview-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-client-context-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-opportunities-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-proposal-builder-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-proposal-simulation-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-suitability-review-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-risk-impact-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-approval-queue-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-client-discussion-pack-live.png`
- `lotus-workbench/output/playwright/live-canonical/advisory-implementation-status-live.png`

The summary records all advisory journey panels as `ready` and `gatewayBacked=true`:

1. Advisory Overview
2. Portfolio Review
3. Opportunities And Ideas
4. Proposal Workspace
5. Proposal Simulation
6. Suitability Review
7. Risk And Impact
8. Approval Queue
9. Client Discussion Pack
10. Implementation Status

The same validation records `proposal.memo_evidence_pack` as a ready panel owned by
`lotus-advise`.

## Hardening Review

Reviewed posture:

1. API and route proof: Slice 7 certified the canonical Advise memo APIs and OpenAPI surface.
2. Gateway integration: Slice 11 routes memo posture, projection, report package, archive refs,
   AI commentary, lineage, and replay evidence through Gateway without recomputing memo facts.
3. Workbench integration: canonical live validation now proves the advisor journey panels and memo
   evidence-pack panel are populated through Gateway-backed contracts.
4. Data-product posture: Slice 14 promoted `AdvisoryProposalMemoEvidencePack:v1` as an active
   advisor-use data product with trust telemetry, `/platform/capabilities`, and platform
   SLO/access/evidence policy posture.
5. Unsupported claims: client-ready memo publication, send-to-client workflow, external client
   communication, and full RFC-0028 bank-demo/RFP package claims remain explicitly gated.

## Cleanup

Removed stale RFC wording that still described canonical live proof, memo-specific mesh policy, and
commercial support material as future gaps after those items had been implemented by Slices 12-15.

## Verification

Commands and checks:

1. `npm run live:validate` in `lotus-workbench`
2. `python -m pytest tests/integration/tools/test_demo_data_pack.py tests/unit/tools/test_front_office_portfolio_seed.py -q` in `lotus-core` for the seed verifier hardening that unblocked live proof retry behavior

GitHub PR evidence:

1. `lotus-core` PR #385 merged as `52a70031` after Feature Lane and PR Merge Gate passed.
2. `lotus-advise` Slice 15 documentation PR owns this RFC/wiki truth update.
