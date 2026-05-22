# RFC-0023 Slice 5: Grounding Packet and Deterministic Template Baseline

| Field | Value |
| --- | --- |
| RFC | RFC-0023 Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| Slice | 5 |
| Status | IMPLEMENTED - DETERMINISTIC ADVISOR-REVIEW BASELINE |
| Capability Posture | Supports opt-in deterministic `ADVISOR_REVIEW` proposal narrative inside the proposal artifact path only. It does not add standalone narrative endpoints, persistence, replay, AI-assisted generation, compliance approval, client-draft, client-ready, report/render/archive, or `/platform/capabilities` promotion. |
| Implementation Date | 2026-05-22 |

## Purpose

Slice 5 introduces the first implementation-backed RFC-0023 narrative capability. It is deliberately
small: callers may request deterministic advisor-review narrative while building a proposal
artifact. The output is generated from a bounded grounding packet over existing proposal artifact,
decision-summary, risk-lens, suitability, alternatives, assumptions, and evidence-hash fields.

The implementation does not call `lotus-ai` or any model provider. This keeps the first narrative
surface auditable, deterministic, and safe to review before AI-assisted draft generation is added in
later slices.

## Implementation

| Area | Evidence | Behavior |
| --- | --- | --- |
| Narrative request and response models | `src/core/advisory/narrative_models.py` | Adds `ProposalNarrativeRequest`, `ProposalNarrativeGroundingPacket`, `ProposalNarrative`, source refs, sections, and explicit missing-evidence models. |
| Grounding packet builder | `src/core/advisory/narrative.py` | Extracts only allowed deterministic artifact facts and source refs; records request and artifact hashes where available. |
| Deterministic template renderer | `src/core/advisory/narrative.py` | Renders stable advisor-review sections without AI dependency. |
| Artifact path exposure | `src/core/models.py`, `src/core/advisory/artifact.py`, `src/core/advisory/artifact_models.py` | `narrative_request` on the simulation/artifact payload returns optional `proposal_narrative` on the artifact response. |
| API proof | `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py` | Proves explicit request, selected sections, deterministic template mode, source hashes, and missing evidence. |

## Supported Request Shape

`narrative_request` is additive and optional on the existing simulation/artifact payload:

```json
{
  "narrative_request": {
    "audience": "ADVISOR_REVIEW",
    "sections": [
      "EXECUTIVE_SUMMARY",
      "RISK_AND_CONCENTRATION",
      "ALTERNATIVES_CONSIDERED"
    ],
    "requested_by": "advisor_123"
  }
}
```

Only `ADVISOR_REVIEW` and `DETERMINISTIC_TEMPLATE` are supported in Slice 5.

## Supported Response Shape

The artifact response may include `proposal_narrative` when requested:

1. `narrative_id`,
2. `status`,
3. `audience`,
4. `generation_mode`,
5. `review_state`,
6. `policy_version`,
7. `grounding_packet`,
8. ordered `sections`,
9. explicit `limitations`.

`review_state` is always `DRAFT` in Slice 5. Client-ready approval is not implemented.

## Grounding Rules

The grounding packet may include only:

1. artifact status, objective tags, gate decision, and recommended next step,
2. proposal result status,
3. proposal decision summary status, reason code, material-change count, and next action,
4. risk-lens status, summary, and highlights,
5. suitability issue counts and highest severity,
6. alternatives counts and selected alternative id where alternatives exist,
7. trade and FX intent counts,
8. deterministic cash and drift takeaways,
9. assumptions, limits, and risk disclaimer,
10. request and artifact hashes.

The grounding packet must not include unrestricted raw internal data, free-form prompt text,
client-ready approval claims, model output, or UI-generated narrative.

## Missing Evidence

Slice 5 always records blockers for client-ready use:

1. `mandate_policy`,
2. `disclosure_policy`,
3. `review_workflow`,
4. `report_archive_lineage`.

It also records unavailable runtime evidence such as:

1. `risk_lens`,
2. `suitability`,
3. `alternatives`.

Missing evidence is visible in `limitations` and section-level `limitation_refs`.

## Non-Promoted Behavior

This slice does not implement:

1. standalone narrative request/read/review/replay endpoints,
2. persisted narrative versions,
3. review approval or rejection actions,
4. AI-assisted generation,
5. compliance-review, client-draft, or client-ready narrative,
6. report/render/archive artifact inclusion,
7. `/platform/capabilities` narrative feature rows,
8. narrative data-product or trust-telemetry promotion.

Those remain gated by later RFC-0023 slices.

## Validation Evidence

The implementation is pinned by:

1. API tests for artifact-path narrative generation,
2. RFC-0023 Slice 5 documentation contract tests,
3. existing OpenAPI, no-alias, API vocabulary, domain-product, trust-telemetry, and full unit gates.

## Acceptance Gate

| Gate | Result |
| --- | --- |
| Unit tests prove grounding packet contains only allowed evidence | Covered by artifact-path narrative test assertions and docs contract. |
| Missing evidence is explicit | `limitations` and `limitation_refs` expose client-ready and unavailable-evidence blockers. |
| Deterministic template produces stable output | Repeated artifact narrative requests produce stable deterministic section output. |
| No model calls are needed for baseline narrative | `generation_mode=DETERMINISTIC_TEMPLATE`; no `lotus-ai` adapter is used. |

## Next Slice

RFC-0023 may proceed to Slice 6 after this slice is merged and validated. Slice 6 should add
narrative policy, disclosure selection, and guardrail framework behavior before any client-draft or
client-ready posture is promoted.
