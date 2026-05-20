from datetime import datetime, timezone

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.async_payloads import (
    extract_async_submission_hash,
    hash_async_create_submission,
    hash_async_version_submission,
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
