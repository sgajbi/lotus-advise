from fastapi.testclient import TestClient

from src.api.main import app


def _assert_property_has_docs(schema: dict, property_name: str) -> None:
    prop = schema["properties"][property_name]
    assert "description" in prop and prop["description"]
    assert ("example" in prop) or ("examples" in prop)


def test_lifecycle_async_and_support_schemas_have_descriptions_and_examples():
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    create_request_schema = schemas["ProposalCreateRequest"]
    _assert_property_has_docs(create_request_schema, "input_mode")
    _assert_property_has_docs(create_request_schema, "simulate_request")
    _assert_property_has_docs(create_request_schema, "stateless_input")
    _assert_property_has_docs(create_request_schema, "stateful_input")

    proposal_summary_schema = schemas["ProposalSummary"]
    _assert_property_has_docs(proposal_summary_schema, "lifecycle_origin")
    _assert_property_has_docs(proposal_summary_schema, "source_workspace_id")

    version_request_schema = schemas["ProposalVersionRequest"]
    _assert_property_has_docs(version_request_schema, "input_mode")
    _assert_property_has_docs(version_request_schema, "expected_current_version_no")
    _assert_property_has_docs(version_request_schema, "simulate_request")
    _assert_property_has_docs(version_request_schema, "stateless_input")
    _assert_property_has_docs(version_request_schema, "stateful_input")

    lineage_schema = schemas["ProposalLineageResponse"]
    _assert_property_has_docs(lineage_schema, "version_count")
    _assert_property_has_docs(lineage_schema, "latest_version_no")
    _assert_property_has_docs(lineage_schema, "latest_version_created_at")
    _assert_property_has_docs(lineage_schema, "lineage_complete")
    _assert_property_has_docs(lineage_schema, "missing_version_numbers")

    timeline_schema = schemas["ProposalWorkflowTimelineResponse"]
    _assert_property_has_docs(timeline_schema, "proposal")
    _assert_property_has_docs(timeline_schema, "event_count")
    _assert_property_has_docs(timeline_schema, "latest_event")

    approvals_schema = schemas["ProposalApprovalsResponse"]
    _assert_property_has_docs(approvals_schema, "proposal")
    _assert_property_has_docs(approvals_schema, "approval_count")
    _assert_property_has_docs(approvals_schema, "latest_approval_at")

    report_request_schema = schemas["ProposalReportRequest"]
    _assert_property_has_docs(report_request_schema, "report_type")
    _assert_property_has_docs(report_request_schema, "requested_by")
    _assert_property_has_docs(report_request_schema, "related_version_no")
    _assert_property_has_docs(report_request_schema, "include_execution_summary")

    report_response_schema = schemas["ProposalReportResponse"]
    _assert_property_has_docs(report_response_schema, "proposal")
    _assert_property_has_docs(report_response_schema, "report_request_id")
    _assert_property_has_docs(report_response_schema, "report_service")
    _assert_property_has_docs(report_response_schema, "report_reference_id")
    _assert_property_has_docs(report_response_schema, "explanation")

    execution_handoff_schema = schemas["ProposalExecutionHandoffRequest"]
    _assert_property_has_docs(execution_handoff_schema, "actor_id")
    _assert_property_has_docs(execution_handoff_schema, "execution_provider")
    _assert_property_has_docs(execution_handoff_schema, "expected_state")
    _assert_property_has_docs(execution_handoff_schema, "notes")

    execution_status_schema = schemas["ProposalExecutionStatusResponse"]
    _assert_property_has_docs(execution_status_schema, "handoff_status")
    _assert_property_has_docs(execution_status_schema, "execution_request_id")
    _assert_property_has_docs(execution_status_schema, "execution_provider")
    _assert_property_has_docs(execution_status_schema, "external_execution_id")
    _assert_property_has_docs(execution_status_schema, "explanation")

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

    create_sync = openapi["paths"]["/advisory/proposals"]["post"]
    create_async = openapi["paths"]["/advisory/proposals/async"]["post"]
    create_version_async = openapi["paths"]["/advisory/proposals/{proposal_id}/versions/async"][
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

    report_request = openapi["paths"]["/advisory/proposals/{proposal_id}/report-requests"]["post"]
    report_request_body_ref = report_request["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    report_request_response_ref = report_request["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert report_request_body_ref.endswith("/ProposalReportRequest")
    assert report_request_response_ref.endswith("/ProposalReportResponse")

    execution_handoff = openapi["paths"]["/advisory/proposals/{proposal_id}/execution-handoffs"][
        "post"
    ]
    parameter_names = [param["name"] for param in execution_handoff["parameters"]]
    assert "Idempotency-Key" in parameter_names
    execution_handoff_body_ref = execution_handoff["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    execution_handoff_response_ref = execution_handoff["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert execution_handoff_body_ref.endswith("/ProposalExecutionHandoffRequest")
    assert execution_handoff_response_ref.endswith("/ProposalExecutionHandoffResponse")


def test_openapi_does_not_expose_api_v1_compatibility_paths():
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    assert not any(path.startswith("/api/v1/") for path in openapi["paths"])


def test_openapi_tag_groups_are_documented_for_self_service_discovery():
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    tags = {item["name"]: item["description"] for item in openapi["tags"]}

    assert "Advisory Simulation" in tags
    assert "evaluate a proposed set of portfolio actions" in tags["Advisory Simulation"]
    assert "Advisory Proposal Lifecycle" in tags
    assert (
        "creation, versioning, state transitions, approvals, report requests, and execution "
        "handoff"
    ) in tags[
        "Advisory Proposal Lifecycle"
    ]
    assert "Advisory Operations & Support" in tags
    assert (
        "async status, workflow history, lineage, approval history, idempotency tracing"
    ) in tags[
        "Advisory Operations & Support"
    ]
    assert "Advisory Workspace" in tags
    assert "iterative advisory preparation" in tags["Advisory Workspace"]
    assert "Integration" in tags
    assert "service capability and contract discovery" in tags["Integration"]
    assert "Health" in tags
    assert "liveness and readiness probes" in tags["Health"]
    assert "Monitoring" in tags
    assert "metrics scraping and observability tooling" in tags["Monitoring"]


def test_openapi_separates_business_and_support_proposal_tags():
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    assert openapi["paths"]["/advisory/proposals"]["post"]["tags"] == [
        "Advisory Proposal Lifecycle"
    ]
    assert openapi["paths"]["/advisory/proposals/{proposal_id}/approvals"]["post"]["tags"] == [
        "Advisory Proposal Lifecycle"
    ]
    assert openapi["paths"]["/advisory/proposals/{proposal_id}/report-requests"]["post"][
        "tags"
    ] == ["Advisory Proposal Lifecycle"]
    assert openapi["paths"]["/advisory/proposals/operations/{operation_id}"]["get"]["tags"] == [
        "Advisory Operations & Support"
    ]
    assert openapi["paths"]["/advisory/proposals/{proposal_id}/workflow-events"]["get"][
        "tags"
    ] == ["Advisory Operations & Support"]
    assert openapi["paths"]["/advisory/proposals/{proposal_id}/execution-status"]["get"][
        "tags"
    ] == ["Advisory Operations & Support"]
