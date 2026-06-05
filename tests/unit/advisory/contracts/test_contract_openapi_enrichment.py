from __future__ import annotations

from src.api.openapi_enrichment import enrich_openapi_schema
from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH


def test_openapi_enrichment_adds_operation_defaults_and_idempotency_header_bounds() -> None:
    schema = {
        "paths": {
            "/advisory/proposals": {
                "post": {
                    "responses": {"200": {"description": "OK"}},
                    "parameters": [
                        {
                            "name": "Idempotency-Key",
                            "in": "header",
                            "schema": {"type": "string"},
                        }
                    ],
                },
                "parameters": [{"name": "ignored"}],
            },
            "/health": {"get": {"responses": {"503": {"description": "Unavailable"}}}},
            "/metrics": {"get": {"responses": {"200": {"description": "OK"}}}},
        }
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-advise")
    proposal_operation = enriched["paths"]["/advisory/proposals"]["post"]
    health_operation = enriched["paths"]["/health"]["get"]
    metrics_operation = enriched["paths"]["/metrics"]["get"]

    assert proposal_operation["summary"] == "POST /advisory/proposals"
    assert proposal_operation["description"] == (
        "POST operation for /advisory/proposals in lotus-advise."
    )
    assert proposal_operation["tags"] == ["Advisory"]
    assert proposal_operation["responses"]["default"] == {
        "description": "Unexpected error response."
    }
    assert proposal_operation["parameters"][0]["schema"]["maxLength"] == (
        MAX_IDEMPOTENCY_KEY_LENGTH
    )
    assert "Idempotency keys are replay-safe" in proposal_operation["parameters"][0]["description"]
    assert health_operation["tags"] == ["Health"]
    assert "default" not in health_operation["responses"]
    assert metrics_operation["tags"] == ["Monitoring"]


def test_openapi_enrichment_repairs_nested_schema_examples() -> None:
    schema = {
        "paths": {},
        "components": {
            "schemas": {
                "Envelope": {
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Item"},
                            "example": [{"sourceId": "SOURCE_009", "priority": "BAD"}],
                        },
                        "weights": {
                            "type": "object",
                            "additionalProperties": {"type": "string", "pattern": r"\d*\.?\d*"},
                            "example": {"USD": 123},
                        },
                    }
                },
                "Item": {
                    "properties": {
                        "sourceId": {"type": "string"},
                        "priority": {"enum": ["HIGH", "LOW"]},
                        "summary": {"type": "string"},
                    },
                    "required": ["sourceId", "priority", "summary"],
                },
            }
        },
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-advise")
    properties = enriched["components"]["schemas"]["Envelope"]["properties"]

    assert properties["items"]["example"] == [
        {"sourceId": "SOURCE_009", "priority": "HIGH", "summary": "example_summary"}
    ]
    assert properties["weights"]["example"] == {"USD": "0.125"}


def test_openapi_enrichment_infers_domain_field_descriptions() -> None:
    schema = {
        "paths": {},
        "components": {
            "schemas": {
                "DescriptionModel": {
                    "properties": {
                        "portfolioId": {"type": "string"},
                        "businessDate": {"type": "string", "format": "date"},
                        "generatedAt": {"type": "string", "format": "date-time"},
                        "settlementCurrency": {"type": "string"},
                        "marketValue": {"type": "number"},
                        "orderQuantity": {"type": "number"},
                        "marketPrice": {"type": "number"},
                        "lifecycleStatus": {"type": "string"},
                        "customField": {"type": "string"},
                    }
                }
            }
        },
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-advise")
    properties = enriched["components"]["schemas"]["DescriptionModel"]["properties"]

    assert properties["portfolioId"]["description"] == "Unique portfolio identifier."
    assert properties["businessDate"]["description"] == "Business date for business date."
    assert properties["generatedAt"]["description"] == "Timestamp for generated at."
    assert properties["settlementCurrency"]["description"] == (
        "ISO currency code for settlement currency."
    )
    assert properties["marketValue"]["description"] == "Monetary value for market value."
    assert properties["orderQuantity"]["description"] == "Quantity value for order quantity."
    assert properties["marketPrice"]["description"] == "Rate/price value for market price."
    assert properties["lifecycleStatus"]["description"] == ("Current status for lifecycle status.")
    assert properties["customField"]["description"] == "description model field: custom field."
