import os
import sys
import time
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
from src.integrations.lotus_report.job_status import is_report_package_terminal_status
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
_REPORT_STATUS_POLLING_TIMEOUT = "REPORT_STATUS_POLLING_TIMEOUT"
_REPORT_STATUS_URL_UNAVAILABLE = "REPORT_STATUS_URL_UNAVAILABLE"
_REPORT_STATUS_PAYLOAD_INVALID = "REPORT_STATUS_PAYLOAD_INVALID"
_REPORT_STATUS_HTTP_UNAVAILABLE = "REPORT_STATUS_HTTP_UNAVAILABLE"


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
        return _unavailable_status_payload(_REPORT_STATUS_URL_UNAVAILABLE)
    attempts = _resolve_status_poll_attempts()
    backoff_seconds = _resolve_status_poll_backoff_seconds()
    last_payload: dict[str, Any] = {}
    for attempt in range(1, attempts + 1):
        payload = _load_report_status_once(
            client=client,
            url=f"{base_url}{status_path}",
            headers=headers,
            attempt=attempt,
        )
        if _status_payload_unavailable(payload) or is_report_package_terminal_status(
            payload.get("status")
        ):
            return payload
        last_payload = payload
        if attempt < attempts and backoff_seconds > 0:
            time.sleep(backoff_seconds)
    return _with_poll_metadata(
        last_payload or _unavailable_status_payload(_REPORT_STATUS_PAYLOAD_INVALID),
        reason=_REPORT_STATUS_POLLING_TIMEOUT,
        attempts=attempts,
    )


def _load_report_status_once(
    *,
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    attempt: int,
) -> dict[str, Any]:
    try:
        status_response = client.get(url, headers=headers)
        status_response.raise_for_status()
        payload = status_response.json()
    except httpx.HTTPStatusError as exc:
        return _unavailable_status_payload(
            f"REPORT_STATUS_HTTP_{exc.response.status_code}",
            attempts=attempt,
        )
    except httpx.HTTPError:
        return _unavailable_status_payload(_REPORT_STATUS_HTTP_UNAVAILABLE, attempts=attempt)
    except ValueError:
        return _unavailable_status_payload(_REPORT_STATUS_PAYLOAD_INVALID, attempts=attempt)
    if not isinstance(payload, dict):
        return _unavailable_status_payload(_REPORT_STATUS_PAYLOAD_INVALID, attempts=attempt)
    return _with_poll_metadata(payload, attempts=attempt)


def _unavailable_status_payload(reason: str, *, attempts: int = 0) -> dict[str, Any]:
    return {
        "status": "report_status_unavailable",
        "report_job_status_unavailable_reason": reason,
        "report_job_poll_attempts": attempts,
    }


def _with_poll_metadata(
    payload: dict[str, Any],
    *,
    attempts: int,
    reason: str | None = None,
) -> dict[str, Any]:
    enriched = dict(payload)
    enriched["report_job_poll_attempts"] = attempts
    if reason is not None:
        enriched["report_job_pending_reason"] = reason
    return enriched


def _status_payload_unavailable(payload: dict[str, Any]) -> bool:
    return payload.get("status") == "report_status_unavailable"


def _resolve_status_poll_attempts() -> int:
    raw_value = os.getenv("LOTUS_REPORT_STATUS_POLL_ATTEMPTS")
    if raw_value is None:
        return 3
    try:
        configured = int(raw_value)
    except ValueError:
        return 3
    return min(max(configured, 1), 5)


def _resolve_status_poll_backoff_seconds() -> float:
    return env_positive_float("LOTUS_REPORT_STATUS_POLL_BACKOFF_SECONDS", default=0.0)


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
