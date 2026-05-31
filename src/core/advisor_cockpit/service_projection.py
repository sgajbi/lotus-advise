from __future__ import annotations

from collections import Counter
from typing import Any

from src.core.advisor_cockpit.action_components import LOTUS_ADVISE_SOURCE_SYSTEM
from src.core.advisor_cockpit.models import (
    AdvisoryActionItem,
    CockpitCallerContext,
    CockpitEvidenceRef,
    MeetingPreparationPacket,
)
from src.core.advisor_cockpit.projection_bounds import (
    bounded_optional_reference,
    bounded_reference,
    bounded_summary,
)
from src.core.advisor_cockpit.source_read_model import AdvisorCockpitSourceReadModel


def project_actions_for_caller(
    *,
    actions: list[AdvisoryActionItem],
    caller_context: CockpitCallerContext,
) -> list[AdvisoryActionItem]:
    visible_owner_roles = visible_owner_roles_for_role(caller_context.role)
    if visible_owner_roles is None:
        return actions
    return [
        action
        for action in actions
        if action.owner_role in visible_owner_roles or action.owner_role == "SYSTEM"
    ]


def visible_owner_roles_for_role(role: str) -> set[str] | None:
    if role in {"ADVISOR", "DESK_HEAD"}:
        return None
    if role == "COMPLIANCE_REVIEWER":
        return {"COMPLIANCE_REVIEWER"}
    if role == "INVESTMENT_DESK":
        return {"INVESTMENT_DESK"}
    if role == "OPERATIONS":
        return {"REPORTING_OWNER", "ARCHIVE_OWNER", "EXECUTION_OWNER", "OPERATIONS"}
    if role in {"PORTFOLIO_MANAGER", "DPM_OWNER"}:
        return {"PORTFOLIO_MANAGER"}
    if role == "CRM_OWNER":
        return {"CRM_OWNER", "ADVISOR"}
    return {role}


def action_counts(actions: list[AdvisoryActionItem]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for action in actions:
        counts[f"family.{action.action_family}"] += 1
        counts[f"status.{action.status}"] += 1
        counts[f"priority.{action.priority}"] += 1
        counts[f"owner.{action.owner_role}"] += 1
        counts[f"sla.{action.sla_age_band}"] += 1
    return dict(sorted(counts.items()))


def supportability(
    *,
    actions: list[AdvisoryActionItem],
    source_limit: int,
    contract_version: str,
) -> dict[str, Any]:
    return {
        "contract_version": contract_version,
        "source_limit": source_limit,
        "action_count": len(actions),
        "api_posture": "SUPPORTED_BY_LOTUS_ADVISE_RFC0026",
        "gateway_posture": "SUPPORTED_BY_LOTUS_GATEWAY_RFC0026",
        "workbench_posture": "CANONICAL_WORKBENCH_PROOF_PASSED_RFC0026",
        "data_product_posture": "ACTIVE_ADVISOR_COCKPIT_PRODUCTS_RFC0026",
        "canonical_proof": "PB_SG_GLOBAL_BAL_001_ADVISOR_COCKPIT_VALIDATED",
        "client_ready_publication": "BLOCKED",
        "external_client_communication": "BLOCKED",
    }


def preparation_packets(
    read_model: AdvisorCockpitSourceReadModel,
) -> list[MeetingPreparationPacket]:
    packets: list[MeetingPreparationPacket] = []
    for source in read_model.meeting_preparations:
        packet_id = bounded_reference(source.preparation_id)
        summary = bounded_summary(source.summary)
        source_ref = bounded_optional_reference(
            source.proposal_id or source.portfolio_id or source.context_ref
        )
        packets.append(
            MeetingPreparationPacket(
                packet_id=packet_id,
                context_type=source.context_type,
                context_ref=bounded_reference(source.context_ref),
                status="READY",
                evidence_refs=source.evidence_refs
                or [
                    CockpitEvidenceRef(
                        evidence_id=packet_id,
                        evidence_type="MEETING_PREPARATION_PACKET",
                        source_system=LOTUS_ADVISE_SOURCE_SYSTEM,
                        access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                        summary=summary,
                    )
                ],
                sections=[
                    {
                        "section_id": "advisor_meeting_context",
                        "title": "Advisor meeting context",
                        "summary": summary,
                        "source_ref": source_ref,
                    }
                ],
            )
        )
    return packets
