from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    PortfolioSnapshot,
    ProposalSimulateRequest,
    ProposedCashFlow,
    ProposedTrade,
    ShelfEntry,
)


def test_advisory_engine_options_defaults():
    options = EngineOptions()
    assert options.enable_proposal_simulation is False
    assert options.proposal_apply_cash_flows_first is True
    assert options.proposal_block_negative_cash is True


def test_advisory_proposed_trade_requires_quantity_or_notional():
    with pytest.raises(ValidationError):
        ProposedTrade(side="BUY", instrument_id="EQ_1")


def test_advisory_proposed_trade_rejects_quantity_and_notional_together():
    with pytest.raises(ValidationError):
        ProposedTrade(
            side="BUY",
            instrument_id="EQ_1",
            quantity=Decimal("1"),
            notional={"amount": "100", "currency": "USD"},
        )


def test_advisory_proposed_trade_rejects_float_quantity():
    with pytest.raises(ValidationError):
        ProposedTrade(side="BUY", instrument_id="EQ_1", quantity=1.25)


def test_advisory_proposed_cash_flow_rejects_float_amount():
    with pytest.raises(ValidationError):
        ProposedCashFlow(currency="USD", amount=10.5)


def test_advisory_proposal_request_shape():
    request = ProposalSimulateRequest(
        portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf", base_currency="USD"),
        market_data_snapshot=MarketDataSnapshot(prices=[], fx_rates=[]),
        shelf_entries=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
        proposed_cash_flows=[ProposedCashFlow(currency="USD", amount=Decimal("100"))],
        proposed_trades=[ProposedTrade(side="BUY", instrument_id="EQ_1", quantity=Decimal("1"))],
    )
    assert request.proposed_cash_flows[0].intent_type == "CASH_FLOW"
    assert request.proposed_trades[0].intent_type == "SECURITY_TRADE"
