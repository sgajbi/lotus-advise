# RFC-0024 Slice 2: Cleanup and Structure

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0024: Advisor Proposal Memo and Evidence Pack |
| **Slice** | 2 - cleanup and structure |
| **Status** | IMPLEMENTED - CLEANUP ONLY; NO MEMO SUPPORT PROMOTED |
| **Implemented Date** | 2026-05-23 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0024-slice2-cleanup-structure` |
| **Capability Posture** | This slice does not implement advisor proposal memo generation, memo APIs, memo persistence, memo report packages, data-product promotion, Gateway/Workbench memo surfaces, or client-ready memo publication. It cleans the report-handoff boundary before memo domain work begins. |

## Decision

RFC-0024 Slice 2 completes the first material cleanup required before memo implementation:
reviewed narrative report-package construction has moved from the API service layer to the proposal
domain/report-handoff layer.

The previous structure worked behaviorally, but it placed report-package business rules under
`src/api/services/proposal_report_narrative.py`. That made the API layer responsible for review
state validation, source-narrative hash continuity, section projection, lineage shaping, and
support-safe summary construction. Those are not controller or API-service responsibilities. They
are domain/report-handoff rules and are now owned by `src/core/proposals/report_narrative_package.py`.

This cleanup prevents RFC-0024 memo work from copying report-package logic into API facades or UI
helpers. Future memo report packages must follow the same direction: domain package builders and
support-safe summaries live in core proposal/memo modules; API services orchestrate only.

## Structural Change

| Boundary | Before Slice 2 | After Slice 2 | Why it matters for RFC-0024 |
| --- | --- | --- | --- |
| Reviewed narrative package builder | `src/api/services/proposal_report_narrative.py` | `src/core/proposals/report_narrative_package.py` | Keeps review-state, hash-continuity, source-lineage, section projection, and summary rules out of API services. |
| Report request API service | Imported API-local package builder and built report request payload | Imports core package builder and remains the orchestration boundary for proposal/version/status/replay reads plus report adapter call | Keeps controllers and API services thin enough for later memo domain/API/persistence split. |
| Tests | Coverage was mostly API-path and downstream adapter behavior | Added engine-level tests for report-package source-backed success, unapproved review blocking, hash-drift blocking, and support-safe summary shape | Moves risk coverage lower in the test pyramid before adding memo-specific report packages. |
| Memo support posture | No first-class memo package exists | Still no first-class memo package exists | Cleanup prepares the boundary without claiming advisor proposal memo support. |

## Removed Or Avoided Complexity

1. Removed API-local report narrative package business logic.
2. Avoided introducing a compatibility alias module under `src/api/services`; downstream code now
   imports the core owner directly.
3. Avoided adding memo placeholder modules before the memo domain contract exists.
4. Avoided duplicating report-package source-lineage and summary rules in tests by moving coverage
   to the core proposal package.

## Dedicated Boundary Direction For Later Memo Work

Slice 2 does not create memo modules yet because the memo contract is Slice 5. It does establish the
boundary rule later slices must follow:

| Future memo concern | Required module direction |
| --- | --- |
| Memo domain model and section builders | `src/core/proposals` or a dedicated `src/core/proposal_memos` package once Slice 5 defines the contract |
| Memo API routes and request validation | `src/api/proposals` route family, with no memo business logic in route functions |
| Memo persistence and replay | Dedicated persistence/read-model modules, not additions to controllers |
| Memo report handoff | Core memo/report-handoff package builders plus thin `lotus-report` adapter calls |
| Memo AI handoff | Core evidence packet/redaction builders plus thin `lotus-ai` adapter calls |
| Memo supportability | Core capability/readiness projection plus conservative `/platform/capabilities` promotion only after implementation-backed support exists |

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Stranded-truth reconciliation | `git fetch origin --prune` and `git branch -r --no-merged origin/main` returned no unmerged remote branches before Slice 2 implementation. |
| Cleanup and structure | Removed `src/api/services/proposal_report_narrative.py`; added `src/core/proposals/report_narrative_package.py`; updated `src/api/services/proposal_reporting_service.py` to import the core owner. |
| Test-pyramid strengthening | Added `tests/unit/advisory/engine/test_engine_proposal_report_narrative_package.py` to cover report-package source-backed success, unapproved review blocking, hash-drift blocking, and support-safe summary behavior at the core layer. |
| Non-claiming documentation | RFC index and wiki supported-feature posture record Slice 2 as cleanup-only and keep memo generation, APIs, persistence, report package, Gateway, Workbench, data-product, and client-ready memo claims planned. |
| Next-slice readiness | RFC-0024 may proceed to Slice 3 data-product and platform hardening with report-handoff business rules moved out of the API service layer. |

## Wiki And README Decision

Wiki source is updated because RFC implementation status and product-roadmap truth changed. README
does not change in this slice because command surfaces, runtime behavior, and supported feature
entrypoints did not change.
