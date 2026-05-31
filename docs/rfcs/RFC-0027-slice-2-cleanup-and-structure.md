# RFC-0027 Slice 2: Cleanup and Structure

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0027: Governed Advisory AI Copilot |
| **Slice** | 2 - cleanup and structure |
| **Status** | IMPLEMENTED - DOMAIN FOUNDATION ONLY |
| **Implemented Date** | 2026-05-28 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0027-governed-advisory-ai-copilot` |
| **Capability Posture** | This slice creates the copilot domain foundation. It does not expose copilot APIs, persist evidence packets or runs, invoke `lotus-ai`, add Gateway routes, add Workbench copilot surfaces, promote data products, seed `RFC27_ADVISORY_COPILOT_CANONICAL`, or claim supported copilot runtime behavior. Those remain mandatory subsequent RFC-0027 slices. |

## Implementation Summary

Slice 2 adds a first-class `src/core/advisory_copilot/` package so copilot semantics do not leak
into controllers, infrastructure adapters, existing proposal narrative code, memo code, policy-pack
code, advisor-cockpit code, or Workbench UI logic.

The package establishes:

1. a typed supported action catalog for the six supported RFC-0027 action families,
2. private-banking audience, source-dependency, evidence-access, review-posture, and client-ready
   posture vocabulary,
3. deterministic evidence-section requirements for each action family,
4. stable forbidden-intent guardrail reason codes,
5. review-action to review-posture mapping,
6. `lotus-ai` workflow-pack boundary metadata without provider calls,
7. business-facing projection labels that avoid prompt, provider, trace, correlation, and run-ledger
   leakage.

## Files Added

| File | Responsibility |
| --- | --- |
| `src/core/advisory_copilot/models.py` | Pydantic models and typed vocabulary for action definitions and business projections. |
| `src/core/advisory_copilot/catalog.py` | First-wave action catalog for proposal explanation, evidence Q&A, meeting preparation, compliance review summary, operations/report handoff, and client follow-up draft. |
| `src/core/advisory_copilot/evidence_packets.py` | Source dependency to evidence-section map and action-specific required evidence sections. |
| `src/core/advisory_copilot/guardrails.py` | Stable forbidden-intent reason-code map for later guardrail execution. |
| `src/core/advisory_copilot/projection.py` | Business-facing action labels, summaries, and review action labels safe for UI, wiki, reports, and commercial material. |
| `src/core/advisory_copilot/review.py` | Review actions, derived review postures, and terminal-review posture helper. |
| `src/core/advisory_copilot/workflow_pack.py` | Workflow-pack boundary metadata that keeps execution authority in `lotus-ai` and caller authority in `lotus-advise`. |
| `src/core/advisory_copilot/__init__.py` | Public package exports for later slices. |

## Boundary Decisions

| Boundary | Decision |
| --- | --- |
| Workspace rationale | Existing workspace-rationale endpoints and `workspace_rationale.pack@v1` remain separate. RFC-0027 does not stretch that route into broad copilot behavior. |
| Proposal narrative | RFC-0027 consumes RFC-0023 narrative lineage but does not duplicate proposal narrative generation. |
| Proposal memo | RFC-0027 consumes RFC-0024 memo evidence but does not own memo build, report request, render, or archive truth. |
| Policy packs | RFC-0027 consumes RFC-0025 policy evidence but does not satisfy, waive, approve, or mutate policy outcomes. |
| Advisor cockpit | RFC-0027 consumes RFC-0026 cockpit actions and preparation packets but does not own action priority, SLA, acknowledgement, or workflow state. |
| `lotus-ai` | `lotus-ai` remains workflow-pack execution authority. Slice 2 defines package identifiers only; it does not call model providers or introduce prompt construction. |
| Gateway and Workbench | No Gateway or Workbench route is introduced in this slice. Later slices must consume certified Advise APIs through Gateway only. |
| Client-ready posture | Every supported action is review-required and client-ready publication is `BLOCKED`. |

## Tests

| Test | Coverage |
| --- | --- |
| `tests/unit/advisory/engine/test_engine_advisory_copilot_foundation.py` | Verifies the six action families, source dependencies, workflow-pack boundary, required evidence sections, forbidden-intent reason codes, review postures, and business-facing projection copy. |

The tests deliberately check that business-facing labels do not leak terms such as workflow-pack,
provider, prompt, correlation, trace, run ledger, or raw payload.

## Rejected Cleanup

No tracked `__pycache__` or `.pyc` files were present. Existing workspace rationale, proposal
narrative, proposal memo AI commentary, and policy AI evidence paths are implementation-backed
scope from earlier RFCs, so they were not removed or renamed in this slice.

## Next Slice Readiness

RFC-0027 may proceed to Slice 3 data-product and platform hardening. The candidate
`AdvisoryCopilotInteractionRecord:v1` remains unpromoted until runtime evidence, persistence,
trust telemetry, `/platform/capabilities`, Gateway/Workbench consumption, canonical proof, and
documentation are implemented and validated.

