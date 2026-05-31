from __future__ import annotations

import os
import time
from typing import Any, cast

import httpx
from pydantic import ValidationError

from src.core.models import (
    ProposalResult,
    ProposalSimulateRequest,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.integrations.base import sanitized_http_base_url
from src.integrations.lotus_core.runtime_config import env_positive_float, env_positive_int
from src.integrations.lotus_risk.concentration_request import build_concentration_request
from src.integrations.lotus_risk.concentration_response import (
    LotusRiskConcentrationResponse,
    apply_concentration_response,
)

_CONCENTRATION_PATH = "/analytics/risk/concentration"


class LotusRiskEnrichmentUnavailableError(Exception):
    pass


def _resolve_base_url() -> str:
    configured = sanitized_http_base_url(os.getenv("LOTUS_RISK_BASE_URL"))
    if configured:
        return cast(str, configured)
    raise LotusRiskEnrichmentUnavailableError("LOTUS_RISK_ENRICHMENT_UNAVAILABLE")


def _resolve_timeout() -> httpx.Timeout:
    return httpx.Timeout(env_positive_float("LOTUS_RISK_TIMEOUT_SECONDS", default=10.0))


def _resolve_retry_attempts() -> int:
    attempts = env_positive_int("LOTUS_RISK_RETRY_ATTEMPTS", default=2)
    return min(int(attempts), 5)


def _is_retryable_http_error(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return bool(status_code >= 500 or status_code == 429)
    return True


def _request_concentration_response(
    *,
    payload: dict[str, Any],
    correlation_id: str,
) -> LotusRiskConcentrationResponse:
    attempts = _resolve_retry_attempts()
    base_url = _resolve_base_url()
    outbound_correlation_id = resolve_correlation_id(correlation_id)
    last_error: Exception | None = None
    with httpx.Client(timeout=_resolve_timeout()) as client:
        for attempt in range(1, attempts + 1):
            try:
                response = client.post(
                    f"{base_url}{_CONCENTRATION_PATH}",
                    json=payload,
                    headers={"X-Correlation-Id": outbound_correlation_id},
                )
                response.raise_for_status()
                body = cast(dict[str, Any], response.json())
                concentration = cast(
                    LotusRiskConcentrationResponse,
                    LotusRiskConcentrationResponse.model_validate(body),
                )
                return concentration
            except ValidationError as exc:
                raise LotusRiskEnrichmentUnavailableError(
                    "LOTUS_RISK_ENRICHMENT_UNAVAILABLE"
                ) from exc
            except ValueError as exc:
                raise LotusRiskEnrichmentUnavailableError(
                    "LOTUS_RISK_ENRICHMENT_UNAVAILABLE"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= attempts or not _is_retryable_http_error(exc):
                    break
                time.sleep(_retry_delay_seconds(attempt=attempt))
    raise LotusRiskEnrichmentUnavailableError("LOTUS_RISK_ENRICHMENT_UNAVAILABLE") from last_error


def _resolve_retry_backoff_seconds() -> Any:
    return min(env_positive_float("LOTUS_RISK_RETRY_BACKOFF_SECONDS", default=0.1), 2.0)


def _retry_delay_seconds(*, attempt: int) -> Any:
    return min(_resolve_retry_backoff_seconds() * attempt, 2.0)


def enrich_with_lotus_risk(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    correlation_id: str,
    resolved_as_of: str | None = None,
    input_mode: str | None = None,
) -> ProposalResult:
    payload = build_concentration_request(
        request=request,
        proposal_result=proposal_result,
        resolved_as_of=resolved_as_of,
        input_mode=input_mode,
    )
    concentration = _request_concentration_response(
        payload=payload,
        correlation_id=correlation_id,
    )
    return apply_concentration_response(
        proposal_result=proposal_result,
        concentration=concentration,
    )
