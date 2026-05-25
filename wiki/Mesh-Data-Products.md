# Mesh Data Products

## Mesh role

`lotus-advise` is a maturity-wave producer in the Lotus enterprise data mesh.

## Governed products

- Product ID: `lotus-advise:AdvisoryProposalLifecycleRecord:v1`
- Product role: governed advisory proposal lifecycle record for downstream management, reporting, gateway, and Workbench discovery flows
- Source declaration: `contracts/domain-data-products/`
- Trust telemetry: `contracts/trust-telemetry/`

- Product ID: `lotus-advise:TacticalHouseViewAffectedCohort:v1`
- Product role: source-owned affected-cohort evaluation for bank-authored tactical house-view instructions and caller-supplied source-backed candidate portfolios
- Source declaration: `contracts/domain-data-products/`
- Approved downstream consumer: `lotus-manage`

- Product ID: `lotus-advise:ProposalNarrativeEvidence:v1`
- Product role: advisor-review proposal narrative evidence for immutable proposal-version reads,
  regeneration candidates, narrative review/replay, reviewed report-request package propagation,
  and delivery-summary posture
- Source declaration: `contracts/domain-data-products/`
- Trust telemetry: `contracts/trust-telemetry/proposal-narrative-evidence.telemetry.v1.json`
- Approved downstream consumers: `lotus-gateway`, `lotus-report`, `lotus-render`,
  `lotus-archive`

- Product ID: `lotus-advise:AdvisoryProposalMemoEvidencePack:v1`
- Product role: advisor-use proposal memo evidence for persisted memo records, advisor projection,
  review posture, report-package handoff, archive refs, AI commentary lineage, and replay hashes
- Source declaration: `contracts/domain-data-products/`
- Trust telemetry: `contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json`
- Approved downstream consumers: `lotus-gateway`, `lotus-report`, `lotus-render`,
  `lotus-archive`, `lotus-workbench`

## Platform relationship

`lotus-platform` aggregates the repo-native declaration, validates trust telemetry, applies mesh SLO/access/evidence policies, and includes this product in generated catalog, dependency graph, live certification, maturity matrix, evidence packs, and RFC-0092 operating reports.

## Operating rule

Advisory lifecycle truth remains in `lotus-advise`. Tactical house-view cohort truth is bounded to
source-backed candidates and must not be replaced by decorative gateway or Workbench status.
`lotus-manage` owns DPM workflows, policies, campaigns, and evidence after consuming the cohort
product.
Proposal narrative evidence truth remains advisor-review only until compliance-review,
client-draft, and client-ready publication slices are implemented and proven.
Proposal memo evidence truth is active for advisor-use support only; client-ready memo publication,
external client communication, and full bank-demo/RFP package claims remain gated.
