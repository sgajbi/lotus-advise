from datetime import datetime, timezone

from src.core.proposals.records import (
    build_proposal_create_command_state,
    build_proposal_idempotency_record,
    build_proposal_record,
)


def test_build_proposal_record_sets_initial_lifecycle_state():
    created_at = datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc)

    proposal = build_proposal_record(
        proposal_id="pp_records",
        portfolio_id="pf_records",
        mandate_id="mandate_records",
        jurisdiction="SG",
        created_by="advisor_records",
        created_at=created_at,
        version_no=1,
        title="Records test proposal",
        advisor_notes="Client requested staged rotation.",
        lifecycle_origin="WORKSPACE_HANDOFF",
        source_workspace_id="aws_records",
    )

    assert proposal.proposal_id == "pp_records"
    assert proposal.portfolio_id == "pf_records"
    assert proposal.created_at == created_at
    assert proposal.last_event_at == created_at
    assert proposal.current_state == "DRAFT"
    assert proposal.current_version_no == 1
    assert proposal.title == "Records test proposal"
    assert proposal.advisor_notes == "Client requested staged rotation."
    assert proposal.lifecycle_origin == "WORKSPACE_HANDOFF"
    assert proposal.source_workspace_id == "aws_records"


def test_build_proposal_idempotency_record_preserves_replay_identity():
    created_at = datetime(2026, 5, 21, 10, 1, tzinfo=timezone.utc)

    record = build_proposal_idempotency_record(
        idempotency_key="idem_records",
        request_hash="sha256:records",
        proposal_id="pp_records",
        proposal_version_no=2,
        created_at=created_at,
    )

    assert record.idempotency_key == "idem_records"
    assert record.request_hash == "sha256:records"
    assert record.proposal_id == "pp_records"
    assert record.proposal_version_no == 2
    assert record.created_at == created_at


def test_build_proposal_create_command_state_returns_initial_referents():
    created_at = datetime(2026, 5, 21, 10, 2, tzinfo=timezone.utc)

    command_state = build_proposal_create_command_state(
        proposal_id="pp_records",
        portfolio_id="pf_records",
        mandate_id="mandate_records",
        jurisdiction="SG",
        created_by="advisor_records",
        created_at=created_at,
        version_no=1,
        title="Records test proposal",
        advisor_notes="Client requested staged rotation.",
        lifecycle_origin="WORKSPACE_HANDOFF",
        source_workspace_id="aws_records",
        event_id="pwe_records_created",
        correlation_id="corr_records",
        idempotency_key="idem_records",
        request_hash="sha256:records",
    )

    assert command_state.proposal.proposal_id == "pp_records"
    assert command_state.proposal.current_state == "DRAFT"
    assert command_state.proposal.current_version_no == 1
    assert command_state.created_event.event_id == "pwe_records_created"
    assert command_state.created_event.event_type == "CREATED"
    assert command_state.created_event.related_version_no == 1
    assert command_state.created_event.reason_json == {"correlation_id": "corr_records"}
    assert command_state.idempotency_record.idempotency_key == "idem_records"
    assert command_state.idempotency_record.request_hash == "sha256:records"
    assert command_state.idempotency_record.proposal_version_no == 1
