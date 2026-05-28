# RFC-0027 Slice 7: lotus-ai Workflow-Pack and Model-Risk Controls

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0027: Governed Advisory AI Copilot |
| **Slice** | 7 - lotus-ai workflow-pack integration and model-risk controls |
| **Status** | IMPLEMENTED - ADAPTER AND WORKFLOW-PACK EXECUTION SEAM ONLY |
| **Implemented Date** | 2026-05-28 |
| **Owner** | `lotus-advise` and `lotus-ai` |
| **Implementation Branch** | `rfc0027-governed-advisory-ai-copilot` |
| **Capability Posture** | This slice adds the governed `lotus-ai` execution seam for RFC-0027 copilot evidence packets. It does not expose Advise copilot APIs, persist copilot runs in Advise, add Gateway routes, add Workbench surfaces, seed canonical live proof, promote data products, or claim advisor-facing copilot product support. |

## Implementation Summary

Slice 7 implements the cross-repository AI execution boundary:

1. `lotus-ai` registers six pilot-scoped review-gated workflow packs:
   - `advisory_copilot_proposal_explanation.pack@v1`
   - `advisory_copilot_evidence_qa.pack@v1`
   - `advisory_copilot_meeting_preparation.pack@v1`
   - `advisory_copilot_compliance_review_summary.pack@v1`
   - `advisory_copilot_operations_report_handoff.pack@v1`
   - `advisory_copilot_client_follow_up_draft.pack@v1`
2. `lotus-ai` validates Advise-owned evidence packets, source refs, model-risk controls,
   review-required posture, blocked client-ready posture, unsupported claims, bounded requested
   outputs, and forbidden technical fields before run, audit, queue, or task-flow side effects.
3. `lotus-advise` adds `src/integrations/lotus_ai/advisory_copilot.py`, which calls only
   `/platform/workflow-packs/execute`.
4. The adapter sends bounded evidence packets and approved model-risk control refs only. It does
   not send raw prompts, raw payloads, provider responses, trace IDs, or correlation IDs inside the
   model input payload.
5. The adapter fails closed:
   - unsafe requested intent or prompt-injection posture returns `GUARDRAIL_REJECTED` before calling
     `lotus-ai`,
   - unavailable, disabled, non-completed, or transport-failed `lotus-ai` returns deterministic
     `UNAVAILABLE`,
   - unsafe output wording returns `GUARDRAIL_REJECTED` and hides generated sections.

## Model-Risk Controls

Every Advise copilot workflow-pack request carries:

1. adapter version: `advisory-copilot-lotus-ai-adapter.v1`,
2. approved instruction set: `advisory-copilot-instructions.v1`,
3. prompt-template version: `advisory-copilot-prompt-template.v1`,
4. output-schema version: `advisory-copilot-output-schema.v1`,
5. evaluation-pack ref: `advisory-copilot-eval-pack.v1`,
6. evidence-packet hash lineage.

These are lineage and review controls, not client-facing product copy.

## Tests

| Test | Coverage |
| --- | --- |
| `tests/unit/advisory/api/test_lotus_ai_advisory_copilot.py` | Advise adapter request shape, no raw prompt/instruction payload, Singapore tenant propagation, successful review-required draft, preflight guardrail rejection, output guardrail rejection, unavailable fallback, and transport-failure fallback. |
| `lotus-ai/tests/unit/test_workflow_pack_execution.py` | Registered pack execution, review-gated output, model-risk fields, and forbidden client output rejection before side effects. |
| `lotus-ai/tests/unit/test_workflow_pack_registry.py` and route-contract tests | Registry, binding, queue-policy, supportability, runtime-status, and wiki-backed route posture for the six copilot packs. |

## Boundary

Slice 7 proves the AI execution boundary only. Advise still needs later RFC-0027 slices for copilot
run persistence, review/audit/retention, certified APIs/OpenAPI, Gateway routes, Workbench product
surface, canonical seed/live proof, data-product promotion, and supported-features promotion.

No client-ready publication, policy approval, waiver, OMS/order action, external client
communication, or complete demo/RFP readiness is claimed by this slice.
