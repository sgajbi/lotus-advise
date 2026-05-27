# RFC-0027 Slice 4: Domain Model, Vocabulary, and Review State

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0027: Governed Advisory AI Copilot |
| **Slice** | 4 - copilot domain model, vocabulary, and review state |
| **Status** | IMPLEMENTED - PURE DOMAIN CONTRACT ONLY |
| **Implemented Date** | 2026-05-28 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0027-governed-advisory-ai-copilot` |
| **Capability Posture** | This slice strengthens the pure copilot domain contract. It does not build evidence packets from live sources, persist copilot runs, expose APIs, invoke `lotus-ai`, add Gateway routes, add Workbench surfaces, promote data products, or claim supported copilot runtime behavior. Those remain mandatory subsequent RFC-0027 slices. |

## Implementation Summary

Slice 4 extends `src/core/advisory_copilot/` with the vocabulary needed before evidence-packet,
guardrail, persistence, API, Gateway, Workbench, and canonical proof work begins.

The implemented domain contract now includes:

1. `CopilotEvidencePacket`,
2. `CopilotEvidencePacketSection`,
3. `CopilotSourceRef`,
4. `CopilotLineageRef`,
5. `CopilotUnsupportedEvidence`,
6. `CopilotUnsupportedEvidenceReason`,
7. `CopilotRetentionClass`.

Every evidence packet remains explicitly bounded to source refs, lineage refs, redacted sections,
unsupported-evidence posture, retention class, and `client_ready_publication = BLOCKED`.

## Review-State Boundary

The review model remains distinct from proposal lifecycle state, policy sign-off state, and
client-ready approval. First-wave review actions map only to copilot-output posture:

| Review action | Copilot posture |
| --- | --- |
| `APPROVE_FOR_INTERNAL_USE` | `APPROVED_FOR_INTERNAL_USE` |
| `REJECT` | `REJECTED` |
| `SUPERSEDE` | `SUPERSEDED` |
| `EXPIRE` | `EXPIRED` |

No review action can approve policy findings, approve client-ready publication, send external
client communication, create CRM tasks, or initiate OMS order lifecycle activity.

## Unsupported-Evidence Boundary

Unsupported-evidence posture is explicit and typed. The first-wave reasons are:

1. `SOURCE_NOT_IMPLEMENTED`,
2. `SOURCE_NOT_AVAILABLE`,
3. `RESTRICTED_BY_ROLE`,
4. `QUESTION_OUT_OF_SCOPE`,
5. `CLIENT_READY_PUBLICATION_BLOCKED`,
6. `POLICY_APPROVAL_NOT_AVAILABLE`,
7. `AI_UNAVAILABLE`.

These reason codes are for deterministic system behavior, not user-facing jargon. Business-facing
messages must remain private-banking oriented and must not expose raw prompts, provider details,
trace IDs, correlation IDs, or run-ledger mechanics.

## Tests

| Test | Coverage |
| --- | --- |
| `tests/unit/advisory/engine/test_engine_advisory_copilot_foundation.py::test_copilot_evidence_packet_shape_preserves_review_and_lineage_boundaries` | Verifies evidence packet shape, source ref content hash, unsupported-evidence reason, lineage ref, retention class, and blocked client-ready posture. |

## Next Slice Readiness

RFC-0027 may proceed to Slice 5 evidence packet, redaction, and projection policies. Slice 5 must
build deterministic evidence packets from source-backed RFC-0023 through RFC-0026 records, prove
restricted fields are excluded, and preserve missing evidence as explicit unsupported posture.

