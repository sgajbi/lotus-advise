from typing import cast

from fastapi import status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.policy_evaluation_parameters import (
    PolicyEvaluationIdPath,
    PolicyEvaluationPortfolioIdQuery,
    PolicyEvaluationStatusQuery,
)
from src.api.proposals.policy_evaluation_responses import (
    POLICY_EVALUATION_READ_RESPONSES,
    POLICY_REVIEW_QUEUE_RESPONSES,
)
from src.core.policy_packs import (
    PolicyEvaluationDiagnosticsResponse,
    PolicyEvaluationLineageResponse,
    PolicyEvaluationRecord,
    PolicyEvaluationReplayRequest,
    PolicyEvaluationReplayResponse,
    PolicyEvaluationReviewQueueResponse,
    PolicyEvaluationSignOffPackageResponse,
    get_policy_evaluation_diagnostics,
    get_policy_evaluation_lineage,
    get_policy_evaluation_record,
    get_policy_evaluation_review_queue,
    get_policy_evaluation_sign_off_package,
    replay_policy_evaluation_record,
)


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
    responses=POLICY_REVIEW_QUEUE_RESPONSES,
)
def read_policy_review_queue(
    evaluation_status: PolicyEvaluationStatusQuery = "PENDING_REVIEW",
    portfolio_id: PolicyEvaluationPortfolioIdQuery = None,
) -> PolicyEvaluationReviewQueueResponse:
    return get_policy_evaluation_review_queue(
        evaluation_status=evaluation_status,
        portfolio_id=portfolio_id,
    )


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
    responses=POLICY_EVALUATION_READ_RESPONSES,
)
def read_policy_evaluation(
    evaluation_id: PolicyEvaluationIdPath,
) -> PolicyEvaluationRecord:
    return cast(
        PolicyEvaluationRecord,
        run_proposal_operation(lambda: get_policy_evaluation_record(evaluation_id=evaluation_id)),
    )


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
    responses=POLICY_EVALUATION_READ_RESPONSES,
)
def replay_policy_evaluation(
    evaluation_id: PolicyEvaluationIdPath,
    payload: PolicyEvaluationReplayRequest,
) -> PolicyEvaluationReplayResponse:
    return cast(
        PolicyEvaluationReplayResponse,
        run_proposal_operation(
            lambda: replay_policy_evaluation_record(
                evaluation_id=evaluation_id,
                evidence_bundle=payload.evidence_bundle,
            )
        ),
    )


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
    responses=POLICY_EVALUATION_READ_RESPONSES,
)
def read_policy_evaluation_lineage(
    evaluation_id: PolicyEvaluationIdPath,
) -> PolicyEvaluationLineageResponse:
    return cast(
        PolicyEvaluationLineageResponse,
        run_proposal_operation(lambda: get_policy_evaluation_lineage(evaluation_id=evaluation_id)),
    )


@shared.router.get(
    "/advisory/policy-evaluations/{evaluation_id}/diagnostics",
    response_model=PolicyEvaluationDiagnosticsResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Read Policy Evaluation Diagnostics",
    description=(
        "Returns a support-safe diagnostic projection for one policy evaluation, including "
        "sign-off, report-package, AI evidence, replay, safe next-action, and runbook posture "
        "without exposing raw downstream payloads or source evidence."
    ),
    responses=POLICY_EVALUATION_READ_RESPONSES,
)
def read_policy_evaluation_diagnostics(
    evaluation_id: PolicyEvaluationIdPath,
) -> PolicyEvaluationDiagnosticsResponse:
    return cast(
        PolicyEvaluationDiagnosticsResponse,
        run_proposal_operation(
            lambda: get_policy_evaluation_diagnostics(evaluation_id=evaluation_id)
        ),
    )


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
    responses=POLICY_EVALUATION_READ_RESPONSES,
)
def read_policy_sign_off_package(
    evaluation_id: PolicyEvaluationIdPath,
) -> PolicyEvaluationSignOffPackageResponse:
    return cast(
        PolicyEvaluationSignOffPackageResponse,
        run_proposal_operation(
            lambda: get_policy_evaluation_sign_off_package(evaluation_id=evaluation_id)
        ),
    )


__all__ = [
    "read_policy_evaluation_diagnostics",
    "read_policy_evaluation",
    "read_policy_evaluation_lineage",
    "read_policy_review_queue",
    "read_policy_sign_off_package",
    "replay_policy_evaluation",
]
