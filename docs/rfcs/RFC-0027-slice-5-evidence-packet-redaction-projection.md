# RFC-0027 Slice 5: Evidence Packet, Redaction, and Projection Policies

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0027: Governed Advisory AI Copilot |
| **Slice** | 5 - evidence packet, redaction, and projection policies |
| **Status** | IMPLEMENTED - PURE EVIDENCE-PACKET BUILDER ONLY |
| **Implemented Date** | 2026-05-28 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0027-governed-advisory-ai-copilot` |
| **Capability Posture** | This slice adds the pure evidence-packet projection builder. It does not read live proposal, memo, policy, cockpit, report, or operations sources; persist evidence packets or runs; invoke `lotus-ai`; expose APIs; add Gateway routes; add Workbench surfaces; promote data products; seed `RFC27_ADVISORY_COPILOT_CANONICAL`; or claim supported copilot runtime behavior. Those remain mandatory subsequent RFC-0027 slices. |

## Implementation Summary

Slice 5 adds deterministic evidence-packet projection support in
`src/core/advisory_copilot/evidence_packets.py`.

The builder:

1. accepts already source-projected `CopilotEvidenceSectionInput` records,
2. orders sections by the required action-family evidence map,
3. includes only sections allowed for the requested audience,
4. emits `RESTRICTED_BY_ROLE` unsupported-evidence records for restricted sections,
5. emits `SOURCE_NOT_AVAILABLE` unsupported-evidence records for missing required sections,
6. preserves source refs and content hashes supplied by source authorities,
7. adds a packet lineage ref owned by `lotus-advise`,
8. computes a deterministic `sha256:` evidence-packet hash,
9. rejects business-copy leakage of raw prompt, provider response, trace ID, correlation ID, run
   ledger, or raw payload details,
10. keeps `client_ready_publication` blocked.

This is intentionally a pure builder. It does not fetch source records, infer missing evidence, call
`lotus-ai`, or hide source gaps.

## Tests

| Test | Coverage |
| --- | --- |
| `test_copilot_evidence_packet_builder_projects_allowed_sections_and_hashes` | Proves deterministic packet hashes, projected source-backed sections, missing-source unsupported posture, lineage refs, and blocked client-ready posture. |
| `test_copilot_evidence_packet_builder_restricts_sections_by_audience` | Proves role-aware projection excludes restricted sections and returns explicit `RESTRICTED_BY_ROLE` posture. |
| `test_copilot_evidence_packet_builder_rejects_technical_copy_leakage` | Proves business-facing evidence text rejects raw prompt leakage before API/UI/report exposure. |

## Boundary

Slice 5 does not yet connect to RFC-0023, RFC-0024, RFC-0025, or RFC-0026 repositories/read models.
That source aggregation belongs in later implementation slices once the evidence packet builder,
guardrail engine, persistence, and API boundaries are stable. This is not day-2 or wave-2 deferral;
it is staged implementation inside RFC-0027.

## Next Slice Readiness

RFC-0027 may proceed to Slice 6 guardrail and unsupported-evidence engine. Slice 6 can reuse the
packet builder's explicit unsupported-evidence posture and technical-copy leakage rejection.

