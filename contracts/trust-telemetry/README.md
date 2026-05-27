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
   Active trust posture for `lotus-advise:AdvisoryPolicyEvaluationRecord:v1`, the RFC-0025
   policy-evaluation product. This snapshot promotes advisor/compliance policy evidence after the
   Slice 6 evaluator, Slice 7 finalized-record persistence/replay path, Slice 8 certified Advise
   evaluation API surface, Slice 9 workflow/sign-off decision boundary, Slice 10 report-package
   realization path, Slice 11 AI policy-evidence boundary, Slice 12 Gateway/Workbench product
   realization, Slice 13 commercial support material, Slice 14 live-suite proof, Slice 15
   supportability hardening, and Slice 16 final closure. Completed approval/waiver authority,
   completed sign-off authority, client-ready publication, and external client communication remain
   blocked.
5. `advisor-cockpit-operating-snapshot.telemetry.v1.json`
   Active trust posture for `lotus-advise:AdvisorCockpitOperatingSnapshot:v1`, the RFC-0026
   advisor cockpit operating snapshot product. This snapshot is bounded to source-owned snapshot,
   supportability, meeting-preparation, Gateway/Workbench, and canonical proof evidence; it does
   not promote client-ready publication, external client communication, CRM system-of-record
   behavior, OMS order lifecycle, completed policy approval authority, or full RFC-0028 demo/RFP
   package claims.
6. `advisory-action-item-register.telemetry.v1.json`
   Active trust posture for `lotus-advise:AdvisoryActionItemRegister:v1`, the RFC-0026 source-owned
   action-item register. Acknowledgements prove review posture only; they do not clear blockers,
   approve policy findings, contact clients, create CRM tasks, or initiate OMS order lifecycle
   activity.

Validate locally with:

```powershell
python -m pytest tests\unit\test_trust_telemetry.py -q
```

When `../lotus-platform` is available, the test generates a current domain-product catalog from
repo-native declarations, validates the snapshots with the platform
`automation/validate_trust_telemetry.py` contract validator, and checks that observed trust
metadata matches the repo-native declaration in
`contracts/domain-data-products/lotus-advise-products.v1.json`.
