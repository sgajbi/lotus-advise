"""OpenAPI enrichment utilities for lotus-advise."""

from __future__ import annotations

import re
from numbers import Real
from typing import Any

from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH

_IDEMPOTENCY_HEADER_DESCRIPTION = (
    "Idempotency keys are replay-safe client request identifiers. They are trimmed before replay "
    f"lookup and must be at most {MAX_IDEMPOTENCY_KEY_LENGTH} visible characters without control "
    "characters."
)

_NUMERIC_STRING_PATTERN_FRAGMENT = r"\d*\.?\d*"
_HTTP_OPERATION_METHODS = {"get", "post", "put", "patch", "delete"}

_EXAMPLE_BY_KEY = {
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
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

_STRING_EXAMPLE_BY_KEY = {
    key: value for key, value in _EXAMPLE_BY_KEY.items() if isinstance(value, str)
}


def _to_snake_case(value: str) -> str:
    transformed = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    transformed = transformed.replace("-", "_").replace(" ", "_")
    return transformed.lower()


def _humanize(key: str) -> str:
    return _to_snake_case(key).replace("_", " ").strip()


def _ref_name(ref: str) -> str | None:
    prefix = "#/components/schemas/"
    if not ref.startswith(prefix):
        return None
    return ref.removeprefix(prefix)


def _example_for_object_schema(
    model_name: str,
    model_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    properties = model_schema.get("properties")
    if not isinstance(properties, dict):
        return {"key": "sample_text"}
    required = model_schema.get("required")
    if not isinstance(required, list) or not required:
        selected_names = list(properties.keys())[:3]
    else:
        selected_names = [str(name) for name in required]
    example: dict[str, Any] = {}
    for prop_name in selected_names:
        prop_schema = properties.get(prop_name)
        if isinstance(prop_schema, dict):
            example[prop_name] = _infer_example(prop_name, prop_schema, components)
    return example or {"key": _to_snake_case(model_name)}


def _infer_ref_example(prop_schema: dict[str, Any], components: dict[str, Any]) -> Any | None:
    ref = prop_schema.get("$ref")
    if not isinstance(ref, str):
        return None
    model_name = _ref_name(ref)
    model_schema = components.get(model_name or "")
    if isinstance(model_name, str) and isinstance(model_schema, dict):
        if isinstance(model_schema.get("properties"), dict):
            return _example_for_object_schema(model_name, model_schema, components)
        return _infer_example(model_name, model_schema, components)
    return None


def _infer_composite_example(
    prop_name: str,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> Any | None:
    for composite_key in ("allOf", "anyOf", "oneOf"):
        composite_schemas = prop_schema.get(composite_key)
        if isinstance(composite_schemas, list) and composite_schemas:
            first_schema = composite_schemas[0]
            if isinstance(first_schema, dict):
                return _infer_example(prop_name, first_schema, components)
    return None


def _infer_array_example(
    prop_name: str,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> list[Any]:
    item_schema = prop_schema.get("items", {})
    if isinstance(item_schema, dict):
        return [_infer_example(f"{prop_name}_item", item_schema, components)]
    return [f"example_{_to_snake_case(prop_name)}_item"]


def _infer_object_example(
    prop_name: str,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    key = _to_snake_case(prop_name)
    additional_schema = prop_schema.get("additionalProperties")
    if isinstance(additional_schema, dict):
        example_key = "USD" if "ccy" in key or "currency" in key else "sample_key"
        return {
            example_key: _infer_example(
                f"{prop_name}_value",
                additional_schema,
                components,
            )
        }
    return {"key": "sample_text"}


def _infer_integer_example(prop_name: str, prop_schema: dict[str, Any]) -> int:
    key = _to_snake_case(prop_name)
    maximum = prop_schema.get("maximum")
    minimum = prop_schema.get("minimum")
    if isinstance(maximum, (int, float)) and maximum <= 10:
        lower_bound = int(minimum) if isinstance(minimum, (int, float)) else 1
        upper_bound = int(maximum)
        return max(lower_bound, min(upper_bound, 5))
    if "ttl" in key or "hours" in key:
        return 24
    if "version" in key:
        return 1
    return 10


def _infer_number_example(prop_name: str) -> float:
    key = _to_snake_case(prop_name)
    if "weight" in key:
        return 0.125
    if "price" in key or "rate" in key:
        return 1.2345
    if "quantity" in key:
        return 100.0
    if "pnl" in key or "amount" in key or "value" in key:
        return 125000.5
    return 10.5


def _infer_string_example(prop_name: str, prop_schema: dict[str, Any]) -> str:
    key = _to_snake_case(prop_name)
    for inference in (
        _string_pattern_example,
        _string_format_example,
        _string_keyed_example,
        _string_identifier_example,
        _string_semantic_key_example,
    ):
        example = inference(key, prop_schema)
        if example is not None:
            return example
    return _string_fallback_example(key)


def _string_pattern_example(key: str, prop_schema: dict[str, Any]) -> str | None:
    pattern = prop_schema.get("pattern")
    if isinstance(pattern, str) and _NUMERIC_STRING_PATTERN_FRAGMENT in pattern:
        return "0.125"
    return None


def _string_format_example(_: str, prop_schema: dict[str, Any]) -> str | None:
    schema_format = prop_schema.get("format")
    if schema_format == "date":
        return "2026-03-02"
    if schema_format == "date-time":
        return "2026-03-02T10:30:00Z"
    return None


def _string_keyed_example(key: str, _: dict[str, Any]) -> str | None:
    keyed_example = _STRING_EXAMPLE_BY_KEY.get(key)
    return keyed_example if isinstance(keyed_example, str) else None


def _string_identifier_example(key: str, _: dict[str, Any]) -> str | None:
    if key.endswith("_id"):
        entity = key[: -len("_id")]
        return f"{entity.upper()}_001"
    return None


def _string_semantic_key_example(key: str, _: dict[str, Any]) -> str | None:
    if "date" in key:
        return "2026-03-02"
    if "time" in key or "timestamp" in key:
        return "2026-03-02T10:30:00Z"
    if "status" in key:
        return "ACTIVE"
    if "currency" in key:
        return "USD"
    return None


def _string_fallback_example(key: str) -> str:
    return f"example_{key}"


def _infer_untyped_example(prop_name: str) -> str:
    key = _to_snake_case(prop_name)
    if key.endswith("_id"):
        entity = key[: -len("_id")]
        return f"{entity.upper()}_001"
    return f"{key}_example"


def _resolved_example_schema(
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    referenced_schema = _resolved_ref_schema(prop_schema, components)
    if referenced_schema is not None:
        return referenced_schema
    composite_schema = _resolved_composite_schema(prop_schema, components)
    if composite_schema is not None:
        return composite_schema
    return prop_schema


def _resolved_ref_schema(
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any] | None:
    ref = prop_schema.get("$ref")
    if not isinstance(ref, str):
        return None
    model_name = _ref_name(ref)
    model_schema = components.get(model_name or "")
    return model_schema if isinstance(model_schema, dict) else None


def _resolved_composite_schema(
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any] | None:
    for composite_key in ("allOf", "anyOf", "oneOf"):
        composite_schemas = prop_schema.get(composite_key)
        if not isinstance(composite_schemas, list):
            continue
        candidate = _first_non_null_schema(composite_schemas)
        if candidate is not None:
            return _resolved_example_schema(candidate, components)
    return None


def _first_non_null_schema(composite_schemas: list[Any]) -> dict[str, Any] | None:
    for candidate in composite_schemas:
        if isinstance(candidate, dict) and candidate.get("type") != "null":
            return candidate
    return None


def _repair_scalar_example(
    prop_name: str,
    example: Any,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> Any:
    if _example_violates_enum(example, prop_schema):
        return _infer_example(prop_name, prop_schema, components)
    if _example_violates_scalar_type(example, prop_schema):
        return _infer_example(prop_name, prop_schema, components)
    if _integer_example_exceeds_maximum(example, prop_schema):
        return _infer_example(prop_name, prop_schema, components)
    return example


def _example_violates_enum(example: Any, prop_schema: dict[str, Any]) -> bool:
    enum_values = prop_schema.get("enum")
    return isinstance(enum_values, list) and bool(enum_values) and example not in enum_values


def _example_violates_scalar_type(example: Any, prop_schema: dict[str, Any]) -> bool:
    schema_type = prop_schema.get("type")
    return (
        schema_type == "string"
        and not isinstance(example, str)
        or schema_type == "integer"
        and not isinstance(example, int)
    )


def _integer_example_exceeds_maximum(example: Any, prop_schema: dict[str, Any]) -> bool:
    if prop_schema.get("type") != "integer" or not isinstance(example, int):
        return False
    maximum = prop_schema.get("maximum")
    return isinstance(maximum, Real) and example > maximum


def _repair_example_against_schema(
    prop_name: str,
    example: Any,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> Any:
    resolved_schema = _resolved_example_schema(prop_schema, components)
    structured_example = _repair_structured_example(
        prop_name,
        example,
        resolved_schema,
        components,
    )
    if structured_example is not None:
        return structured_example
    return _repair_scalar_example(prop_name, example, resolved_schema, components)


def _repair_structured_example(
    prop_name: str,
    example: Any,
    resolved_schema: dict[str, Any],
    components: dict[str, Any],
) -> Any | None:
    repaired_array = _repaired_array_or_none(prop_name, example, resolved_schema, components)
    if repaired_array is not None:
        return repaired_array
    repaired_object = _repaired_object_or_none(example, resolved_schema, components)
    if repaired_object is not None:
        return repaired_object
    return None


def _repaired_array_or_none(
    prop_name: str,
    example: Any,
    resolved_schema: dict[str, Any],
    components: dict[str, Any],
) -> list[Any] | None:
    if resolved_schema.get("type") != "array":
        return None
    return _repair_array_example(prop_name, example, resolved_schema, components)


def _repaired_object_or_none(
    example: Any,
    resolved_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any] | None:
    properties = resolved_schema.get("properties")
    if isinstance(properties, dict) and isinstance(example, dict):
        return _repair_object_properties_example(example, properties, resolved_schema, components)

    if resolved_schema.get("type") != "object" or not isinstance(example, dict):
        return None
    return _repair_additional_property_examples(example, resolved_schema, components)


def _repair_array_example(
    prop_name: str,
    example: Any,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> list[Any] | None:
    if not isinstance(example, list):
        return None

    item_schema = prop_schema.get("items")
    if not isinstance(item_schema, dict):
        return None

    return [
        _repair_example_against_schema(f"{prop_name}_item", item, item_schema, components)
        for item in example
    ]


def _repair_object_properties_example(
    example: dict[str, Any],
    properties: dict[str, Any],
    resolved_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    repaired = dict(example)
    _add_missing_required_examples(repaired, properties, resolved_schema, components)
    _repair_existing_property_examples(repaired, properties, components)
    return repaired


def _add_missing_required_examples(
    repaired: dict[str, Any],
    properties: dict[str, Any],
    resolved_schema: dict[str, Any],
    components: dict[str, Any],
) -> None:
    required = resolved_schema.get("required")
    if not isinstance(required, list):
        return

    for required_name in required:
        required_key = str(required_name)
        if required_key in repaired:
            continue
        required_schema = properties.get(required_key)
        if isinstance(required_schema, dict):
            repaired[required_key] = _infer_example(required_key, required_schema, components)


def _repair_existing_property_examples(
    repaired: dict[str, Any],
    properties: dict[str, Any],
    components: dict[str, Any],
) -> None:
    for existing_name, existing_value in list(repaired.items()):
        existing_schema = properties.get(existing_name)
        if isinstance(existing_schema, dict):
            repaired[existing_name] = _repair_example_against_schema(
                existing_name,
                existing_value,
                existing_schema,
                components,
            )


def _repair_additional_property_examples(
    example: dict[str, Any],
    resolved_schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any] | None:
    additional_schema = resolved_schema.get("additionalProperties")
    if not isinstance(additional_schema, dict):
        return None

    return {
        key: _repair_example_against_schema(str(key), value, additional_schema, components)
        for key, value in example.items()
    }


def _infer_example(prop_name: str, prop_schema: dict[str, Any], components: dict[str, Any]) -> Any:
    prioritized_example = _infer_prioritized_example(prop_name, prop_schema, components)
    if prioritized_example is not None:
        return prioritized_example

    schema_type = prop_schema.get("type")
    typed_example = _infer_typed_example(prop_name, prop_schema, components, schema_type)
    if typed_example is not None:
        return typed_example

    key = _to_snake_case(prop_name)
    if key in _EXAMPLE_BY_KEY:
        return _EXAMPLE_BY_KEY[key]
    return _infer_untyped_example(prop_name)


def _infer_prioritized_example(
    prop_name: str,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
) -> Any | None:
    const_value = prop_schema.get("const")
    if const_value is not None:
        return const_value

    enum_example = _infer_enum_example(prop_schema)
    if enum_example is not None:
        return enum_example

    referenced_example = _infer_ref_example(prop_schema, components)
    if referenced_example is not None:
        return referenced_example

    return _infer_composite_example(prop_name, prop_schema, components)


def _infer_enum_example(prop_schema: dict[str, Any]) -> Any | None:
    enum_values = prop_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]
    return None


def _infer_typed_example(
    prop_name: str,
    prop_schema: dict[str, Any],
    components: dict[str, Any],
    schema_type: Any,
) -> Any | None:
    if schema_type == "array":
        return _infer_array_example(prop_name, prop_schema, components)
    if schema_type == "object":
        return _infer_object_example(prop_name, prop_schema, components)
    if schema_type == "boolean":
        return True
    if schema_type == "integer":
        return _infer_integer_example(prop_name, prop_schema)
    if schema_type == "number":
        return _infer_number_example(prop_name)
    if schema_type == "string":
        return _infer_string_example(prop_name, prop_schema)
    return None


def _infer_description(model_name: str, prop_name: str, prop_schema: dict[str, Any]) -> str:
    key = _to_snake_case(prop_name)
    text = _humanize(prop_name)
    description = _specialized_field_description(key, text, prop_schema)
    if description is not None:
        return description
    return _default_field_description(model_name, text)


def _specialized_field_description(
    key: str,
    text: str,
    prop_schema: dict[str, Any],
) -> str | None:
    for describer in (
        _identifier_description,
        _date_description,
        _timestamp_description,
        _currency_description,
        _monetary_description,
        _quantity_description,
        _rate_price_description,
        _status_description,
    ):
        description = describer(key, text, prop_schema)
        if description is not None:
            return description
    return None


def _identifier_description(key: str, _: str, __: dict[str, Any]) -> str | None:
    if not key.endswith("_id"):
        return None
    entity = key[: -len("_id")].replace("_", " ")
    return f"Unique {entity} identifier."


def _date_description(key: str, text: str, prop_schema: dict[str, Any]) -> str | None:
    if "date" in key and prop_schema.get("format") == "date":
        return f"Business date for {text}."
    return None


def _timestamp_description(key: str, text: str, prop_schema: dict[str, Any]) -> str | None:
    if "time" in key or prop_schema.get("format") == "date-time":
        return f"Timestamp for {text}."
    return None


def _currency_description(key: str, text: str, _: dict[str, Any]) -> str | None:
    if "currency" in key:
        return f"ISO currency code for {text}."
    return None


def _monetary_description(key: str, text: str, _: dict[str, Any]) -> str | None:
    if any(marker in key for marker in ("amount", "value", "pnl")):
        return f"Monetary value for {text}."
    return None


def _quantity_description(key: str, text: str, _: dict[str, Any]) -> str | None:
    if "quantity" in key:
        return f"Quantity value for {text}."
    return None


def _rate_price_description(key: str, text: str, _: dict[str, Any]) -> str | None:
    if "rate" in key or "price" in key:
        return f"Rate/price value for {text}."
    return None


def _status_description(key: str, text: str, _: dict[str, Any]) -> str | None:
    if "status" in key:
        return f"Current status for {text}."
    return None


def _default_field_description(model_name: str, text: str) -> str:
    return f"{_humanize(model_name)} field: {text}."


def _ensure_operation_documentation(schema: dict[str, Any], service_name: str) -> None:
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if not _is_documentable_operation(method, operation):
                continue
            _ensure_operation_summary(operation, method, path)
            _ensure_operation_description(operation, method, path, service_name)
            _ensure_operation_tags(operation, path)
            _ensure_default_error_response(operation)
            _ensure_operation_parameter_documentation(operation)


def _is_documentable_operation(method: str, operation: Any) -> bool:
    return method.lower() in _HTTP_OPERATION_METHODS and isinstance(operation, dict)


def _ensure_operation_summary(operation: dict[str, Any], method: str, path: str) -> None:
    if not operation.get("summary"):
        operation["summary"] = f"{method.upper()} {path}"


def _ensure_operation_description(
    operation: dict[str, Any],
    method: str,
    path: str,
    service_name: str,
) -> None:
    if not operation.get("description"):
        operation["description"] = f"{method.upper()} operation for {path} in {service_name}."


def _ensure_operation_tags(operation: dict[str, Any], path: str) -> None:
    if operation.get("tags"):
        return
    operation["tags"] = [_inferred_operation_tag(path)]


def _inferred_operation_tag(path: str) -> str:
    if path.startswith("/health/") or path == "/health":
        return "Health"
    if path == "/metrics":
        return "Monitoring"
    segment = path.strip("/").split("/", 1)[0] or "default"
    return segment.replace("-", " ").title()


def _ensure_default_error_response(operation: dict[str, Any]) -> None:
    responses = operation.get("responses")
    if not isinstance(responses, dict) or _has_error_response(responses):
        return
    responses["default"] = {"description": "Unexpected error response."}


def _has_error_response(responses: dict[str, Any]) -> bool:
    return any(
        str(code).startswith("4") or str(code).startswith("5") or code == "default"
        for code in responses
    )


def _ensure_operation_parameter_documentation(operation: dict[str, Any]) -> None:
    parameters = operation.get("parameters")
    if not isinstance(parameters, list):
        return
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        if parameter.get("name") != "Idempotency-Key" or parameter.get("in") != "header":
            continue
        schema = parameter.setdefault("schema", {})
        if isinstance(schema, dict):
            schema["maxLength"] = MAX_IDEMPOTENCY_KEY_LENGTH
        description = parameter.get("description") or ""
        if _IDEMPOTENCY_HEADER_DESCRIPTION not in description:
            parameter["description"] = f"{description} {_IDEMPOTENCY_HEADER_DESCRIPTION}".strip()


def _ensure_schema_documentation(schema: dict[str, Any]) -> None:
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    if not isinstance(schemas, dict):
        schemas = {}
    for model_name, model_schema in schemas.items():
        if not isinstance(model_schema, dict):
            continue
        if "example" in model_schema:
            model_schema["example"] = _repair_example_against_schema(
                str(model_name),
                model_schema["example"],
                model_schema,
                schemas,
            )
        properties = model_schema.get("properties", {})
        if not isinstance(properties, dict):
            continue
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            if not prop_schema.get("description"):
                prop_schema["description"] = _infer_description(model_name, prop_name, prop_schema)
            if "example" not in prop_schema:
                prop_schema["example"] = _infer_example(prop_name, prop_schema, schemas)
            else:
                prop_schema["example"] = _repair_example_against_schema(
                    prop_name,
                    prop_schema["example"],
                    prop_schema,
                    schemas,
                )


def _ensure_media_example_documentation(schema: dict[str, Any]) -> None:
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    if not isinstance(schemas, dict):
        schemas = {}
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return
    for methods in paths.values():
        if not isinstance(methods, dict):
            continue
        for operation in methods.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses")
            if isinstance(responses, dict):
                _repair_response_media_examples(responses, schemas)


def _repair_response_media_examples(responses: dict[str, Any], schemas: dict[str, Any]) -> None:
    for response in responses.values():
        if not isinstance(response, dict):
            continue
        content = response.get("content")
        if not isinstance(content, dict):
            continue
        for media in content.values():
            if isinstance(media, dict):
                _repair_media_examples(media, schemas)


def _repair_media_examples(media: dict[str, Any], schemas: dict[str, Any]) -> None:
    media_schema = media.get("schema")
    if not isinstance(media_schema, dict):
        return
    examples = media.get("examples")
    if isinstance(examples, dict):
        for example_name, example in examples.items():
            if isinstance(example, dict) and "value" in example:
                example["value"] = _repair_example_against_schema(
                    str(example_name),
                    example["value"],
                    media_schema,
                    schemas,
                )
    if "example" in media:
        media["example"] = _repair_example_against_schema(
            "media_example",
            media["example"],
            media_schema,
            schemas,
        )


def enrich_openapi_schema(schema: dict[str, Any], service_name: str) -> dict[str, Any]:
    """Mutate schema in-place to ensure minimum documentation completeness."""
    info = schema.setdefault("info", {})
    info.setdefault("title", "Lotus Advise API")
    info.setdefault(
        "contact",
        {
            "name": "Lotus Platform Engineering",
        },
    )
    if "lotus" not in (info.get("description") or "").lower():
        branded_desc = (info.get("description") or "").strip()
        prefix = "Lotus platform API contract."
        info["description"] = f"{prefix} {branded_desc}".strip()
    schema.setdefault(
        "servers",
        [
            {
                "url": "/",
                "description": "Relative Lotus Advise service root.",
            }
        ],
    )

    _ensure_operation_documentation(schema, service_name=service_name)
    _ensure_schema_documentation(schema)
    _ensure_media_example_documentation(schema)
    return schema
