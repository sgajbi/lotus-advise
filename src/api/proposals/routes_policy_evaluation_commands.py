from typing import cast

from fastapi import status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.policy_evaluation_parameters import (
    PolicyEvaluationEventIdempotencyKeyHeader,
    PolicyEvaluationFinalizeIdempotencyKeyHeader,
    PolicyEvaluationIdPath,
    PolicyEvaluationProposalIdPath,
    PolicyEvaluationProposalVersionIdPath,
)
from src.api.proposals.policy_evaluation_responses import (
    POLICY_EVALUATION_CREATE_RESPONSES,
    POLICY_EVALUATION_EVENT_RESPONSES,
)
from src.core.policy_packs import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationCreateRequest,
    PolicyEvaluationEventRequest,
    PolicyEvaluationPersistenceResult,
    append_policy_evaluation_event,
    finalize_policy_evaluation_record,
)


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations",
    response_model=PolicyEvaluationPersistenceResult,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Create Or Replay Policy Evaluation",
    description=(
        "Creates or replays a finalized RFC-0025 policy evaluation record from source-backed "
        "proposal evidence. The record is hash-backed, idempotent, and bounded to Advise APIs; "
        "Gateway/Workbench consumption and signed-off report-package handoff are supported by "
        "the current RFC-0025 implementation, while client-ready publication remains gated."
    ),
    responses=POLICY_EVALUATION_CREATE_RESPONSES,
)
def create_or_replay_policy_evaluation(
    proposal_id: PolicyEvaluationProposalIdPath,
    proposal_version_id: PolicyEvaluationProposalVersionIdPath,
    payload: PolicyEvaluationCreateRequest,
    idempotency_key: PolicyEvaluationFinalizeIdempotencyKeyHeader,
) -> PolicyEvaluationPersistenceResult:
    return cast(
        PolicyEvaluationPersistenceResult,
        run_proposal_operation(
            lambda: finalize_policy_evaluation_record(
                evidence_bundle=payload.evidence_bundle,
                policy_pack_id=payload.policy_pack_id,
                policy_version=payload.policy_version,
                proposal_id=proposal_id,
                proposal_version_id=proposal_version_id,
                created_by=payload.created_by,
                idempotency_key=idempotency_key,
                reason=payload.reason,
            )
        ),
    )


@shared.router.post(
    "/advisory/policy-evaluations/{evaluation_id}/events",
    response_model=PolicyEvaluationAuditEvent,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Record Policy Evaluation Event",
    description=(
        "Records an append-only review, sign-off, or report/archive reference event against the "
        "finalized policy evaluation hash. Event capture does not mutate the immutable evaluation "
        "truth or release client-ready publication."
    ),
    responses=POLICY_EVALUATION_EVENT_RESPONSES,
)
def record_policy_evaluation_event(
    evaluation_id: PolicyEvaluationIdPath,
    payload: PolicyEvaluationEventRequest,
    idempotency_key: PolicyEvaluationEventIdempotencyKeyHeader = None,
) -> PolicyEvaluationAuditEvent:
    return cast(
        PolicyEvaluationAuditEvent,
        run_proposal_operation(
            lambda: append_policy_evaluation_event(
                evaluation_id=evaluation_id,
                event_type=payload.event_type,
                actor_id=payload.actor_id,
                reason=payload.reason,
                idempotency_key=idempotency_key,
            )
        ),
    )


__all__ = [
    "create_or_replay_policy_evaluation",
    "record_policy_evaluation_event",
]
