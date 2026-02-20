import os

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


def _strict_openapi_validation_enabled() -> bool:
    value = os.getenv("DPM_STRICT_OPENAPI_VALIDATION")
    if value is None:
        return True
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _guard_strict_validation() -> None:
    if not _strict_openapi_validation_enabled():
        pytest.skip("DPM_STRICT_OPENAPI_VALIDATION=false")


def _assert_property_has_docs(schema: dict, property_name: str) -> None:
    prop = schema["properties"][property_name]
    assert "description" in prop and prop["description"]
    assert ("example" in prop) or ("examples" in prop) or ("$ref" in prop)


def test_dpm_supportability_and_async_schemas_have_descriptions_and_examples():
    _guard_strict_validation()
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    run_lookup_schema = schemas["DpmRunLookupResponse"]
    _assert_property_has_docs(run_lookup_schema, "rebalance_run_id")
    _assert_property_has_docs(run_lookup_schema, "correlation_id")
    _assert_property_has_docs(run_lookup_schema, "request_hash")
    _assert_property_has_docs(run_lookup_schema, "portfolio_id")
    _assert_property_has_docs(run_lookup_schema, "created_at")
    _assert_property_has_docs(run_lookup_schema, "result")

    run_list_schema = schemas["DpmRunListResponse"]
    _assert_property_has_docs(run_list_schema, "items")
    _assert_property_has_docs(run_list_schema, "next_cursor")

    run_list_item_schema = schemas["DpmRunListItemResponse"]
    _assert_property_has_docs(run_list_item_schema, "rebalance_run_id")
    _assert_property_has_docs(run_list_item_schema, "correlation_id")
    _assert_property_has_docs(run_list_item_schema, "request_hash")
    _assert_property_has_docs(run_list_item_schema, "idempotency_key")
    _assert_property_has_docs(run_list_item_schema, "portfolio_id")
    _assert_property_has_docs(run_list_item_schema, "status")
    _assert_property_has_docs(run_list_item_schema, "created_at")

    idempotency_schema = schemas["DpmRunIdempotencyLookupResponse"]
    _assert_property_has_docs(idempotency_schema, "idempotency_key")
    _assert_property_has_docs(idempotency_schema, "request_hash")
    _assert_property_has_docs(idempotency_schema, "rebalance_run_id")
    _assert_property_has_docs(idempotency_schema, "created_at")

    idempotency_history_schema = schemas["DpmRunIdempotencyHistoryResponse"]
    _assert_property_has_docs(idempotency_history_schema, "idempotency_key")
    _assert_property_has_docs(idempotency_history_schema, "history")

    idempotency_history_item_schema = schemas["DpmRunIdempotencyHistoryItem"]
    _assert_property_has_docs(idempotency_history_item_schema, "rebalance_run_id")
    _assert_property_has_docs(idempotency_history_item_schema, "correlation_id")
    _assert_property_has_docs(idempotency_history_item_schema, "request_hash")
    _assert_property_has_docs(idempotency_history_item_schema, "created_at")

    async_accepted_schema = schemas["DpmAsyncAcceptedResponse"]
    _assert_property_has_docs(async_accepted_schema, "operation_id")
    _assert_property_has_docs(async_accepted_schema, "operation_type")
    _assert_property_has_docs(async_accepted_schema, "status")
    _assert_property_has_docs(async_accepted_schema, "correlation_id")
    _assert_property_has_docs(async_accepted_schema, "created_at")
    _assert_property_has_docs(async_accepted_schema, "status_url")
    _assert_property_has_docs(async_accepted_schema, "execute_url")

    async_status_schema = schemas["DpmAsyncOperationStatusResponse"]
    _assert_property_has_docs(async_status_schema, "operation_id")
    _assert_property_has_docs(async_status_schema, "operation_type")
    _assert_property_has_docs(async_status_schema, "status")
    _assert_property_has_docs(async_status_schema, "is_executable")
    _assert_property_has_docs(async_status_schema, "correlation_id")
    _assert_property_has_docs(async_status_schema, "created_at")
    _assert_property_has_docs(async_status_schema, "result")
    _assert_property_has_docs(async_status_schema, "error")

    artifact_schema = schemas["DpmRunArtifactResponse"]
    _assert_property_has_docs(artifact_schema, "artifact_id")
    _assert_property_has_docs(artifact_schema, "artifact_version")
    _assert_property_has_docs(artifact_schema, "rebalance_run_id")
    _assert_property_has_docs(artifact_schema, "correlation_id")
    _assert_property_has_docs(artifact_schema, "portfolio_id")
    _assert_property_has_docs(artifact_schema, "status")
    _assert_property_has_docs(artifact_schema, "request_snapshot")
    _assert_property_has_docs(artifact_schema, "before_summary")
    _assert_property_has_docs(artifact_schema, "after_summary")
    _assert_property_has_docs(artifact_schema, "order_intents")
    _assert_property_has_docs(artifact_schema, "rule_outcomes")
    _assert_property_has_docs(artifact_schema, "diagnostics")
    _assert_property_has_docs(artifact_schema, "result")
    _assert_property_has_docs(artifact_schema, "evidence")

    workflow_action_schema = schemas["DpmRunWorkflowActionRequest"]
    _assert_property_has_docs(workflow_action_schema, "action")
    _assert_property_has_docs(workflow_action_schema, "reason_code")
    _assert_property_has_docs(workflow_action_schema, "comment")
    _assert_property_has_docs(workflow_action_schema, "actor_id")

    workflow_schema = schemas["DpmRunWorkflowResponse"]
    _assert_property_has_docs(workflow_schema, "run_id")
    _assert_property_has_docs(workflow_schema, "run_status")
    _assert_property_has_docs(workflow_schema, "workflow_status")
    _assert_property_has_docs(workflow_schema, "requires_review")
    _assert_property_has_docs(workflow_schema, "latest_decision")

    workflow_history_schema = schemas["DpmRunWorkflowHistoryResponse"]
    _assert_property_has_docs(workflow_history_schema, "run_id")
    _assert_property_has_docs(workflow_history_schema, "decisions")

    lineage_schema = schemas["DpmLineageResponse"]
    _assert_property_has_docs(lineage_schema, "entity_id")
    _assert_property_has_docs(lineage_schema, "edges")


def test_dpm_async_and_supportability_endpoints_use_expected_request_response_contracts():
    _guard_strict_validation()
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    analyze_async = openapi["paths"]["/rebalance/analyze/async"]["post"]
    assert analyze_async["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BatchRebalanceRequest"
    )
    assert analyze_async["responses"]["202"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncAcceptedResponse")
    assert "X-Correlation-Id" in analyze_async["responses"]["202"]["headers"]

    execute_async = openapi["paths"]["/rebalance/operations/{operation_id}/execute"]["post"]
    assert "requestBody" not in execute_async
    assert execute_async["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmAsyncOperationStatusResponse")

    run_artifact = openapi["paths"]["/rebalance/runs/{rebalance_run_id}/artifact"]["get"]
    assert run_artifact["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunArtifactResponse")

    list_runs = openapi["paths"]["/rebalance/runs"]["get"]
    assert list_runs["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmRunListResponse"
    )

    lineage = openapi["paths"]["/rebalance/lineage/{entity_id}"]["get"]
    assert lineage["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmLineageResponse"
    )

    idempotency_history = openapi["paths"]["/rebalance/idempotency/{idempotency_key}/history"][
        "get"
    ]
    assert idempotency_history["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunIdempotencyHistoryResponse")

    workflow = openapi["paths"]["/rebalance/runs/{rebalance_run_id}/workflow"]["get"]
    assert workflow["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/DpmRunWorkflowResponse"
    )

    workflow_by_correlation = openapi["paths"][
        "/rebalance/runs/by-correlation/{correlation_id}/workflow"
    ]["get"]
    assert workflow_by_correlation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")

    workflow_by_idempotency = openapi["paths"][
        "/rebalance/runs/idempotency/{idempotency_key}/workflow"
    ]["get"]
    assert workflow_by_idempotency["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")

    workflow_actions = openapi["paths"]["/rebalance/runs/{rebalance_run_id}/workflow/actions"][
        "post"
    ]
    workflow_action_request_ref = workflow_actions["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert workflow_action_request_ref.endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowResponse")

    workflow_actions_by_correlation = openapi["paths"][
        "/rebalance/runs/by-correlation/{correlation_id}/workflow/actions"
    ]["post"]
    assert workflow_actions_by_correlation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowResponse")

    workflow_actions_by_idempotency = openapi["paths"][
        "/rebalance/runs/idempotency/{idempotency_key}/workflow/actions"
    ]["post"]
    assert workflow_actions_by_idempotency["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowActionRequest")
    assert workflow_actions_by_idempotency["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowResponse")

    workflow_history = openapi["paths"]["/rebalance/runs/{rebalance_run_id}/workflow/history"][
        "get"
    ]
    assert workflow_history["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/DpmRunWorkflowHistoryResponse")

    workflow_history_by_correlation = openapi["paths"][
        "/rebalance/runs/by-correlation/{correlation_id}/workflow/history"
    ]["get"]
    assert workflow_history_by_correlation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowHistoryResponse")

    workflow_history_by_idempotency = openapi["paths"][
        "/rebalance/runs/idempotency/{idempotency_key}/workflow/history"
    ]["get"]
    assert workflow_history_by_idempotency["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/DpmRunWorkflowHistoryResponse")
