from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from src.core.proposals.contract_types import ProposalReportType
from src.core.proposals.models import ProposalReportResponse
from src.integrations.lotus_report.request_mapping import (
    as_mapping,
    normalize_memo_report_job_status,
    normalize_report_job_status,
    report_status_path,
    required_string,
)


def build_portfolio_review_response(
    *,
    request: dict[str, Any],
    request_id: str,
    report_type: ProposalReportType,
    report_job_request: dict[str, Any],
    response_payload: dict[str, Any],
) -> ProposalReportResponse:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    normalized_report_status_path = report_status_path(response_payload.get("status_url"))
    explanation = {
        "ownership": "REPORTING_OWNED_BY_LOTUS_REPORT",
        "related_version_no": request.get("related_version_no"),
        "include_execution_summary": request.get("include_execution_summary"),
        "include_reviewed_narrative": request.get("include_reviewed_narrative"),
        "report_job_status_url": normalized_report_status_path,
        "report_job_idempotency_key": response_payload.get("idempotency_key"),
        "report_job_request": _report_job_request_summary(report_job_request),
    }
    proposal_narrative_package = request.get("proposal_narrative_package")
    if isinstance(proposal_narrative_package, dict):
        explanation["proposal_narrative_package"] = {
            "package_status": proposal_narrative_package.get("package_status"),
            "narrative_id": proposal_narrative_package.get("narrative_id"),
            "review_state": as_mapping(proposal_narrative_package.get("review")).get(
                "review_state"
            ),
            "source_narrative_hash": as_mapping(
                proposal_narrative_package.get("source_lineage")
            ).get("source_narrative_hash"),
        }
    return ProposalReportResponse(
        proposal=proposal,
        report_request_id=request_id,
        report_type=report_type,
        report_service="lotus-report",
        status=normalize_report_job_status(response_payload.get("status")),
        generated_at=_generated_at(),
        report_reference_id=required_string(response_payload, "report_job_id"),
        artifact_url=normalized_report_status_path,
        explanation=explanation,
    )


def build_memo_report_package_response(
    *,
    request: dict[str, Any],
    request_id: str,
    report_job_request: dict[str, Any],
    response_payload: dict[str, Any],
    status_payload: dict[str, Any],
) -> ProposalReportResponse:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    memo_package = as_mapping(request.get("proposal_memo_package"))
    normalized_report_status_path = report_status_path(response_payload.get("status_url"))
    explanation = {
        "ownership": "REPORT_RENDER_ARCHIVE_OWNED_BY_LOTUS_REPORT_RENDER_ARCHIVE",
        "related_version_no": request.get("related_version_no"),
        "proposal_memo_package": {
            "package_status": memo_package.get("package_status"),
            "memo_id": memo_package.get("memo_id"),
            "memo_hash": memo_package.get("memo_hash"),
            "review_action": as_mapping(memo_package.get("review")).get("review_action"),
            "client_ready_publication": "BLOCKED",
        },
        "report_job_status_url": normalized_report_status_path,
        "report_job_idempotency_key": response_payload.get("idempotency_key"),
        "render": as_mapping(status_payload.get("render")),
        "archive": as_mapping(status_payload.get("archive")),
        "report_job_request": _report_job_request_summary(report_job_request),
    }
    return ProposalReportResponse(
        proposal=proposal,
        report_request_id=request_id,
        report_type=cast(ProposalReportType, "PORTFOLIO_REVIEW"),
        report_service="lotus-report",
        status=normalize_memo_report_job_status(
            status_payload.get("status") or response_payload.get("status")
        ),
        generated_at=_generated_at(),
        report_reference_id=required_string(response_payload, "report_job_id"),
        artifact_url=normalized_report_status_path,
        explanation=explanation,
    )


def build_policy_sign_off_report_package_response(
    *,
    request: dict[str, Any],
    request_id: str,
    report_job_request: dict[str, Any],
    response_payload: dict[str, Any],
    status_payload: dict[str, Any],
) -> ProposalReportResponse:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    package = as_mapping(request.get("policy_sign_off_package"))
    normalized_report_status_path = report_status_path(response_payload.get("status_url"))
    explanation = {
        "ownership": "REPORT_RENDER_ARCHIVE_OWNED_BY_LOTUS_REPORT_RENDER_ARCHIVE",
        "related_policy_evaluation_id": request.get("related_policy_evaluation_id"),
        "policy_sign_off_package": {
            "package_status": package.get("package_status"),
            "evaluation_id": as_mapping(package.get("evaluation")).get("evaluation_id"),
            "evaluation_hash": as_mapping(package.get("evaluation")).get("evaluation_hash"),
            "client_ready_publication": "BLOCKED",
        },
        "report_job_status_url": normalized_report_status_path,
        "report_job_idempotency_key": response_payload.get("idempotency_key"),
        "render": as_mapping(status_payload.get("render")),
        "archive": as_mapping(status_payload.get("archive")),
        "report_job_request": _report_job_request_summary(report_job_request),
    }
    return ProposalReportResponse(
        proposal=proposal,
        report_request_id=request_id,
        report_type=cast(ProposalReportType, "PORTFOLIO_REVIEW"),
        report_service="lotus-report",
        status=normalize_memo_report_job_status(
            status_payload.get("status") or response_payload.get("status")
        ),
        generated_at=_generated_at(),
        report_reference_id=required_string(response_payload, "report_job_id"),
        artifact_url=normalized_report_status_path,
        explanation=explanation,
    )


def _report_job_request_summary(report_job_request: dict[str, Any]) -> dict[str, Any]:
    return {
        "portfolio_scope": report_job_request["portfolio_scope"],
        "as_of_date": report_job_request["as_of_date"],
        "requested_output_formats": report_job_request["requested_output_formats"],
    }


def _generated_at() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
