from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_PATH = str(PROJECT_ROOT)
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

from src.api.main import app  # noqa: E402

ALLOWED_METHODS = {"get", "post", "put", "patch", "delete"}


def _has_success_response(operation: dict[str, Any]) -> bool:
    responses = operation.get("responses", {})
    return any(str(code).startswith("2") for code in responses)


def _has_error_response(operation: dict[str, Any]) -> bool:
    responses = operation.get("responses", {})
    return any(
        str(code).startswith("4") or str(code).startswith("5") or str(code) == "default"
        for code in responses
    )


def _is_ref_only(prop_schema: dict[str, Any]) -> bool:
    return set(prop_schema.keys()) == {"$ref"}


def _iter_operations(
    schema: dict[str, Any],
) -> Iterable[tuple[str, str, dict[str, Any]]]:
    for path, methods in schema.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in ALLOWED_METHODS or not isinstance(operation, dict):
                continue
            yield method.upper(), str(path), operation


def _missing_operation_documentation(
    *,
    method: str,
    path: str,
    operation: dict[str, Any],
) -> list[tuple[str, str, str]]:
    missing_docs: list[tuple[str, str, str]] = []
    for field_name in ("summary", "description", "tags"):
        if not operation.get(field_name):
            missing_docs.append((method, path, field_name))

    if not operation.get("responses"):
        missing_docs.append((method, path, "responses"))
        return missing_docs

    if not _has_success_response(operation):
        missing_docs.append((method, path, "2xx response"))
    if not _has_error_response(operation):
        missing_docs.append((method, path, "error response (4xx/5xx/default)"))
    return missing_docs


def _iter_component_properties(
    schema: dict[str, Any],
) -> Iterable[tuple[str, str, dict[str, Any]]]:
    schemas = schema.get("components", {}).get("schemas", {})
    if not isinstance(schemas, dict):
        return

    for model_name, model_schema in schemas.items():
        if not isinstance(model_schema, dict):
            continue
        properties = model_schema.get("properties", {})
        if not isinstance(properties, dict):
            continue
        for prop_name, prop_schema in properties.items():
            if isinstance(prop_schema, dict):
                yield str(model_name), str(prop_name), prop_schema


def _missing_schema_field_metadata(
    *,
    model_name: str,
    prop_name: str,
    prop_schema: dict[str, Any],
) -> list[tuple[str, str, str]]:
    if _is_ref_only(prop_schema):
        return []

    missing_fields: list[tuple[str, str, str]] = []
    if not prop_schema.get("description"):
        missing_fields.append((model_name, prop_name, "description"))
    if "example" not in prop_schema and "examples" not in prop_schema:
        missing_fields.append((model_name, prop_name, "example"))
    return missing_fields


def _duplicate_operation_ids(operation_ids: Iterable[str]) -> list[str]:
    return sorted([op_id for op_id, count in Counter(operation_ids).items() if count > 1])


def evaluate_schema(schema: dict[str, Any], *, service_name: str) -> list[str]:
    missing_docs: list[tuple[str, str, str]] = []
    missing_fields: list[tuple[str, str, str]] = []
    operation_ids: list[str] = []

    for method, path, operation in _iter_operations(schema):
        operation_id = operation.get("operationId")
        if operation_id:
            operation_ids.append(str(operation_id))
        missing_docs.extend(
            _missing_operation_documentation(
                method=method,
                path=path,
                operation=operation,
            )
        )

    for model_name, prop_name, prop_schema in _iter_component_properties(schema):
        missing_fields.extend(
            _missing_schema_field_metadata(
                model_name=model_name,
                prop_name=prop_name,
                prop_schema=prop_schema,
            )
        )

    errors: list[str] = []
    if missing_docs:
        errors.append(
            "OpenAPI quality gate "
            f"({service_name}): missing endpoint documentation/response contract"
        )
        errors.extend(
            f"  - {method} {path}: missing {field_name}"
            for method, path, field_name in missing_docs
        )

    if missing_fields:
        errors.append(f"OpenAPI quality gate ({service_name}): missing schema field metadata")
        errors.extend(
            f"  - {model}.{field}: missing {field_name}"
            for model, field, field_name in missing_fields
        )

    duplicate_operation_ids = _duplicate_operation_ids(operation_ids)
    if duplicate_operation_ids:
        errors.append(f"OpenAPI quality gate ({service_name}): duplicate operationId values")
        errors.extend(f"  - {op_id}" for op_id in duplicate_operation_ids)

    return errors


def main() -> int:
    schema = app.openapi()
    if "paths" not in schema or not schema["paths"]:
        print("OpenAPI quality gate (lotus-advise): no paths defined")
        return 1

    errors = evaluate_schema(schema, service_name="lotus-advise")
    if errors:
        print("\n".join(errors))
        return 1

    print("OpenAPI quality gate passed for lotus-advise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
