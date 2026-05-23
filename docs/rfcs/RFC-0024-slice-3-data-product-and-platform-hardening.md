# RFC-0024 Slice 3: Data Product and Platform Hardening

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0024: Advisor Proposal Memo and Evidence Pack |
| **Slice** | 3 - data product and platform hardening |
| **Status** | IMPLEMENTED - PROPOSED/BLOCKED DATA PRODUCT; NO MEMO SUPPORT PROMOTED |
| **Implemented Date** | 2026-05-23 |
| **Owner** | `lotus-advise`; `lotus-platform` for generated catalog/certification refresh |
| **Implementation Branch** | `rfc0024-slice3-data-product-hardening` |
| **Capability Posture** | This slice declares `AdvisoryProposalMemoEvidencePack:v1` as a governed proposed product with blocked trust telemetry. It does not implement advisor proposal memo generation, memo APIs, memo persistence, memo report packages, Gateway/Workbench memo surfaces, or client-ready memo publication. |

## Decision

RFC-0024 needs data-product guardrails before implementation-bearing memo work, but it must not
advertise memo support before the memo domain model, persistence, API, report package, downstream
consumption, and proof exist.

Slice 3 therefore creates a proposed, blocked product boundary:

1. `AdvisoryProposalMemoEvidencePack:v1` is declared in
   `contracts/domain-data-products/lotus-advise-products.v1.json`,
2. blocked trust telemetry exists in
   `contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json`,
3. the product has no `current_routes` because no memo API exists yet,
4. the product has no `/platform/capabilities` support row because capability promotion would be
   false product truth,
5. platform catalog, graph, and certification artifacts must be regenerated after the repo-native
   declaration reaches `main`.

## Data Product Posture

| Control | Slice 3 posture |
| --- | --- |
| Product identity | `lotus-advise:AdvisoryProposalMemoEvidencePack:v1` |
| Lifecycle status | `proposed` |
| Product family | `reporting_and_evidence` |
| Freshness class | `event_driven` |
| Completeness default | `blocked` |
| Lineage | Required, but not materialized until memo evidence exists |
| Evidence bundle | Required for eventual support |
| Approved consumers | `lotus-gateway`, `lotus-report`, `lotus-render`, `lotus-archive`, `lotus-workbench` |
| Current routes | None in this slice |
| Capability promotion | Capability promotion is forbidden until memo APIs and implementation proof exist |

## Trust Telemetry Posture

The RFC-0024 telemetry snapshot is intentionally blocked:

1. `freshness_state` is `unknown`,
2. `completeness_status` is `blocked`,
3. `data_quality_status` is `quality_unknown`,
4. `lineage.lineage_materialized` is `false`,
5. `blocking.blocked` is `true` with an explicit implementation blocker reason.

This is the correct enterprise posture. A private-banking memo evidence product should be visible to
governance and planning controls before implementation, but it must be unavailable to business
consumers until source-backed memo evidence, review, persistence, replay, report/archive posture,
and product-surface proof are implemented.

## Platform Hardening Posture

| Platform concern | Slice 3 decision |
| --- | --- |
| Catalog and dependency graph | Regenerate `lotus-platform/generated/domain-product-catalog.*` and `domain-product-dependency-graph.json` after the Advise declaration lands. |
| Certification report | Regenerate domain-product certification artifacts so the proposed memo product is visible and explicitly non-active. |
| SLO/access/evidence policy | Do not create active mesh SLO/access/evidence policy files for the memo yet. The product is proposed and blocked; active mesh policy files belong with the first supported memo API/data-product promotion slice. |
| Mesh certification | Must remain green for existing required first-wave products. The proposed memo product must not break existing mesh gates or imply supported memo readiness. |
| `/platform/capabilities` | No memo row is added in this slice. Capability promotion is allowed only after memo endpoints, persistence, data-product telemetry, and proof are real. |

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before Slice 3 implementation. |
| Producer declaration | Added proposed `AdvisoryProposalMemoEvidencePack:v1` to `contracts/domain-data-products/lotus-advise-products.v1.json`. |
| Trust telemetry | Added blocked `contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json`. |
| Capability non-promotion | Tests assert the product has no current routes and `/platform/capabilities` does not advertise `advisory.proposals.memo_evidence_pack`. |
| Documentation truth | README/wiki/supported-feature truth keeps memo support planned until implementation-backed slices close. |
| Platform refresh | The same slice must refresh `lotus-platform` generated catalog, graph, and certification artifacts after the Advise declaration is merged. |

## Wiki And README Decision

Wiki source is updated because RFC implementation status, mesh/data-product posture, and
operator-facing supported-feature truth changed. README does not change in this slice because
runtime commands and supported API entrypoints did not change.
