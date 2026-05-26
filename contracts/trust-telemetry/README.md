# Lotus Advise Trust Telemetry

This directory contains repo-owned RFC-0087 trust telemetry snapshots for governed `lotus-advise`
domain products.

The current first-wave snapshot is:

1. `advisory-proposal-lifecycle-record.telemetry.v1.json`
   Runtime trust proof for `lotus-advise:AdvisoryProposalLifecycleRecord:v1`.
2. `proposal-narrative-evidence.telemetry.v1.json`
   Runtime trust proof for `lotus-advise:ProposalNarrativeEvidence:v1`, the RFC-0023
   advisor-review narrative evidence product. This snapshot does not promote compliance-review,
   client-draft, client-ready publication, or demo screenshot proof.
3. `advisory-proposal-memo-evidence-pack.telemetry.v1.json`
   Runtime trust proof for `lotus-advise:AdvisoryProposalMemoEvidencePack:v1`, the active RFC-0024
   advisor-use proposal memo product. This snapshot is bounded to implemented memo model,
   persistence, APIs, report/render/archive realization, review-gated AI commentary,
   Gateway/Workbench consumption, memo-specific commercial support material, live-suite
   implementation proof, and platform SLO/access/evidence policy posture. It does not promote
   client-ready memo publication, external client communication, or full RFC-0028 bank-demo/RFP
   package claims.
4. `advisory-policy-evaluation-record.telemetry.v1.json`
   Blocked trust posture for `lotus-advise:AdvisoryPolicyEvaluationRecord:v1`, the proposed
   RFC-0025 policy-evaluation product. This snapshot makes the product visible to mesh governance
   without promoting Gateway/Workbench policy surfaces, active data-product support, live proof, or
   client-ready publication. The internal Slice 6 evaluator, Slice 7 finalized-record
   persistence/replay path, Slice 8 certified Advise evaluation API surface, Slice 9 Advise source
   workflow/sign-off decision boundary, Slice 10 Advise report-package realization path, and Slice
   11 Advise AI policy-evidence boundary are implementation-backed but remain below the
   data-product publication boundary until later product-surface slices are complete.

Validate locally with:

```powershell
python -m pytest tests\unit\test_trust_telemetry.py -q
```

When `../lotus-platform` is available, the test generates a current domain-product catalog from
repo-native declarations, validates the snapshots with the platform
`automation/validate_trust_telemetry.py` contract validator, and checks that observed trust
metadata matches the repo-native declaration in
`contracts/domain-data-products/lotus-advise-products.v1.json`.
