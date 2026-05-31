# RFC-0023 Slice 6: Narrative Policy, Disclosure, and Guardrail Framework

| Field | Value |
| --- | --- |
| RFC | RFC-0023 Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| Slice | 6 |
| Status | IMPLEMENTED - POLICY, DISCLOSURE, AND GUARDRAIL BASELINE |
| Capability Posture | Extends the Slice 5 artifact-path `ADVISOR_REVIEW` narrative with deterministic policy metadata, approved disclosure selection, unsupported-claim guardrails, and explicit client-ready blockers. It does not add standalone narrative endpoints, persistence, replay, review approval, AI-assisted generation, compliance approval, client-draft, client-ready, report/render/archive, data-product, trust-telemetry, or `/platform/capabilities` promotion. |
| Implementation Date | 2026-05-22 |

## Purpose

Slice 6 adds the control framework needed before any AI-assisted or client-ready narrative work can
start. The implementation remains intentionally narrow: the proposal artifact path can include
policy, disclosure, and guardrail evidence next to the deterministic advisor-review narrative, but
client-ready distribution is still blocked.

This slice improves the product by making narrative output auditable for private-banking review:
policy version, jurisdiction, product types, risk posture, selected disclosures, prohibited claim
patterns, guardrail outcomes, and client-ready blockers are explicit in the response.

## Implementation

| Area | Evidence | Behavior |
| --- | --- | --- |
| Narrative policy models | `src/core/advisory/narrative_models.py` | Adds policy context, disclosure, guardrail result, and narrative-policy response models. |
| Policy resolver | `src/core/advisory/narrative_policy.py` | Resolves jurisdiction, product types, risk posture, disclosure selection, prohibited claims, and client-ready blockers. |
| Guardrail framework | `src/core/advisory/narrative_policy.py` | Rejects unsupported deterministic claims and ungrounded sections. |
| Artifact path integration | `src/core/advisory/narrative.py` | Attaches `narrative_policy`, `disclosures`, and `guardrail_results` to the optional `proposal_narrative`. |
| API proof | `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py` | Proves SG equity/FX disclosure selection and client-ready blocking when disclosure policy is unavailable. |
| Guardrail proof | `tests/unit/advisory/engine/test_engine_proposal_narrative_policy.py` | Proves unsupported claims and missing source refs are rejected. |

## Supported Request Shape

`narrative_request` remains additive and optional on the existing proposal artifact payload.
Slice 6 adds policy inputs:

```json
{
  "narrative_request": {
    "audience": "ADVISOR_REVIEW",
    "jurisdiction": "SG",
    "product_types": ["EQUITY", "FX"],
    "client_audience": "ADVISOR_REVIEW",
    "sections": ["LIMITATIONS_AND_DISCLOSURES"]
  }
}
```

`client_audience=CLIENT_READY` is accepted only to return blocked policy evidence. It does not
promote client-ready narrative support.

## Supported Response Shape

When requested, `proposal_narrative` may now include:

1. `narrative_policy`,
2. `disclosures`,
3. `guardrail_results`.

`narrative_policy.policy_version` is `advisory-narrative-policy.2026-05`.
`proposal_narrative.policy_version` remains the deterministic template version.

## Disclosure Rules

Slice 6 supports deterministic disclosure selection for these initial policy jurisdictions:

1. `SG`,
2. `US`.

Disclosure selection considers:

1. request jurisdiction,
2. request product types,
3. product types derived from proposal shelf-entry evidence,
4. FX intent presence,
5. concentration-review risk posture,
6. policy audience.

Unsupported or missing jurisdictions do not invent disclosure text. They produce explicit
`disclosure_policy` missing evidence and block client-ready posture.

## Guardrail Rules

The guardrail framework rejects:

1. unsupported guaranteed-return claims,
2. risk-free claims,
3. broad suitability-for-all claims,
4. tax-advice claims,
5. approved-for-client-distribution claims,
6. sections without grounding source references.

The deterministic Slice 6 template path returns a pass result when no unsupported claim is found.
Future AI-assisted slices must reuse this framework before persistence or review promotion.

## Client-Ready Blocking

Slice 6 still blocks client-ready output. A `CLIENT_READY` policy request may return blockers such
as:

1. `CLIENT_READY_DISCLOSURE_POLICY_UNAVAILABLE`,
2. `CLIENT_READY_DISCLOSURES_NOT_SELECTED`,
3. `CLIENT_READY_NARRATIVE_RELEASE_NOT_SUPPORTED`.

The narrative status becomes `BLOCKED_POLICY_INCOMPLETE` when client-ready policy blockers are
present. This is blocked evidence, not client-ready support.

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

1. API tests for policy disclosure selection and client-ready blocking,
2. unit tests for unsupported-claim and source-reference guardrails,
3. RFC-0023 Slice 6 documentation contract tests,
4. existing OpenAPI, no-alias, API vocabulary, domain-product, trust-telemetry, and full unit gates.

## Acceptance Gate

| Gate | Result |
| --- | --- |
| Disclosure tests cover jurisdiction, product type, risk posture, and client audience | Covered by SG equity/FX policy-selection tests and explicit policy context assertions. |
| Guardrail tests reject unsupported claims | Covered by direct guardrail tests for guaranteed-return claims and missing source refs. |
| Missing disclosure policy blocks client-ready narrative | Covered by `CLIENT_READY` policy request with unsupported jurisdiction returning `BLOCKED_POLICY_INCOMPLETE`. |
| Policy versions are persisted | `narrative_policy.policy_version` and disclosure `policy_version` are serialized in the artifact-path narrative response and bound into the artifact hash. |

## Next Slice

RFC-0023 may proceed to Slice 7 after this slice is merged and validated. Slice 7 should integrate
the `lotus-ai` adapter narrowly, pass only grounding packet and approved policy instructions, and
run generated text through this guardrail framework before any draft posture is promoted.
