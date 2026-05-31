from __future__ import annotations

import os
import time
from decimal import Decimal
from typing import Any, cast

import httpx
from pydantic import BaseModel, Field, ValidationError

from src.core.models import (
    ProposalResult,
    ProposalSimulateRequest,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.integrations.base import sanitized_http_base_url
from src.integrations.lotus_core.runtime_config import env_positive_float, env_positive_int
from src.integrations.lotus_risk.concentration_request import build_concentration_request

_CONCENTRATION_PATH = "/analytics/risk/concentration"


class LotusRiskEnrichmentUnavailableError(Exception):
    pass


class LotusRiskConcentrationRiskProxy(BaseModel):
    hhi_current: Decimal
    hhi_proposed: Decimal
    hhi_delta: Decimal


class LotusRiskPositionDescriptor(BaseModel):
    security_id: str | None = None
    security_name: str | None = None
    weight: Decimal


class LotusRiskIssuerDescriptor(BaseModel):
    issuer_id: str | None = None
    issuer_name: str | None = None
    weight: Decimal


class LotusRiskSinglePositionConcentration(BaseModel):
    top_position_weight_current: Decimal
    top_position_weight_proposed: Decimal
    top_position_weight_delta: Decimal
    top_n_cumulative_weight_current: Decimal
    top_n_cumulative_weight_proposed: Decimal
    top_n_cumulative_weight_delta: Decimal
    top_n: int
    top_position_current: LotusRiskPositionDescriptor | None = None
    top_position_proposed: LotusRiskPositionDescriptor | None = None


class LotusRiskIssuerConcentration(BaseModel):
    hhi_current: Decimal
    hhi_proposed: Decimal
    hhi_delta: Decimal
    top_issuer_weight_current: Decimal
    top_issuer_weight_proposed: Decimal
    top_issuer_weight_delta: Decimal
    coverage_status: str
    coverage_ratio_current: Decimal | None = None
    coverage_ratio_proposed: Decimal | None = None
    covered_position_count_current: int
    covered_position_count_proposed: int
    total_position_count_current: int
    total_position_count_proposed: int
    uncovered_position_count_current: int | None = None
    uncovered_position_count_proposed: int | None = None
    top_issuer_current: LotusRiskIssuerDescriptor | None = None
    top_issuer_proposed: LotusRiskIssuerDescriptor | None = None
    note: str | None = None


class LotusRiskConcentrationResponse(BaseModel):
    source_service: str = Field(pattern="^lotus-risk$")
    input_mode: str = Field(pattern="^(simulation|stateless)$")
    risk_proxy: LotusRiskConcentrationRiskProxy
    single_position_concentration: LotusRiskSinglePositionConcentration
    issuer_concentration: LotusRiskIssuerConcentration
    valuation_context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


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


def _apply_concentration_response(
    *,
    proposal_result: ProposalResult,
    concentration: LotusRiskConcentrationResponse,
) -> ProposalResult:
    explanation = dict(proposal_result.explanation)
    explanation["risk_lens"] = {
        "source_service": concentration.source_service,
        "input_mode": concentration.input_mode,
        "risk_proxy": concentration.risk_proxy.model_dump(mode="json"),
        "single_position_concentration": (
            concentration.single_position_concentration.model_dump(mode="json")
        ),
        "issuer_concentration": concentration.issuer_concentration.model_dump(mode="json"),
        "valuation_context": concentration.valuation_context,
        "metadata": concentration.metadata,
    }
    proposal_result.explanation = explanation
    return proposal_result


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
    return _apply_concentration_response(
        proposal_result=proposal_result,
        concentration=concentration,
    )
