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
    _assert_property_has_docs(session_schema, "draft_state")
    _assert_property_has_docs(session_schema, "resolved_context")
    _assert_property_has_docs(session_schema, "latest_replay_evidence")
    _assert_property_has_docs(session_schema, "saved_version_count")
    _assert_property_has_docs(session_schema, "latest_saved_version")

    action_request_schema = schemas["WorkspaceDraftActionRequest"]
    _assert_property_has_docs(action_request_schema, "actor_id")
    _assert_property_has_docs(action_request_schema, "action_type")
    _assert_property_has_docs(action_request_schema, "workspace_trade_id")
    _assert_property_has_docs(action_request_schema, "workspace_cash_flow_id")
    _assert_property_has_docs(action_request_schema, "trade")
    _assert_property_has_docs(action_request_schema, "cash_flow")
    _assert_property_has_docs(action_request_schema, "options")

    save_request_schema = schemas["WorkspaceSaveRequest"]
    _assert_property_has_docs(save_request_schema, "saved_by")
    _assert_property_has_docs(save_request_schema, "version_label")

    compare_request_schema = schemas["WorkspaceCompareRequest"]
    _assert_property_has_docs(compare_request_schema, "workspace_version_id")

    saved_version_schema = schemas["WorkspaceSavedVersion"]
    _assert_property_has_docs(saved_version_schema, "workspace_version_id")
    _assert_property_has_docs(saved_version_schema, "version_number")
    _assert_property_has_docs(saved_version_schema, "replay_evidence")


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

    draft_action = openapi["paths"]["/advisory/workspaces/{workspace_id}/draft-actions"]["post"]
    draft_action_request_ref = draft_action["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    draft_action_response_ref = draft_action["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert draft_action_request_ref.endswith("/WorkspaceDraftActionRequest")
    assert draft_action_response_ref.endswith("/WorkspaceDraftActionResponse")
    assert draft_action["summary"] == "Apply an Advisory Workspace Draft Action"

    save_workspace = openapi["paths"]["/advisory/workspaces/{workspace_id}/save"]["post"]
    save_request_ref = save_workspace["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    save_response_ref = save_workspace["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert save_request_ref.endswith("/WorkspaceSaveRequest")
    assert save_response_ref.endswith("/WorkspaceSaveResponse")
    assert save_workspace["summary"] == "Save an Advisory Workspace Version"

    list_saved_versions = openapi["paths"]["/advisory/workspaces/{workspace_id}/saved-versions"]["get"]
    list_response_ref = list_saved_versions["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    assert list_response_ref.endswith("/WorkspaceSavedVersionListResponse")

    resume_workspace = openapi["paths"]["/advisory/workspaces/{workspace_id}/resume"]["post"]
    resume_request_ref = resume_workspace["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    resume_response_ref = resume_workspace["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    assert resume_request_ref.endswith("/WorkspaceResumeRequest")
    assert resume_response_ref.endswith("/WorkspaceSession")

    compare_workspace = openapi["paths"]["/advisory/workspaces/{workspace_id}/compare"]["post"]
    compare_request_ref = compare_workspace["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    compare_response_ref = compare_workspace["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert compare_request_ref.endswith("/WorkspaceCompareRequest")
    assert compare_response_ref.endswith("/WorkspaceCompareResponse")
