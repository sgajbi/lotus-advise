from datetime import datetime, timezone

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalCreateRequest,
    ProposalIdempotencyRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.projections import (
    build_approvals_response,
    build_create_response_from_referents,
    build_proposal_lineage_response,
    build_workflow_timeline_response,
    to_approval_record,
    to_async_accepted_response,
    to_async_status_response,
    to_create_response,
    to_idempotency_lookup_response,
    to_proposal_summary,
    to_version_detail,
    to_workflow_event,
)
from src.core.proposals.service import ProposalWorkflowService
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _simulate_request(portfolio_id: str = "pf_projection") -> dict:
    return {
        "portfolio_snapshot": {
            "portfolio_id": portfolio_id,
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [
                {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"},
                {"instrument_id": "EQ_NEW", "price": "50", "currency": "USD"},
            ],
            "fx_rates": [],
        },
        "shelf_entries": [
            {"instrument_id": "EQ_OLD", "status": "APPROVED"},
            {"instrument_id": "EQ_NEW", "status": "APPROVED"},
        ],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [{"currency": "USD", "amount": "100"}],
        "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"}],
    }


def _proposal(
    *,
    current_version_no: int = 2,
    current_state: str = "DRAFT",
) -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_projection",
        portfolio_id="pf_projection",
        mandate_id="mandate_projection",
        jurisdiction="SG",
        created_by="advisor_projection",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc),
        current_state=current_state,
        current_version_no=current_version_no,
        title="Projection test proposal",
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
    )


def _version(version_no: int) -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id=f"ppv_projection_{version_no}",
        proposal_id="pp_projection",
        version_no=version_no,
        created_at=datetime(2026, 5, 20, 9, version_no, tzinfo=timezone.utc),
        request_hash=f"sha256:req{version_no}",
        artifact_hash=f"sha256:artifact{version_no}",
        simulation_hash=f"sha256:simulation{version_no}",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={"artifact_id": f"pa_projection_{version_no}"},
        evidence_bundle_json={"version_no": version_no},
        gate_decision_json=None,
    )


def test_to_proposal_summary_preserves_lifecycle_identity():
    proposal = ProposalRecord(
        proposal_id="pp_projection",
        portfolio_id="pf_projection",
        mandate_id="mandate_projection",
        jurisdiction="SG",
        created_by="advisor_projection",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc),
        current_state="DRAFT",
        current_version_no=1,
        title="Projection test proposal",
        lifecycle_origin="WORKSPACE_HANDOFF",
        source_workspace_id="aws_projection",
    )

    summary = to_proposal_summary(proposal)

    assert summary.model_dump(mode="json") == {
        "proposal_id": "pp_projection",
        "portfolio_id": "pf_projection",
        "mandate_id": "mandate_projection",
        "jurisdiction": "SG",
        "created_by": "advisor_projection",
        "created_at": "2026-05-20T09:00:00+00:00",
        "last_event_at": "2026-05-20T09:05:00+00:00",
        "current_state": "DRAFT",
        "current_version_no": 1,
        "title": "Projection test proposal",
        "lifecycle_origin": "WORKSPACE_HANDOFF",
        "source_workspace_id": "aws_projection",
    }


def test_to_version_detail_can_omit_evidence_bundle():
    repository = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repository)
    created = service.create_proposal(
        payload=ProposalCreateRequest(
            created_by="advisor_projection",
            simulate_request=_simulate_request(),
        ),
        idempotency_key="idem_projection",
        correlation_id="corr_projection",
    )
    version = repository.get_version(
        proposal_id=created.proposal.proposal_id,
        version_no=created.version.version_no,
    )
    assert version is not None

    without_evidence = to_version_detail(version, include_evidence=False)
    with_evidence = to_version_detail(version, include_evidence=True)

    assert without_evidence.evidence_bundle == {}
    assert with_evidence.evidence_bundle == version.evidence_bundle_json
    assert with_evidence.gate_decision.model_dump(mode="json") == version.gate_decision_json


def test_to_version_detail_isolated_from_persisted_record_mutation():
    repository = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repository)
    created = service.create_proposal(
        payload=ProposalCreateRequest(
            created_by="advisor_projection",
            simulate_request=_simulate_request("pf_projection_immutable"),
        ),
        idempotency_key="idem_projection_immutable",
        correlation_id="corr_projection_immutable",
    )
    version = repository.get_version(
        proposal_id=created.proposal.proposal_id,
        version_no=created.version.version_no,
    )
    assert version is not None
    version.proposal_result_json["lineage"]["request_hash"] = "sha256:original"
    version.artifact_json["evidence_bundle"]["hashes"]["artifact_hash"] = "sha256:original"
    version.evidence_bundle_json["context_resolution"]["source"] = "ORIGINAL"
    assert version.gate_decision_json is not None
    version.gate_decision_json["summary"]["hard_fail_count"] = 0

    detail = to_version_detail(version, include_evidence=True)

    version.proposal_result_json["lineage"]["request_hash"] = "sha256:tampered"
    version.artifact_json["evidence_bundle"]["hashes"]["artifact_hash"] = "sha256:tampered"
    version.evidence_bundle_json["context_resolution"]["source"] = "TAMPERED"
    version.gate_decision_json["summary"]["hard_fail_count"] = 99

    assert detail.proposal_result.lineage.request_hash == "sha256:original"
    assert detail.artifact.evidence_bundle.hashes.artifact_hash == "sha256:original"
    assert detail.evidence_bundle["context_resolution"]["source"] == "ORIGINAL"
    assert detail.gate_decision.summary.hard_fail_count == 0


def test_to_workflow_event_and_approval_record_preserve_audit_payloads():
    event = ProposalWorkflowEventRecord(
        event_id="pwe_projection",
        proposal_id="pp_projection",
        event_type="CLIENT_CONSENT_RECORDED",
        from_state="AWAITING_CLIENT_CONSENT",
        to_state="EXECUTION_READY",
        actor_id="client_projection",
        occurred_at=datetime(2026, 5, 20, 9, 15, tzinfo=timezone.utc),
        reason_json={"channel": "IN_PERSON"},
        related_version_no=2,
    )
    approval = ProposalApprovalRecordData(
        approval_id="pap_projection",
        proposal_id="pp_projection",
        approval_type="CLIENT_CONSENT",
        approved=True,
        actor_id="client_projection",
        occurred_at=datetime(2026, 5, 20, 9, 16, tzinfo=timezone.utc),
        details_json={"channel": "IN_PERSON"},
        related_version_no=2,
    )

    projected_event = to_workflow_event(event)
    projected_approval = to_approval_record(approval)

    assert projected_event.reason == {"channel": "IN_PERSON"}
    assert projected_event.occurred_at == "2026-05-20T09:15:00+00:00"
    assert projected_approval is not None
    assert projected_approval.details == {"channel": "IN_PERSON"}
    assert projected_approval.occurred_at == "2026-05-20T09:16:00+00:00"
    assert to_approval_record(None) is None


def test_to_create_response_projects_created_aggregate_version_and_event():
    repository = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repository)
    created = service.create_proposal(
        payload=ProposalCreateRequest(
            created_by="advisor_projection",
            simulate_request=_simulate_request("pf_create_projection"),
        ),
        idempotency_key="idem_create_projection",
        correlation_id="corr_create_projection",
    )
    proposal = repository.get_proposal(proposal_id=created.proposal.proposal_id)
    version = repository.get_version(
        proposal_id=created.proposal.proposal_id,
        version_no=created.version.version_no,
    )
    events = repository.list_events(proposal_id=created.proposal.proposal_id)
    assert proposal is not None
    assert version is not None
    assert events

    response = to_create_response(proposal=proposal, version=version, latest_event=events[-1])

    assert response.proposal.proposal_id == created.proposal.proposal_id
    assert response.version.evidence_bundle == version.evidence_bundle_json
    assert response.latest_workflow_event.event_type == "CREATED"


def test_build_create_response_from_referents_requires_complete_referents():
    repository = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repository)
    created = service.create_proposal(
        payload=ProposalCreateRequest(
            created_by="advisor_projection",
            simulate_request=_simulate_request("pf_referent_projection"),
        ),
        idempotency_key="idem_referent_projection",
        correlation_id="corr_referent_projection",
    )
    proposal = repository.get_proposal(proposal_id=created.proposal.proposal_id)
    version = repository.get_version(
        proposal_id=created.proposal.proposal_id,
        version_no=created.version.version_no,
    )
    events = repository.list_events(proposal_id=created.proposal.proposal_id)
    assert proposal is not None
    assert version is not None
    assert events

    response = build_create_response_from_referents(
        proposal=proposal,
        version=version,
        events=events,
    )

    assert response is not None
    assert response.proposal.proposal_id == proposal.proposal_id
    assert response.version.version_no == 1
    assert response.latest_workflow_event.event_type == "CREATED"
    assert (
        build_create_response_from_referents(proposal=None, version=version, events=events) is None
    )
    assert (
        build_create_response_from_referents(proposal=proposal, version=None, events=events) is None
    )
    assert (
        build_create_response_from_referents(proposal=proposal, version=version, events=[]) is None
    )


def test_to_idempotency_lookup_response_projects_audit_record():
    response = to_idempotency_lookup_response(
        ProposalIdempotencyRecord(
            idempotency_key="idem_projection",
            request_hash="sha256:req_projection",
            proposal_id="pp_projection",
            proposal_version_no=2,
            created_at=datetime(2026, 5, 20, 9, 6, tzinfo=timezone.utc),
        )
    )

    assert response.model_dump(mode="json") == {
        "idempotency_key": "idem_projection",
        "request_hash": "sha256:req_projection",
        "proposal_id": "pp_projection",
        "proposal_version_no": 2,
        "created_at": "2026-05-20T09:06:00+00:00",
    }


def test_build_proposal_lineage_response_projects_complete_version_history():
    response = build_proposal_lineage_response(
        proposal=_proposal(current_version_no=2),
        versions_by_number={1: _version(1), 2: _version(2)},
    )

    assert response.version_count == 2
    assert response.latest_version_no == 2
    assert response.latest_version_created_at == "2026-05-20T09:02:00+00:00"
    assert response.lineage_complete is True
    assert response.missing_version_numbers == []
    assert [version.version_no for version in response.versions] == [1, 2]
    assert response.versions[1].request_hash == "sha256:req2"


def test_build_proposal_lineage_response_marks_missing_versions():
    response = build_proposal_lineage_response(
        proposal=_proposal(current_version_no=3),
        versions_by_number={1: _version(1), 3: _version(3)},
    )

    assert response.version_count == 2
    assert response.latest_version_no == 3
    assert response.lineage_complete is False
    assert response.missing_version_numbers == [2]
    assert [version.version_no for version in response.versions] == [1, 3]


def test_build_workflow_timeline_response_orders_projected_events():
    events = [
        ProposalWorkflowEventRecord(
            event_id="pwe_projection_1",
            proposal_id="pp_projection",
            event_type="CREATED",
            from_state=None,
            to_state="DRAFT",
            actor_id="advisor_projection",
            occurred_at=datetime(2026, 5, 20, 9, 1, tzinfo=timezone.utc),
            reason_json={"source": "unit"},
            related_version_no=1,
        ),
        ProposalWorkflowEventRecord(
            event_id="pwe_projection_2",
            proposal_id="pp_projection",
            event_type="SUBMITTED_FOR_COMPLIANCE_REVIEW",
            from_state="DRAFT",
            to_state="COMPLIANCE_REVIEW",
            actor_id="advisor_projection",
            occurred_at=datetime(2026, 5, 20, 9, 2, tzinfo=timezone.utc),
            reason_json={"source": "unit"},
            related_version_no=1,
        ),
    ]

    response = build_workflow_timeline_response(
        proposal=_proposal(current_state="COMPLIANCE_REVIEW"),
        events=events,
    )

    assert response.current_state == "COMPLIANCE_REVIEW"
    assert response.event_count == 2
    assert response.latest_event is not None
    assert response.latest_event.event_type == "SUBMITTED_FOR_COMPLIANCE_REVIEW"
    assert [event.event_id for event in response.events] == [
        "pwe_projection_1",
        "pwe_projection_2",
    ]


def test_build_approvals_response_projects_latest_approval_posture():
    approvals = [
        None,
        ProposalApprovalRecordData(
            approval_id="pap_projection_1",
            proposal_id="pp_projection",
            approval_type="COMPLIANCE",
            approved=True,
            actor_id="compliance_projection",
            occurred_at=datetime(2026, 5, 20, 9, 3, tzinfo=timezone.utc),
            details_json={"decision": "approved"},
            related_version_no=1,
        ),
        ProposalApprovalRecordData(
            approval_id="pap_projection_2",
            proposal_id="pp_projection",
            approval_type="CLIENT_CONSENT",
            approved=True,
            actor_id="client_projection",
            occurred_at=datetime(2026, 5, 20, 9, 4, tzinfo=timezone.utc),
            details_json={"channel": "IN_PERSON"},
            related_version_no=1,
        ),
    ]

    response = build_approvals_response(proposal=_proposal(), approvals=approvals)

    assert response.approval_count == 2
    assert response.latest_approval_at == "2026-05-20T09:04:00+00:00"
    assert [approval.approval_type for approval in response.approvals] == [
        "COMPLIANCE",
        "CLIENT_CONSENT",
    ]


def test_async_operation_response_projections_preserve_operational_state():
    operation = ProposalAsyncOperationRecord(
        operation_id="pop_projection",
        operation_type="CREATE_PROPOSAL",
        status="FAILED",
        correlation_id="corr_projection",
        idempotency_key="idem_projection",
        proposal_id="pp_projection",
        created_by="advisor_projection",
        created_at=datetime(2026, 5, 20, 9, 20, tzinfo=timezone.utc),
        started_at=datetime(2026, 5, 20, 9, 21, tzinfo=timezone.utc),
        lease_expires_at=datetime(2026, 5, 20, 9, 22, tzinfo=timezone.utc),
        finished_at=datetime(2026, 5, 20, 9, 23, tzinfo=timezone.utc),
        attempt_count=2,
        max_attempts=3,
        payload_json={},
        error_json={"code": "RuntimeError", "message": "downstream unavailable"},
    )

    accepted = to_async_accepted_response(operation)
    status = to_async_status_response(operation)

    assert accepted.status_url == "/advisory/proposals/operations/pop_projection"
    assert accepted.attempt_count == 2
    assert status.operation_id == "pop_projection"
    assert status.started_at == "2026-05-20T09:21:00+00:00"
    assert status.lease_expires_at == "2026-05-20T09:22:00+00:00"
    assert status.finished_at == "2026-05-20T09:23:00+00:00"
    assert status.error is not None
    assert status.error.model_dump(mode="json") == {
        "code": "RuntimeError",
        "message": "downstream unavailable",
    }
