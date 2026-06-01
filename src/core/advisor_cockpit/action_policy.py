from __future__ import annotations

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_builder import build_source_backed_action
from src.core.advisor_cockpit.action_models import AdvisoryActionItem
from src.core.advisor_cockpit.action_sources import (
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
    PolicyReviewActionSource,
)
from src.core.advisor_cockpit.type_models import AdvisorCockpitActionStatus


def build_policy_review_required_action(
    source: PolicyReviewActionSource,
) -> AdvisoryActionItem:
    status: AdvisorCockpitActionStatus = (
        "PENDING_REVIEW" if source.policy_result == "PENDING_REVIEW" else "BLOCKED"
    )
    reason_codes = ["POLICY_PENDING_REVIEW", "CLIENT_READY_BLOCKED"]
    if source.policy_result == "BLOCKED":
        reason_codes = ["POLICY_BLOCKED", "CLIENT_READY_BLOCKED"]

    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.policy_evaluation_id,
            action_family="POLICY_REVIEW_REQUIRED",
            status=status,
            priority="HIGH",
            owner_role="COMPLIANCE_REVIEWER",
            title="Policy review required",
            next_required_action=(
                "Review the policy evaluation before advisor follow-up or client-ready release."
            ),
            reason_codes=reason_codes,
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                policy_evaluation_id=source.policy_evaluation_id,
            ),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                action_components.evidence_ref(
                    evidence_id=source.policy_evaluation_id,
                    evidence_type="POLICY_EVALUATION",
                    summary=source.summary,
                    access_class="RESTRICTED_CUSTOMER_EVIDENCE",
                )
            ],
            source_readiness_gaps=[
                action_components.source_readiness_gap(
                    source_family="policy",
                    gap_code=reason_codes[0],
                    owner_role="COMPLIANCE_REVIEWER",
                    message=(
                        "Policy review must be resolved before the proposal can become "
                        "client-ready."
                    ),
                )
            ],
            lineage_refs=action_components.lineage_refs(source.lineage_id, source.content_hash),
            unsupported_capabilities=[
                "CLIENT_READY_PUBLICATION",
                "COMPLETED_POLICY_APPROVAL_AUTHORITY",
                "COMPLETED_POLICY_SIGN_OFF_AUTHORITY",
            ],
            correlation_id=source.correlation_id,
        )
    )
