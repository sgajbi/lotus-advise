# RFC-0023 Slice 2: Cleanup and Structure

| Field | Value |
| --- | --- |
| **RFC** | RFC-0023 Grounded Advisory AI Narrative and Client-Ready Proposal Commentary |
| **Slice** | 2 |
| **Status** | IMPLEMENTED - CLEANUP AND STRUCTURE ONLY |
| **Implemented On** | 2026-05-22 |
| **Primary Repo** | `lotus-advise` |
| **Capability Posture** | This slice does not implement generated proposal narrative. It cleans the workspace-rationale boundary and removes one premature client-ready artifact claim before narrative contract work starts. |

## Outcome

Slice 2 tightened the existing narrative-adjacent surface before any proposal narrative endpoint,
model, persistence, or AI adapter is added.

The implemented change separates workspace-rationale evidence construction from API orchestration:

1. `src/core/workspace/assistant_evidence.py` now owns the deterministic workspace evidence packet
   used by the existing workspace AI rationale seam.
2. `src/api/services/workspace_ai_service.py` now remains a thin orchestration layer that loads the
   workspace, delegates evidence construction, and calls the bounded `lotus-ai` adapter.
3. `src/api/main.py` no longer describes advisory simulation as generating a "client-ready
   artifact"; OpenAPI now says the simulation endpoints generate deterministic proposal evidence.

This preserves the Slice 0 boundary: workspace rationale is supported, but proposal narrative and
client-ready commentary remain future RFC-0023 work.

## Boundary Decisions

| Boundary | Slice 2 decision |
| --- | --- |
| Domain evidence | Workspace assistant evidence belongs in `src/core/workspace/assistant_evidence.py`, not in API route or service facades. |
| API orchestration | API services may retrieve sessions, translate exceptions, and call adapters, but they must not own narrative business rules. |
| AI adapter | The existing `lotus-ai` workspace-rationale adapter remains specific to `workspace_rationale.pack`; it is not reused as proposal narrative. |
| Proposal narrative | No `proposal_narrative` endpoint, persistence model, capability row, or supported-feature claim is added in this slice. |
| Client-ready wording | Client-ready wording is removed from the simulation OpenAPI tag until policy, disclosure, review, report/render/archive, and replay gates exist. |
| Documentation | RFC, README index, and wiki source stay layered: Slice 2 closure is indexed, while supported-features remains conservative. |

## Cleanup Performed

1. Extracted deterministic workspace assistant evidence construction into a core workspace module.
2. Reduced `workspace_ai_service` responsibility to orchestration and exception translation.
3. Corrected OpenAPI tag language that could be read as a supported client-ready artifact claim.
4. Added boundary tests proving the workspace AI service delegates evidence construction and does
   not present workspace rationale as proposal narrative.
5. Added behavior tests for evidence readiness and deterministic evidence fields.

## Retained With Rationale

| Item | Rationale |
| --- | --- |
| Existing workspace rationale route | It is already implementation-backed, separately documented, and explicitly scoped to workspace rationale rather than proposal narrative. |
| Existing `lotus-ai` rationale adapter name and workflow pack | Renaming it in Slice 2 would add churn without implementing proposal narrative. Proposal narrative will need its own bounded contract in later slices. |
| Existing proposal lifecycle service structure | The service is already split across read-model, command, persistence, reporting, async, and projection modules. Slice 2 does not add narrative logic to it. |

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Thin API service | `tests/unit/advisory/contracts/test_rfc0023_slice2_boundaries.py` verifies `workspace_ai_service` imports the core evidence builder and does not construct `WorkspaceAssistantEvidence` directly. |
| Workspace evidence behavior | `tests/unit/advisory/api/test_workspace_assistant_evidence.py` verifies evidence requires evaluated workspace state and carries deterministic workspace fields. |
| No proposal-narrative overclaim | `tests/unit/advisory/contracts/test_rfc0023_slice2_boundaries.py` verifies workspace rationale OpenAPI text does not claim proposal narrative or client-ready output. |
| OpenAPI client-ready cleanup | `tests/unit/advisory/contracts/test_rfc0023_slice2_boundaries.py` verifies the advisory simulation tag says deterministic proposal evidence, not client-ready artifact. |
| Targeted local tests | `python -m pytest tests/unit/advisory/api/test_workspace_assistant_evidence.py tests/unit/advisory/contracts/test_rfc0023_slice2_boundaries.py tests/unit/advisory/api/test_lotus_ai_rationale.py -q` passed with `20 passed`. |
| Targeted lint | `python -m ruff check src/core/workspace/assistant_evidence.py src/api/services/workspace_ai_service.py tests/unit/advisory/api/test_workspace_assistant_evidence.py tests/unit/advisory/contracts/test_rfc0023_slice2_boundaries.py` passed. |

## README And Wiki Decision

README/wiki source changes are required because Slice 2 changes RFC closure truth and corrects
feature posture around narrative-adjacent surfaces.

Supported Features remains deliberately non-claiming:

1. workspace rationale remains the only implemented AI-facing advisory seam,
2. generated proposal narrative remains planned,
3. client-ready commentary remains blocked until later slices implement policy, review, report,
   archive, Gateway, Workbench, and proof requirements.

## Next Slice

RFC-0023 may proceed to Slice 3 current-state assessment and narrative contract baseline after
Slice 2 is merged, CI is green, wiki publication is complete, and branch hygiene is clean.
