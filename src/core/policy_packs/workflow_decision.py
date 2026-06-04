from typing import Any

from src.core.policy_packs.workflow_models import (
    PolicyEvaluationSignOffDecisionRequest,
    PolicyEvaluationWorkflowResponse,
)
from src.core.proposals.exceptions import ProposalValidationError


def validate_policy_sign_off_decision(
    *,
    record: Any,
    workflow: PolicyEvaluationWorkflowResponse,
    payload: PolicyEvaluationSignOffDecisionRequest,
) -> None:
    if payload.actor_id == record.created_by and payload.decision == "APPROVE_FOR_POLICY_SIGN_OFF":
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_REQUIRES_MAKER_CHECKER")
    if payload.decision != "APPROVE_FOR_POLICY_SIGN_OFF":
        return

    blockers = approval_blockers(record=record, payload=payload)
    if workflow.conflict_posture["status"] == "BLOCKED" and payload.conflict_review_outcome != (
        "NO_MATERIAL_CONFLICT_REMAINING"
    ):
        blockers.append("CONFLICT_REVIEW_OUTCOME_REQUIRED")
    if record.evaluation_status == "BLOCKED":
        blockers.append("BLOCKED_POLICY_EVALUATION_CANNOT_BE_SIGNED_OFF")
    if blockers:
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_REQUIREMENTS_OPEN")


def approval_blockers(*, record: Any, payload: PolicyEvaluationSignOffDecisionRequest) -> list[str]:
    blockers: list[str] = []
    resolved = set(payload.resolved_approval_dependencies)
    disclosures = set(payload.satisfied_disclosure_requirements)
    consents = set(payload.satisfied_consent_requirements)
    missing_approvals = sorted(set(record.approval_dependencies) - resolved)
    missing_disclosures = sorted(set(record.disclosure_requirements) - disclosures)
    missing_consents = sorted(set(record.consent_requirements) - consents)
    if missing_approvals:
        blockers.extend(f"APPROVAL_DEPENDENCY_OPEN:{item}" for item in missing_approvals)
    if missing_disclosures:
        blockers.extend(f"DISCLOSURE_REQUIREMENT_OPEN:{item}" for item in missing_disclosures)
    if missing_consents:
        blockers.extend(f"CONSENT_REQUIREMENT_OPEN:{item}" for item in missing_consents)
    return blockers


__all__ = ["validate_policy_sign_off_decision"]
