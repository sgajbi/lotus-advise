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
