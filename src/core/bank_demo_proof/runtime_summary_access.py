from __future__ import annotations

from typing import Any


def dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"RFC0028_BACKEND_PROOF_FIELD_MISSING: {key}")
    return value


def value_at(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"RFC0028_BACKEND_PROOF_FIELD_MISSING: {dotted_path}")
        current = current[part]
    return current


def select_fields(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys}
