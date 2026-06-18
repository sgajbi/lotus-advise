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
    "string",
    "value",
    "test",
    "foo",
    "bar",
    "baz",
    "placeholder",
}
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
    "array": ["STANDARD_ITEM"],
    "object": {"key": "sample_text"},
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
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    return str(schema.get("type", "object"))


def _resolve_schema(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    return components.get("schemas", {}).get(ref.rsplit("/", 1)[-1], {})


def _fallback_description(name: str) -> str:
    readable = _canonical_term(name).replace("_", " ")
    return f"Canonical {readable} used by lotus-advise APIs."


def _fallback_example(name: str, schema: dict[str, Any]) -> Any:
    canonical = _canonical_term(name)
    enum_example = _first_enum_example(schema)
    if enum_example is not _NO_ENUM_EXAMPLE:
        return enum_example
    format_example = FORMAT_FALLBACK_EXAMPLES.get(str(schema.get("format", "")))
    if format_example is not None:
        return format_example
    name_example = _name_based_fallback_example(canonical)
    if name_example is not None:
        return name_example
    return TYPE_FALLBACK_EXAMPLES.get(_fallback_type(schema), "STANDARD_TEXT")


def _first_enum_example(schema: dict[str, Any]) -> Any:
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]
    return _NO_ENUM_EXAMPLE


def _fallback_type(schema: dict[str, Any]) -> str:
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return schema_type
    if isinstance(schema_type, list):
        return next(
            (value for value in schema_type if isinstance(value, str) and value != "null"), ""
        )
    return ""


def _name_based_fallback_example(canonical: str) -> Any | None:
    if canonical.endswith("_id"):
        return "ENTITY_001"
    if canonical.endswith("_date"):
        return "2026-02-20"
    return None


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
    example = resolved_schema.get("example")
    return example if example is not None else _fallback_example(field_name, resolved_schema)


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
                "example": parameter.get("example")
                if parameter.get("example") is not None
                else _fallback_example(name, schema),
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
    return {
        "semanticId": field["semanticId"],
        "canonicalTerm": canonical,
        "preferredName": canonical,
        "description": field.get("description") or _fallback_description(field["name"]),
        "example": field.get("example"),
        "type": field_type,
        "locations": [field.get("location", "body")],
        "observedTypes": [field_type],
    }


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
        return value.strip().lower() in PLACEHOLDER_EXAMPLES
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0].strip().lower() in PLACEHOLDER_EXAMPLES
    return False


def validate_inventory(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_attribute_catalog(inventory.get("attributeCatalog", [])))
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

    output_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote inventory: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
