from fastapi.testclient import TestClient

from src.api.main import app


def _assert_property_has_docs(schema: dict, property_name: str) -> None:
    prop = schema["properties"][property_name]
    assert "description" in prop and prop["description"]
    assert ("example" in prop) or ("examples" in prop)


def test_workspace_schemas_have_descriptions_and_examples():
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    create_request_schema = schemas["WorkspaceSessionCreateRequest"]
    _assert_property_has_docs(create_request_schema, "workspace_name")
    _assert_property_has_docs(create_request_schema, "created_by")
    _assert_property_has_docs(create_request_schema, "input_mode")
    _assert_property_has_docs(create_request_schema, "stateless_input")
    _assert_property_has_docs(create_request_schema, "stateful_input")

    session_schema = schemas["WorkspaceSession"]
    _assert_property_has_docs(session_schema, "workspace_id")
    _assert_property_has_docs(session_schema, "workspace_name")
    _assert_property_has_docs(session_schema, "lifecycle_state")
    _assert_property_has_docs(session_schema, "input_mode")
    _assert_property_has_docs(session_schema, "resolved_context")


def test_workspace_endpoint_has_documented_request_and_response_contracts():
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    create_workspace = openapi["paths"]["/advisory/workspaces"]["post"]
    request_ref = create_workspace["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    response_ref = create_workspace["responses"]["201"]["content"]["application/json"]["schema"][
        "$ref"
    ]

    assert request_ref.endswith("/WorkspaceSessionCreateRequest")
    assert response_ref.endswith("/WorkspaceSessionCreateResponse")
    assert create_workspace["summary"] == "Create an Advisory Workspace Session"
