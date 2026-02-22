"""
FILE: tests/conftest.py
Shared fixtures for engine tests.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from src.core.models import (
    CashBalance,
    EngineOptions,
    PortfolioSnapshot,
)


def _has_marker(item: pytest.Item, name: str) -> bool:
    return item.get_closest_marker(name) is not None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if (
            _has_marker(item, "unit")
            or _has_marker(item, "integration")
            or _has_marker(item, "e2e")
        ):
            continue

        path = Path(str(item.fspath)).as_posix().lower()
        if "/tests/integration/" in path or "_integration.py" in path:
            item.add_marker(pytest.mark.integration)
            continue
        if "/tests/e2e/" in path or "/tests/shared/demo/" in path:
            item.add_marker(pytest.mark.e2e)
            continue
        if "/tests/unit/" in path:
            item.add_marker(pytest.mark.unit)
            continue
        item.add_marker(pytest.mark.unit)


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
        single_position_max_weight=None,
    )
