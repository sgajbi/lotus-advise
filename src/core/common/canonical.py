import hashlib
import json
from copy import deepcopy
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def hash_canonical_payload(payload: Any) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def strip_keys(payload: Any, *, exclude: set[str]) -> Any:
    if isinstance(payload, dict):
        return _strip_mapping_keys(payload, exclude=exclude)
    if isinstance(payload, list):
        return _strip_sequence_keys(payload, exclude=exclude)
    return deepcopy(payload)


def _strip_mapping_keys(payload: dict[Any, Any], *, exclude: set[str]) -> dict[Any, Any]:
    return {
        key: strip_keys(value, exclude=exclude)
        for key, value in payload.items()
        if key not in exclude
    }


def _strip_sequence_keys(payload: list[Any], *, exclude: set[str]) -> list[Any]:
    return [strip_keys(item, exclude=exclude) for item in payload]
