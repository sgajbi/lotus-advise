"""
FILE: tests/conftest.py
Shared fixtures for engine tests.
"""

from decimal import Decimal

import pytest

from src.core.models import CashBalance, EngineOptions, PortfolioSnapshot


@pytest.fixture
def base_portfolio():
    return PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )


@pytest.fixture
def base_options():
    return EngineOptions(
        allow_restricted=False,
        suppress_dust_trades=True,
        block_on_missing_prices=True,
    )
