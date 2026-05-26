from typing import Annotated

from fastapi import Header, Path, Query, status

import src.api.proposals.router as shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.core.policy_packs import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationCreateRequest,
    PolicyEvaluationEventRequest,
    PolicyEvaluationLineageResponse,
    PolicyEvaluationPersistenceResult,
    PolicyEvaluationRecord,
    PolicyEvaluationReplayRequest,
    PolicyEvaluationReplayResponse,
    PolicyEvaluationReviewQueueResponse,
    PolicyEvaluationSignOffPackageResponse,
    append_policy_evaluation_event,
    finalize_policy_evaluation_record,
    get_policy_evaluation_lineage,
    get_policy_evaluation_record,
    get_policy_evaluation_review_queue,
    get_policy_evaluation_sign_off_package,
    replay_policy_evaluation_record,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
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
        "Gateway, Workbench, report realization, and client-ready publication remain gated."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Policy-pack version was not found."},
        status.HTTP_409_CONFLICT: {
            "description": "Idempotency key was reused for a different evaluation request."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Policy pack is inactive, not applicable, or source evidence is invalid."
        },
    },
)
def create_or_replay_policy_evaluation(
    proposal_id: Annotated[
        str,
        Path(
            description="Proposal identifier evaluated by the policy record.",
            examples=["pp_001"],
        ),
    ],
    proposal_version_id: Annotated[
        str,
        Path(
            description="Immutable proposal version identifier evaluated by the policy record.",
            examples=["ppv_001"],
        ),
    ],
    payload: PolicyEvaluationCreateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key for replay-safe policy evaluation finalization.",
            examples=["policy-evaluation-finalize-001"],
        ),
    ],
) -> PolicyEvaluationPersistenceResult:
    try:
        return finalize_policy_evaluation_record(
            evidence_bundle=payload.evidence_bundle,
            policy_pack_id=payload.policy_pack_id,
            policy_version=payload.policy_version,
            proposal_id=proposal_id,
            proposal_version_id=proposal_version_id,
            created_by=payload.created_by,
            idempotency_key=idempotency_key,
            reason=payload.reason,
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/policy-evaluations/review-queue",
    response_model=PolicyEvaluationReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Read Policy Review Queue",
    description=(
        "Returns finalized policy evaluation records filtered by aggregate policy posture. This is "
        "the Advise source queue for later Gateway and Workbench review surfaces, not a "
        "client-ready release queue."
    ),
    responses={200: {"description": "Policy review queue returned."}},
)
def read_policy_review_queue(
    evaluation_status: Annotated[
        str | None,
        Query(
            description=(
                "Optional aggregate policy posture filter. Defaults to evaluations requiring "
                "review."
            ),
            examples=["PENDING_REVIEW"],
        ),
    ] = "PENDING_REVIEW",
) -> PolicyEvaluationReviewQueueResponse:
    return get_policy_evaluation_review_queue(evaluation_status=evaluation_status)


@shared.router.get(
    "/advisory/policy-evaluations/{evaluation_id}",
    response_model=PolicyEvaluationRecord,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Read Policy Evaluation",
    description=(
        "Returns the immutable policy evaluation record, material rule hashes, source refs, source "
        "gaps, approval dependencies, disclosure requirements, consent requirements, and "
        "append-only review/sign-off/report reference arrays."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "Policy evaluation was not found."}},
)
def read_policy_evaluation(
    evaluation_id: Annotated[
        str,
        Path(description="Policy evaluation record identifier.", examples=["pev_123abc"]),
    ],
) -> PolicyEvaluationRecord:
    try:
        return get_policy_evaluation_record(evaluation_id=evaluation_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


@shared.router.post(
    "/advisory/policy-evaluations/{evaluation_id}/replay",
    response_model=PolicyEvaluationReplayResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Replay Policy Evaluation",
    description=(
        "Compares pinned policy version, policy content hash, source evidence hash, and evaluation "
        "hash against the finalized policy evaluation record. Optional current evidence proves "
        "whether material source or result truth has drifted."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "Policy evaluation was not found."}},
)
def replay_policy_evaluation(
    evaluation_id: Annotated[
        str,
        Path(description="Policy evaluation record identifier.", examples=["pev_123abc"]),
    ],
    payload: PolicyEvaluationReplayRequest,
) -> PolicyEvaluationReplayResponse:
    try:
        return replay_policy_evaluation_record(
            evaluation_id=evaluation_id,
            evidence_bundle=payload.evidence_bundle,
        )
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Policy evaluation was not found."},
        status.HTTP_409_CONFLICT: {
            "description": "Idempotency key was reused for a different event request."
        },
    },
)
def record_policy_evaluation_event(
    evaluation_id: Annotated[
        str,
        Path(description="Policy evaluation record identifier.", examples=["pev_123abc"]),
    ],
    payload: PolicyEvaluationEventRequest,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description="Optional idempotency key for replay-safe policy evaluation event capture.",
            examples=["policy-evaluation-review-001"],
        ),
    ] = None,
) -> PolicyEvaluationAuditEvent:
    try:
        return append_policy_evaluation_event(
            evaluation_id=evaluation_id,
            event_type=payload.event_type,
            actor_id=payload.actor_id,
            reason=payload.reason,
            idempotency_key=idempotency_key,
        )
    except (ProposalIdempotencyConflictError, ProposalNotFoundError) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/policy-evaluations/{evaluation_id}/lineage",
    response_model=PolicyEvaluationLineageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Read Policy Evaluation Lineage",
    description=(
        "Returns hash-backed policy, source, rule-result, and audit-event lineage for a finalized "
        "policy evaluation record."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "Policy evaluation was not found."}},
)
def read_policy_evaluation_lineage(
    evaluation_id: Annotated[
        str,
        Path(description="Policy evaluation record identifier.", examples=["pev_123abc"]),
    ],
) -> PolicyEvaluationLineageResponse:
    try:
        return get_policy_evaluation_lineage(evaluation_id=evaluation_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/policy-evaluations/{evaluation_id}/sign-off-package",
    response_model=PolicyEvaluationSignOffPackageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Read Policy Sign-Off Package",
    description=(
        "Returns the certified Advise source package for policy review and sign-off. The package "
        "contains the finalized evaluation, lineage, and audit events, but does not claim "
        "report/render/archive realization or client-ready publication."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "Policy evaluation was not found."}},
)
def read_policy_sign_off_package(
    evaluation_id: Annotated[
        str,
        Path(description="Policy evaluation record identifier.", examples=["pev_123abc"]),
    ],
) -> PolicyEvaluationSignOffPackageResponse:
    try:
        return get_policy_evaluation_sign_off_package(evaluation_id=evaluation_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)
