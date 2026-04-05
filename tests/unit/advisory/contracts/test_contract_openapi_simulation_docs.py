from fastapi.testclient import TestClient

from src.api.main import app


def _assert_property_has_docs(schema: dict, property_name: str) -> None:
    prop = schema["properties"][property_name]
    assert "description" in prop and prop["description"]
    assert ("example" in prop) or ("examples" in prop)


def test_simulation_openapi_documents_normalized_request_contract():
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    request_schema = schemas["ProposalSimulationRequest"]
    _assert_property_has_docs(request_schema, "input_mode")
    _assert_property_has_docs(request_schema, "simulate_request")
    _assert_property_has_docs(request_schema, "stateless_input")
    _assert_property_has_docs(request_schema, "stateful_input")

    with TestClient(app) as client:
        live_openapi = client.get("/openapi.json").json()

    simulate = live_openapi["paths"]["/advisory/proposals/simulate"]["post"]
    artifact = live_openapi["paths"]["/advisory/proposals/artifact"]["post"]

    simulate_body_ref = simulate["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    artifact_body_ref = artifact["requestBody"]["content"]["application/json"]["schema"]["$ref"]

    assert simulate_body_ref.endswith("/ProposalSimulationRequest")
    assert artifact_body_ref.endswith("/ProposalSimulationRequest")
    assert "normalized `stateless`/`stateful` advisory context contract" in simulate["description"]
    assert "Legacy direct simulation payloads remain supported" in artifact["description"]
