# RFC-0026 Slice 9: Supervisory, Approval, and Compliance Queues

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0026: Advisor Cockpit Operating Workflow |
| **Slice** | 9 - supervisory, approval, and compliance work queues |
| **Status** | IMPLEMENTED - SOURCE-BACKED ADVISE QUEUE SUPPORT |
| **Implemented Date** | 2026-05-27 |
| **Owner** | `lotus-advise` |
| **Implementation Branch** | `rfc0026-advisor-cockpit-gold-standard` |

## Decision

Slice 9 surfaces proposal lifecycle approval and consent dependencies as backend-owned cockpit
queue items. The cockpit does not grant approval, waiver, sign-off, or client-ready authority; it
shows source-backed queue posture with deterministic owner, reason-code, SLA, evidence, and
unsupported-capability metadata.

Implemented queue projection:

| Proposal state | Approval dependency | Action family | Owner role |
| --- | --- | --- | --- |
| `RISK_REVIEW` | `RISK` | `APPROVAL_DEPENDENCY_AGING` | `INVESTMENT_DESK` |
| `COMPLIANCE_REVIEW` | `COMPLIANCE` | `APPROVAL_DEPENDENCY_AGING` | `COMPLIANCE_REVIEWER` |
| `AWAITING_CLIENT_CONSENT` | `CLIENT_CONSENT` | `CLIENT_CONSENT_REQUIRED` | `ADVISOR` |

Completed source approvals suppress queue items. Rejected source approvals produce blocked,
critical-priority queue items with explicit remediation posture.

Caller-role projection is enforced in the Advise service before pagination:

1. `ADVISOR` and `DESK_HEAD` views keep the full portfolio-scoped blocker set visible so advisors
   can see external-owner blockers without completing them locally.
2. `COMPLIANCE_REVIEWER`, `INVESTMENT_DESK`, `OPERATIONS`, `DPM_OWNER`, and other non-advisor
   roles receive owner-role queues plus system posture items.
3. A caller role cannot use the generic action list to retrieve another owner queue and then
   acknowledge the item as if it were advisor-owned.

## Implementation Evidence

| Area | Evidence |
| --- | --- |
| Approval queue action factory | `ApprovalDependencyActionSource` and `build_approval_dependency_action`. |
| Source-read model aggregation | `AdvisorCockpitSourceBatch.approvals`, `APPROVAL_DEPENDENCY_STATES`, and approval dependency projection. |
| Performance-safe source reads | `list_approvals_for_proposals` in the cockpit/proposal repository protocols, in-memory adapter, and Postgres adapter. |
| Deterministic posture | Tests cover pending, completed, and rejected approval dependencies. |
| Caller-role projection | Service and API tests prove compliance-reviewer queues contain only compliance-owned actions while advisor views retain visible blockers. |
| Owner boundaries | Risk uses `INVESTMENT_DESK`, compliance uses `COMPLIANCE_REVIEWER`, consent uses `ADVISOR`. |
| Unsupported claims blocked | Approval dependencies keep `CLIENT_READY_PUBLICATION` and completed approval authority blocked; consent keeps CRM/external communication blocked. |

Validation:

1. `python -m pytest tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py tests/unit/advisory/engine/test_engine_proposal_repository_in_memory.py tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py -q`
2. `python -m ruff check ...`
3. `python -m mypy src/core/advisor_cockpit/action_factory.py src/core/advisor_cockpit/source_read_model.py src/core/advisor_cockpit/repository.py src/core/advisor_cockpit/service.py src/core/proposals/repository.py src/infrastructure/proposals/in_memory.py src/infrastructure/proposals/postgres.py`
4. `git diff --check`

## Claim Boundary

This slice does not implement completed approval/waiver authority, completed policy sign-off,
client-ready release, OMS execution, CRM communication, or Workbench-local queue inference. It
provides source-backed queue records for downstream rendering through the Advise/Gateway contract.
