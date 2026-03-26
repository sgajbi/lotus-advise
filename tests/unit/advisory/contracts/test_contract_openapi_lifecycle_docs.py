from fastapi.testclient import TestClient

from src.api.main import app


def _assert_property_has_docs(schema: dict, property_name: str) -> None:
    prop = schema["properties"][property_name]
    assert "description" in prop and prop["description"]
    assert ("example" in prop) or ("examples" in prop)


def test_lifecycle_async_and_support_schemas_have_descriptions_and_examples():
    openapi = app.openapi()
    schemas = openapi["components"]["schemas"]

    proposal_summary_schema = schemas["ProposalSummary"]
    _assert_property_has_docs(proposal_summary_schema, "lifecycle_origin")
    _assert_property_has_docs(proposal_summary_schema, "source_workspace_id")

    supportability_schema = schemas["ProposalSupportabilityConfigResponse"]
    _assert_property_has_docs(supportability_schema, "startup_validation_scope")
    _assert_property_has_docs(supportability_schema, "migration_namespace")
    _assert_property_has_docs(supportability_schema, "expected_migration_versions")

    version_request_schema = schemas["ProposalVersionRequest"]
    _assert_property_has_docs(version_request_schema, "expected_current_version_no")

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
    execution_handoff_body_ref = execution_handoff["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    execution_handoff_response_ref = execution_handoff["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert execution_handoff_body_ref.endswith("/ProposalExecutionHandoffRequest")
    assert execution_handoff_response_ref.endswith("/ProposalExecutionHandoffResponse")
