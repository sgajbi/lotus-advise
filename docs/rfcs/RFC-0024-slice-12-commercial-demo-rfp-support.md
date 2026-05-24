# RFC-0024 Slice 12: Commercial, Demo, and RFP-Support Material

## Status

Implemented for memo-specific commercial support material grounded in Slices 0-11.

This slice does not promote client-ready memo publication, send-to-client controls, active
`AdvisoryProposalMemoEvidencePack:v1` data-product support, or the broader RFC-0028 bank-demo/RFP
package.

## Implemented Behavior

Slice 12 adds a bounded commercial-support source for the advisor proposal memo:

1. memo-specific product one-pager language,
2. sales/pre-sales demo notes,
3. API examples for memo create, review, report-package, and AI-commentary flows,
4. architecture flow showing Advise, Report, Render, Archive, AI, Gateway, and Workbench boundaries,
5. operator guidance for readiness, degraded AI, lineage, replay, and blocker explanation,
6. RFP-safe and unsafe wording,
7. explicit RFC-0028 boundary decision.

The guide is intentionally claim-controlled: it explains the implemented advisor-use memo posture
without claiming client-ready publication, active data-product certification, or a complete bank-demo
journey.

## Commercial Boundary

The implemented commercial claim is:

`lotus-advise` can explain and demonstrate an advisor-use proposal memo capability with persisted
memo evidence, hash-continuity review gates, report/render/archive refs, review-gated AI
commentary, Gateway/Workbench visibility, lineage, and replay evidence.

The slice keeps these claims gated:

1. client-ready memo publication,
2. external client communication,
3. active `AdvisoryProposalMemoEvidencePack:v1` data-product support,
4. full bank-demo proof pack,
5. enterprise security/RFP pack,
6. architecture deck and ROI material.

## Acceptance Review

Implementation evidence:

1. `docs/commercial/RFC-0024-advisor-proposal-memo-commercial-support.md`
2. `docs/demo/README.md`
3. `docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md`
4. `docs/rfcs/README.md`
5. `wiki/RFC-Index.md`
6. `wiki/Supported-Features.md`
7. `contracts/domain-data-products/lotus-advise-products.v1.json`
8. `contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json`

Validation evidence:

1. `python -m pytest tests/unit/test_rfc0024_slice12_documentation_contract.py tests/unit/test_trust_telemetry.py -q`
2. `make check`
3. `..\\lotus-platform\\automation\\Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-advise`

## RFC-0028 Decision

No RFC-0028 source update is required in this slice. The new commercial support guide stays inside
memo-specific RFC-0024 evidence and explicitly defers complete bank-demo journeys, enterprise
RFP/security packs, architecture decks, ROI material, and client-demo supported-claim proof packs to
RFC-0028.

## Remaining Gates

Slice 12 does not promote:

1. client-ready memo publication,
2. client-ready report package release,
3. send-to-client controls,
4. active `AdvisoryProposalMemoEvidencePack:v1` data-product support,
5. RFC-0028 full bank-demo or RFP package support,
6. final RFC-0024 closure.
