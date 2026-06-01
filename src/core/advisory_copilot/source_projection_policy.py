from __future__ import annotations

from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.source_projection_refs import projection_source_ref
from src.core.advisory_copilot.source_projection_text import projection_summary_item
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord


def build_policy_posture_section(
    *, policy_evaluations: list[PolicyEvaluationRecord]
) -> CopilotEvidenceSectionInput:
    latest = sorted(policy_evaluations, key=lambda item: item.generated_at)[-1]
    review_items = sorted(
        set(
            latest.approval_dependencies
            + latest.disclosure_requirements
            + latest.consent_requirements
            + latest.source_gaps
        )
    )
    summary_items = [
        projection_summary_item(
            f"Policy evaluation {latest.evaluation_id} is {latest.evaluation_status}."
        ),
        projection_summary_item(
            f"Policy pack {latest.policy_pack_id} version {latest.policy_version} is the "
            "source authority."
        ),
        "Client-ready publication remains blocked until policy and review gates are resolved.",
    ]
    if review_items:
        summary_items.append(
            projection_summary_item(f"Open policy evidence items: {', '.join(review_items[:5])}.")
        )
    return CopilotEvidenceSectionInput(
        section_key="POLICY_POSTURE",
        title="Policy posture",
        evidence_class="COMPLIANCE_REVIEW_EVIDENCE",
        source_refs=(
            projection_source_ref(
                source_type="POLICY_EVALUATION",
                source_id=latest.evaluation_id,
                content_hash=latest.evaluation_hash,
                access_class="COMPLIANCE_REVIEW_EVIDENCE",
            ),
        ),
        summary_items=tuple(summary_items),
        allowed_audiences=("ADVISOR", "DESK_HEAD", "COMPLIANCE_REVIEWER"),
    )
