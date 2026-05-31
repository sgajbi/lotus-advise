import pytest

from src.core.proposals.context import (
    ProposalContextResolutionError,
    build_create_request_hash,
    build_version_request_hash,
    resolve_create_request,
    resolve_simulation_request,
    resolve_version_request,
)
from src.core.proposals.models import (
    ProposalCreateRequest,
    ProposalSimulationRequest,
    ProposalVersionRequest,
)


def _simulate_request(portfolio_id: str = "pf_context_hash") -> dict:
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


def test_build_create_request_hash_normalizes_legacy_and_stateless_contracts():
    legacy_payload = ProposalCreateRequest(
        created_by="advisor_context",
        simulate_request=_simulate_request(),
        metadata={"title": "Context hash"},
    )
    stateless_payload = ProposalCreateRequest(
        created_by="advisor_context",
        input_mode="stateless",
        stateless_input={"simulate_request": _simulate_request()},
        metadata={"title": "Context hash"},
    )

    legacy_hash = build_create_request_hash(
        payload=legacy_payload,
        resolved=resolve_create_request(legacy_payload),
    )
    stateless_hash = build_create_request_hash(
        payload=stateless_payload,
        resolved=resolve_create_request(stateless_payload),
    )

    assert legacy_hash.startswith("sha256:")
    assert legacy_hash == stateless_hash


def test_build_version_request_hash_is_canonical_and_concurrency_sensitive():
    first_payload = ProposalVersionRequest(
        created_by="advisor_context",
        simulate_request=_simulate_request(),
        expected_current_version_no=1,
    )
    same_payload = ProposalVersionRequest(
        created_by="advisor_context",
        input_mode="stateless",
        stateless_input={"simulate_request": _simulate_request()},
        expected_current_version_no=1,
    )
    changed_payload = ProposalVersionRequest(
        created_by="advisor_context",
        simulate_request=_simulate_request(),
        expected_current_version_no=2,
    )

    first_hash = build_version_request_hash(
        payload=first_payload,
        resolved=resolve_version_request(first_payload),
    )
    same_hash = build_version_request_hash(
        payload=same_payload,
        resolved=resolve_version_request(same_payload),
    )
    changed_hash = build_version_request_hash(
        payload=changed_payload,
        resolved=resolve_version_request(changed_payload),
    )

    assert first_hash.startswith("sha256:")
    assert first_hash == same_hash
    assert first_hash != changed_hash


@pytest.mark.parametrize(
    ("payload", "resolver", "expected_message"),
    [
        (
            ProposalCreateRequest.model_construct(
                created_by="advisor_context",
                input_mode="stateful",
                stateful_input=None,
                stateless_input=None,
                simulate_request=None,
                metadata={},
            ),
            resolve_create_request,
            "PROPOSAL_STATEFUL_INPUT_REQUIRED",
        ),
        (
            ProposalCreateRequest.model_construct(
                created_by="advisor_context",
                input_mode="stateless",
                stateful_input=None,
                stateless_input=None,
                simulate_request=None,
                metadata={},
            ),
            resolve_create_request,
            "PROPOSAL_STATELESS_INPUT_REQUIRED",
        ),
        (
            ProposalSimulationRequest.model_construct(
                input_mode="stateful",
                stateful_input=None,
                stateless_input=None,
                simulate_request=None,
                alternatives_request=None,
            ),
            resolve_simulation_request,
            "PROPOSAL_STATEFUL_INPUT_REQUIRED",
        ),
        (
            ProposalSimulationRequest.model_construct(
                input_mode="stateless",
                stateful_input=None,
                stateless_input=None,
                simulate_request=None,
                alternatives_request=None,
            ),
            resolve_simulation_request,
            "PROPOSAL_STATELESS_INPUT_REQUIRED",
        ),
        (
            ProposalVersionRequest.model_construct(
                created_by="advisor_context",
                input_mode="legacy",
                stateful_input=None,
                stateless_input=None,
                simulate_request=None,
                expected_current_version_no=None,
            ),
            resolve_version_request,
            "PROPOSAL_SIMULATE_REQUEST_REQUIRED",
        ),
    ],
)
def test_context_resolution_uses_domain_errors_for_constructed_invalid_payloads(
    payload,
    resolver,
    expected_message: str,
):
    with pytest.raises(ProposalContextResolutionError, match=expected_message):
        resolver(payload)
