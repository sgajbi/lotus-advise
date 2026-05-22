# RFC-0023 Slice 4: Data Product and Supportability Baseline

| Field | Value |
| --- | --- |
| RFC | RFC-0023 Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| Slice | 4 |
| Status | IMPLEMENTED - NON-PROMOTION BASELINE |
| Capability Posture | This slice does not promote `proposal_narrative` as a governed data product or supported `/platform/capabilities` feature. It pins the supportability decision that promotion is blocked until deterministic advisor-review narrative exists in Slice 5 and later review/replay slices. |
| Implementation Date | 2026-05-22 |

## Purpose

Slice 4 settles the data-product and supportability boundary before proposal narrative code is
introduced. The correct enterprise posture is conservative: `lotus-advise` already exposes
implementation-backed advisory lifecycle and tactical house-view data products, but it does not yet
emit a proposal narrative product.

This slice therefore records a deliberate non-promotion decision and adds regression evidence so
future implementation slices cannot accidentally advertise AI-assisted, client-draft, client-ready,
or mesh-certified narrative support before the backing implementation exists.

## Current Data-Product Evidence

| Current product | Source | Current status | RFC-0023 relevance |
| --- | --- | --- | --- |
| `AdvisoryProposalLifecycleRecord` | `contracts/domain-data-products/lotus-advise-products.v1.json` | Active governed product | Provides lifecycle and proposal-version context that future narrative can cite, but it is not narrative text. |
| `TacticalHouseViewAffectedCohort` | `contracts/domain-data-products/lotus-advise-products.v1.json` | Active governed product | Supports advisory-to-DPM operating evidence; not a narrative product. |
| `AdvisoryProposalLifecycleRecord` trust telemetry | `contracts/trust-telemetry/advisory-proposal-lifecycle-record.telemetry.v1.json` | Active RFC-0087 fixture | Validates existing lifecycle product trust posture only. |
| `/platform/capabilities` advisory supportability | `src/api/capabilities/service.py` | Active runtime posture | Publishes implemented feature/workflow readiness and must not list proposal narrative until deterministic readiness exists. |

## Non-Promotion Decision

RFC-0023 does not promote a `ProposalNarrativeEvidence`, `ProposalNarrative`, or
`proposal_narrative` data product in Slice 4.

The promotion remains blocked because:

1. no deterministic advisor-review narrative builder exists yet,
2. no persisted narrative version exists yet,
3. no narrative replay endpoint exists yet,
4. no review workflow exists for advisor, compliance, client-draft, or client-ready states,
5. no narrative source-input hash set exists yet,
6. no narrative guardrail result exists yet,
7. no report/render/archive lineage exists for client-ready artifacts.

Adding a domain-product declaration or trust telemetry fixture before those controls exist would
create a decorative mesh claim rather than implementation-backed product truth.

## Future Promotion Rule

A proposal narrative data product can be introduced only after an implementation slice proves all
minimum controls below:

| Control | Required evidence before promotion |
| --- | --- |
| Deterministic narrative readiness | Advisor-review narrative can be produced without AI dependency from allowed proposal evidence. |
| Source authority | Every narrative section carries source refs and input hashes for proposal version, artifact, decision summary, alternatives, risk, suitability, and limitations evidence where present. |
| Review state | Narrative response includes explicit review state and blocks client-ready posture until review controls exist. |
| Replay | Replay returns the exact persisted narrative evidence without model calls. |
| Guardrails | Unsupported claims, missing policy evidence, missing disclosures, and degraded dependencies return blocked or degraded state instead of polished unsafe text. |
| Trust telemetry | RFC-0087 trust telemetry fixture validates against the platform catalog and the declared product metadata. |
| `/platform/capabilities` | Capability row is emitted only when deterministic narrative is implemented and ready; AI-assisted and client-ready states remain gated until their own controls pass. |
| Wiki and supported features | Supported Features distinguishes deterministic advisor-review, AI-assisted draft, client-draft, and client-ready readiness. |

## `/platform/capabilities` Baseline

Slice 4 makes no `/platform/capabilities` response change. The endpoint must continue to omit:

1. `advisory.proposals.narrative`,
2. `advisory.proposals.client_ready_commentary`,
3. `advisory_proposal_narrative`,
4. `proposal_narrative`.

This is intentional. Consumers such as `lotus-gateway` and `lotus-workbench` must not discover
proposal narrative support until the Advise backend can produce implementation-backed narrative
state.

## Mesh and Trust Telemetry Baseline

No new trust telemetry fixture is added in this slice. Existing telemetry remains scoped to
`AdvisoryProposalLifecycleRecord`.

Future narrative telemetry must be separate from lifecycle telemetry because lifecycle state is
authoritative proposal workflow evidence, while proposal narrative is a derived commentary product
with stricter grounding, guardrail, review, replay, and client-disclosure controls.

## Supportability Policy

Until later slices promote deterministic readiness:

1. docs and wiki may describe proposal narrative only as planned RFC-0023 work,
2. `/platform/capabilities` must not advertise proposal narrative feature or workflow readiness,
3. domain-product declarations must not include a narrative product,
4. trust telemetry must not include a narrative fixture,
5. sales, demo, and pre-sales material must not claim client-ready proposal commentary support.

## Validation Evidence

This slice is pinned by tests that verify:

1. the Slice 4 closure document is indexed,
2. Supported Features remains non-claiming,
3. domain-product declarations do not contain a proposal narrative product,
4. trust telemetry remains tied only to implemented products,
5. `/platform/capabilities` does not expose narrative feature or workflow keys.

## Acceptance Gate

| Gate | Result |
| --- | --- |
| Repo-native domain-product gate passes when declarations change | No declarations changed; existing domain-product gate remains the required proof. |
| Trust telemetry and mesh certification pass where a product claim is made | No new product claim is made; existing telemetry tests remain scoped to implemented lifecycle product. |
| Capabilities and supported-features material do not overclaim AI-assisted or client-ready readiness | Pinned by docs and API regression tests. |

## Next Slice

RFC-0023 may proceed to Slice 5 only after this non-promotion baseline is merged to `main`.
Slice 5 should implement the first deterministic advisor-review narrative path without AI
dependency, then decide whether the resulting implementation is mature enough for a narrow
capability row or remains internal until persistence/replay is complete.
