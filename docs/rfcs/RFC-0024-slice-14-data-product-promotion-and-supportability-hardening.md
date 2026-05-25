# RFC-0024 Slice 14: Data-Product Promotion and Supportability Hardening

Status: Implemented on 2026-05-25

Owning RFC: `RFC-0024`

Owner repositories: `lotus-advise`, `lotus-platform`

## Purpose

Slice 14 promotes only the implemented advisor-use memo evidence pack as an active governed domain
product. It closes the remaining data-product gap left after Slice 13 live proof by aligning the
producer declaration, trust telemetry, platform SLO/access/evidence-policy posture, catalog
artifacts, and `/platform/capabilities`.

This slice does not promote client-ready memo publication, external client communication, or full
RFC-0028 bank-demo/RFP package claims.

## Implemented Behavior

`lotus-advise` now declares `AdvisoryProposalMemoEvidencePack:v1` as an active advisor-use evidence
product for persisted memo evidence, projection, review posture, report-package handoff, archive
refs, review-gated AI commentary lineage, and replay hashes.

The active product declaration records the canonical memo route family:

1. memo create and read,
2. advisor projection,
3. advisor-use review,
4. report-package event and request posture,
5. non-authoritative AI commentary,
6. proposal memo lineage,
7. memo replay evidence.

`contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json` now reports
current freshness, complete completeness, passed data quality, materialized lineage, and an
unblocked advisor-use evidence posture.

`GET /platform/capabilities` now advertises:

1. feature key `advisory.proposals.memo_evidence_pack`,
2. workflow key `advisory_proposal_memo_evidence_pack`,
3. dependency on `advisory.proposals.lifecycle`, `advisory.proposals.reporting`, and `lotus-report`,
4. degraded posture when report-package support is unavailable,
5. explicit wording that client-ready memo publication, external client communication, and full
   bank-demo/RFP package claims remain gated.

`lotus-platform` adds mesh SLO, access, and evidence-pack policies for the product and refreshes the
generated domain-product catalog, dependency graph, certification report, and maturity matrix.

## Acceptance Review

| Gate | Result | Evidence |
| --- | --- | --- |
| Producer declaration active | Pass | `contracts/domain-data-products/lotus-advise-products.v1.json` declares `AdvisoryProposalMemoEvidencePack:v1` as active with memo routes |
| Trust telemetry validates | Pass | `tests/unit/test_trust_telemetry.py` ties telemetry to the active declaration and blocks client-ready overclaiming |
| Capability promotion bounded | Pass | `tests/unit/advisory/api/test_api_integration_capabilities.py` asserts memo evidence feature/workflow and degraded report dependency behavior |
| Platform supportability posture exists | Pass | `lotus-platform/platform-contracts/mesh-slo`, `mesh-access`, and `mesh-evidence` include memo policy files |
| Catalog and certification refresh | Pass | `lotus-platform/generated/domain-product-catalog.*`, dependency graph, certification report, and maturity matrix include active memo support |
| Documentation truth aligned | Pass | RFC index, wiki source, commercial guide, supported features, trust telemetry README, and repository context distinguish advisor-use data-product support from remaining gated claims |

## Local Validation

Targeted validation for this slice:

1. `python scripts/validate_domain_data_product_declarations.py`
2. `python -m pytest tests/unit/advisory/api/test_api_integration_capabilities.py tests/unit/test_trust_telemetry.py tests/unit/test_rfc0024_slice14_documentation_contract.py -q`
3. `python automation/generate_domain_product_discovery.py --check --generated-at-utc 2026-04-19T00:00:00Z` in `lotus-platform`
4. `python automation/generate_domain_product_certification.py --generated-at-utc 2026-04-19T00:00:00Z` in `lotus-platform`
5. `python automation/generate_enterprise_mesh_maturity_matrix.py --check --generated-at-utc 2026-04-20T00:00:00Z` in `lotus-platform`
6. `python automation/validate_trust_telemetry.py ..\lotus-advise\contracts\trust-telemetry --catalog generated\domain-product-catalog.json` in `lotus-platform`

## Remaining Gates

The following RFC-0024 claims remain gated until later implementation closes them with tests,
documentation, and publication evidence:

1. client-ready memo publication,
2. external client communication,
3. full RFC-0028 bank-demo and RFP package claims,
4. final RFC closure and post-completion communication.
