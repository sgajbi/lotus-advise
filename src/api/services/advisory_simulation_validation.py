from __future__ import annotations

from src.api.services.advisory_simulation_errors import simulation_validation_exception
from src.core.common.idempotency import normalize_required_idempotency_key


def normalize_simulation_idempotency_key(idempotency_key: str) -> str:
    try:
        return normalize_required_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise simulation_validation_exception(str(exc)) from exc
