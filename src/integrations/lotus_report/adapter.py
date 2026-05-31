import os
import sys
from collections.abc import Callable
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
    build_memo_report_package_job_request,
    build_policy_sign_off_package_job_request,
    build_portfolio_review_job_request,
    build_report_headers,
    report_request_id,
    report_status_path,
    required_string,
)
from src.integrations.lotus_report.response_projection import (
    build_memo_report_package_response,
    build_policy_sign_off_report_package_response,
    build_portfolio_review_response,
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

    return _project_response(
        build_portfolio_review_response,
        request=request,
        request_id=request_id,
        report_type=report_type,
        report_job_request=payload,
        response_payload=response_payload,
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

    return _project_response(
        build_memo_report_package_response,
        request=request,
        request_id=request_id,
        report_job_request=payload,
        response_payload=response_payload,
        status_payload=status_payload,
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

    return _project_response(
        build_policy_sign_off_report_package_response,
        request=request,
        request_id=request_id,
        report_job_request=payload,
        response_payload=response_payload,
        status_payload=status_payload,
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


def _project_response(
    projector: Callable[..., ProposalReportResponse], **kwargs: Any
) -> ProposalReportResponse:
    try:
        return projector(**kwargs)
    except LotusReportRequestMappingError as exc:
        raise LotusReportUnavailableError("LOTUS_REPORT_REQUEST_UNAVAILABLE") from exc
