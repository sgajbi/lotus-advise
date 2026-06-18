from scripts.openapi_quality_gate import evaluate_schema


def test_evaluate_schema_reports_missing_endpoint_and_schema_metadata() -> None:
    schema = {
        "paths": {
            "/advisory/demo": {
                "get": {
                    "operationId": "readDemo",
                    "responses": {
                        "200": {"description": "OK"},
                    },
                },
                "parameters": [],
            }
        },
        "components": {
            "schemas": {
                "DemoResponse": {
                    "properties": {
                        "portfolio_id": {"type": "string"},
                        "advisor": {"$ref": "#/components/schemas/Advisor"},
                    }
                }
            }
        },
    }

    assert evaluate_schema(schema, service_name="lotus-advise") == [
        "OpenAPI quality gate (lotus-advise): missing endpoint documentation/response contract",
        "  - GET /advisory/demo: missing summary",
        "  - GET /advisory/demo: missing description",
        "  - GET /advisory/demo: missing tags",
        "  - GET /advisory/demo: missing error response (4xx/5xx/default)",
        "OpenAPI quality gate (lotus-advise): missing schema field metadata",
        "  - DemoResponse.portfolio_id: missing description",
        "  - DemoResponse.portfolio_id: missing example",
    ]


def test_evaluate_schema_reports_duplicate_operation_ids() -> None:
    operation = {
        "summary": "Read demo",
        "description": "Read demo contract.",
        "tags": ["advisory"],
        "operationId": "readDemo",
        "responses": {
            "200": {"description": "OK"},
            "404": {"description": "Not found"},
        },
    }
    schema = {
        "paths": {
            "/advisory/demo-a": {"get": operation},
            "/advisory/demo-b": {"post": operation},
        }
    }

    assert evaluate_schema(schema, service_name="lotus-advise") == [
        "OpenAPI quality gate (lotus-advise): duplicate operationId values",
        "  - readDemo",
    ]


def test_evaluate_schema_accepts_complete_operation_and_field_metadata() -> None:
    schema = {
        "paths": {
            "/advisory/demo": {
                "get": {
                    "summary": "Read demo",
                    "description": "Read demo contract.",
                    "tags": ["advisory"],
                    "operationId": "readDemo",
                    "responses": {
                        "200": {"description": "OK"},
                        "422": {"description": "Validation error"},
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "DemoResponse": {
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio identifier.",
                            "example": "PB_SG_GLOBAL_BAL_001",
                        },
                    }
                }
            }
        },
    }

    assert evaluate_schema(schema, service_name="lotus-advise") == []
