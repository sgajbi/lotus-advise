from datetime import datetime, timezone

import pytest

from src.core.proposals.idempotency import (
    ProposalReplayHashConflictError,
    find_replayed_approval,
    find_replayed_event,
)
from src.core.proposals.models import ProposalApprovalRecordData, ProposalWorkflowEventRecord


def _event(
    *,
    event_id: str,
    idempotency_key: str,
    request_hash: str,
) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id="pp_idem",
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor_idem",
        occurred_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        reason_json={
            "idempotency_key": idempotency_key,
            "idempotency_request_hash": request_hash,
        },
        related_version_no=1,
    )


def _approval(
    *,
    approval_id: str,
    idempotency_key: str,
    request_hash: str,
) -> ProposalApprovalRecordData:
    return ProposalApprovalRecordData(
        approval_id=approval_id,
        proposal_id="pp_idem",
        approval_type="RISK",
        approved=True,
        actor_id="risk_idem",
        occurred_at=datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc),
        details_json={
            "idempotency_key": idempotency_key,
            "idempotency_request_hash": request_hash,
        },
        related_version_no=1,
    )


def test_find_replayed_event_returns_latest_matching_event():
    first = _event(event_id="pwe_first", idempotency_key="idem_target", request_hash="sha256:a")
    latest = _event(event_id="pwe_latest", idempotency_key="idem_target", request_hash="sha256:a")
    unrelated = _event(
        event_id="pwe_unrelated",
        idempotency_key="idem_other",
        request_hash="sha256:other",
    )

    assert (
        find_replayed_event(
            events=[first, unrelated, latest],
            idempotency_key="idem_target",
            request_hash="sha256:a",
        )
        == latest
    )


def test_find_replayed_event_raises_on_hash_conflict():
    event = _event(event_id="pwe_conflict", idempotency_key="idem_target", request_hash="sha256:a")

    with pytest.raises(ProposalReplayHashConflictError) as exc:
        find_replayed_event(
            events=[event],
            idempotency_key="idem_target",
            request_hash="sha256:b",
        )

    assert str(exc.value) == "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"


def test_find_replayed_approval_returns_latest_matching_approval():
    first = _approval(
        approval_id="pap_first",
        idempotency_key="idem_target",
        request_hash="sha256:a",
    )
    latest = _approval(
        approval_id="pap_latest",
        idempotency_key="idem_target",
        request_hash="sha256:a",
    )

    assert (
        find_replayed_approval(
            approvals=[first, latest],
            idempotency_key="idem_target",
            request_hash="sha256:a",
        )
        == latest
    )


def test_find_replayed_approval_handles_empty_key_and_hash_conflict():
    approval = _approval(
        approval_id="pap_conflict",
        idempotency_key="idem_target",
        request_hash="sha256:a",
    )

    assert (
        find_replayed_approval(
            approvals=[approval],
            idempotency_key=None,
            request_hash="sha256:a",
        )
        is None
    )
    with pytest.raises(ProposalReplayHashConflictError):
        find_replayed_approval(
            approvals=[approval],
            idempotency_key="idem_target",
            request_hash="sha256:b",
        )
