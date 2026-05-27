# RFC-0026 Slice 2: Cleanup and Structure

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 2 - cleanup and structure |
| **Status** | IMPLEMENTED - COCKPIT CORE PACKAGE ESTABLISHED |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |
| **Capability Posture** | This slice establishes the backend cockpit domain package and tests. It does not expose cockpit APIs, persist action items, promote cockpit data products, add Gateway/Workbench surfaces, or claim supported advisor-cockpit runtime behavior. Those remain mandatory subsequent RFC-0026 slices. |

## Outcome

Slice 2 creates the dedicated `src/core/advisor_cockpit/` package before API or UI work begins.
This keeps cockpit semantics out of proposal controllers, Workbench code, and Gateway adapters.

Implemented structure:

1. `src/core/advisor_cockpit/models.py`
   defines typed cockpit contracts for caller context, evidence refs, lineage refs,
   source-readiness gaps, dependency readiness, acknowledgement state, advisory action items,
   action-item pages, meeting-preparation packets, and cockpit snapshots.
2. `src/core/advisor_cockpit/vocabulary.py`
   defines deterministic priority, SLA, status, and action-family ordering plus a stable action
   sort helper.
3. `src/core/advisor_cockpit/pagination.py`
   pins the RFC-0026 page-size defaults: default 25, maximum 100.
4. `src/core/advisor_cockpit/__init__.py`
   exports only the domain contracts and helpers needed by subsequent RFC-0026 slices.

No existing proposal, memo, policy, workspace, Gateway, or Workbench behavior is changed in this
slice.

## Cleanup and Structure Decisions

| Area | Decision |
| --- | --- |
| Package boundary | Cockpit domain code lives under `src/core/advisor_cockpit/`, not under proposal controllers, workspace API services, Gateway, or Workbench. |
| Naming | Public model names use `AdvisorCockpit*`, `AdvisoryActionItem*`, and `Cockpit*` prefixes to avoid generic task-board language. |
| Vocabulary | Status, priority, owner role, SLA, action-family, evidence-access, dependency, and unsupported-capability values are typed in one module. |
| Sorting | The first deterministic ordering helper implements the RFC-0026 stable order: priority, due time, SLA aging, materiality, status, action family, then action id. |
| Pagination | Page-size defaults are centralized before API implementation so list endpoints cannot diverge. |
| Entitlement posture | `CockpitCallerContext` is a server-side model. Workbench must receive projected cockpit data rather than infer permissions locally. |
| Unsupported claims | Unsupported capabilities are explicit model values, including client-ready publication, external client communication, CRM/calendar ownership, OMS order lifecycle, completed policy approval/sign-off authority, and full RFC-0028 demo/RFP packaging. |

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Dedicated cockpit module | `src/core/advisor_cockpit/` now contains domain models, vocabulary, and pagination helpers. |
| No UI/API leakage | `tests/unit/advisory/engine/test_engine_advisor_cockpit_models.py` asserts the core package has no `src.api`, `src.integrations`, or `src.infrastructure` dependency. |
| Private-banking vocabulary | Model-schema tests assert business-facing wording and unsupported-capability boundaries. |
| Deterministic ordering | Unit tests assert stable cockpit action ordering by priority, due time, SLA, materiality, status, action family, and action id. |
| Pagination defaults | Unit tests assert default page size 25 and max page size 100. |
| Non-claiming posture | No router, capability flag, data-product declaration, Gateway route, Workbench surface, or live seed is added in this slice. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_models.py`
2. `python -m ruff check src/core/advisor_cockpit tests/unit/advisory/engine/test_engine_advisor_cockpit_models.py`
3. `python -m ruff format --check src/core/advisor_cockpit tests/unit/advisory/engine/test_engine_advisor_cockpit_models.py`

## Next Slice Handoff

Slice 3 may add data-product posture only when it remains non-promoting until runtime behavior
exists. Slice 4 can build on the new domain package to complete first-wave action-family
semantics, priority vocabulary, and source-backed action construction.
