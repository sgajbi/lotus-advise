from typing import Any

from src.core.policy_packs.workflow_models import (
    PolicyEvaluationSignOffDecisionRequest,
    PolicyEvaluationWorkflowResponse,
)
from src.core.proposals.exceptions import ProposalValidationError

_APPROVE_FOR_POLICY_SIGN_OFF = "APPROVE_FOR_POLICY_SIGN_OFF"
_CONFLICT_RESOLUTION_OUTCOME = "NO_MATERIAL_CONFLICT_REMAINING"
_REQUIREMENT_BLOCKER_FIELDS = (
    (
        "approval_dependencies",
        "resolved_approval_dependencies",
        "APPROVAL_DEPENDENCY_OPEN",
    ),
    (
        "disclosure_requirements",
        "satisfied_disclosure_requirements",
        "DISCLOSURE_REQUIREMENT_OPEN",
    ),
    (
        "consent_requirements",
        "satisfied_consent_requirements",
        "CONSENT_REQUIREMENT_OPEN",
    ),
)


def validate_policy_sign_off_decision(
    *,
    record: Any,
    workflow: PolicyEvaluationWorkflowResponse,
    payload: PolicyEvaluationSignOffDecisionRequest,
) -> None:
    if _is_maker_checker_violation(record=record, payload=payload):
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_REQUIRES_MAKER_CHECKER")
    if not _is_policy_sign_off_approval(payload=payload):
        return

    blockers = approval_blockers(record=record, payload=payload)
    blockers.extend(_workflow_posture_blockers(record=record, workflow=workflow, payload=payload))
    if blockers:
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_REQUIREMENTS_OPEN")


def approval_blockers(*, record: Any, payload: PolicyEvaluationSignOffDecisionRequest) -> list[str]:
    blockers: list[str] = []
    for record_field, payload_field, blocker_prefix in _REQUIREMENT_BLOCKER_FIELDS:
        blockers.extend(
            _missing_requirement_blockers(
                record_values=getattr(record, record_field),
                payload_values=getattr(payload, payload_field),
                blocker_prefix=blocker_prefix,
            )
        )
    return blockers


def _is_policy_sign_off_approval(*, payload: PolicyEvaluationSignOffDecisionRequest) -> bool:
    return payload.decision == _APPROVE_FOR_POLICY_SIGN_OFF


def _is_maker_checker_violation(
    *, record: Any, payload: PolicyEvaluationSignOffDecisionRequest
) -> bool:
    return payload.actor_id == record.created_by and _is_policy_sign_off_approval(payload=payload)


def _workflow_posture_blockers(
    *,
    record: Any,
    workflow: PolicyEvaluationWorkflowResponse,
    payload: PolicyEvaluationSignOffDecisionRequest,
) -> list[str]:
    blockers: list[str] = []
    if _requires_conflict_review_outcome(workflow=workflow, payload=payload):
        blockers.append("CONFLICT_REVIEW_OUTCOME_REQUIRED")
    if record.evaluation_status == "BLOCKED":
        blockers.append("BLOCKED_POLICY_EVALUATION_CANNOT_BE_SIGNED_OFF")
    return blockers


def _requires_conflict_review_outcome(
    *, workflow: PolicyEvaluationWorkflowResponse, payload: PolicyEvaluationSignOffDecisionRequest
) -> bool:
    return (
        workflow.conflict_posture["status"] == "BLOCKED"
        and payload.conflict_review_outcome != _CONFLICT_RESOLUTION_OUTCOME
    )


def _missing_requirement_blockers(
    *,
    record_values: list[str],
    payload_values: list[str],
    blocker_prefix: str,
) -> list[str]:
    missing_values = sorted(set(record_values) - set(payload_values))
    return [f"{blocker_prefix}:{item}" for item in missing_values]


__all__ = ["validate_policy_sign_off_decision"]
