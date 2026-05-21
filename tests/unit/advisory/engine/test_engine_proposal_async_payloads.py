from datetime import datetime, timezone

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.async_payloads import (
    AsyncPayloadResolutionFailure,
    extract_async_submission_hash,
    hash_async_create_submission,
    hash_async_version_submission,
    resolve_async_create_payload,
    resolve_async_version_payload,
)
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateRequest,
    ProposalVersionRequest,
)


def _simulate_request(portfolio_id: str = "pf_async_payloads") -> dict:
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


def test_async_create_submission_hash_normalizes_legacy_and_stateless_contracts():
    legacy_payload = ProposalCreateRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
        metadata={"title": "Async payload hash test"},
    )
    stateless_payload = ProposalCreateRequest(
        created_by="advisor_service",
        input_mode="stateless",
        stateless_input={"simulate_request": _simulate_request()},
        metadata={"title": "Async payload hash test"},
    )

    assert hash_async_create_submission(legacy_payload) == hash_async_create_submission(
        stateless_payload
    )


def test_async_version_submission_hash_is_scoped_to_proposal_identity():
    payload = ProposalVersionRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
    )

    first_hash = hash_async_version_submission(proposal_id="pp_one", payload=payload)
    second_hash = hash_async_version_submission(proposal_id="pp_two", payload=payload)

    assert first_hash != second_hash


def test_extract_async_submission_hash_prefers_persisted_submission_hash():
    operation = ProposalAsyncOperationRecord(
        operation_id="op_async_payload_hash",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_async_payload_hash",
        idempotency_key="idem_async_payload_hash",
        created_by="advisor_service",
        created_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        payload_json={
            "submission_hash": "sha256:persisted",
            "payload": {"value": "fallback"},
        },
    )

    assert extract_async_submission_hash(operation) == "sha256:persisted"


def test_extract_async_submission_hash_falls_back_to_payload_hash():
    payload = {"created_by": "advisor_service", "value": "fallback"}
    operation = ProposalAsyncOperationRecord(
        operation_id="op_async_payload_fallback",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_async_payload_fallback",
        idempotency_key="idem_async_payload_fallback",
        created_by="advisor_service",
        created_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        payload_json={"payload": payload},
    )

    assert extract_async_submission_hash(operation) == str(hash_canonical_payload(payload))


def test_resolve_async_create_payload_uses_persisted_payload_and_idempotency_key():
    payload = ProposalCreateRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
    )
    operation = ProposalAsyncOperationRecord(
        operation_id="op_async_create_resolve",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_async_create_resolve",
        idempotency_key=None,
        created_by="advisor_service",
        created_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        payload_json={
            "payload": payload.model_dump(mode="json", exclude_none=True),
            "idempotency_key": "idem_from_payload",
        },
    )

    resolved = resolve_async_create_payload(
        operation=operation,
        fallback_payload=None,
        fallback_idempotency_key=None,
    )

    assert not isinstance(resolved, AsyncPayloadResolutionFailure)
    assert resolved.payload.created_by == "advisor_service"
    assert resolved.idempotency_key == "idem_from_payload"


def test_resolve_async_create_payload_reports_invalid_payload_and_missing_idempotency():
    operation = ProposalAsyncOperationRecord(
        operation_id="op_async_create_invalid",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_async_create_invalid",
        idempotency_key=None,
        created_by="advisor_service",
        created_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        payload_json={"payload": {"created_by": "advisor_service"}},
    )

    invalid_payload = resolve_async_create_payload(
        operation=operation,
        fallback_payload=None,
        fallback_idempotency_key=None,
    )
    assert invalid_payload == AsyncPayloadResolutionFailure(
        message="PROPOSAL_ASYNC_PAYLOAD_INVALID"
    )

    fallback_payload = ProposalCreateRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
    )
    operation.payload_json = {}
    missing_idempotency = resolve_async_create_payload(
        operation=operation,
        fallback_payload=fallback_payload,
        fallback_idempotency_key=None,
    )
    assert missing_idempotency == AsyncPayloadResolutionFailure(
        message="PROPOSAL_ASYNC_IDEMPOTENCY_KEY_REQUIRED"
    )


def test_resolve_async_version_payload_uses_fallback_proposal_scope():
    payload = ProposalVersionRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
    )
    operation = ProposalAsyncOperationRecord(
        operation_id="op_async_version_resolve",
        operation_type="CREATE_PROPOSAL_VERSION",
        status="PENDING",
        correlation_id="corr_async_version_resolve",
        proposal_id=None,
        created_by="advisor_service",
        created_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        payload_json={"payload": payload.model_dump(mode="json", exclude_none=True)},
    )

    resolved = resolve_async_version_payload(
        operation=operation,
        fallback_proposal_id="pp_fallback",
        fallback_payload=None,
    )

    assert not isinstance(resolved, AsyncPayloadResolutionFailure)
    assert resolved.proposal_id == "pp_fallback"
    assert resolved.payload.created_by == "advisor_service"


def test_resolve_async_version_payload_reports_missing_proposal_scope():
    operation = ProposalAsyncOperationRecord(
        operation_id="op_async_version_missing_scope",
        operation_type="CREATE_PROPOSAL_VERSION",
        status="PENDING",
        correlation_id="corr_async_version_missing_scope",
        proposal_id=None,
        created_by="advisor_service",
        created_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
        payload_json={},
    )

    resolved = resolve_async_version_payload(
        operation=operation,
        fallback_proposal_id=None,
        fallback_payload=ProposalVersionRequest(
            created_by="advisor_service",
            simulate_request=_simulate_request(),
        ),
    )

    assert resolved == AsyncPayloadResolutionFailure(message="PROPOSAL_ASYNC_PROPOSAL_ID_REQUIRED")
