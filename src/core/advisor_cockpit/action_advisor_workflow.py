from __future__ import annotations

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_builder import build_source_backed_action
from src.core.advisor_cockpit.action_sources import (
    ClientFollowUpActionSource,
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
    MeetingPreparationActionSource,
)
from src.core.advisor_cockpit.models import AdvisoryActionItem


def build_meeting_preparation_action(
    source: MeetingPreparationActionSource,
) -> AdvisoryActionItem:
    portfolio_id = source.portfolio_id
    if source.context_type == "PORTFOLIO" and portfolio_id is None:
        portfolio_id = source.context_ref

    evidence_refs = source.evidence_refs or [
        action_components.evidence_ref(
            evidence_id=source.preparation_id,
            evidence_type="MEETING_PREPARATION_PACKET",
            summary=source.summary,
            access_class="CUSTOMER_CONSUMABLE_SUMMARY",
        )
    ]
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.preparation_id,
            action_family="CLIENT_MEETING_PREPARATION",
            status="READY",
            priority="MEDIUM",
            owner_role="ADVISOR",
            title="Meeting preparation ready",
            next_required_action="Review the meeting preparation packet before client discussion.",
            reason_codes=["MEETING_PREPARATION_READY"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=portfolio_id,
                proposal_id=source.proposal_id,
            ),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=evidence_refs,
            correlation_id=source.correlation_id,
        )
    )


def build_client_follow_up_action(
    source: ClientFollowUpActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.follow_up_id,
            action_family="CLIENT_FOLLOW_UP_REQUIRED",
            status="READY",
            priority="HIGH",
            owner_role="ADVISOR",
            title="Client follow-up required",
            next_required_action=(
                "Review the source-backed follow-up requirement before taking any client action."
            ),
            reason_codes=[source.follow_up_code, "EXTERNAL_CLIENT_COMMUNICATION_BLOCKED"],
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
                    evidence_id=source.follow_up_id,
                    evidence_type="CLIENT_FOLLOW_UP_REQUIREMENT",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            source_readiness_gaps=[
                action_components.source_readiness_gap(
                    source_family="proposal_lifecycle",
                    gap_code=source.follow_up_code,
                    owner_role="ADVISOR",
                    message=source.summary,
                )
            ],
            unsupported_capabilities=["EXTERNAL_CLIENT_COMMUNICATION", "CRM_SYSTEM_OF_RECORD"],
            correlation_id=source.correlation_id,
        )
    )
