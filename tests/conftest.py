"""
FILE: tests/conftest.py
Shared fixtures for advisory tests.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from src.api.main import app, get_db_session
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import CashBalance, EngineOptions, PortfolioSnapshot
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


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
        elif "/tests/e2e/" in path:
            item.add_marker(pytest.mark.e2e)
        else:
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def base_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )


@pytest.fixture
def base_options() -> EngineOptions:
    return EngineOptions(
        allow_restricted=False,
        suppress_dust_trades=True,
        block_on_missing_prices=True,
        single_position_max_weight=None,
    )


@pytest.fixture(autouse=True)
def postgres_runtime_test_harness(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://test:test@localhost:5432/proposals")
    monkeypatch.setattr(
        "src.api.proposals.runtime.PostgresProposalRepository",
        lambda **_kwargs: InMemoryProposalRepository(),
    )


@pytest.fixture(autouse=True)
def advisory_runtime_test_harness(monkeypatch: pytest.MonkeyPatch):
    async def _override_get_db_session():
        yield None

    def _simulate_with_lotus_core(**kwargs):
        request = kwargs["request"]
        return run_proposal_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            shelf=request.shelf_entries,
            options=request.options,
            proposed_cash_flows=request.proposed_cash_flows,
            proposed_trades=request.proposed_trades,
            reference_model=request.reference_model,
            request_hash=kwargs["request_hash"],
            idempotency_key=kwargs["idempotency_key"],
            correlation_id=kwargs["correlation_id"],
            simulation_contract_version="advisory-simulation.v1",
            policy_context=kwargs.get("policy_context"),
        )

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )
    monkeypatch.setitem(app.dependency_overrides, get_db_session, _override_get_db_session)
    reset_proposal_workflow_service_for_tests()
    yield
    app.dependency_overrides.pop(get_db_session, None)
    reset_proposal_workflow_service_for_tests()
