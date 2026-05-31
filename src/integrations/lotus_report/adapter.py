import os
import sys
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from src.core.proposals.contract_types import ProposalReportType
from src.core.proposals.models import ProposalReportResponse
from src.integrations.base import (
    IntegrationDependencyState,
    build_dependency_state,
    sanitized_http_base_url,
)
from src.integrations.lotus_core.runtime_config import env_positive_float
from src.integrations.lotus_report.request_mapping import (
    LotusReportRequestMappingError,
    as_mapping,
    build_memo_report_package_job_request,
    build_policy_sign_off_package_job_request,
    build_portfolio_review_job_request,
    build_report_headers,
    normalize_memo_report_job_status,
    normalize_report_job_status,
    report_request_id,
    report_status_path,
    required_string,
)

_PORTFOLIO_REVIEW_PATH = "/reports/portfolio-reviews"


class LotusReportUnavailableError(Exception):
    pass


def build_lotus_report_dependency_state() -> IntegrationDependencyState:
    return build_dependency_state(
        key="lotus_report",
        service_name="lotus-report",
        description="Lotus-branded reporting and portfolio review payload service.",
        base_url_env="LOTUS_REPORT_BASE_URL",
    )


def request_proposal_report_with_lotus_report(*, request: dict[str, Any]) -> ProposalReportResponse:
    main_module = sys.modules.get("src.api.main")
    override = getattr(main_module, "request_proposal_report_with_lotus_report", None)
    if override is not None:
        response = override(request=request)
        return cast(ProposalReportResponse, ProposalReportResponse.model_validate(response))

    base_url = _resolve_base_url()
    try:
        request_id = report_request_id(request)
        report_type = cast(ProposalReportType, required_string(request, "report_type"))
        payload = build_portfolio_review_job_request(request)
        headers = build_report_headers(
            request=request,
            request_id=request_id,
            tenant_id=os.getenv("LOTUS_ADVISE_TENANT_ID"),
        )
    except LotusReportRequestMappingError as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc

    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}{_PORTFOLIO_REVIEW_PATH}",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            response_payload = cast(dict[str, Any], response.json())
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    normalized_report_status_path = report_status_path(response_payload.get("status_url"))
    explanation = {
        "ownership": "REPORTING_OWNED_BY_LOTUS_REPORT",
        "related_version_no": request.get("related_version_no"),
        "include_execution_summary": request.get("include_execution_summary"),
        "include_reviewed_narrative": request.get("include_reviewed_narrative"),
        "report_job_status_url": normalized_report_status_path,
        "report_job_idempotency_key": response_payload.get("idempotency_key"),
        "report_job_request": {
            "portfolio_scope": payload["portfolio_scope"],
            "as_of_date": payload["as_of_date"],
            "requested_output_formats": payload["requested_output_formats"],
        },
    }
    proposal_narrative_package = request.get("proposal_narrative_package")
    if isinstance(proposal_narrative_package, dict):
        explanation["proposal_narrative_package"] = {
            "package_status": proposal_narrative_package.get("package_status"),
            "narrative_id": proposal_narrative_package.get("narrative_id"),
            "review_state": (
                (proposal_narrative_package.get("review") or {}).get("review_state")
                if isinstance(proposal_narrative_package.get("review"), dict)
                else None
            ),
            "source_narrative_hash": (
                (proposal_narrative_package.get("source_lineage") or {}).get(
                    "source_narrative_hash"
                )
                if isinstance(proposal_narrative_package.get("source_lineage"), dict)
                else None
            ),
        }
    return ProposalReportResponse(
        proposal=proposal,
        report_request_id=request_id,
        report_type=report_type,
        report_service="lotus-report",
        status=normalize_report_job_status(response_payload.get("status")),
        generated_at=now,
        report_reference_id=_required_response_string(response_payload, "report_job_id"),
        artifact_url=normalized_report_status_path,
        explanation=explanation,
    )


def request_proposal_memo_report_package_with_lotus_report(
    *, request: dict[str, Any]
) -> ProposalReportResponse:
    main_module = sys.modules.get("src.api.main")
    override = getattr(main_module, "request_proposal_memo_report_package_with_lotus_report", None)
    if override is not None:
        response = override(request=request)
        return cast(ProposalReportResponse, ProposalReportResponse.model_validate(response))

    base_url = _resolve_base_url()
    try:
        request_id = report_request_id(request)
        payload = build_memo_report_package_job_request(request)
        headers = build_report_headers(
            request=request,
            request_id=request_id,
            tenant_id=os.getenv("LOTUS_ADVISE_TENANT_ID"),
        )
    except LotusReportRequestMappingError as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc

    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}{_PORTFOLIO_REVIEW_PATH}",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            response_payload = cast(dict[str, Any], response.json())
            status_payload = _load_report_status(
                client=client,
                base_url=base_url,
                status_url=response_payload.get("status_url"),
                headers=headers,
            )
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    memo_package = cast(dict[str, Any], request.get("proposal_memo_package") or {})
    report_job_id = _required_response_string(response_payload, "report_job_id")
    normalized_report_status_path = report_status_path(response_payload.get("status_url"))
    status = normalize_memo_report_job_status(
        status_payload.get("status") or response_payload.get("status")
    )
    explanation = {
        "ownership": "REPORT_RENDER_ARCHIVE_OWNED_BY_LOTUS_REPORT_RENDER_ARCHIVE",
        "related_version_no": request.get("related_version_no"),
        "proposal_memo_package": {
            "package_status": memo_package.get("package_status"),
            "memo_id": memo_package.get("memo_id"),
            "memo_hash": memo_package.get("memo_hash"),
            "review_action": _as_mapping(memo_package.get("review")).get("review_action"),
            "client_ready_publication": "BLOCKED",
        },
        "report_job_status_url": normalized_report_status_path,
        "report_job_idempotency_key": response_payload.get("idempotency_key"),
        "render": _as_mapping(status_payload.get("render")),
        "archive": _as_mapping(status_payload.get("archive")),
        "report_job_request": {
            "portfolio_scope": payload["portfolio_scope"],
            "as_of_date": payload["as_of_date"],
            "requested_output_formats": payload["requested_output_formats"],
        },
    }
    return ProposalReportResponse(
        proposal=proposal,
        report_request_id=request_id,
        report_type=cast(ProposalReportType, "PORTFOLIO_REVIEW"),
        report_service="lotus-report",
        status=status,
        generated_at=now,
        report_reference_id=report_job_id,
        artifact_url=normalized_report_status_path,
        explanation=explanation,
    )


def request_policy_sign_off_report_package_with_lotus_report(
    *, request: dict[str, Any]
) -> ProposalReportResponse:
    main_module = sys.modules.get("src.api.main")
    override = getattr(
        main_module, "request_policy_sign_off_report_package_with_lotus_report", None
    )
    if override is not None:
        response = override(request=request)
        return cast(ProposalReportResponse, ProposalReportResponse.model_validate(response))

    base_url = _resolve_base_url()
    try:
        request_id = report_request_id(request)
        payload = build_policy_sign_off_package_job_request(request)
        headers = build_report_headers(
            request=request,
            request_id=request_id,
            tenant_id=os.getenv("LOTUS_ADVISE_TENANT_ID"),
        )
    except LotusReportRequestMappingError as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc

    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                f"{base_url}{_PORTFOLIO_REVIEW_PATH}",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            response_payload = cast(dict[str, Any], response.json())
            status_payload = _load_report_status(
                client=client,
                base_url=base_url,
                status_url=response_payload.get("status_url"),
                headers=headers,
            )
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    package = cast(dict[str, Any], request.get("policy_sign_off_package") or {})
    report_job_id = _required_response_string(response_payload, "report_job_id")
    normalized_report_status_path = report_status_path(response_payload.get("status_url"))
    status = normalize_memo_report_job_status(
        status_payload.get("status") or response_payload.get("status")
    )
    explanation = {
        "ownership": "REPORT_RENDER_ARCHIVE_OWNED_BY_LOTUS_REPORT_RENDER_ARCHIVE",
        "related_policy_evaluation_id": request.get("related_policy_evaluation_id"),
        "policy_sign_off_package": {
            "package_status": package.get("package_status"),
            "evaluation_id": _as_mapping(package.get("evaluation")).get("evaluation_id"),
            "evaluation_hash": _as_mapping(package.get("evaluation")).get("evaluation_hash"),
            "client_ready_publication": "BLOCKED",
        },
        "report_job_status_url": normalized_report_status_path,
        "report_job_idempotency_key": response_payload.get("idempotency_key"),
        "render": _as_mapping(status_payload.get("render")),
        "archive": _as_mapping(status_payload.get("archive")),
        "report_job_request": {
            "portfolio_scope": payload["portfolio_scope"],
            "as_of_date": payload["as_of_date"],
            "requested_output_formats": payload["requested_output_formats"],
        },
    }
    return ProposalReportResponse(
        proposal=proposal,
        report_request_id=request_id,
        report_type=cast(ProposalReportType, "PORTFOLIO_REVIEW"),
        report_service="lotus-report",
        status=status,
        generated_at=now,
        report_reference_id=report_job_id,
        artifact_url=normalized_report_status_path,
        explanation=explanation,
    )


def _load_report_status(
    *,
    client: httpx.Client,
    base_url: str,
    status_url: Any,
    headers: dict[str, str],
) -> dict[str, Any]:
    status_path = report_status_path(status_url)
    if status_path is None:
        return {}
    status_response = client.get(f"{base_url}{status_path}", headers=headers)
    status_response.raise_for_status()
    payload = status_response.json()
    return payload if isinstance(payload, dict) else {}


def _resolve_base_url() -> str:
    configured = sanitized_http_base_url(os.getenv("LOTUS_REPORT_BASE_URL"))
    if configured:
        return cast(str, configured)
    raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE")


def _resolve_timeout() -> httpx.Timeout:
    timeout_seconds = env_positive_float("LOTUS_REPORT_TIMEOUT_SECONDS", default=30.0)
    return httpx.Timeout(timeout_seconds)


def _as_mapping(value: Any) -> dict[str, Any]:
    return as_mapping(value)


def _required_response_string(payload: dict[str, Any], key: str) -> str:
    try:
        return required_string(payload, key)
    except LotusReportRequestMappingError as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc
