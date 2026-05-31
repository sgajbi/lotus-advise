from __future__ import annotations

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_builder import build_source_backed_action
from src.core.advisor_cockpit.action_sources import (
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
    ExecutionHandoffReadyActionSource,
    ExecutionStatusAttentionActionSource,
)
from src.core.advisor_cockpit.models import AdvisoryActionItem


def build_execution_handoff_ready_action(
    source: ExecutionHandoffReadyActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.handoff_id,
            action_family="EXECUTION_HANDOFF_READY",
            status="READY",
            priority="MEDIUM",
            owner_role="EXECUTION_OWNER",
            title="Execution handoff ready",
            next_required_action=(
                "Request execution handoff through the governed Advise execution boundary."
            ),
            reason_codes=["EXECUTION_HANDOFF_READY", "OMS_ORDER_LIFECYCLE_BLOCKED"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                execution_ref=source.handoff_id,
            ),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                action_components.evidence_ref(
                    evidence_id=source.handoff_id,
                    evidence_type="PROPOSAL_EXECUTION_HANDOFF_READINESS",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            unsupported_capabilities=["OMS_ORDER_LIFECYCLE"],
            correlation_id=source.correlation_id,
        )
    )


def build_execution_status_attention_action(
    source: ExecutionStatusAttentionActionSource,
) -> AdvisoryActionItem:
    is_blocking = source.handoff_status in {"REJECTED", "CANCELLED", "EXPIRED"}
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.execution_ref,
            action_family="EXECUTION_STATUS_ATTENTION",
            status="BLOCKED" if is_blocking else "PENDING_REVIEW",
            priority="HIGH" if is_blocking else "MEDIUM",
            owner_role="EXECUTION_OWNER",
            title="Execution status attention",
            next_required_action=(
                "Review downstream execution posture without treating Advise as the OMS."
            ),
            reason_codes=[
                f"EXECUTION_STATUS_{source.handoff_status}",
                "OMS_ORDER_LIFECYCLE_BLOCKED",
            ],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                execution_ref=source.execution_ref,
            ),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                action_components.evidence_ref(
                    evidence_id=source.execution_ref,
                    evidence_type="PROPOSAL_EXECUTION_STATUS",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            unsupported_capabilities=["OMS_ORDER_LIFECYCLE"],
            correlation_id=source.correlation_id,
        )
    )
