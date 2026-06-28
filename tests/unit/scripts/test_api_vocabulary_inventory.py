from __future__ import annotations

from scripts.api_vocabulary_inventory import (
    _attribute_catalog_entry,
    _extract_fields,
    _fallback_example,
    _preserve_stable_generated_at,
    validate_inventory,
)


def test_fallback_example_uses_governed_non_placeholder_values() -> None:
    assert _fallback_example("status", {"enum": ["READY", "BLOCKED"]}) == "READY"
    assert _fallback_example("status", {"enum": [None, "READY"]}) is None
    assert _fallback_example("as_of", {"format": "date"}) == "2026-02-20"
    assert _fallback_example("created_at", {"format": "date-time"}) == "2026-02-20T00:00:00Z"
    assert _fallback_example("proposal_id", {"type": "string"}) == "ENTITY_001"
    assert _fallback_example("review_required", {"type": "boolean"}) is True
    assert _fallback_example("review_required", {"type": ["boolean", "null"]}) is True
    assert _fallback_example("cash_weight", {"type": "number"}) == 0.1
    assert _fallback_example("unsupported", {"type": "string"}) == "STANDARD_TEXT"


def test_extract_fields_expands_nested_objects_refs_and_arrays() -> None:
    components = {
        "schemas": {
            "ClientRef": {
                "type": "object",
                "required": ["clientId"],
                "properties": {
                    "clientId": {
                        "type": "string",
                        "description": "Client identifier.",
                        "example": "CLIENT_001",
                    },
                    "bookingCenter": {"type": "string"},
                },
            }
        }
    }
    schema = {
        "type": "object",
        "required": ["client", "actions"],
        "properties": {
            "client": {"$ref": "#/components/schemas/ClientRef"},
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["actionId"],
                    "properties": {"actionId": {"type": "string"}},
                },
            },
        },
    }

    fields = _extract_fields(schema, components=components)
    by_name = {field["name"]: field for field in fields}

    assert by_name["client"]["required"] is True
    assert by_name["client.clientId"]["required"] is True
    assert by_name["client.clientId"]["semanticId"] == "lotus.client_id"
    assert by_name["client.clientId"]["example"] == "CLIENT_001"
    assert by_name["client.bookingCenter"]["semanticId"] == "lotus.booking_center_code"
    assert by_name["actions"]["required"] is True
    assert by_name["actions[].actionId"]["semanticId"] == "lotus.action_id"
    assert by_name["actions[].actionId"]["example"] == "ENTITY_001"


def test_attribute_catalog_uses_canonical_description_for_reused_terms() -> None:
    entry = _attribute_catalog_entry(
        {
            "name": "intent_type",
            "location": "body",
            "type": "string",
            "semanticId": "lotus.intent_type",
            "description": "Endpoint-specific intake posture.",
            "example": "REVIEW_FOR_ADVISORY_PROPOSAL",
        }
    )

    assert entry["description"] == (
        "Canonical business intent discriminator used by lotus-advise APIs."
    )
    assert entry["example"] == "SECURITY_TRADE"


def test_preserve_stable_generated_at_when_inventory_content_is_unchanged() -> None:
    existing = {
        "generatedAt": "2026-06-28T00:00:00+00:00",
        "attributeCatalog": [{"semanticId": "lotus.client_id"}],
    }
    generated = {
        "generatedAt": "2026-06-28T01:00:00+00:00",
        "attributeCatalog": [{"semanticId": "lotus.client_id"}],
    }

    stable = _preserve_stable_generated_at(generated, existing)

    assert stable["generatedAt"] == "2026-06-28T00:00:00+00:00"


def test_preserve_stable_generated_at_keeps_new_timestamp_when_inventory_changed() -> None:
    existing = {
        "generatedAt": "2026-06-28T00:00:00+00:00",
        "attributeCatalog": [{"semanticId": "lotus.client_id"}],
    }
    generated = {
        "generatedAt": "2026-06-28T01:00:00+00:00",
        "attributeCatalog": [{"semanticId": "lotus.client_id"}, {"semanticId": "lotus.risk_id"}],
    }

    stable = _preserve_stable_generated_at(generated, existing)

    assert stable["generatedAt"] == "2026-06-28T01:00:00+00:00"


def test_validate_inventory_rejects_placeholder_and_endpoint_metadata_duplication() -> None:
    inventory = {
        "attributeCatalog": [
            {
                "semanticId": "lotus.client_id",
                "canonicalTerm": "client_id",
                "preferredName": "client_id",
                "example": "sample",
            },
            {
                "semanticId": "lotus.client_id",
                "canonicalTerm": "clientId",
                "preferredName": "client_id",
                "example": "CLIENT_001",
            },
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/advisory/proposals",
                "request": {
                    "fields": [
                        {
                            "name": "clientId",
                            "semanticId": "",
                            "attributeRef": "",
                            "description": "duplicated metadata",
                        }
                    ]
                },
                "response": {"fields": []},
            }
        ],
    }

    errors = validate_inventory(inventory)

    assert "generic placeholder example is not allowed: lotus.client_id" in errors
    assert "duplicate semanticId: lotus.client_id" in errors
    assert "canonicalTerm/preferredName mismatch: lotus.client_id" in errors
    assert "canonicalTerm must be snake_case: lotus.client_id -> clientId" in errors
    assert any(
        "endpoint field duplicates attribute metadata (description)" in error for error in errors
    )
    assert any("endpoint field missing semanticId" in error for error in errors)
    assert any("endpoint field missing attributeRef" in error for error in errors)
