# RFC-0027 Slice 3: Data Product and Platform Hardening

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0027: Governed Advisory AI Copilot |
| **Slice** | 3 - data product and platform hardening |
| **Status** | IMPLEMENTED - NON-PROMOTING DATA-PRODUCT POSTURE |
| **Implemented Date** | 2026-05-28 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0027-governed-advisory-ai-copilot` |
| **Capability Posture** | This slice blocks premature copilot data-product and capability promotion. It does not declare `AdvisoryCopilotInteractionRecord:v1`, `AdvisoryCopilotEvidencePacket:v1`, or `AdvisoryCopilotReviewRecord:v1`; it does not add copilot trust telemetry; it does not promote `/platform/capabilities` copilot support; and it does not claim supported copilot runtime behavior. Those remain mandatory subsequent RFC-0027 slices after runtime implementation and proof exist. |

## Decision

RFC-0027 now has a supported copilot domain foundation, but it still lacks runtime action APIs,
durable evidence-packet and run persistence, review-state persistence, `lotus-ai` workflow-pack
execution, Gateway routing, Workbench product surfaces, canonical live proof, and production
evidence. Declaring a copilot data product or capability now would be misleading.

The candidate products remain:

1. `AdvisoryCopilotInteractionRecord:v1`
2. `AdvisoryCopilotEvidencePacket:v1`
3. `AdvisoryCopilotReviewRecord:v1`

They are not declared in `contracts/domain-data-products/lotus-advise-products.v1.json` in this
slice. Evidence packets, rejected runs, unsupported runs, unavailable runs, and guardrail-rejected
runs remain internal/audit concepts until later slices prove their persistence, lineage, review,
access, retention, and supportability posture.

## Promotion Requirements

Before any copilot data product, trust telemetry snapshot, or `/platform/capabilities` support
claim may be promoted, RFC-0027 must implement and prove:

1. runtime action APIs,
2. durable evidence-packet and run persistence,
3. review-state persistence,
4. guardrail and unsupported-evidence outcomes,
5. `lotus-ai` workflow-pack lineage,
6. source refs and content hashes for all returned evidence,
7. role-aware redaction and projection,
8. Gateway routing without direct Gateway-to-`lotus-ai` calls,
9. Workbench Gateway-first product surface,
10. `RFC27_ADVISORY_COPILOT_CANONICAL` live proof for `PB_SG_GLOBAL_BAL_001`,
11. SLO, access, retention, and evidence-policy posture,
12. trust telemetry,
13. `/platform/capabilities` promotion,
14. platform mesh certification,
15. implementation-backed README, wiki, supported-features, model-risk, operations, and business
    material.

## Guard Tests Added

| Test | Guard |
| --- | --- |
| `tests/unit/scripts/test_validate_domain_data_product_declarations.py::test_rfc0027_copilot_products_are_not_promoted_before_runtime_proof` | Fails if copilot products or copilot routes are declared before runtime proof exists. |
| `tests/unit/advisory/api/test_api_integration_capabilities.py::test_rfc0027_capabilities_do_not_promote_copilot_before_runtime_proof` | Fails if `/platform/capabilities` advertises advisory copilot support before proof exists. |
| `tests/unit/test_rfc0027_slice3_data_product_posture_contract.py` | Pins this non-promoting slice evidence, promotion requirements, negative governance tests, and the fact that no copilot trust telemetry snapshot exists yet. |

## Trust Telemetry Decision

No copilot trust telemetry snapshot is added in this slice. A snapshot would be premature without
runtime records, live proof, source freshness evidence, review state, access policy, retention
posture, and support-safe lineage refs.

When promotion is justified, the trust telemetry snapshot must prove at least:

1. source evidence freshness and completeness,
2. evidence-packet redaction and projection posture,
3. guardrail and unsupported-evidence outcomes,
4. review posture,
5. `lotus-ai` workflow-pack lineage without raw prompts or raw provider output,
6. Gateway and Workbench consumption evidence,
7. canonical live proof for `RFC27_ADVISORY_COPILOT_CANONICAL`,
8. blocked client-ready publication posture.

## Next Slice Readiness

RFC-0027 may proceed to Slice 4 copilot domain model, vocabulary, and review state. Slice 4 can
build on the `src/core/advisory_copilot/` package without needing data-product promotion.

