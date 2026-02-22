from fastapi.testclient import TestClient

from src.api.main import app


def _assert_property_has_docs(schema: dict, property_name: str) -> None:
    prop = schema["properties"][property_name]
    assert "description" in prop and prop["description"]
    assert ("example" in prop) or ("examples" in prop)


def test_lifecycle_async_and_support_schemas_have_descriptions_and_examples():
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    idempotency_schema = schemas["ProposalIdempotencyLookupResponse"]
    _assert_property_has_docs(idempotency_schema, "idempotency_key")
    _assert_property_has_docs(idempotency_schema, "request_hash")
    _assert_property_has_docs(idempotency_schema, "proposal_id")
    _assert_property_has_docs(idempotency_schema, "proposal_version_no")
    _assert_property_has_docs(idempotency_schema, "created_at")

    async_accepted_schema = schemas["ProposalAsyncAcceptedResponse"]
    _assert_property_has_docs(async_accepted_schema, "operation_id")
    _assert_property_has_docs(async_accepted_schema, "operation_type")
    _assert_property_has_docs(async_accepted_schema, "status")
    _assert_property_has_docs(async_accepted_schema, "correlation_id")
    _assert_property_has_docs(async_accepted_schema, "created_at")
    _assert_property_has_docs(async_accepted_schema, "status_url")

    async_status_schema = schemas["ProposalAsyncOperationStatusResponse"]
    _assert_property_has_docs(async_status_schema, "operation_id")
    _assert_property_has_docs(async_status_schema, "operation_type")
    _assert_property_has_docs(async_status_schema, "status")
    _assert_property_has_docs(async_status_schema, "correlation_id")
    _assert_property_has_docs(async_status_schema, "created_by")
    _assert_property_has_docs(async_status_schema, "created_at")
    _assert_property_has_docs(async_status_schema, "result")
    _assert_property_has_docs(async_status_schema, "error")


def test_lifecycle_endpoints_use_separate_request_and_response_objects():
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    create_sync = openapi["paths"]["/rebalance/proposals"]["post"]
    create_async = openapi["paths"]["/rebalance/proposals/async"]["post"]
    create_version_async = openapi["paths"]["/rebalance/proposals/{proposal_id}/versions/async"][
        "post"
    ]

    create_sync_body_ref = create_sync["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    create_sync_response_ref = create_sync["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert create_sync_body_ref.endswith("/ProposalCreateRequest")
    assert create_sync_response_ref.endswith("/ProposalCreateResponse")

    create_async_body_ref = create_async["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    create_async_response_ref = create_async["responses"]["202"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert create_async_body_ref.endswith("/ProposalCreateRequest")
    assert create_async_response_ref.endswith("/ProposalAsyncAcceptedResponse")

    create_version_async_body_ref = create_version_async["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    create_version_async_response_ref = create_version_async["responses"]["202"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert create_version_async_body_ref.endswith("/ProposalVersionRequest")
    assert create_version_async_response_ref.endswith("/ProposalAsyncAcceptedResponse")
