from __future__ import annotations

import json
import re
import sys
from argparse import ArgumentParser
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_PATH = str(PROJECT_ROOT)
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

from src.api.main import app  # noqa: E402

ALLOWED_METHODS = {"get", "post", "put", "patch", "delete"}
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "docs" / "standards" / "api-vocabulary" / "lotus-advise-api-vocabulary.v1.json"
)
PLACEHOLDER_EXAMPLES = {
    "example",
    "sample",
    "sample_key",
    "sample_text",
    "string",
    "value",
    "test",
    "foo",
    "bar",
    "baz",
    "placeholder",
    "standard_item",
    "standard_text",
    "entity_001",
}
PLACEHOLDER_EXAMPLE_PATTERNS = (
    re.compile(r"(^|[:/])example_[A-Za-z0-9_]+"),
    re.compile(r"\bsample_(key|text|item)\b"),
)
LEGACY_TERM_MAP: dict[str, str] = {
    "cif_id": "client_id",
    "booking_center": "booking_center_code",
}
FORMAT_FALLBACK_EXAMPLES: dict[str, Any] = {
    "date": "2026-02-20",
    "date-time": "2026-02-20T00:00:00Z",
}
TYPE_FALLBACK_EXAMPLES: dict[str, Any] = {
    "boolean": True,
    "integer": 1,
    "number": 0.1,
    "string": "advisory_review_context",
}
CANONICAL_FALLBACK_EXAMPLES: dict[str, Any] = {
    "acknowledged_at": "2026-02-20T10:00:00Z",
    "acknowledged_by": "advisor_123",
    "activated_by": "supervisor_123",
    "advisor_id": "advisor_123",
    "archive_id": "archive_001",
    "as_of": "2026-02-20",
    "as_of_date": "2026-02-20",
    "base_currency": "USD",
    "booking_center_code": "SG",
    "client_id": "client_sg_001",
    "content_hash": "sha256:advisory-content",
    "correlation_id": "corr_advisory_001",
    "created_at": "2026-02-20T10:00:00Z",
    "created_by": "advisor_123",
    "currency": "USD",
    "generated_at": "2026-02-20T10:00:00Z",
    "idempotency_key": "proposal-create-idem-001",
    "jurisdiction": "SG",
    "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
    "memo_id": "memo_001",
    "occurred_at": "2026-02-20T10:00:00Z",
    "operation_id": "pop_001",
    "policy_evaluation_id": "policy_eval_sg_001",
    "policy_pack_id": "SG_PRIVATE_BANKING_REFERENCE",
    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
    "proposal_id": "pp_001",
    "proposal_run_id": "pr_001",
    "proposal_version_id": "ppv_001",
    "report_id": "report_001",
    "request_hash": "sha256:advisory-request",
    "source_service": "lotus-advise",
    "source_system": "lotus-advise",
    "source_type": "ADVISORY_EVIDENCE",
    "tenant_id": "default",
    "updated_at": "2026-02-20T10:00:00Z",
    "version_no": 1,
}
ATTRIBUTE_CATALOG_OVERRIDES: dict[str, dict[str, Any]] = {
    "lotus.intent_type": {
        "description": "Canonical business intent discriminator used by lotus-advise APIs.",
        "example": "SECURITY_TRADE",
    },
    "lotus.supportability_status": {
        "description": (
            "Canonical supportability posture for an API response, workflow, or proof artifact."
        ),
        "example": "not_certified",
    },
}
_NO_ENUM_EXAMPLE = object()


def _to_snake_case(value: str) -> str:
    transformed = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    transformed = transformed.replace("-", "_").replace(" ", "_").replace(".", "_")
    transformed = transformed.strip("_")
    return transformed.lower()


def _canonical_term(name: str) -> str:
    base = _to_snake_case(name.split(".")[-1].replace("[]", ""))
    return LEGACY_TERM_MAP.get(base, base)


def _semantic_id(name: str) -> str:
    return f"lotus.{_canonical_term(name)}"


def _schema_type(schema: dict[str, Any]) -> str:
    schema = _schema_without_null_variant(schema)
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]
    return str(schema.get("type", "object"))


def _resolve_schema(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    schemas = components.get("schemas", {})
    if not isinstance(schemas, dict):
        return {}
    resolved = schemas.get(ref.rsplit("/", 1)[-1], {})
    return _typed_json_object(resolved)


def _fallback_description(name: str) -> str:
    readable = _canonical_term(name).replace("_", " ")
    return f"Canonical {readable} used by lotus-advise APIs."


def _fallback_example(name: str, schema: dict[str, Any]) -> Any:
    canonical = _canonical_term(name)
    canonical_example = CANONICAL_FALLBACK_EXAMPLES.get(canonical)
    if canonical_example is not None:
        return canonical_example
    enum_example = _first_enum_example(schema)
    if enum_example is not _NO_ENUM_EXAMPLE:
        return enum_example
    format_example = FORMAT_FALLBACK_EXAMPLES.get(str(schema.get("format", "")))
    if format_example is not None:
        return format_example
    structured_example = _structured_fallback_example(canonical, schema)
    if structured_example is not _NO_ENUM_EXAMPLE:
        return structured_example
    name_example = _name_based_fallback_example(canonical)
    if name_example is not None:
        return name_example
    return TYPE_FALLBACK_EXAMPLES.get(_fallback_type(schema), f"{canonical}_value")


def _first_enum_example(schema: dict[str, Any]) -> Any:
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]
    return _NO_ENUM_EXAMPLE


def _fallback_type(schema: dict[str, Any]) -> str:
    schema = _schema_without_null_variant(schema)
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return schema_type
    if isinstance(schema_type, list):
        return next(
            (value for value in schema_type if isinstance(value, str) and value != "null"), ""
        )
    return ""


def _schema_without_null_variant(schema: dict[str, Any]) -> dict[str, Any]:
    for union_key in ("anyOf", "oneOf"):
        variants = schema.get(union_key)
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            if variant.get("type") == "null":
                continue
            return _typed_json_object(variant)
    return schema


def _typed_json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _name_based_fallback_example(canonical: str) -> Any | None:
    if canonical.endswith("_id"):
        return f"{canonical.removesuffix('_id')}_001"
    if canonical.endswith("_at") or "timestamp" in canonical:
        return "2026-02-20T10:00:00Z"
    if canonical.endswith("_date"):
        return "2026-02-20"
    if canonical.endswith("_by") or "actor" in canonical or "reviewer" in canonical:
        return "advisor_123"
    if canonical.endswith("_hash") or "hash" in canonical:
        return "sha256:advisory-evidence"
    if canonical.endswith("_uri") or canonical.endswith("_url") or canonical.endswith("_href"):
        return "/advisory/proposals/pp_001"
    if "currency" in canonical:
        return "USD"
    if "amount" in canonical or "value" in canonical:
        return 125000.5
    if "weight" in canonical or "rate" in canonical:
        return 0.1
    if canonical.endswith("_code") or "reason" in canonical:
        return "ADVISORY_REVIEW_REQUIRED"
    return None


def _structured_fallback_example(canonical: str, schema: dict[str, Any]) -> Any:
    schema_type = _fallback_type(schema)
    if schema_type == "array":
        return _array_fallback_example(canonical, schema)
    if schema_type == "object" or "properties" in schema:
        return _object_fallback_example(canonical, schema)
    return _NO_ENUM_EXAMPLE


def _array_fallback_example(canonical: str, schema: dict[str, Any]) -> list[Any]:
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        return [_fallback_example(f"{canonical}_item", item_schema)]
    return [f"{canonical}_value"]


def _object_fallback_example(canonical: str, schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        selected_names = _selected_object_property_names(schema, properties)
        return {
            str(prop_name): _fallback_example(str(prop_name), prop_schema)
            for prop_name, prop_schema in selected_names
            if isinstance(prop_schema, dict)
        }
    additional_schema = schema.get("additionalProperties")
    if isinstance(additional_schema, dict):
        example_key = "USD" if "currency" in canonical or "ccy" in canonical else "advisory_key"
        return {example_key: _fallback_example(f"{canonical}_value", additional_schema)}
    return {
        "source_system": "lotus-advise",
        "business_context": f"{canonical}_contract",
    }


def _selected_object_property_names(
    schema: dict[str, Any],
    properties: dict[str, Any],
) -> list[tuple[str, Any]]:
    required = schema.get("required")
    if isinstance(required, list) and required:
        return [(str(name), properties.get(str(name))) for name in required[:5]]
    return [(str(name), prop_schema) for name, prop_schema in list(properties.items())[:5]]


def _extract_fields(
    schema: dict[str, Any],
    *,
    components: dict[str, Any],
    prefix: str = "",
    location: str = "body",
) -> list[dict[str, Any]]:
    resolved = _resolve_schema(schema, components)
    fields: list[dict[str, Any]] = []
    for prop_name, prop_schema, required in _iter_schema_properties(resolved):
        prop_resolved = _resolve_schema(prop_schema, components)
        field_name = f"{prefix}.{prop_name}" if prefix else prop_name
        fields.append(
            _field_metadata(prop_name, prop_schema, prop_resolved, field_name, location, required)
        )
        for nested_schema, nested_prefix in _iter_nested_field_schemas(
            prop_schema, prop_resolved, field_name
        ):
            fields.extend(
                _extract_fields(
                    nested_schema,
                    components=components,
                    prefix=nested_prefix,
                    location=location,
                )
            )
    return fields


def _iter_schema_properties(
    resolved_schema: dict[str, Any],
) -> Iterator[tuple[str, dict[str, Any], bool]]:
    properties = resolved_schema.get("properties", {})
    required = set(resolved_schema.get("required", []))
    if not isinstance(properties, dict):
        return
    for prop_name, prop_schema in properties.items():
        if isinstance(prop_schema, dict):
            yield prop_name, prop_schema, prop_name in required


def _field_metadata(
    prop_name: str,
    prop_schema: dict[str, Any],
    prop_resolved: dict[str, Any],
    field_name: str,
    location: str,
    required: bool,
) -> dict[str, Any]:
    semantic_id = _semantic_id(prop_name)
    return {
        "name": field_name,
        "location": location,
        "required": required,
        "type": _schema_type(prop_schema),
        "semanticId": semantic_id,
        "attributeRef": f"#/attributeCatalog/{semantic_id}",
        "description": prop_resolved.get("description") or _fallback_description(field_name),
        "example": _field_example(field_name, prop_resolved),
    }


def _field_example(field_name: str, resolved_schema: dict[str, Any]) -> Any:
    example = _schema_example(resolved_schema)
    if example is None or _is_placeholder_example(example):
        return _fallback_example(field_name, resolved_schema)
    return example


def _schema_example(schema: dict[str, Any]) -> Any | None:
    example = schema.get("example")
    if example is not None:
        return example
    examples = schema.get("examples")
    if isinstance(examples, list):
        for candidate in examples:
            if not _is_placeholder_example(candidate):
                return candidate
        return examples[0] if examples else None
    return None


def _iter_nested_field_schemas(
    prop_schema: dict[str, Any],
    prop_resolved: dict[str, Any],
    field_name: str,
) -> Iterator[tuple[dict[str, Any], str]]:
    nested_type = prop_resolved.get("type")
    if nested_type == "object" or "$ref" in prop_schema:
        yield prop_schema, field_name
        return
    if nested_type != "array":
        return
    item_schema = prop_resolved.get("items")
    if isinstance(item_schema, dict):
        yield item_schema, f"{field_name}[]"


def _extract_request_fields(
    operation: dict[str, Any], components: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    request_fields: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []

    for parameter in operation.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        schema = parameter.get("schema", {})
        if not isinstance(schema, dict):
            schema = {}
        name = str(parameter.get("name", ""))
        canonical = _canonical_term(name)
        request_fields.append(
            {
                "name": name,
                "location": parameter.get("in", "query"),
                "required": bool(parameter.get("required", False)),
                "type": _schema_type(schema),
                "semanticId": _semantic_id(name),
                "attributeRef": f"#/attributeCatalog/{_semantic_id(name)}",
            }
        )
        controls.append(
            {
                "name": canonical,
                "kind": "request_option",
                "location": parameter.get("in", "query"),
                "required": bool(parameter.get("required", False)),
                "type": _schema_type(schema),
                "description": parameter.get("description")
                or schema.get("description")
                or _fallback_description(name),
                "example": _parameter_example(name, parameter, schema),
                "allowedValues": schema.get("enum", []),
                "semanticId": _semantic_id(name),
                "attributeRef": f"#/attributeCatalog/{_semantic_id(name)}",
            }
        )

    request_body = operation.get("requestBody", {})
    if isinstance(request_body, dict):
        json_content = request_body.get("content", {}).get("application/json")
        if isinstance(json_content, dict):
            schema = json_content.get("schema", {})
            if isinstance(schema, dict):
                request_fields.extend(_extract_fields(schema, components=components))

    return request_fields, controls


def _parameter_example(name: str, parameter: dict[str, Any], schema: dict[str, Any]) -> Any:
    example = parameter.get("example")
    if example is None:
        example = _schema_example(schema)
    if example is None or _is_placeholder_example(example):
        return _fallback_example(name, schema)
    return example


def _extract_response_fields(
    operation: dict[str, Any], components: dict[str, Any]
) -> list[dict[str, Any]]:
    responses = operation.get("responses", {})
    success_codes = sorted(code for code in responses if str(code).startswith("2"))
    if not success_codes:
        return []
    response = responses[success_codes[0]]
    if not isinstance(response, dict):
        return []
    json_content = response.get("content", {}).get("application/json")
    if not isinstance(json_content, dict):
        return []
    schema = json_content.get("schema", {})
    if not isinstance(schema, dict):
        return []
    return _extract_fields(schema, components=components)


def _domain(path: str, tags: list[str]) -> str:
    if tags:
        return _to_snake_case(tags[0])
    root = path.strip("/").split("/")[0] if path.strip("/") else "operational"
    return _to_snake_case(root)


def build_inventory() -> dict[str, Any]:
    schema = app.openapi()
    components = schema.get("components", {})

    attribute_catalog_map: dict[str, dict[str, Any]] = {}
    endpoints: list[dict[str, Any]] = []
    controls_catalog: list[dict[str, Any]] = []

    for path, method, operation in _iter_openapi_operations(schema):
        request_fields, controls = _extract_request_fields(operation, components)
        response_fields = _extract_response_fields(operation, components)
        _record_attribute_fields(attribute_catalog_map, [*request_fields, *response_fields])
        endpoints.append(_endpoint_record(path, method, operation, request_fields, response_fields))
        controls_catalog.extend(controls)

    return {
        "specVersion": "1.0.0",
        "application": "lotus-advise",
        "sourceOpenApi": [_source_openapi_metadata(schema)],
        "generatedAt": datetime.now(UTC).isoformat(),
        "attributeCatalog": sorted(attribute_catalog_map.values(), key=lambda x: x["semanticId"]),
        "controlsCatalog": controls_catalog,
        "endpoints": endpoints,
    }


def _iter_openapi_operations(schema: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    for path, methods in schema.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() in ALLOWED_METHODS and isinstance(operation, dict):
                yield path, method, operation


def _record_attribute_fields(
    attribute_catalog_map: dict[str, dict[str, Any]],
    fields: list[dict[str, Any]],
) -> None:
    for field in fields:
        semantic_id = field["semanticId"]
        if semantic_id not in attribute_catalog_map:
            attribute_catalog_map[semantic_id] = _attribute_catalog_entry(field)
        else:
            _merge_attribute_observation(attribute_catalog_map[semantic_id], field)


def _attribute_catalog_entry(field: dict[str, Any]) -> dict[str, Any]:
    canonical = _canonical_term(field["name"])
    field_type = field.get("type", "string")
    entry = {
        "semanticId": field["semanticId"],
        "canonicalTerm": canonical,
        "preferredName": canonical,
        "description": field.get("description") or _fallback_description(field["name"]),
        "example": field.get("example"),
        "type": field_type,
        "locations": [field.get("location", "body")],
        "observedTypes": [field_type],
    }
    entry.update(ATTRIBUTE_CATALOG_OVERRIDES.get(field["semanticId"], {}))
    return entry


def _merge_attribute_observation(item: dict[str, Any], field: dict[str, Any]) -> None:
    location = field.get("location", "body")
    observed_type = field.get("type", "string")
    if location not in item["locations"]:
        item["locations"].append(location)
    if observed_type not in item["observedTypes"]:
        item["observedTypes"].append(observed_type)


def _endpoint_record(
    path: str,
    method: str,
    operation: dict[str, Any],
    request_fields: list[dict[str, Any]],
    response_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "domain": _domain(path, operation.get("tags", [])),
        "method": method.upper(),
        "path": path,
        "operationId": operation.get("operationId"),
        "summary": operation.get("summary") or "",
        "request": {"fields": [_endpoint_field_ref(field) for field in request_fields]},
        "response": {"fields": [_endpoint_field_ref(field) for field in response_fields]},
    }


def _endpoint_field_ref(field: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": field["name"],
        "location": field["location"],
        "required": field["required"],
        "type": field["type"],
        "semanticId": field["semanticId"],
        "attributeRef": field["attributeRef"],
    }


def _source_openapi_metadata(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "service": "lotus-advise",
        "version": schema.get("info", {}).get("version", "0.1.0"),
        "openApiVersion": schema.get("openapi", "3.1.0"),
    }


def _is_snake_case(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))


def _is_placeholder_example(value: Any) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in PLACEHOLDER_EXAMPLES or any(
            pattern.search(value) for pattern in PLACEHOLDER_EXAMPLE_PATTERNS
        )
    if isinstance(value, list):
        return any(_is_placeholder_example(item) for item in value)
    if isinstance(value, dict):
        return any(_is_placeholder_example(item) for item in value.values())
    return False


def validate_inventory(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_attribute_catalog(inventory.get("attributeCatalog", [])))
    errors.extend(_validate_controls_catalog(inventory.get("controlsCatalog", [])))
    errors.extend(_validate_endpoint_field_refs(inventory.get("endpoints", [])))
    return errors


def _validate_attribute_catalog(attribute_catalog: Any) -> list[str]:
    errors: list[str] = []
    semantic_ids: set[str] = set()
    for attr in attribute_catalog:
        if not isinstance(attr, dict):
            errors.append("attributeCatalog entry must be an object")
            continue
        semantic_id = str(attr.get("semanticId", ""))
        errors.extend(_validate_attribute_identity(attr, semantic_id, semantic_ids))
        if semantic_id:
            semantic_ids.add(semantic_id)
    return errors


def _validate_attribute_identity(
    attr: dict[str, Any],
    semantic_id: str,
    semantic_ids: set[str],
) -> list[str]:
    if not semantic_id:
        return ["attributeCatalog entry missing semanticId"]
    errors: list[str] = []
    canonical = str(attr.get("canonicalTerm", ""))
    preferred = str(attr.get("preferredName", ""))
    if semantic_id in semantic_ids:
        errors.append(f"duplicate semanticId: {semantic_id}")
    if canonical != preferred:
        errors.append(f"canonicalTerm/preferredName mismatch: {semantic_id}")
    if not _is_snake_case(canonical):
        errors.append(f"canonicalTerm must be snake_case: {semantic_id} -> {canonical}")
    if canonical in LEGACY_TERM_MAP:
        errors.append(f"legacy term is not allowed: {canonical} (use {LEGACY_TERM_MAP[canonical]})")
    if _is_placeholder_example(attr.get("example")):
        errors.append(f"generic placeholder example is not allowed: {semantic_id}")
    return errors


def _validate_controls_catalog(controls_catalog: Any) -> list[str]:
    errors: list[str] = []
    for control in controls_catalog:
        if not isinstance(control, dict):
            errors.append("controlsCatalog entry must be an object")
            continue
        semantic_id = str(control.get("semanticId", ""))
        if _is_placeholder_example(control.get("example")):
            errors.append(f"generic control example is not allowed: {semantic_id}")
    return errors


def _validate_endpoint_field_refs(endpoints: Any) -> list[str]:
    errors: list[str] = []
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            errors.append("endpoint entry must be an object")
            continue
        for field in _iter_endpoint_fields(endpoint):
            errors.extend(_validate_endpoint_field_ref(endpoint, field))
    return errors


def _iter_endpoint_fields(endpoint: dict[str, Any]) -> Iterator[dict[str, Any]]:
    request_fields = endpoint.get("request", {}).get("fields", [])
    response_fields = endpoint.get("response", {}).get("fields", [])
    for field in [*request_fields, *response_fields]:
        if isinstance(field, dict):
            yield field


def _validate_endpoint_field_ref(
    endpoint: dict[str, Any],
    field: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    field_context = f"{endpoint.get('method')} {endpoint.get('path')}::{field.get('name')}"
    for forbidden in ("description", "example", "canonicalTerm", "preferredName"):
        if forbidden in field:
            errors.append(
                f"endpoint field duplicates attribute metadata ({forbidden}): {field_context}"
            )
    if not field.get("semanticId"):
        errors.append(f"endpoint field missing semanticId: {field_context}")
    if not field.get("attributeRef"):
        errors.append(f"endpoint field missing attributeRef: {field_context}")
    return errors


def _normalize_for_compare(payload: dict[str, Any]) -> dict[str, Any]:
    clone = dict(payload)
    clone.pop("generatedAt", None)
    return clone


def _preserve_stable_generated_at(
    inventory: dict[str, Any],
    existing_inventory: dict[str, Any] | None,
) -> dict[str, Any]:
    if existing_inventory is None:
        return inventory
    if _normalize_for_compare(existing_inventory) != _normalize_for_compare(inventory):
        return inventory
    stable_inventory = dict(inventory)
    stable_inventory["generatedAt"] = existing_inventory.get("generatedAt")
    return stable_inventory


def main() -> int:
    parser = ArgumentParser(
        description="Generate and validate lotus-advise API vocabulary inventory"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    inventory = build_inventory()
    errors = validate_inventory(inventory)
    if errors:
        print("API vocabulary inventory validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.validate_only:
        if not output_path.exists():
            print(f"Inventory file missing: {output_path}")
            return 1
        on_disk = json.loads(output_path.read_text(encoding="utf-8"))
        if _normalize_for_compare(on_disk) != _normalize_for_compare(inventory):
            print("Inventory drift detected. Regenerate with:")
            print(f"python scripts/api_vocabulary_inventory.py --output {output_path}")
            return 1
        print("API vocabulary inventory gate passed (no drift).")
        return 0

    existing_inventory = (
        json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
    )
    inventory = _preserve_stable_generated_at(inventory, existing_inventory)
    output_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote inventory: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
