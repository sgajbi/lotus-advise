import os
from typing import Any, cast

import httpx

from src.core.models import ProposalResult, ProposalSimulateRequest
from src.integrations.lotus_core.contracts import (
    ADVISORY_SIMULATION_CONTRACT_VERSION,
    ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER,
)

DEFAULT_LOTUS_CORE_BASE_URL = "http://core-query.dev.lotus"
_EXECUTION_PATH = "/integration/advisory/proposals/simulate-execution"


class LotusCoreSimulationUnavailableError(Exception):
    def __init__(self, detail: str, *, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _resolve_base_url() -> str:
    configured = os.getenv("LOTUS_CORE_BASE_URL")
    if configured:
        return configured.rstrip("/")
    raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")


def _resolve_timeout() -> httpx.Timeout:
    timeout_seconds = float(os.getenv("LOTUS_CORE_TIMEOUT_SECONDS", "10"))
    return httpx.Timeout(timeout_seconds)


def simulate_with_lotus_core(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
) -> ProposalResult:
    headers: dict[str, str] = {
        "X-Correlation-Id": correlation_id,
        "X-Request-Hash": request_hash,
        ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER: ADVISORY_SIMULATION_CONTRACT_VERSION,
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    url = f"{_resolve_base_url()}{_EXECUTION_PATH}"
    try:
        with httpx.Client(timeout=_resolve_timeout()) as client:
            response = client.post(
                url,
                json=request.model_dump(mode="json"),
                headers=headers,
            )
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
    except httpx.HTTPStatusError as exc:
        detail = f"LOTUS_CORE_SIMULATION_UNAVAILABLE: {exc.response.status_code}"
        try:
            problem_payload = cast(dict[str, Any], exc.response.json())
            problem_detail = problem_payload.get("detail")
            contract_version = problem_payload.get("contract_version")
            if isinstance(problem_detail, str) and problem_detail:
                detail = problem_detail
            if (
                isinstance(contract_version, str)
                and contract_version != ADVISORY_SIMULATION_CONTRACT_VERSION
            ):
                detail = (
                    "LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH: "
                    f"expected {ADVISORY_SIMULATION_CONTRACT_VERSION}, got {contract_version}"
                )
        except ValueError:
            pass
        raise LotusCoreSimulationUnavailableError(
            detail,
            status_code=exc.response.status_code,
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE") from exc

    response_contract_version = response.headers.get(ADVISORY_SIMULATION_CONTRACT_VERSION_HEADER)
    if response_contract_version != ADVISORY_SIMULATION_CONTRACT_VERSION:
        raise LotusCoreSimulationUnavailableError(
            "LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH: "
            "expected "
            f"{ADVISORY_SIMULATION_CONTRACT_VERSION}, "
            f"got {response_contract_version or 'missing'}"
        )

    result: ProposalResult = ProposalResult.model_validate(payload)
    if result.lineage.simulation_contract_version != ADVISORY_SIMULATION_CONTRACT_VERSION:
        raise LotusCoreSimulationUnavailableError(
            "LOTUS_CORE_SIMULATION_CONTRACT_VERSION_MISMATCH: "
            "response lineage did not match the canonical contract version"
        )
    return result
