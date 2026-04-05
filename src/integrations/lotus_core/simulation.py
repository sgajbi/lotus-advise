import os
from typing import Any

import httpx

from src.core.models import ProposalResult, ProposalSimulateRequest

DEFAULT_LOTUS_CORE_BASE_URL = "http://core-query.dev.lotus"
_EXECUTION_PATH = "/integration/advisory/proposals/simulate-execution"


class LotusCoreSimulationUnavailableError(Exception):
    pass


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
            payload: Any = response.json()
    except httpx.HTTPStatusError as exc:
        raise LotusCoreSimulationUnavailableError(
            f"LOTUS_CORE_SIMULATION_UNAVAILABLE: {exc.response.status_code}"
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE") from exc

    return ProposalResult.model_validate(payload)
