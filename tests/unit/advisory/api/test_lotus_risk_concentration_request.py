from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.integrations.lotus_risk.concentration_request import build_concentration_request


def _request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "portfolio_id": "DEMO_ADV_USD_001",
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                "fx_rates": [],
            },
            "shelf_entries": [
                {
                    "instrument_id": "EQ_1",
                    "status": "APPROVED",
                    "issuer_id": "ISSUER_1",
                    "attributes": {
                        "issuer_name": "Issuer 1",
                        "ultimate_parent_issuer_id": "PARENT_1",
                        "ultimate_parent_issuer_name": "Parent 1",
                    },
                }
            ],
            "reference_model": {
                "model_id": "MODEL_1",
                "as_of": "2026-03-25",
                "base_currency": "USD",
                "asset_class_targets": [],
            },
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_1", "quantity": "2"}],
        }
    )


def _request_without_changed_security_issuer() -> ProposalSimulateRequest:
    payload = _request().model_dump(mode="json")
    payload["market_data_snapshot"]["prices"].append(
        {"instrument_id": "EQ_NO_ISSUER", "price": "50", "currency": "USD"}
    )
    payload["shelf_entries"].append(
        {
            "instrument_id": "EQ_NO_ISSUER",
            "status": "APPROVED",
            "issuer_id": None,
            "attributes": {
                "issuer_name": "Issuer evidence is intentionally absent",
            },
        }
    )
    payload["proposed_trades"] = [{"side": "BUY", "instrument_id": "EQ_NO_ISSUER", "quantity": "1"}]
    return ProposalSimulateRequest.model_validate(payload)


def _proposal_result(request: ProposalSimulateRequest) -> ProposalResult:
    return run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash="sha256:risk-request",
        idempotency_key=None,
        correlation_id="corr-risk-request",
        simulation_contract_version="advisory-simulation.v1",
    )


def test_stateless_concentration_request_projects_positions_and_cash() -> None:
    request = _request()
    result = _proposal_result(request)

    payload = build_concentration_request(
        request=request,
        proposal_result=result,
        resolved_as_of=None,
        input_mode=None,
    )

    stateless_input = payload["stateless_input"]
    assert payload["input_mode"] == "stateless"
    assert payload["issuer_grouping_level"] == "ultimate_parent"
    assert payload["enrichment_policy"] == "use_caller_only"
    assert stateless_input["current_positions"] == [
        {
            "security_id": "CASH_USD",
            "security_name": "USD Cash",
            "quantity": "1000",
            "market_value_base": "1000",
            "weight": "1",
            "issuer_id": "CASH_USD",
            "ultimate_parent_issuer_id": "CASH_USD",
        }
    ]
    assert stateless_input["projected_positions"][0] == {
        "security_id": "EQ_1",
        "security_name": "EQ_1",
        "proposed_quantity": "2",
        "projected_market_value_base": "200.0",
        "projected_weight": "0.2",
        "issuer_id": "ISSUER_1",
        "ultimate_parent_issuer_id": "PARENT_1",
    }


def test_stateful_concentration_request_projects_simulation_changes_and_issuer_mappings() -> None:
    request = _request()
    result = _proposal_result(request)

    payload = build_concentration_request(
        request=request,
        proposal_result=result,
        resolved_as_of="2026-03-25",
        input_mode="stateful",
    )

    simulation_input = payload["simulation_input"]
    assert payload["input_mode"] == "simulation"
    assert payload["enrichment_policy"] == "merge_caller_then_core"
    assert simulation_input["portfolio_id"] == "DEMO_ADV_USD_001"
    assert simulation_input["as_of_date"] == "2026-03-25"
    assert simulation_input["simulation_changes"] == [
        {
            "security_id": "EQ_1",
            "transaction_type": "BUY",
            "quantity": "2",
            "metadata": {
                "proposal_intent_id": "oi_1",
                "proposal_intent_type": "SECURITY_TRADE",
            },
            "amount": "200",
            "currency": "USD",
        }
    ]
    assert simulation_input["issuer_mappings"] == [
        {
            "security_id": "EQ_1",
            "issuer_id": "ISSUER_1",
            "issuer_name": "Issuer 1",
            "ultimate_parent_issuer_id": "PARENT_1",
            "ultimate_parent_issuer_name": "Parent 1",
        }
    ]


def test_stateful_concentration_request_omits_issuer_mappings_without_issuer_evidence() -> None:
    request = _request_without_changed_security_issuer()
    result = _proposal_result(request)

    payload = build_concentration_request(
        request=request,
        proposal_result=result,
        resolved_as_of="2026-03-25",
        input_mode="stateful",
    )

    simulation_input = payload["simulation_input"]
    assert simulation_input["simulation_changes"] == [
        {
            "security_id": "EQ_NO_ISSUER",
            "transaction_type": "BUY",
            "quantity": "1",
            "metadata": {
                "proposal_intent_id": "oi_1",
                "proposal_intent_type": "SECURITY_TRADE",
            },
            "amount": "50",
            "currency": "USD",
        }
    ]
    assert "issuer_mappings" not in simulation_input
