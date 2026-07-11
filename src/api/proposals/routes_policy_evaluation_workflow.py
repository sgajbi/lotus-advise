from typing import cast

from fastapi import Depends, status

import src.api.proposals.router as shared
from src.api.observability import record_policy_evaluation_operation
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.policy_control_principal import (
    POLICY_EVALUATION_SIGN_OFF_CAPABILITY,
    PolicyControlPrincipal,
    assert_policy_evaluation_record_scope,
    bind_policy_control_actor,
    policy_control_audit_reason,
    require_policy_evaluation_sign_off_principal,
)
from src.api.proposals.policy_evaluation_parameters import (
    PolicyEvaluationIdPath,
    PolicyEvaluationSignOffDecisionIdempotencyKeyHeader,
)
from src.api.proposals.policy_evaluation_responses import (
    POLICY_EVALUATION_READ_RESPONSES,
    POLICY_SIGN_OFF_DECISION_RESPONSES,
)
from src.core.policy_packs import (
    PolicyEvaluationSignOffDecisionRequest,
    PolicyEvaluationSignOffDecisionResponse,
    PolicyEvaluationWorkflowResponse,
)
from src.core.proposals.exceptions import ProposalIdempotencyConflictError, ProposalValidationError


@shared.router.get(
    "/advisory/policy-evaluations/{evaluation_id}/workflow",
    response_model=PolicyEvaluationWorkflowResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Read Policy Evaluation Workflow",
    description=(
        "Returns approval dependencies, disclosure and consent requirements, conflict posture, "
        "SLA aging, maker-checker posture, and sign-off blockers derived from the finalized policy "
        "evaluation record. This route does not infer client-ready publication."
    ),
    responses=POLICY_EVALUATION_READ_RESPONSES,
)
def read_policy_evaluation_workflow(
    evaluation_id: PolicyEvaluationIdPath,
) -> PolicyEvaluationWorkflowResponse:
    return cast(
        PolicyEvaluationWorkflowResponse,
        run_proposal_operation(
            lambda: shared.get_policy_evidence_application_service().get_policy_evaluation_workflow(
                evaluation_id=evaluation_id
            )
        ),
    )


@shared.router.post(
    "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
    response_model=PolicyEvaluationSignOffDecisionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Record Policy Sign-Off Decision",
    description=(
        "Records an RFC-0025 policy sign-off decision against the immutable evaluation hash. "
        "The `actor_id` field must match the trusted policy checker principal and the request "
        "must be authorized for the evaluation's proposal, portfolio, tenant, and legal entity. "
        "Approval requires maker-checker separation and explicit resolution of approval, "
        "disclosure, consent, and conflict requirements; client-ready publication remains blocked."
    ),
    responses=POLICY_SIGN_OFF_DECISION_RESPONSES,
)
def record_policy_sign_off_decision(
    evaluation_id: PolicyEvaluationIdPath,
    payload: PolicyEvaluationSignOffDecisionRequest,
    idempotency_key: PolicyEvaluationSignOffDecisionIdempotencyKeyHeader,
    principal: PolicyControlPrincipal = Depends(require_policy_evaluation_sign_off_principal),
) -> PolicyEvaluationSignOffDecisionResponse:
    return cast(
        PolicyEvaluationSignOffDecisionResponse,
        run_proposal_operation(
            lambda: _record_policy_sign_off_decision_with_telemetry(
                evaluation_id=evaluation_id,
                payload=payload,
                idempotency_key=idempotency_key,
                principal=principal,
            )
        ),
    )


def _record_policy_sign_off_decision_with_telemetry(
    *,
    evaluation_id: str,
    payload: PolicyEvaluationSignOffDecisionRequest,
    idempotency_key: str,
    principal: PolicyControlPrincipal,
) -> PolicyEvaluationSignOffDecisionResponse:
    service = shared.get_policy_evidence_application_service()
    record = service.get_policy_evaluation_record(evaluation_id=evaluation_id)
    lineage = service.get_policy_evaluation_lineage(evaluation_id=evaluation_id)
    assert_policy_evaluation_record_scope(
        principal=principal,
        record=record,
        lineage=lineage,
    )
    trusted_payload = payload.model_copy(
        update={
            "actor_id": bind_policy_control_actor(payload.actor_id, principal),
            "reason": policy_control_audit_reason(
                payload.reason,
                principal=principal,
                capability=POLICY_EVALUATION_SIGN_OFF_CAPABILITY,
            ),
        }
    )
    try:
        response = service.record_policy_evaluation_sign_off_decision(
            evaluation_id=evaluation_id,
            payload=trusted_payload,
            idempotency_key=idempotency_key,
        )
    except ProposalIdempotencyConflictError:
        _record_policy_workflow_operation("sign_off_decision", "conflict", "idempotency")
        raise
    except ProposalValidationError as exc:
        _record_policy_workflow_operation("sign_off_decision", "validation_blocked", str(exc))
        raise
    _record_policy_workflow_operation(
        "sign_off_decision",
        "success",
        str(response.sign_off_event.reason_json.get("decision") or "recorded"),
    )
    return response


def _record_policy_workflow_operation(operation: str, status: str, reason: str) -> None:
    record_policy_evaluation_operation(
        operation=f"policy_evaluation.{operation}",
        status=status,
        reason=reason,
        dependency="none",
    )


__all__ = [
    "read_policy_evaluation_workflow",
    "record_policy_sign_off_decision",
]
