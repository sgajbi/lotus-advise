# RFC-0086 Repo-Native Domain Product Onboarding

This document records the first governed product and dependency wave for `lotus-advise` under
`RFC-0086` and the deliberately narrow future telemetry posture for `RFC-0087`.

## Govern Now

The first stable governed product for `lotus-advise` is:

1. `AdvisoryProposalLifecycleRecord`
   Persisted advisory proposal lifecycle state, immutable version evidence, approvals, and workflow
   transitions exposed through the lifecycle API family.

This is the right first-wave product because it is:

1. backend-owned,
2. persisted,
3. already consumed through stable lifecycle routes,
4. explicitly separated from `lotus-manage` discretionary workflow ownership.

## Hold For Later

The following surfaces should not be governed as stable products in this wave:

1. advisory workspace sessions and saved versions
   These are currently draft-oriented, partially in-memory, and better treated as internal advisory
   workflow state until persistence and consumer posture are stronger.
2. replay-evidence endpoints
   These are valuable support and audit surfaces, but they are currently better treated as
   supportability artifacts than first-wave product declarations.
3. integration-capabilities payloads
   These are control-plane readiness contracts, not advisory domain products.
4. workspace AI rationale output
   This remains a bounded adjacent seam on `lotus-ai`, not a stable domain product published by
   `lotus-advise`.

## First-Wave Dependencies

The first repo-native consumer declaration only covers upstream products that are already stable in
the current platform catalog and already approved for `lotus-advise` consumption:

1. `lotus-core` `HoldingsAsOf`
2. `lotus-core` `InstrumentReferenceBundle`

Deferred dependencies:

1. `lotus-risk`
   `lotus-advise` does consume risk enrichment operationally, but the current platform product
   catalog does not yet expose an approved `lotus-risk` product that truthfully matches the current
   advisory risk-enrichment seam.
2. `lotus-performance`
   Current usage remains readiness-only rather than governed product consumption.
3. `lotus-report` and `lotus-ai`
   Current usage remains bounded adjacent seams, not first-wave governed upstream products.

## Repo-Native Declaration Path

Repo-native declarations live in:

1. `contracts/domain-data-products/lotus-advise-products.v1.json`
2. `contracts/domain-data-products/lotus-advise-consumers.v1.json`

Platform schemas and registries remain owned by `lotus-platform`.

The wave-1 producer declaration intentionally anchors on `portfolio_id` plus `correlation_id`.
That fallback is transitional, not a durable advisory-native identifier, and it should remain
explicitly documented as such until the platform semantics registry grows a stable advisory
identifier family.

Local validation stages the repo-native declarations together with the current platform declaration
catalog and platform trust registries. This avoids forking platform-owned schemas or vocabularies
into the repo.

## Local Validation Path

Use:

1. `python scripts/validate_domain_data_product_declarations.py`
2. `make domain-data-products-gate`

The gate is included in `make check`, `make ci-local`, and `make ci`.

## Future RFC-0087 Telemetry Seams

Do not implement new telemetry contracts in this slice. The important future seams are:

1. lifecycle freshness from latest persisted workflow event timestamp,
2. blocked-state certification from workflow state and execution handoff posture,
3. lineage certification from request hash, simulation hash, artifact hash, and replay continuity,
4. upstream dependency certification from `lotus-core` and `lotus-risk` readiness and degraded
   reasons.

These seams already exist conceptually in the codebase and evidence model. RFC-0087 should
normalize them rather than introduce parallel advisory-only telemetry shapes.
