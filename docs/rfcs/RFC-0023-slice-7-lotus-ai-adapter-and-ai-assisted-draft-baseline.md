# RFC-0023 Slice 7: Lotus-AI Adapter and AI-Assisted Draft Baseline

| Field | Value |
| --- | --- |
| RFC | RFC-0023 Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| Slice | 7 |
| Status | IMPLEMENTED - AI-ASSISTED ADVISOR-REVIEW DRAFT BASELINE |
| Capability Posture | Adds opt-in `AI_ASSISTED_DRAFT` generation for artifact-path `ADVISOR_REVIEW` proposal narrative through a narrow `lotus-ai` workflow-pack adapter. It remains draft-only and does not add standalone narrative endpoints, persistence, replay, review approval, compliance approval, client-draft, client-ready, report/render/archive, data-product, trust-telemetry, or `/platform/capabilities` promotion. |
| Implementation Date | 2026-05-22 |

## Purpose

Slice 7 introduces the first governed AI-assisted proposal narrative path without weakening the
Slice 5 deterministic grounding model or the Slice 6 policy and guardrail framework. The adapter
passes only a structured grounding packet, resolved narrative policy, requested section keys, source
references, and approved static instructions to `lotus-ai`.

This slice deliberately avoids user-supplied raw prompt execution. AI output is treated as an
advisor-review draft, is never client-ready, and is validated by the same unsupported-claim and
source-reference guardrails before the response is returned.

## Implementation

| Area | Evidence | Behavior |
| --- | --- | --- |
| Request contract | `src/core/advisory/narrative_models.py` | Adds `narrative_request.generation_mode` with `DETERMINISTIC_TEMPLATE` and `AI_ASSISTED_DRAFT`. |
| AI lineage contract | `src/core/advisory/narrative_models.py` | Adds adapter, workflow-pack, prompt-template, model, run, and fallback lineage to `proposal_narrative.ai_lineage`. |
| Lotus-AI adapter | `src/integrations/lotus_ai/proposal_narrative.py` | Calls `/platform/workflow-packs/execute` with structured context only and maps completed sections into draft response objects. |
| Artifact path integration | `src/core/advisory/narrative.py` | Uses deterministic sections as the source-reference backbone, substitutes validated AI text where available, and falls back deterministically when `lotus-ai` is unavailable. |
| Adapter tests | `tests/unit/advisory/api/test_lotus_ai_proposal_narrative.py` | Proves structured-context request shape, no raw prompt handoff, lineage mapping, and timeout/transport fallback. |
| API tests | `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py` | Proves AI-assisted draft success, deterministic fallback, and unsupported-claim guardrail blocking. |

## Supported Request Shape

`narrative_request` remains optional on the existing proposal artifact payload. Slice 7 adds the
explicit generation mode:

```json
{
  "narrative_request": {
    "audience": "ADVISOR_REVIEW",
    "generation_mode": "AI_ASSISTED_DRAFT",
    "jurisdiction": "SG",
    "sections": ["EXECUTIVE_SUMMARY"],
    "requested_by": "advisor_123"
  }
}
```

`AI_ASSISTED_DRAFT` requires `LOTUS_AI_BASE_URL` at runtime. If `lotus-ai` is unavailable,
times out, returns an incomplete run, or returns no usable sections, `lotus-advise` returns the
deterministic template output with `ai_lineage.fallback_reason`.

## Lotus-AI Boundary

The adapter submits:

1. `grounding_packet`,
2. `narrative_policy`,
3. requested section keys,
4. approved static instructions,
5. source references.

The adapter does not submit:

1. user-authored raw prompts,
2. arbitrary instruction text from the request,
3. unmanaged client-ready language,
4. unbounded proposal artifacts outside the grounding packet.

## Supported Response Shape

When AI draft generation succeeds, `proposal_narrative` includes:

1. `generation_mode=AI_ASSISTED_DRAFT`,
2. `review_state=DRAFT`,
3. AI-authored section text mapped onto deterministic source references,
4. `ai_lineage.workflow_run_id`,
5. `ai_lineage.model_version` when supplied by `lotus-ai`,
6. guardrail results after AI output validation.

When AI draft generation falls back, `proposal_narrative` includes:

1. `generation_mode=DETERMINISTIC_TEMPLATE`,
2. `review_state=DRAFT`,
3. deterministic section text,
4. `ai_lineage.fallback_reason=LOTUS_AI_NARRATIVE_UNAVAILABLE`,
5. no AI workflow run id.

## Guardrail Rules

AI-assisted draft sections reuse the Slice 6 guardrail framework. Unsupported claims such as
guaranteed returns, risk-free language, universal suitability, tax advice, or client-distribution
approval block the narrative with `BLOCKED_GUARDRAIL_FAILURE`.

AI draft text does not override missing evidence. If risk, suitability, alternatives, disclosure,
review, or report/archive evidence is missing, the response still carries the relevant limitations
and readiness blockers.

## Non-Promoted Behavior

This slice does not implement:

1. standalone narrative request/read/review/replay endpoints,
2. persisted narrative versions,
3. review approval or rejection actions,
4. compliance-review, client-draft, or client-ready narrative,
5. report/render/archive artifact inclusion,
6. `/platform/capabilities` narrative feature rows,
7. narrative data-product or trust-telemetry promotion,
8. demo-ready Workbench or report surfaces.

Those remain gated by later RFC-0023 slices.

## Validation Evidence

The implementation is pinned by:

1. adapter unit tests for structured-context handoff, lineage, and timeout fallback,
2. artifact API tests for AI-assisted draft success and deterministic fallback,
3. artifact API tests proving unsafe AI claims are blocked before response promotion,
4. RFC-0023 Slice 7 documentation contract tests,
5. existing OpenAPI, no-alias, API vocabulary, domain-product, trust-telemetry, and full unit gates.

## Acceptance Gate

| Gate | Result |
| --- | --- |
| No raw unmanaged prompt is sent to `lotus-ai` | Covered by adapter request-shape tests: request payload contains structured grounding context and approved instructions only. |
| Timeout and unavailable AI behavior is deterministic | Covered by adapter timeout masking and artifact-path fallback tests. |
| Unsupported AI claims are rejected | Covered by artifact-path AI draft test returning a guaranteed-return claim and receiving `BLOCKED_GUARDRAIL_FAILURE`. |
| AI-assisted output remains draft until review | Serialized as `review_state=DRAFT`; no client-ready promotion or review approval path is added. |

## Next Slice

RFC-0023 may proceed to Slice 8 after this slice is merged and validated. The next implementation
slice should add persistence, replay, and review lifecycle only if it can preserve deterministic
source authority, AI lineage, guardrail evidence, idempotency, and auditability end to end.
