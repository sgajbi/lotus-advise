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
    _assert_property_has_docs(report_request_schema, "include_reviewed_narrative")

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

    execution_update_schema = schemas["ProposalExecutionUpdateRequest"]
    _assert_property_has_docs(execution_update_schema, "update_id")
    _assert_property_has_docs(execution_update_schema, "execution_request_id")
    _assert_property_has_docs(execution_update_schema, "execution_provider")
    _assert_property_has_docs(execution_update_schema, "update_status")
    _assert_property_has_docs(execution_update_schema, "external_execution_id")
    _assert_property_has_docs(execution_update_schema, "occurred_at")
    _assert_property_has_docs(execution_update_schema, "details")

    execution_status_schema = schemas["ProposalExecutionStatusResponse"]
    _assert_property_has_docs(execution_status_schema, "handoff_status")
    _assert_property_has_docs(execution_status_schema, "execution_request_id")
    _assert_property_has_docs(execution_status_schema, "execution_provider")
    _assert_property_has_docs(execution_status_schema, "external_execution_id")
    _assert_property_has_docs(execution_status_schema, "execution_ownership")
    _assert_property_has_docs(execution_status_schema, "explanation")

    execution_handoff_response_schema = schemas["ProposalExecutionHandoffResponse"]
    _assert_property_has_docs(execution_handoff_response_schema, "execution_ownership")

    delivery_execution_schema = schemas["ProposalDeliveryExecutionSummary"]
    _assert_property_has_docs(delivery_execution_schema, "execution_ownership")

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
    _assert_property_has_docs(async_accepted_schema, "attempt_count")
    _assert_property_has_docs(async_accepted_schema, "max_attempts")
    _assert_property_has_docs(async_accepted_schema, "status_url")

    async_status_schema = schemas["ProposalAsyncOperationStatusResponse"]
    _assert_property_has_docs(async_status_schema, "operation_id")
    _assert_property_has_docs(async_status_schema, "operation_type")
    _assert_property_has_docs(async_status_schema, "status")
    _assert_property_has_docs(async_status_schema, "correlation_id")
    _assert_property_has_docs(async_status_schema, "created_by")
    _assert_property_has_docs(async_status_schema, "created_at")
    _assert_property_has_docs(async_status_schema, "attempt_count")
    _assert_property_has_docs(async_status_schema, "max_attempts")
    _assert_property_has_docs(async_status_schema, "lease_expires_at")
    _assert_property_has_docs(async_status_schema, "result")
    _assert_property_has_docs(async_status_schema, "error")

    replay_schema = schemas["AdvisoryReplayEvidenceResponse"]
    _assert_property_has_docs(replay_schema, "subject")
    _assert_property_has_docs(replay_schema, "resolved_context")
    _assert_property_has_docs(replay_schema, "hashes")
    _assert_property_has_docs(replay_schema, "continuity")
    _assert_property_has_docs(replay_schema, "evidence")
    _assert_property_has_docs(replay_schema, "explanation")

    narrative_review_request_schema = schemas["ProposalNarrativeReviewRequest"]
    _assert_property_has_docs(narrative_review_request_schema, "action")
    _assert_property_has_docs(narrative_review_request_schema, "reviewed_by")
    _assert_property_has_docs(narrative_review_request_schema, "reason")
    _assert_property_has_docs(narrative_review_request_schema, "client_ready_release_requested")
    _assert_property_has_docs(narrative_review_request_schema, "replacement_narrative_id")

    narrative_review_schema = schemas["ProposalNarrativeReviewRecord"]
    _assert_property_has_docs(narrative_review_schema, "review_id")
    _assert_property_has_docs(narrative_review_schema, "proposal_id")
    _assert_property_has_docs(narrative_review_schema, "proposal_version_no")
    _assert_property_has_docs(narrative_review_schema, "narrative_id")
    _assert_property_has_docs(narrative_review_schema, "source_narrative_hash")
    _assert_property_has_docs(narrative_review_schema, "replayed")

    narrative_review_response_schema = schemas["ProposalNarrativeReviewResponse"]
    _assert_property_has_docs(narrative_review_response_schema, "proposal")
    _assert_property_has_docs(narrative_review_response_schema, "narrative_review")
    _assert_property_has_docs(narrative_review_response_schema, "latest_workflow_event")

    narrative_read_response_schema = schemas["ProposalNarrativeReadResponse"]
    _assert_property_has_docs(narrative_read_response_schema, "proposal_narrative")
    _assert_property_has_docs(narrative_read_response_schema, "narrative_review")
    _assert_property_has_docs(narrative_read_response_schema, "source_narrative_hash")
    _assert_property_has_docs(narrative_read_response_schema, "replay_evidence_path")
    _assert_property_has_docs(narrative_read_response_schema, "read_posture")

    narrative_regeneration_request_schema = schemas["ProposalNarrativeRegenerationRequest"]
    _assert_property_has_docs(narrative_regeneration_request_schema, "requested_by")
    _assert_property_has_docs(narrative_regeneration_request_schema, "reason")
    _assert_property_has_docs(narrative_regeneration_request_schema, "sections")
    _assert_property_has_docs(narrative_regeneration_request_schema, "generation_mode")
    _assert_property_has_docs(narrative_regeneration_request_schema, "client_audience")

    narrative_regeneration_response_schema = schemas["ProposalNarrativeRegenerationResponse"]
    _assert_property_has_docs(narrative_regeneration_response_schema, "current_narrative_id")
    _assert_property_has_docs(narrative_regeneration_response_schema, "regenerated_narrative")
    _assert_property_has_docs(narrative_regeneration_response_schema, "source_artifact_hash")
    _assert_property_has_docs(narrative_regeneration_response_schema, "source_request_hash")
    _assert_property_has_docs(narrative_regeneration_response_schema, "regeneration_posture")


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
    report_request_response_ref = report_request["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert report_request_body_ref.endswith("/ProposalReportRequest")
    assert report_request_response_ref.endswith("/ProposalReportResponse")

    proposal_replay = openapi["paths"][
        "/advisory/proposals/{proposal_id}/versions/{version_no}/replay-evidence"
    ]["get"]
    proposal_replay_ref = proposal_replay["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert proposal_replay_ref.endswith("/AdvisoryReplayEvidenceResponse")

    async_replay = openapi["paths"][
        "/advisory/proposals/operations/{operation_id}/replay-evidence"
    ]["get"]
    async_replay_ref = async_replay["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    assert async_replay_ref.endswith("/AdvisoryReplayEvidenceResponse")

    narrative_review = openapi["paths"][
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/review"
    ]["post"]
    narrative_review_body_ref = narrative_review["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    narrative_review_response_ref = narrative_review["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    narrative_review_parameter_names = [param["name"] for param in narrative_review["parameters"]]
    assert narrative_review_body_ref.endswith("/ProposalNarrativeReviewRequest")
    assert narrative_review_response_ref.endswith("/ProposalNarrativeReviewResponse")
    assert "Idempotency-Key" in narrative_review_parameter_names

    narrative_read = openapi["paths"][
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative"
    ]["get"]
    narrative_read_ref = narrative_read["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert narrative_read_ref.endswith("/ProposalNarrativeReadResponse")

    narrative_regeneration = openapi["paths"][
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/regenerate"
    ]["post"]
    narrative_regeneration_body_ref = narrative_regeneration["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    narrative_regeneration_response_ref = narrative_regeneration["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert narrative_regeneration_body_ref.endswith("/ProposalNarrativeRegenerationRequest")
    assert narrative_regeneration_response_ref.endswith("/ProposalNarrativeRegenerationResponse")

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

    execution_update = openapi["paths"]["/advisory/proposals/{proposal_id}/execution-updates"][
        "post"
    ]
    execution_update_body_ref = execution_update["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    execution_update_response_ref = execution_update["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert execution_update_body_ref.endswith("/ProposalExecutionUpdateRequest")
    assert execution_update_response_ref.endswith("/ProposalExecutionStatusResponse")


def test_rfc0023_narrative_route_family_is_canonical_and_error_documented():
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    paths = openapi["paths"]
    narrative_paths = sorted(path for path in paths if "narrative" in path.lower())
    assert narrative_paths == [
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative",
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/regenerate",
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/review",
    ]

    narrative_read = paths["/advisory/proposals/{proposal_id}/versions/{version_no}/narrative"][
        "get"
    ]
    assert narrative_read["summary"] == "Read Persisted Proposal Narrative"
    assert "never regenerates text" in narrative_read["description"]
    assert narrative_read["tags"] == ["Advisory Proposal Lifecycle"]
    read_responses = narrative_read["responses"]
    assert "proposal version was not found" in read_responses["404"]["description"]
    assert "no persisted `proposal_narrative`" in read_responses["422"]["description"]

    narrative_regeneration = paths[
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/regenerate"
    ]["post"]
    assert narrative_regeneration["summary"] == "Regenerate Proposal Narrative Candidate"
    assert "does not mutate proposal state" in narrative_regeneration["description"]
    assert "does not publish client-ready commentary" in narrative_regeneration["description"]
    regeneration_responses = narrative_regeneration["responses"]
    assert "proposal version was not found" in regeneration_responses["404"]["description"]
    assert "no persisted `proposal_narrative`" in regeneration_responses["422"]["description"]

    narrative_review = paths[
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative/review"
    ]["post"]
    assert narrative_review["summary"] == "Review Persisted Proposal Narrative"
    assert "never regenerates narrative text" in narrative_review["description"]
    assert narrative_review["tags"] == ["Advisory Proposal Lifecycle"]

    parameter_docs = {param["name"]: param for param in narrative_review["parameters"]}
    assert parameter_docs["proposal_id"]["schema"]["type"] == "string"
    assert parameter_docs["version_no"]["schema"]["type"] == "integer"
    idempotency_header = parameter_docs["Idempotency-Key"]
    assert idempotency_header["in"] == "header"
    assert "replay-safe narrative review writes" in idempotency_header["description"]
    assert "proposal-narrative-review-idem-001" in str(idempotency_header)

    responses = narrative_review["responses"]
    assert responses["200"]["description"] == "Successful Response"
    assert "proposal version was not found" in responses["404"]["description"]
    assert "Idempotency key was reused" in responses["409"]["description"]
    assert "no reviewable `proposal_narrative`" in responses["422"]["description"]
    assert "runtime persistence is unavailable" in responses["503"]["description"]

    for stale_fragment in ("/narratives", "/narrative/lineage"):
        assert not any(stale_fragment in path.lower() for path in paths)


def test_rfc0023_narrative_additive_fields_are_openapi_documented():
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    schemas = openapi["components"]["schemas"]
    proposal_artifact = schemas["ProposalArtifact"]
    assert "proposal_narrative" in proposal_artifact["properties"]
    assert (
        "advisor-review narrative"
        in (proposal_artifact["properties"]["proposal_narrative"]["description"])
    )

    replay_response = schemas["AdvisoryReplayEvidenceResponse"]
    evidence_description = replay_response["properties"]["evidence"]["description"]
    assert "Supporting evidence references" in evidence_description

    narrative_schema = schemas["ProposalNarrative"]
    for property_name in (
        "narrative_id",
        "status",
        "audience",
        "generation_mode",
        "review_state",
        "narrative_policy",
        "ai_lineage",
        "grounding_packet",
        "sections",
        "disclosures",
        "guardrail_results",
        "limitations",
    ):
        _assert_property_has_docs(narrative_schema, property_name)


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
        "creation, versioning, state transitions, approvals, report requests, and execution handoff"
    ) in tags["Advisory Proposal Lifecycle"]
    assert "Advisory Operations & Support" in tags
    assert (
        "async status, workflow history, lineage, approval history, idempotency tracing"
    ) in tags["Advisory Operations & Support"]
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
    assert openapi["paths"]["/advisory/proposals/{proposal_id}/execution-updates"]["post"][
        "tags"
    ] == ["Advisory Proposal Lifecycle"]
    assert openapi["paths"]["/advisory/proposals/operations/{operation_id}"]["get"]["tags"] == [
        "Advisory Operations & Support"
    ]
    assert openapi["paths"]["/advisory/proposals/{proposal_id}/workflow-events"]["get"]["tags"] == [
        "Advisory Operations & Support"
    ]
    assert openapi["paths"]["/advisory/proposals/{proposal_id}/execution-status"]["get"][
        "tags"
    ] == ["Advisory Operations & Support"]
    assert openapi["paths"][
        "/advisory/proposals/{proposal_id}/versions/{version_no}/replay-evidence"
    ]["get"]["tags"] == ["Advisory Operations & Support"]
