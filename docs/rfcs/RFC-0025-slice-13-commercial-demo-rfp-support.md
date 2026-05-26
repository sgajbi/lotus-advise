# RFC-0025 Slice 13: Commercial, Demo, and RFP-Support Material

## Status

Implemented for policy-pack-specific commercial support material grounded in Slices 0-12.

This slice does not promote active `AdvisoryPolicyEvaluationRecord:v1` data-product support,
`/platform/capabilities` policy evaluation support, canonical live proof, approval/waiver authority,
completed sign-off authority, client-ready publication, or the broader RFC-0028 bank-demo/RFP
package.

## Implemented Behavior

Slice 13 adds a bounded commercial-support source for enterprise suitability and best-interest
policy packs:

1. policy-pack-specific product one-pager language,
2. sales/pre-sales demo notes,
3. API examples for policy-pack, policy-evaluation, review-queue, sign-off decision, and AI
   policy-evidence flows,
4. architecture flow showing Advise, policy packs, Gateway, Workbench, Report, Render, Archive,
   AI, replay, and lineage boundaries,
5. operator guidance for readiness, capability discovery, degraded AI, lineage, replay, and blocker
   explanation,
6. RFP-safe and unsafe wording,
7. explicit RFC-0028 boundary decision.

The guide is intentionally claim-controlled: it explains the implemented advisor, compliance,
supervisory, operations, and support review posture without claiming active data-product promotion,
platform capability promotion, completed approval authority, client-ready publication, or a complete
bank-demo journey.

## Commercial Boundary

The implemented commercial claim is:

`lotus-advise` can explain and demonstrate a policy-pack review capability with active reference
policy packs, source-backed policy evaluations, finalized record hashes, review queue, sign-off
source packages, workflow posture, report/render/archive lineage, bounded AI policy-evidence
summary lineage, Gateway/Workbench visibility, lineage, and replay evidence.

The slice keeps these claims gated:

1. active `AdvisoryPolicyEvaluationRecord:v1` data-product support,
2. `/platform/capabilities` policy evaluation promotion,
3. canonical live proof and demo-ready screenshot proof,
4. approval, waiver, or completed sign-off authority,
5. client-ready policy publication and external client communication,
6. full bank-demo proof pack,
7. enterprise security/RFP pack,
8. architecture deck and ROI material.

## Acceptance Review

Implementation evidence:

1. `docs/commercial/RFC-0025-enterprise-policy-pack-commercial-support.md`
2. `docs/demo/README.md`
3. `docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md`
4. `docs/rfcs/README.md`
5. `wiki/RFC-Index.md`
6. `wiki/Supported-Features.md`
7. `contracts/domain-data-products/lotus-advise-products.v1.json`
8. `contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json`

Validation evidence:

1. `python -m pytest tests/unit/test_rfc0025_slice13_commercial_support_contract.py tests/unit/test_trust_telemetry.py -q`
2. `make check`
3. `..\\lotus-platform\\automation\\Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-advise`

## RFC-0028 Decision

No RFC-0028 source update is required in this slice. The new commercial support guide stays inside
policy-pack-specific RFC-0025 evidence and explicitly defers complete bank-demo journeys,
enterprise RFP/security packs, architecture decks, ROI material, and client-demo supported-claim
proof packs to RFC-0028.

## Remaining Gates

Slice 13 does not promote:

1. active `AdvisoryPolicyEvaluationRecord:v1` data-product support,
2. `/platform/capabilities` policy evaluation support,
3. canonical live proof,
4. completed approval, waiver, or sign-off authority,
5. client-ready policy publication,
6. client-ready report package release,
7. send-to-client controls,
8. RFC-0028 full bank-demo or RFP package support,
9. final RFC-0025 closure.
