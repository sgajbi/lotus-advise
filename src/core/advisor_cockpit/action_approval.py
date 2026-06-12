from __future__ import annotations

from typing import Literal

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_builder import build_source_backed_action
from src.core.advisor_cockpit.action_models import AdvisoryActionItem
from src.core.advisor_cockpit.action_sources import (
    ApprovalDependencyActionSource,
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionFamily,
    AdvisorCockpitOwnerRole,
    AdvisorCockpitUnsupportedCapability,
)


def build_approval_dependency_action(
    source: ApprovalDependencyActionSource,
) -> AdvisoryActionItem:
    action_family = _approval_action_family(source.approval_type)
    owner_role = _approval_owner_role(source.approval_type)
    reason_codes = _approval_reason_codes(
        approval_type=source.approval_type,
        approval_status=source.approval_status,
    )

    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.dependency_id,
            action_family=action_family,
            status=_approval_action_status(source.approval_status),
            priority=_approval_action_priority(source.approval_status),
            owner_role=owner_role,
            title=_approval_action_title(source.approval_type),
            next_required_action=_approval_next_required_action(source.approval_type),
            reason_codes=reason_codes,
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
            ),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                action_components.evidence_ref(
                    evidence_id=source.dependency_id,
                    evidence_type="PROPOSAL_APPROVAL_DEPENDENCY",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            source_readiness_gaps=[
                action_components.source_readiness_gap(
                    source_family="proposal_lifecycle",
                    gap_code=reason_codes[0],
                    owner_role=owner_role,
                    message=source.summary,
                )
            ],
            unsupported_capabilities=_approval_unsupported_capabilities(source.approval_type),
            correlation_id=source.correlation_id,
        )
    )


def _approval_action_family(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> AdvisorCockpitActionFamily:
    if approval_type == "CLIENT_CONSENT":
        return "CLIENT_CONSENT_REQUIRED"
    return "APPROVAL_DEPENDENCY_AGING"


def _approval_action_status(
    approval_status: Literal["PENDING", "REJECTED"],
) -> Literal["BLOCKED", "PENDING_REVIEW"]:
    if approval_status == "REJECTED":
        return "BLOCKED"
    return "PENDING_REVIEW"


def _approval_action_priority(
    approval_status: Literal["PENDING", "REJECTED"],
) -> Literal["CRITICAL", "HIGH"]:
    if approval_status == "REJECTED":
        return "CRITICAL"
    return "HIGH"


def _approval_reason_codes(
    *,
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
    approval_status: Literal["PENDING", "REJECTED"],
) -> list[str]:
    if approval_status == "REJECTED":
        return [f"{approval_type}_APPROVAL_REJECTED", "CLIENT_READY_BLOCKED"]
    return [f"{approval_type}_APPROVAL_PENDING", "CLIENT_READY_BLOCKED"]


def _approval_unsupported_capabilities(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> list[AdvisorCockpitUnsupportedCapability]:
    if approval_type == "CLIENT_CONSENT":
        return ["EXTERNAL_CLIENT_COMMUNICATION", "CRM_SYSTEM_OF_RECORD"]
    return ["CLIENT_READY_PUBLICATION", "COMPLETED_POLICY_APPROVAL_AUTHORITY"]


def _approval_owner_role(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> AdvisorCockpitOwnerRole:
    if approval_type == "RISK":
        return "INVESTMENT_DESK"
    if approval_type == "COMPLIANCE":
        return "COMPLIANCE_REVIEWER"
    return "ADVISOR"


def _approval_action_title(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> str:
    if approval_type == "RISK":
        return "Risk review pending"
    if approval_type == "COMPLIANCE":
        return "Compliance review pending"
    return "Client consent required"


def _approval_next_required_action(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> str:
    if approval_type == "RISK":
        return "Review the proposal risk dependency before client consent can progress."
    if approval_type == "COMPLIANCE":
        return "Review the compliance dependency before client consent can progress."
    return "Record source-backed consent posture before execution readiness can change."
