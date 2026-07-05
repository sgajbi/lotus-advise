from typing import cast

from fastapi import status

import src.api.proposals.router as shared
from src.api.observability import record_policy_evaluation_operation
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.policy_evaluation_parameters import (
    PolicyEvaluationAiEvidenceIdempotencyKeyHeader,
    PolicyEvaluationIdPath,
    PolicyEvaluationReportPackageIdempotencyKeyHeader,
)
from src.api.proposals.policy_evaluation_responses import (
    POLICY_AI_EVIDENCE_RESPONSES,
    POLICY_REPORT_PACKAGE_RESPONSES,
)
from src.api.proposals.report_errors import run_lotus_report_operation
from src.core.policy_packs import (
    PolicyEvaluationAiEvidenceRequest,
    PolicyEvaluationAiEvidenceResponse,
    PolicyEvaluationReportPackageRequest,
    PolicyEvaluationReportPackageResponse,
)
from src.core.proposals.exceptions import ProposalIdempotencyConflictError, ProposalValidationError
from src.core.proposals.identifiers import new_report_request_id
from src.runtime.policy_evaluation_clients import (
    get_policy_ai_evidence_client,
    get_policy_report_package_client,
)


@shared.router.post(
    "/advisory/policy-evaluations/{evaluation_id}/report-packages",
    response_model=PolicyEvaluationReportPackageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Request Policy Report Package",
    description=(
        "Requests lotus-report materialization for a signed-off policy evaluation package, submits "
        "approval, disclosure, consent, conflict, and sign-off evidence for deterministic "
        "report/render/archive handling, and records returned report, render, and archive "
        "references in policy lineage. Client-ready document release remains blocked."
    ),
    responses=POLICY_REPORT_PACKAGE_RESPONSES,
)
def request_policy_report_package(
    evaluation_id: PolicyEvaluationIdPath,
    payload: PolicyEvaluationReportPackageRequest,
    idempotency_key: PolicyEvaluationReportPackageIdempotencyKeyHeader,
) -> PolicyEvaluationReportPackageResponse:
    return cast(
        PolicyEvaluationReportPackageResponse,
        run_lotus_report_operation(
            lambda: run_proposal_operation(
                lambda: _request_policy_report_package_with_telemetry(
                    evaluation_id=evaluation_id,
                    payload=payload,
                    idempotency_key=idempotency_key,
                )
            ),
            on_unavailable=_record_policy_report_unavailable,
        ),
    )


@shared.router.post(
    "/advisory/policy-evaluations/{evaluation_id}/ai-evidence",
    response_model=PolicyEvaluationAiEvidenceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Evaluation"],
    summary="Request Policy AI Evidence",
    description=(
        "Requests bounded AI policy-evidence commentary for a finalized policy evaluation. The "
        "operation sends only redacted policy status, rule-result, workflow, source-ref, and "
        "append-only event evidence to lotus-ai, records AI lineage, requires human review, and "
        "cannot alter policy status, rule results, approvals, waivers, disclosures, consent, or "
        "client-ready publication posture."
    ),
    responses=POLICY_AI_EVIDENCE_RESPONSES,
)
def request_policy_ai_evidence(
    evaluation_id: PolicyEvaluationIdPath,
    payload: PolicyEvaluationAiEvidenceRequest,
    idempotency_key: PolicyEvaluationAiEvidenceIdempotencyKeyHeader,
) -> PolicyEvaluationAiEvidenceResponse:
    return cast(
        PolicyEvaluationAiEvidenceResponse,
        run_proposal_operation(
            lambda: _request_policy_ai_evidence_with_telemetry(
                evaluation_id=evaluation_id,
                payload=payload,
                idempotency_key=idempotency_key,
            )
        ),
    )


def _request_policy_report_package_with_telemetry(
    *,
    evaluation_id: str,
    payload: PolicyEvaluationReportPackageRequest,
    idempotency_key: str,
) -> PolicyEvaluationReportPackageResponse:
    service = shared.get_policy_evidence_application_service()
    try:
        response = service.request_policy_evaluation_report_package(
            evaluation_id=evaluation_id,
            payload=payload,
            report_request_id=new_report_request_id(),
            report_client=get_policy_report_package_client(),
            idempotency_key=idempotency_key,
        )
    except ProposalIdempotencyConflictError:
        _record_policy_package_operation("report_package_request", "conflict", "idempotency")
        raise
    except ProposalValidationError as exc:
        _record_policy_package_operation(
            "report_package_request",
            "validation_blocked",
            _policy_operation_reason(exc),
        )
        raise
    _record_policy_package_operation(
        "report_package_request",
        "replay" if response.replayed else "success",
        "replayed" if response.replayed else "recorded",
        dependency="lotus_report",
    )
    return response


def _record_policy_report_unavailable() -> None:
    _record_policy_package_operation(
        "report_package_request",
        "dependency_unavailable",
        "lotus_report_unavailable",
        dependency="lotus_report",
    )


def _request_policy_ai_evidence_with_telemetry(
    *,
    evaluation_id: str,
    payload: PolicyEvaluationAiEvidenceRequest,
    idempotency_key: str,
) -> PolicyEvaluationAiEvidenceResponse:
    try:
        response = (
            shared.get_policy_evidence_application_service().request_policy_evaluation_ai_evidence(
                evaluation_id=evaluation_id,
                payload=payload,
                ai_client=get_policy_ai_evidence_client(),
                idempotency_key=idempotency_key,
            )
        )
    except ProposalIdempotencyConflictError:
        _record_policy_package_operation("ai_evidence_request", "conflict", "idempotency")
        raise
    except ProposalValidationError as exc:
        _record_policy_package_operation(
            "ai_evidence_request",
            "validation_blocked",
            _policy_operation_reason(exc),
        )
        raise
    ai_status = str(response.policy_evidence.get("status") or "").lower()
    _record_policy_package_operation(
        "ai_evidence_request",
        "replay" if response.replayed else ai_status or "success",
        "replayed" if response.replayed else ai_status or "recorded",
        dependency="lotus_ai",
    )
    return response


def _record_policy_package_operation(
    operation: str,
    status: str,
    reason: str,
    *,
    dependency: str = "none",
) -> None:
    record_policy_evaluation_operation(
        operation=f"policy_evaluation.{operation}",
        status=status,
        reason=reason,
        dependency=dependency,
    )


def _policy_operation_reason(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__


__all__ = [
    "request_policy_ai_evidence",
    "request_policy_report_package",
]
