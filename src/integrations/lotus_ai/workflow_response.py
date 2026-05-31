from __future__ import annotations

from typing import Any


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def extract_workflow_run_id(
    payload: dict[str, Any],
    *,
    max_length: int | None = None,
) -> str | None:
    workflow_pack_run = safe_dict(payload.get("workflow_pack_run"))
    return optional_text(workflow_pack_run.get("run_id"), max_length=max_length)


def extract_model_version(
    result: dict[str, Any],
    *,
    max_length: int | None = None,
) -> str | None:
    return optional_text(result.get("model_version"), max_length=max_length)


def extract_error_detail(
    payload: dict[str, Any],
    *,
    default: str,
    max_length: int | None = None,
) -> str:
    detail = optional_text(payload.get("detail"), max_length=max_length)
    return detail if detail is not None else default


def optional_text(value: Any, *, max_length: int | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    if max_length is None:
        normalized = value.strip()
        return normalized or None

    normalized = " ".join(value.split())
    if not normalized:
        return None
    if len(normalized) <= max_length:
        return normalized
    suffix = "..."
    return normalized[: max_length - len(suffix)].rstrip() + suffix
