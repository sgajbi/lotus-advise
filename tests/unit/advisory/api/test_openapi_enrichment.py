from __future__ import annotations

from src.api.openapi_enrichment import enrich_openapi_schema


def test_openapi_enrichment_adds_operation_docs_tags_errors_and_schema_examples() -> None:
    schema = {
        "info": {"description": "Advisory API."},
        "paths": {
            "/health": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/metrics": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/advisory/proposals": {
                "post": {
                    "responses": {
                        "201": {
                            "description": "created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ReferencedModel"},
                                    "examples": {
                                        "created": {
                                            "value": {
                                                "sourceId": "SOURCE_003",
                                                "priority": "NOT_VALID",
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    }
                },
                "parameters": [],
            },
            "/ignored": ["not", "a", "method-map"],
        },
        "components": {
            "schemas": {
                "ExampleModel": {
                    "properties": {
                        "portfolioId": {"type": "string"},
                        "status": {"enum": ["READY", "PENDING"]},
                        "referencedEnum": {"$ref": "#/components/schemas/ReferencedEnum"},
                        "items": {"type": "array", "items": {"type": "integer"}},
                        "refItems": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ReferencedModel"},
                        },
                        "composedItems": {
                            "type": "array",
                            "items": {"allOf": [{"$ref": "#/components/schemas/ReferencedModel"}]},
                        },
                        "incompleteExistingItems": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ReferencedModel"},
                            "example": [{"sourceId": "SOURCE_002"}],
                        },
                        "invalidEnum": {
                            "enum": ["PASSED", "FAILED"],
                            "example": "READY",
                        },
                        "currencyMap": {
                            "type": "object",
                            "additionalProperties": {"type": "string", "pattern": r"\d*\.?\d*"},
                        },
                        "metadata": {"type": "object"},
                        "enabled": {"type": "boolean"},
                        "ttlHours": {"type": "integer"},
                        "version": {"type": "integer"},
                        "settlementDays": {"type": "integer", "maximum": 10},
                        "floatBoundedDays": {"type": "integer", "minimum": 0.0, "maximum": 10.0},
                        "weight": {"type": "number"},
                        "numericText": {"type": "string", "pattern": r"\d*\.?\d*"},
                        "constantText": {"type": "string", "const": "AUTO_FX"},
                        "marketPrice": {"type": "number"},
                        "orderQuantity": {"type": "number"},
                        "marketValue": {"type": "number"},
                        "genericRatio": {"type": "number"},
                        "businessDate": {"type": "string", "format": "date"},
                        "generatedAt": {"type": "string", "format": "date-time"},
                        "settlementCurrency": {"type": "string"},
                        "effectiveDate": {"type": "string"},
                        "eventTimestamp": {"type": "string"},
                        "lifecycleStatus": {"type": "string"},
                        "unknownText": {"type": "string"},
                        "fallbackThingId": {},
                        "fallback": {},
                        "ignored": ["not", "a", "property"],
                    }
                },
                "ReferencedModel": {
                    "properties": {
                        "sourceId": {"type": "string"},
                        "weight": {"type": "string", "pattern": r"\d*\.?\d*"},
                        "summary": {"type": "string"},
                        "priority": {"enum": ["HIGH", "LOW"]},
                        "actorId": {"type": "string"},
                    },
                    "required": ["sourceId", "weight", "summary", "priority", "actorId"],
                },
                "ReferencedEnum": {
                    "type": "string",
                    "enum": ["HEURISTIC", "SOLVER"],
                },
                "ModelWithoutProperties": {"properties": []},
                "IgnoredModel": ["not", "a", "schema"],
            }
        },
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-advise")

    assert enriched["info"]["title"] == "Lotus Advise API"
    assert enriched["info"]["contact"] == {"name": "Lotus Platform Engineering"}
    assert enriched["info"]["description"].startswith("Lotus platform API contract.")
    assert enriched["servers"] == [
        {"url": "/", "description": "Relative Lotus Advise service root."}
    ]
    health = enriched["paths"]["/health"]["get"]
    metrics = enriched["paths"]["/metrics"]["get"]
    proposal = enriched["paths"]["/advisory/proposals"]["post"]
    properties = enriched["components"]["schemas"]["ExampleModel"]["properties"]

    assert health["summary"] == "GET /health"
    assert health["tags"] == ["Health"]
    assert metrics["tags"] == ["Monitoring"]
    assert proposal["tags"] == ["Advisory"]
    assert proposal["responses"]["default"] == {"description": "Unexpected error response."}
    assert proposal["responses"]["201"]["content"]["application/json"]["examples"]["created"][
        "value"
    ] == {
        "sourceId": "SOURCE_003",
        "weight": "0.125",
        "summary": "example_summary",
        "priority": "HIGH",
        "actorId": "ACTOR_001",
    }
    assert properties["portfolioId"]["description"] == "Unique portfolio identifier."
    assert properties["portfolioId"]["example"] == "PB_SG_GLOBAL_BAL_001"
    assert properties["status"]["example"] == "READY"
    assert properties["referencedEnum"]["example"] == "HEURISTIC"
    assert properties["items"]["example"] == [10]
    expected_referenced_example = {
        "sourceId": "SOURCE_001",
        "weight": "0.125",
        "summary": "example_summary",
        "priority": "HIGH",
        "actorId": "ACTOR_001",
    }
    assert properties["refItems"]["example"] == [expected_referenced_example]
    assert properties["composedItems"]["example"] == [expected_referenced_example]
    assert properties["incompleteExistingItems"]["example"] == [
        {
            "sourceId": "SOURCE_002",
            "weight": "0.125",
            "summary": "example_summary",
            "priority": "HIGH",
            "actorId": "ACTOR_001",
        }
    ]
    assert properties["invalidEnum"]["example"] == "PASSED"
    assert properties["currencyMap"]["example"] == {"USD": "0.125"}
    assert properties["metadata"]["example"] == {"key": "sample_text"}
    assert properties["enabled"]["example"] is True
    assert properties["ttlHours"]["example"] == 24
    assert properties["version"]["example"] == 1
    assert properties["settlementDays"]["example"] == 5
    assert properties["floatBoundedDays"]["example"] == 5
    assert properties["weight"]["example"] == 0.125
    assert properties["numericText"]["example"] == "0.125"
    assert properties["constantText"]["example"] == "AUTO_FX"
    assert properties["marketPrice"]["example"] == 1.2345
    assert properties["orderQuantity"]["example"] == 100.0
    assert properties["marketValue"]["example"] == 125000.5
    assert properties["genericRatio"]["example"] == 10.5
    assert properties["businessDate"]["example"] == "2026-03-02"
    assert properties["generatedAt"]["example"] == "2026-03-02T10:30:00Z"
    assert properties["settlementCurrency"]["example"] == "USD"
    assert properties["effectiveDate"]["description"] == "example model field: effective date."
    assert properties["eventTimestamp"]["example"] == "2026-03-02T10:30:00Z"
    assert properties["lifecycleStatus"]["example"] == "ACTIVE"
    assert properties["unknownText"]["example"] == "example_unknown_text"
    assert properties["fallbackThingId"]["example"] == "FALLBACK_THING_001"
    assert properties["fallback"]["example"] == "fallback_example"


def test_openapi_enrichment_preserves_existing_lotus_description_and_error_responses() -> None:
    schema = {
        "info": {"title": "Custom API", "description": "Lotus custom contract."},
        "paths": {
            "/custom": {
                "get": {
                    "summary": "Existing summary",
                    "description": "Existing description",
                    "tags": ["Custom"],
                    "responses": {"404": {"description": "missing"}},
                },
                "head": {"responses": {"200": {"description": "ok"}}},
                "post": ["not", "an", "operation"],
            }
        },
        "components": {"schemas": {}},
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-advise")

    operation = enriched["paths"]["/custom"]["get"]
    assert enriched["info"]["title"] == "Custom API"
    assert enriched["info"]["contact"] == {"name": "Lotus Platform Engineering"}
    assert enriched["info"]["description"] == "Lotus custom contract."
    assert operation["summary"] == "Existing summary"
    assert operation["description"] == "Existing description"
    assert operation["tags"] == ["Custom"]
    assert "default" not in operation["responses"]
