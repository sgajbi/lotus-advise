# RFC-0027 Slice 6: Guardrail and Unsupported-Evidence Engine

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0027: Governed Advisory AI Copilot |
| **Slice** | 6 - guardrail and unsupported-evidence engine |
| **Status** | IMPLEMENTED - PURE GUARDRAIL ENGINE ONLY |
| **Implemented Date** | 2026-05-28 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0027-governed-advisory-ai-copilot` |
| **Capability Posture** | This slice adds pure guardrail evaluation. It does not invoke `lotus-ai`, persist runs, expose APIs, add Gateway routes, add Workbench surfaces, promote data products, seed canonical proof data, or claim supported copilot runtime behavior. Those remain mandatory subsequent RFC-0027 slices. |

## Implementation Summary

Slice 6 extends `src/core/advisory_copilot/guardrails.py` with
`evaluate_copilot_guardrails`. The evaluator returns stable reason codes for:

1. autonomous advice or recommendation selection,
2. trade or order generation,
3. policy approval or waiver attempts,
4. client-ready publication or external client communication wording,
5. missing source refs,
6. prompt-injection markers,
7. sensitive technical leakage such as raw prompts, provider responses, trace IDs, correlation IDs,
   or raw payload references.

The function is pure and deterministic. It accepts already-classified requested intents,
source-ref posture, user instruction text, and output text. It does not call model providers and it
does not inspect unrestricted source payloads.

## Tests

| Test | Coverage |
| --- | --- |
| `test_copilot_guardrail_evaluator_rejects_unsafe_requests_and_outputs` | Proves forbidden intents, missing source refs, prompt injection, client-ready wording, and sensitive output leakage return stable reason codes. |
| `test_copilot_guardrail_evaluator_allows_source_backed_review_request` | Proves a source-backed advisor-review request with safe output returns no guardrail finding. |

## Boundary

Slice 6 is still pre-runtime. It does not yet attach guardrail results to persisted copilot runs,
audit events, `lotus-ai` workflow-pack execution, Gateway responses, Workbench UI, or canonical live
proof. That attachment belongs in later RFC-0027 slices and remains mandatory before any supported
copilot claim is promoted.

## Next Slice Readiness

RFC-0027 may proceed to Slice 7 `lotus-ai` workflow-pack integration and model-risk controls. Slice
7 must use this guardrail foundation to block unsafe requests before workflow-pack execution and to
validate outputs before advisor/reviewer exposure.

