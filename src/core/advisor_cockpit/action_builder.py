from __future__ import annotations

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_sources import CockpitActionConstructionInput
from src.core.advisor_cockpit.models import AdvisoryActionItem
from src.core.advisor_cockpit.projection_bounds import bounded_optional_reference

LOTUS_ADVISE_SOURCE_SYSTEM = action_components.LOTUS_ADVISE_SOURCE_SYSTEM


def build_source_backed_action(source: CockpitActionConstructionInput) -> AdvisoryActionItem:
    if not source.reason_codes:
        raise ValueError("cockpit action construction requires at least one reason code")
    if not (
        source.evidence_refs
        or source.source_readiness_gaps
        or source.dependency_readiness
        or source.unsupported_capabilities
    ):
        raise ValueError(
            "cockpit action construction requires evidence, readiness, dependency, "
            "or unsupported-capability context"
        )

    action_item_id = action_components.build_action_item_id(
        source.action_family,
        source.source_action_id,
    )
    source_refs = action_components.bounded_source_refs(source.source_refs)
    return AdvisoryActionItem(
        action_item_id=action_item_id,
        action_item_version=1,
        action_family=source.action_family,
        status=source.status,
        priority=source.priority,
        owner_role=source.owner_role,
        owning_system=LOTUS_ADVISE_SOURCE_SYSTEM,
        title=source.title,
        next_required_action=source.next_required_action,
        reason_codes=action_components.unique_ordered(source.reason_codes),
        client_ref=source_refs.client_ref,
        household_ref=source_refs.household_ref,
        portfolio_id=source_refs.portfolio_id,
        proposal_id=source_refs.proposal_id,
        workspace_id=source_refs.workspace_id,
        memo_id=source_refs.memo_id,
        policy_evaluation_id=source_refs.policy_evaluation_id,
        report_ref=source_refs.report_ref,
        execution_ref=source_refs.execution_ref,
        due_at=bounded_optional_reference(source.due_at),
        sla_age_band=source.sla_age_band,
        materiality_rank=source.materiality_rank,
        source_timestamp=bounded_optional_reference(source.source_timestamp),
        evidence_refs=source.evidence_refs,
        source_readiness_gaps=source.source_readiness_gaps,
        dependency_readiness=source.dependency_readiness,
        lineage_refs=source.lineage_refs
        or action_components.lineage_refs(
            f"{source.action_family.lower()}:{source.source_action_id}",
            None,
        ),
        unsupported_capabilities=action_components.unique_ordered(source.unsupported_capabilities),
        correlation_id=bounded_optional_reference(source.correlation_id),
    )
