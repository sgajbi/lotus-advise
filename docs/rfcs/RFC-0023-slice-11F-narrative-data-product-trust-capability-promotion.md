# RFC-0023 Slice 11F: Narrative Data Product, Trust Telemetry, and Capability Promotion

Status: Implemented on 2026-05-22

Owning RFC: `RFC-0023`

Owner repositories: `lotus-advise`, `lotus-platform`

## Purpose

Slice 11F closes the RFC-0023 advisor-review narrative evidence promotion gap left open by Slice
11E. It promotes only implementation-backed advisor-review proposal narrative evidence as a
governed domain product, trust telemetry snapshot, and `/platform/capabilities` feature/workflow.

This slice does not promote compliance-review narrative, client-draft narrative, client-ready
commentary, client-ready publication, or canonical demo screenshot proof.

## Implemented Behavior

`lotus-advise` now declares `ProposalNarrativeEvidence:v1` as an active governed product for
advisor-review proposal narrative evidence. The product covers immutable proposal-version
narrative reads, non-persistent regeneration candidates, narrative review, replay evidence,
reviewed report-request package propagation, and delivery-summary evidence.

The product declaration records:

1. advisory workflow source authority,
2. portfolio-scoped request posture,
3. event-time freshness through `generated_at`,
4. required trust metadata including product name, version, generated time, content hash, and
   correlation ID,
5. lineage requirement and customer-consumable evidence access class,
6. approved downstream consumers for Gateway, Report, Render, and Archive paths.

`contracts/trust-telemetry/proposal-narrative-evidence.telemetry.v1.json` provides the repo-native
trust telemetry snapshot for `lotus-advise:ProposalNarrativeEvidence:v1`. The snapshot is bounded
to advisor-review narrative evidence and intentionally excludes client-ready and compliance-review
claims.

`GET /platform/capabilities` now advertises:

1. feature key `advisory.proposals.reviewed_narrative_evidence`,
2. workflow key `advisory_proposal_reviewed_narrative_evidence`,
3. dependency on the existing advisory proposal lifecycle feature,
4. lifecycle-disabled degradation when advisory lifecycle support is disabled,
5. explicit wording that compliance-review, client-draft, client-ready publication, and demo proof
   remain gated.

`lotus-platform` generated domain-product discovery, dependency graph, and certification artifacts
are refreshed so the platform catalog resolves and certifies the new product.

## Acceptance Review

| Gate | Result | Evidence |
| --- | --- | --- |
| Producer declaration exists | Pass | `contracts/domain-data-products/lotus-advise-products.v1.json` declares `ProposalNarrativeEvidence:v1` |
| Trust telemetry validates against product declaration | Pass | `tests/unit/test_trust_telemetry.py` ties telemetry metadata to the product declaration |
| Platform catalog resolves product | Pass | `lotus-platform` generated catalog includes `lotus-advise:ProposalNarrativeEvidence:v1` |
| Capability promotion is bounded | Pass | `tests/unit/advisory/api/test_api_integration_capabilities.py` asserts reviewed narrative evidence feature/workflow and absence of client-ready capability |
| Client-ready and compliance claims remain blocked | Pass | Trust telemetry and capability tests assert no client-ready or compliance-review promotion |
| Documentation truth is aligned | Pass | README, RFC index, wiki source, and repository context distinguish advisor-review data-product support from remaining gated claims |
| Platform catalog refresh is merged | Pass | `lotus-platform` PR #344 merged as `f188cf1d9b24631a4ab691527d543522b5f220d2` |

## Local Validation

Targeted validation for this slice:

1. `python scripts/validate_domain_data_product_declarations.py`
2. `python -m pytest tests/unit/advisory/api/test_api_integration_capabilities.py tests/unit/test_trust_telemetry.py tests/unit/test_rfc0023_slice11f_documentation_contract.py -q`
3. `python automation/generate_domain_product_discovery.py --check --generated-at-utc 2026-04-19T00:00:00Z` in `lotus-platform`
4. `python automation/validate_trust_telemetry.py ..\lotus-advise\contracts\trust-telemetry --catalog generated\domain-product-catalog.json` in `lotus-platform`
5. `python -m pytest tests/unit/test_domain_product_discovery_generator.py tests/unit/test_domain_product_certification_report.py tests/unit/test_domain_product_discovery_query.py -q` in `lotus-platform`

## Remaining Gates

The following RFC-0023 claims remain gated until later implementation slices close with tests,
documentation, and publication evidence:

1. compliance-review narrative,
2. client-draft narrative,
3. client-ready commentary and publication,
4. canonical demo screenshot proof for populated proposal narrative journeys.
