# RFC-0026 Slice 10: Readiness, Execution, and House-View Actions

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 10 - report, archive, execution, and house-view readiness |
| **Status** | IMPLEMENTED - SOURCE-BACKED ADVISE READINESS SUPPORT |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |

## Decision

Slice 10 adds backend-owned cockpit actions for downstream readiness and source-owned tactical
impact without moving downstream system-of-record ownership into `lotus-advise`.

Implemented action families:

| Family | Source evidence | Owner role | Boundary |
| --- | --- | --- | --- |
| `REPORT_RENDER_ARCHIVE_BLOCKED` | Ready memo records missing report-package or archive refs | `REPORTING_OWNER` or `ARCHIVE_OWNER` | Does not claim completed report/render/archive or client-ready publication. |
| `EXECUTION_HANDOFF_READY` | `EXECUTION_READY` proposals without execution request events | `EXECUTION_OWNER` | Does not claim OMS order lifecycle ownership. |
| `EXECUTION_STATUS_ATTENTION` | Proposal execution workflow events | `EXECUTION_OWNER` | Renders downstream status without treating Advise as execution SOR. |
| `HOUSE_VIEW_IMPACT_REVIEW` | Persisted `TacticalHouseViewAffectedCohort:v1` source-product evidence | `PORTFOLIO_MANAGER` | Does not infer house-view impacts without source cohort evidence. |

## Implementation Evidence

| Area | Evidence |
| --- | --- |
| Report/archive readiness | `ReportRenderArchiveActionSource` and memo-derived `REPORT_PACKAGE_NOT_REQUESTED` / `ARCHIVE_REF_MISSING` projection. |
| Execution handoff readiness | `ExecutionHandoffReadyActionSource` from `EXECUTION_READY` proposals without execution request events. |
| Execution status attention | `ExecutionStatusAttentionActionSource` from batched proposal workflow events and `execution_status_for_event`. |
| Tactical house-view impact | `HouseViewImpactActionSource` projects persisted `TacticalHouseViewAffectedCohort:v1` evidence into `PORTFOLIO_MANAGER` queue items. |
| Source-product persistence | `record_tactical_house_view_affected_cohort` and `list_tactical_house_view_affected_cohorts` keep evaluated cohorts available for cockpit projection. |
| Performance-safe source reads | `list_events_for_proposals` in cockpit/proposal repository protocols and in-memory/Postgres adapters. |
| Boundary controls | Actions carry `CLIENT_READY_PUBLICATION` or `OMS_ORDER_LIFECYCLE` unsupported-capability boundaries where relevant. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py tests/unit/advisory/engine/test_engine_proposal_repository_in_memory.py tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py -q`
2. `python -m ruff check ...`
3. `python -m mypy src/core/advisor_cockpit/action_factory.py src/core/advisor_cockpit/source_read_model.py src/core/advisor_cockpit/repository.py src/core/advisor_cockpit/service.py src/core/proposals/repository.py src/infrastructure/proposals/in_memory.py src/infrastructure/proposals/postgres.py`
4. `git diff --check`

## Claim Boundary

This slice does not implement report rendering, archive storage, OMS orders, fills, settlement,
portfolio rebalancing, discretionary portfolio-management campaign creation, or unbacked house-view inference. It surfaces
source-backed readiness and attention actions for Gateway/Workbench rendering.
