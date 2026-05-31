# RFC-0026 Slice 4: Cockpit Domain Model and Vocabulary

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 4 - cockpit domain model and vocabulary |
| **Status** | IMPLEMENTED - SOURCE-BACKED ACTION CONSTRUCTION |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |
| **Capability Posture** | This slice implements pure Advise core action construction for cockpit action families. It does not expose cockpit APIs, persist action items, promote cockpit data products, add Gateway/Workbench surfaces, or claim runtime advisor-cockpit support. Those remain mandatory subsequent RFC-0026 slices. |

## Decision

RFC-0026 needs backend-owned action semantics before any API, Gateway, or Workbench surface is
safe to expose. Slice 4 adds that foundation in `src/core/advisor_cockpit/action_sources.py`
and `src/core/advisor_cockpit/action_factory.py`.

The factory is intentionally pure core code:

1. it depends only on cockpit models and vocabulary,
2. it constructs `AdvisoryActionItem` records from explicit source inputs,
3. it preserves source refs, evidence refs, lineage refs, dependency readiness, source-readiness
   gaps, reason codes, owner roles, SLA posture, and correlation ids,
4. it keeps unsupported capabilities visible instead of silently omitting them,
5. it returns stable sorted supported actions using the existing cockpit ordering helper.

This prevents Workbench or Gateway from reconstructing advisory suitability, memo, narrative,
policy, supportability, or priority semantics locally.

## Implemented Core Contracts

Slice 4 adds these construction inputs and helpers:

| Contract | Responsibility |
| --- | --- |
| `CockpitActionConstructionInput` | Generic source-backed construction input for every cockpit action family. |
| `CockpitActionSourceRefs` | Source refs carried into action items without presentation-layer inference. |
| `PolicyReviewActionSource` | Policy evaluation input for compliance-owned review actions. |
| `MemoPackageBlockedActionSource` | Memo evidence input for blocked proposal-memo package actions. |
| `MeetingPreparationActionSource` | Source-backed meeting-preparation input for advisor-owned ready actions. |
| `SupportabilityDegradedActionSource` | Dependency readiness input for degraded or unavailable source systems. |
| `UnsupportedCapabilityActionSource` | Explicit unsupported capability input for non-claimable cockpit behavior. |
| `build_source_backed_action` | Generic construction helper that rejects unexplained actions. |
| `build_policy_review_required_action` | Converts pending or blocked policy evaluation posture into a compliance review action. |
| `build_memo_package_blocked_action` | Converts memo evidence gaps into a blocked memo-package action. |
| `build_meeting_preparation_action` | Converts preparation packet evidence into an advisor-owned ready action. |
| `build_supportability_degraded_action` | Converts source dependency posture into a supportability action. |
| `build_unsupported_capability_action` | Converts unsupported capability posture into a visible blocked action. |
| `build_first_wave_cockpit_actions` | Aggregates the first implemented source families and returns deterministic priority order. |

## Source-Backed Behavior

The first implemented source constructors cover the cockpit-critical RFC-0023 through RFC-0025
consumption path:

1. policy evaluations with `PENDING_REVIEW` or `BLOCKED` posture produce
   `POLICY_REVIEW_REQUIRED`,
2. memo evidence blockers produce `MEMO_PACKAGE_BLOCKED`,
3. preparation packets produce `CLIENT_MEETING_PREPARATION`,
4. degraded or unavailable source systems produce `SUPPORTABILITY_DEGRADED`,
5. unsupported claims produce `UNSUPPORTED_CAPABILITY`.

The generic construction helper can construct every supported action family only when the caller
supplies reason codes plus evidence, readiness, dependency, or unsupported-capability context. This
keeps the vocabulary complete while avoiding fabricated action items.

## Boundary Controls

Slice 4 preserves the current non-promoting posture:

1. no API route is added,
2. no action-item persistence is added,
3. no acknowledgement write path is added,
4. no data product or trust telemetry is promoted,
5. `/platform/capabilities` remains unchanged,
6. Gateway and Workbench behavior remains unimplemented until their owning slices,
7. canonical `RFC26_ADVISOR_COCKPIT_CANONICAL` automation remains blocked until backend, Gateway,
   and Workbench runtime behavior exists.

This is not deferral outside RFC-0026. It is the required domain-construction step before runtime
snapshot/action APIs and downstream product surfaces can be implemented truthfully.

## Acceptance Evidence

| Gate | Evidence |
| --- | --- |
| Source-backed policy action | Tests prove `PENDING_REVIEW` policy evidence yields a compliance-owned review action, preserves lineage/correlation, and keeps client-ready publication blocked. |
| Source-backed memo action | Tests prove blocked memo evidence produces a reporting-owned action with memo evidence refs and readiness gaps. |
| Meeting-preparation action | Tests prove preparation packet evidence produces an advisor-owned ready action without UI inference. |
| Supportability action | Tests prove unavailable dependencies become blocking supportability actions. |
| Unsupported capabilities | Tests prove unsupported client-ready publication is visible as a blocked action. |
| Supported vocabulary coverage | Tests prove the generic source-backed builder can construct every supported action family only with source evidence and reason codes. |
| Stable ordering | Tests prove supported aggregation returns deterministic cockpit priority order. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py`
2. `python -m pytest tests/unit/test_rfc0026_slice4_domain_action_factory_contract.py`
3. `python -m ruff check .`
4. `python -m ruff format --check .`

## Next Slice Handoff

Slice 5 can now add source read models and performance-safe aggregation over proposals, policy
evaluations, memos, workspace state, report/package posture, execution posture, and supportability
sources. Runtime support remains unpromoted until the RFC-0026 API, persistence, Gateway,
Workbench, mesh, and canonical proof slices are implemented and validated.
