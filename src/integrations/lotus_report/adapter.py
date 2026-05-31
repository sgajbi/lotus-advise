import os
import re
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

_PORTFOLIO_REVIEW_PATH = "/reports/portfolio-reviews"
_SNAPSHOT_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


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
    request_id = _required_string(request, "report_request_id")
    report_type = cast(ProposalReportType, _required_string(request, "report_type"))
    payload = _build_portfolio_review_job_request(request)
    headers = {
        "Idempotency-Key": request_id,
        "X-Actor-Id": _optional_string(request.get("requested_by")) or "lotus-advise",
        "X-Caller-Application": "lotus-advise",
        "X-Tenant-Id": "default",
        "X-Region": _proposal_region(request),
        "X-Booking-Center-Code": _proposal_region(request),
        "X-Role": "advisor",
    }

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
    explanation = {
        "ownership": "REPORTING_OWNED_BY_LOTUS_REPORT",
        "related_version_no": request.get("related_version_no"),
        "include_execution_summary": request.get("include_execution_summary"),
        "include_reviewed_narrative": request.get("include_reviewed_narrative"),
        "report_job_status_url": response_payload.get("status_url"),
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
        status=_normalize_report_job_status(response_payload.get("status")),
        generated_at=now,
        report_reference_id=_required_string(response_payload, "report_job_id"),
        artifact_url=response_payload.get("status_url"),
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
    request_id = _required_string(request, "report_request_id")
    payload = _build_memo_report_package_job_request(request)
    headers = {
        "Idempotency-Key": request_id,
        "X-Actor-Id": _optional_string(request.get("requested_by")) or "lotus-advise",
        "X-Caller-Application": "lotus-advise",
        "X-Tenant-Id": "default",
        "X-Region": _proposal_region(request),
        "X-Booking-Center-Code": _proposal_region(request),
        "X-Role": "advisor",
    }

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
    report_job_id = _required_string(response_payload, "report_job_id")
    status = _normalize_memo_report_job_status(
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
        "report_job_status_url": response_payload.get("status_url"),
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
        artifact_url=response_payload.get("status_url"),
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
    request_id = _required_string(request, "report_request_id")
    payload = _build_policy_sign_off_package_job_request(request)
    headers = {
        "Idempotency-Key": request_id,
        "X-Actor-Id": _optional_string(request.get("requested_by")) or "lotus-advise",
        "X-Caller-Application": "lotus-advise",
        "X-Tenant-Id": "default",
        "X-Region": _proposal_region(request),
        "X-Booking-Center-Code": _proposal_region(request),
        "X-Role": "advisor",
    }

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
    report_job_id = _required_string(response_payload, "report_job_id")
    status = _normalize_memo_report_job_status(
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
        "report_job_status_url": response_payload.get("status_url"),
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
        artifact_url=response_payload.get("status_url"),
        explanation=explanation,
    )


def _load_report_status(
    *,
    client: httpx.Client,
    base_url: str,
    status_url: Any,
    headers: dict[str, str],
) -> dict[str, Any]:
    normalized_status_url = _optional_string(status_url)
    if not normalized_status_url:
        return {}
    status_response = client.get(f"{base_url}{normalized_status_url}", headers=headers)
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


def _build_portfolio_review_job_request(request: dict[str, Any]) -> dict[str, Any]:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    portfolio_id = _required_string(proposal, "portfolio_id")
    related_version_no = request.get("related_version_no")
    proposal_narrative_package = request.get("proposal_narrative_package")
    payload: dict[str, Any] = {
        "portfolio_scope": {"portfolio_ids": [portfolio_id]},
        "as_of_date": _extract_report_as_of_date(request),
        "requested_output_formats": ["json"],
        "reporting_currency": _extract_reporting_currency(request),
        "options": {
            "source_system": "lotus-advise",
            "source_proposal_id": proposal.get("proposal_id"),
            "source_report_type": request.get("report_type"),
            "requested_by": request.get("requested_by"),
            "related_version_no": related_version_no,
            "include_execution_summary": request.get("include_execution_summary"),
            "include_reviewed_narrative": request.get("include_reviewed_narrative"),
        },
    }
    if isinstance(proposal_narrative_package, dict):
        payload["proposal_narrative_package"] = proposal_narrative_package
    return payload


def _build_memo_report_package_job_request(request: dict[str, Any]) -> dict[str, Any]:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    portfolio_id = _required_string(proposal, "portfolio_id")
    requested_output_formats = request.get("requested_output_formats")
    if not isinstance(requested_output_formats, list) or not requested_output_formats:
        requested_output_formats = ["pdf"]
    payload = {
        "portfolio_scope": {"portfolio_ids": [portfolio_id]},
        "as_of_date": _extract_report_as_of_date(request),
        "requested_output_formats": [
            str(item).strip().lower()
            for item in requested_output_formats
            if str(item).strip().lower() in {"pdf", "json"}
        ]
        or ["pdf"],
        "reporting_currency": _extract_reporting_currency(request),
        "options": {
            "source_system": "lotus-advise",
            "source_proposal_id": proposal.get("proposal_id"),
            "source_report_type": "ADVISORY_PROPOSAL_MEMO",
            "requested_by": request.get("requested_by"),
            "related_version_no": request.get("related_version_no"),
            "retention_policy_id": _as_mapping(request.get("reason")).get("retention_policy_id"),
        },
        "proposal_memo_package": request.get("proposal_memo_package"),
    }
    return payload


def _build_policy_sign_off_package_job_request(request: dict[str, Any]) -> dict[str, Any]:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    portfolio_id = _required_string(proposal, "portfolio_id")
    requested_output_formats = request.get("requested_output_formats")
    if not isinstance(requested_output_formats, list) or not requested_output_formats:
        requested_output_formats = ["pdf"]
    payload = {
        "portfolio_scope": {"portfolio_ids": [portfolio_id]},
        "as_of_date": _extract_report_as_of_date(request),
        "requested_output_formats": [
            str(item).strip().lower()
            for item in requested_output_formats
            if str(item).strip().lower() in {"pdf", "json"}
        ]
        or ["pdf"],
        "reporting_currency": _extract_reporting_currency(request),
        "options": {
            "source_system": "lotus-advise",
            "source_proposal_id": proposal.get("proposal_id"),
            "source_report_type": "ADVISORY_POLICY_SIGN_OFF_PACKAGE",
            "requested_by": request.get("requested_by"),
            "related_policy_evaluation_id": request.get("related_policy_evaluation_id"),
            "retention_policy_id": _as_mapping(request.get("reason")).get("retention_policy_id"),
        },
        "policy_sign_off_package": request.get("policy_sign_off_package"),
    }
    return payload


def _extract_report_as_of_date(request: dict[str, Any]) -> str:
    proposal_version = cast(dict[str, Any], request.get("proposal_version") or {})
    proposal_result = cast(dict[str, Any], proposal_version.get("proposal_result") or {})
    direct_date = _find_first_key_value(
        proposal_result,
        keys={"as_of_date", "report_end_date", "valuation_date"},
    )
    if direct_date is not None:
        return direct_date
    lineage = proposal_result.get("lineage")
    if isinstance(lineage, dict):
        for value in lineage.values():
            if isinstance(value, str):
                match = _SNAPSHOT_DATE_PATTERN.search(value)
                if match:
                    return match.group(0)
    return datetime.now(UTC).date().isoformat()


def _extract_reporting_currency(request: dict[str, Any]) -> str | None:
    proposal_version = cast(dict[str, Any], request.get("proposal_version") or {})
    proposal_result = cast(dict[str, Any], proposal_version.get("proposal_result") or {})
    before = proposal_result.get("before")
    if isinstance(before, dict):
        total_value = before.get("total_value")
        if isinstance(total_value, dict):
            currency = _optional_string(total_value.get("currency"))
            if currency:
                return currency
    return "USD"


def _find_first_key_value(payload: Any, *, keys: set[str]) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys:
                normalized = _optional_string(value)
                if normalized and _SNAPSHOT_DATE_PATTERN.fullmatch(normalized):
                    return normalized
            nested = _find_first_key_value(value, keys=keys)
            if nested:
                return nested
    if isinstance(payload, list):
        for value in payload:
            nested = _find_first_key_value(value, keys=keys)
            if nested:
                return nested
    return None


def _proposal_region(request: dict[str, Any]) -> str:
    proposal = cast(dict[str, Any], request.get("proposal") or {})
    return _optional_string(proposal.get("jurisdiction")) or "SG"


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_report_job_status(value: Any) -> str:
    normalized = _optional_string(value)
    if normalized in {"data_ready", "completed", "archived", "completed_with_warnings"}:
        return "READY"
    if normalized:
        return normalized.upper()
    return "ACCEPTED"


def _normalize_memo_report_job_status(value: Any) -> str:
    normalized = _optional_string(value)
    if normalized == "archived":
        return "ARCHIVED"
    return _normalize_report_job_status(value)


def _required_string(payload: dict[str, Any], key: str) -> str:
    normalized = _optional_string(payload.get(key))
    if normalized is None:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE")
    return normalized


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
