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

## Platform relationship

`lotus-platform` aggregates the repo-native declaration, validates trust telemetry, applies mesh SLO/access/evidence policies, and includes this product in generated catalog, dependency graph, live certification, maturity matrix, evidence packs, and RFC-0092 operating reports.

## Operating rule

Advisory lifecycle truth remains in `lotus-advise`. Tactical house-view cohort truth is bounded to
source-backed candidates and must not be replaced by decorative gateway or Workbench status.
`lotus-manage` owns DPM workflows, policies, campaigns, and evidence after consuming the cohort
product.
