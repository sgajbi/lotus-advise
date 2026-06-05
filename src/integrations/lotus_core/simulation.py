import os
from typing import Any, cast

import httpx

from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult
from src.core.proposals.correlation import resolve_correlation_id
from src.integrations.base import sanitized_http_base_url
from src.integrations.lotus_core.contracts import (
    ADVISORY_SIMULATION_CONTRACT_VERSION,
    ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER,
)
from src.integrations.lotus_core.runtime_config import resolve_lotus_core_timeout

_EXECUTION_PATH = "/integration/advisory/proposals/simulate-execution"
_SUITABILITY_CLASSIFICATIONS = {
    "NEW",
    "RESOLVED",
    "PERSISTENT",
    "UNKNOWN_DUE_TO_MISSING_EVIDENCE",
}


class LotusCoreSimulationUnavailableError(Exception):
    def __init__(self, detail: str, *, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _resolve_base_url() -> str:
    configured = sanitized_http_base_url(os.getenv("LOTUS_CORE_BASE_URL"))
    if configured:
        return cast(str, configured)
    raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")


def _resolve_timeout() -> httpx.Timeout:
    return resolve_lotus_core_timeout()


def _normalize_suitability_issue_classification(payload: dict[str, Any]) -> dict[str, Any]:
    suitability = payload.get("suitability")
    if not isinstance(suitability, dict):
        return payload
    issues = suitability.get("issues")
    if not isinstance(issues, list):
        return payload
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        classification = issue.get("classification")
        if isinstance(classification, str) and classification in _SUITABILITY_CLASSIFICATIONS:
            continue
        status_change = issue.get("status_change")
        if isinstance(status_change, str) and status_change in _SUITABILITY_CLASSIFICATIONS:
            issue["classification"] = status_change
            continue
        issue["classification"] = "UNKNOWN_DUE_TO_MISSING_EVIDENCE"
    return payload


def simulate_with_lotus_core(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
    policy_context: dict[str, object] | None = None,
) -> ProposalResult:
    del policy_context
    response = _post_simulation_request(
        request=request,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    payload = _simulation_response_payload(response)
    _validate_response_contract_header(response)
    result: ProposalResult = ProposalResult.model_validate(
        _normalize_suitability_issue_classification(payload)
    )
    _validate_result_contracts(result)
    return result


def _simulation_headers(
    *,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
) -> dict[str, str]:
    headers: dict[str, str] = {
        "X-Correlation-Id": resolve_correlation_id(correlation_id),
        "X-Request-Hash": request_hash,
        ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION,
    }
    outbound_idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    if outbound_idempotency_key is not None:
        headers["Idempotency-Key"] = outbound_idempotency_key
    return headers


def _post_simulation_request(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
) -> httpx.Response:
    url = f"{_resolve_base_url()}{_EXECUTION_PATH}"
    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                url,
                json=request.model_dump(mode="json"),
                headers=_simulation_headers(
                    request_hash=request_hash,
                    idempotency_key=idempotency_key,
                    correlation_id=correlation_id,
                ),
            )
            response.raise_for_status()
            return response
    except httpx.HTTPStatusError as exc:
        raise LotusCoreSimulationUnavailableError(
            _problem_detail_from_status_error(exc),
            status_code=exc.response.status_code,
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE") from exc


def _problem_detail_from_status_error(exc: httpx.HTTPStatusError) -> str:
    detail = f"LOTUS_CORE_SIMULATION_UNAVAILABLE: {exc.response.status_code}"
    try:
        problem_payload = cast(dict[str, Any], exc.response.json())
    except ValueError:
        return detail
    problem_detail = problem_payload.get("detail")
    contract_version = problem_payload.get("contract_version")
    if isinstance(problem_detail, str) and problem_detail:
        detail = problem_detail
    if (
        isinstance(contract_version, str)
        and contract_version != ADVISORY_SIMULATION_CONTRACT_VERSION
    ):
        return (
            "LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH: "
            f"expected {ADVISORY_SIMULATION_CONTRACT_VERSION}, got {contract_version}"
        )
    return detail


def _validate_response_contract_header(response: httpx.Response) -> None:
    response_contract_version = response.headers.get(ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER)
    if response_contract_version != ADVISORY_SIMULATION_CONTRACT_VERSION:
        raise LotusCoreSimulationUnavailableError(
            "LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH: "
            "expected "
            f"{ADVISORY_SIMULATION_CONTRACT_VERSION}, "
            f"got {response_contract_version or 'missing'}"
        )


def _simulation_response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], response.json())
    except ValueError as exc:
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE") from exc


def _validate_result_contracts(result: ProposalResult) -> None:
    if result.lineage.simulation_contract_version != ADVISORY_SIMULATION_CONTRACT_VERSION:
        raise LotusCoreSimulationUnavailableError(
            "LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH: "
            "response lineage did not match the canonical contract version"
        )
    if result.allocation_lens.contract_version != ADVISORY_SIMULATION_CONTRACT_VERSION:
        raise LotusCoreSimulationUnavailableError(
            "LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH: "
            "response allocation lens did not match the canonical contract version"
        )
