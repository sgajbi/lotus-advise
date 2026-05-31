from __future__ import annotations

from typing import Literal

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_builder import build_source_backed_action
from src.core.advisor_cockpit.action_sources import (
    ApprovalDependencyActionSource,
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitActionFamily,
    AdvisorCockpitOwnerRole,
    AdvisorCockpitUnsupportedCapability,
    AdvisoryActionItem,
)


def build_approval_dependency_action(
    source: ApprovalDependencyActionSource,
) -> AdvisoryActionItem:
    action_family: AdvisorCockpitActionFamily = (
        "CLIENT_CONSENT_REQUIRED"
        if source.approval_type == "CLIENT_CONSENT"
        else "APPROVAL_DEPENDENCY_AGING"
    )
    owner_role = _approval_owner_role(source.approval_type)
    pending_reason = f"{source.approval_type}_APPROVAL_PENDING"
    reason_codes = (
        [f"{source.approval_type}_APPROVAL_REJECTED", "CLIENT_READY_BLOCKED"]
        if source.approval_status == "REJECTED"
        else [pending_reason, "CLIENT_READY_BLOCKED"]
    )
    unsupported_capabilities: list[AdvisorCockpitUnsupportedCapability] = [
        "CLIENT_READY_PUBLICATION",
        "COMPLETED_POLICY_APPROVAL_AUTHORITY",
    ]
    if source.approval_type == "CLIENT_CONSENT":
        unsupported_capabilities = [
            "EXTERNAL_CLIENT_COMMUNICATION",
            "CRM_SYSTEM_OF_RECORD",
        ]

    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.dependency_id,
            action_family=action_family,
            status="BLOCKED" if source.approval_status == "REJECTED" else "PENDING_REVIEW",
            priority="CRITICAL" if source.approval_status == "REJECTED" else "HIGH",
            owner_role=owner_role,
            title=_approval_action_title(source.approval_type),
            next_required_action=_approval_next_required_action(source.approval_type),
            reason_codes=reason_codes,
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
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
            unsupported_capabilities=unsupported_capabilities,
            correlation_id=source.correlation_id,
        )
    )


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
