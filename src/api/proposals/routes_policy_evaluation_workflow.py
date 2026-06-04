from typing import cast

from fastapi import status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
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
    get_policy_evaluation_workflow,
    record_policy_evaluation_sign_off_decision,
)


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
        run_proposal_operation(lambda: get_policy_evaluation_workflow(evaluation_id=evaluation_id)),
    )


@shared.router.post(
    "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
    response_model=PolicyEvaluationSignOffDecisionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Record Policy Sign-Off Decision",
    description=(
        "Records an RFC-0025 policy sign-off decision against the immutable evaluation hash. "
        "Approval requires maker-checker separation and explicit resolution of approval, "
        "disclosure, consent, and conflict requirements; client-ready publication remains blocked."
    ),
    responses=POLICY_SIGN_OFF_DECISION_RESPONSES,
)
def record_policy_sign_off_decision(
    evaluation_id: PolicyEvaluationIdPath,
    payload: PolicyEvaluationSignOffDecisionRequest,
    idempotency_key: PolicyEvaluationSignOffDecisionIdempotencyKeyHeader = None,
) -> PolicyEvaluationSignOffDecisionResponse:
    return cast(
        PolicyEvaluationSignOffDecisionResponse,
        run_proposal_operation(
            lambda: record_policy_evaluation_sign_off_decision(
                evaluation_id=evaluation_id,
                payload=payload,
                idempotency_key=idempotency_key,
            )
        ),
    )


__all__ = [
    "read_policy_evaluation_workflow",
    "record_policy_sign_off_decision",
]
