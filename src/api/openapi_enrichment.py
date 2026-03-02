"""OpenAPI enrichment utilities for lotus-advise."""

from __future__ import annotations

import re
from typing import Any

_EXAMPLE_BY_KEY = {
    "portfolio_id": "DEMO_DPM_EUR_001",
    "proposal_id": "pp_001",
    "proposal_run_id": "pr_001",
    "operation_id": "pop_001",
    "version_no": 1,
    "consumer_system": "lotus-gateway",
    "tenant_id": "default",
    "policy_version": "advisory.v1",
    "source_service": "lotus-advise",
    "contract_version": "v1",
    "generated_at": "2026-03-02T10:30:00Z",
    "as_of_date": "2026-03-02",
    "created_at": "2026-03-02T10:30:00Z",
    "currency": "USD",
    "base_currency": "USD",
    "status": "READY",
    "workflow_key": "advisory_proposal_lifecycle",
    "instrument_id": "EQ_US_AAPL",
    "quantity": 100.0,
    "price": 182.35,
    "rate": 1.3524,
    "amount": 125000.5,
    "request_hash": "sha256:example_hash",
    "idempotency_key": "proposal-create-idem-001",
    "correlation_id": "corr_proposal_001",
}


def _to_snake_case(value: str) -> str:
    transformed = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    transformed = transformed.replace("-", "_").replace(" ", "_")
    return transformed.lower()


def _humanize(key: str) -> str:
    return _to_snake_case(key).replace("_", " ").strip()


def _infer_example(prop_name: str, prop_schema: dict[str, Any]) -> Any:
    key = _to_snake_case(prop_name)
    if key in _EXAMPLE_BY_KEY:
        return _EXAMPLE_BY_KEY[key]

    enum_values = prop_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    schema_type = prop_schema.get("type")
    schema_format = prop_schema.get("format")
    if schema_type == "array":
        item_schema = prop_schema.get("items", {})
        return [_infer_example(f"{prop_name}_item", item_schema)]
    if schema_type == "object":
        return {"key": "sample_text"}
    if schema_type == "boolean":
        return True
    if schema_type == "integer":
        if "ttl" in key or "hours" in key:
            return 24
        if "version" in key:
            return 1
        return 10
    if schema_type == "number":
        if "weight" in key:
            return 0.125
        if "price" in key or "rate" in key:
            return 1.2345
        if "quantity" in key:
            return 100.0
        if "pnl" in key or "amount" in key or "value" in key:
            return 125000.5
        return 10.5

    if schema_format == "date":
        return "2026-03-02"
    if schema_format == "date-time":
        return "2026-03-02T10:30:00Z"

    if key.endswith("_id"):
        entity = key[: -len("_id")]
        return f"{entity.upper()}_001"
    if "currency" in key:
        return "USD"
    if "date" in key:
        return "2026-03-02"
    if "time" in key or "timestamp" in key:
        return "2026-03-02T10:30:00Z"
    if "status" in key:
        return "ACTIVE"
    if schema_type == "string":
        return f"example_{key}"
    return f"{key}_example"


def _infer_description(model_name: str, prop_name: str, prop_schema: dict[str, Any]) -> str:
    key = _to_snake_case(prop_name)
    text = _humanize(prop_name)
    if key.endswith("_id"):
        entity = key[: -len("_id")].replace("_", " ")
        return f"Unique {entity} identifier."
    if "date" in key and prop_schema.get("format") == "date":
        return f"Business date for {text}."
    if "time" in key or prop_schema.get("format") == "date-time":
        return f"Timestamp for {text}."
    if "currency" in key:
        return f"ISO currency code for {text}."
    if "amount" in key or "value" in key or "pnl" in key:
        return f"Monetary value for {text}."
    if "quantity" in key:
        return f"Quantity value for {text}."
    if "rate" in key or "price" in key:
        return f"Rate/price value for {text}."
    if "status" in key:
        return f"Current status for {text}."
    return f"{_humanize(model_name)} field: {text}."


def _ensure_operation_documentation(schema: dict[str, Any], service_name: str) -> None:
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue
            if not operation.get("summary"):
                operation["summary"] = f"{method.upper()} {path}"
            if not operation.get("description"):
                operation["description"] = (
                    f"{method.upper()} operation for {path} in {service_name}."
                )
            if not operation.get("tags"):
                if path.startswith("/health/") or path == "/health":
                    operation["tags"] = ["Health"]
                elif path == "/metrics":
                    operation["tags"] = ["Monitoring"]
                else:
                    segment = path.strip("/").split("/", 1)[0] or "default"
                    operation["tags"] = [segment.replace("-", " ").title()]
            responses = operation.get("responses")
            if isinstance(responses, dict):
                has_error = any(
                    code.startswith("4") or code.startswith("5") or code == "default"
                    for code in responses
                )
                if not has_error:
                    responses["default"] = {"description": "Unexpected error response."}


def _ensure_schema_documentation(schema: dict[str, Any]) -> None:
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    for model_name, model_schema in schemas.items():
        if not isinstance(model_schema, dict):
            continue
        properties = model_schema.get("properties", {})
        if not isinstance(properties, dict):
            continue
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            if not prop_schema.get("description"):
                prop_schema["description"] = _infer_description(model_name, prop_name, prop_schema)
            if "example" not in prop_schema:
                prop_schema["example"] = _infer_example(prop_name, prop_schema)


def enrich_openapi_schema(schema: dict[str, Any], service_name: str) -> dict[str, Any]:
    """Mutate schema in-place to ensure minimum documentation completeness."""
    info = schema.setdefault("info", {})
    info.setdefault("title", "Lotus Advise API")
    if "lotus" not in (info.get("description") or "").lower():
        branded_desc = (info.get("description") or "").strip()
        prefix = "Lotus platform API contract."
        info["description"] = f"{prefix} {branded_desc}".strip()

    _ensure_operation_documentation(schema, service_name=service_name)
    _ensure_schema_documentation(schema)
    return schema
