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
   Blocked governance telemetry for `lotus-advise:AdvisoryProposalMemoEvidencePack:v1`, the
   proposed RFC-0024 advisor proposal memo product. This snapshot exists so catalog, trust, SLO,
   access, and evidence policy controls can see the planned product boundary. It now acknowledges
   implemented advisor-use memo model, persistence, APIs, report/render/archive realization,
   review-gated AI commentary, Gateway/Workbench consumption, and memo-specific commercial support
   material while keeping active data-product promotion and client-ready memo publication blocked.

Validate locally with:

```powershell
python -m pytest tests\unit\test_trust_telemetry.py -q
```

When `../lotus-platform` is available, the test validates the snapshot with the platform
`automation/validate_trust_telemetry.py` contract validator and checks that observed trust metadata
matches the repo-native declaration in `contracts/domain-data-products/lotus-advise-products.v1.json`.
