from __future__ import annotations

from typing import Any

from src.core.advisory_copilot.business_text import contains_copilot_business_technical_detail

RAW_AI_STORAGE_KEYS = frozenset(
    {
        "prompt",
        "raw_prompt",
        "raw_output",
        "unsafe_output",
        "provider_response",
        "model_response",
        "provider_payload",
        "instruction",
        "raw_payload",
        "raw_source",
        "system_instruction",
        "trace_id",
    }
)

MAX_SAFE_STRUCTURED_PAYLOAD_DEPTH = 8
MAX_SAFE_STRUCTURED_PAYLOAD_ITEMS = 64
MAX_SAFE_STRUCTURED_PAYLOAD_TEXT_LENGTH = 4000


def assert_safe_structured_payload(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_SAFE_STRUCTURED_PAYLOAD_DEPTH:
        raise ValueError("COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE")
    if isinstance(value, dict):
        if len(value) > MAX_SAFE_STRUCTURED_PAYLOAD_ITEMS:
            raise ValueError("COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE")
        for key, nested in value.items():
            if normalize_structured_payload_key(key) in RAW_AI_STORAGE_KEYS:
                raise ValueError("COPILOT_RAW_AI_PAYLOAD_NOT_ALLOWED")
            assert_safe_structured_payload(nested, depth=depth + 1)
    elif isinstance(value, list | tuple):
        if len(value) > MAX_SAFE_STRUCTURED_PAYLOAD_ITEMS:
            raise ValueError("COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE")
        for item in value:
            assert_safe_structured_payload(item, depth=depth + 1)
    elif isinstance(value, str):
        if len(value) > MAX_SAFE_STRUCTURED_PAYLOAD_TEXT_LENGTH:
            raise ValueError("COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE")
        if contains_copilot_business_technical_detail(value):
            raise ValueError("COPILOT_STRUCTURED_PAYLOAD_TECHNICAL_DETAIL")


def normalize_structured_payload_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")
