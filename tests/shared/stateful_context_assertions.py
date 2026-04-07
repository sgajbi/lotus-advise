from src.integrations.lotus_core.stateful_context import StatefulContextFetchStats


def assert_core_context_fetch_counts(
    stats: StatefulContextFetchStats,
    *,
    portfolio: int,
    positions: int,
    cash: int,
) -> None:
    assert stats.portfolio_fetches == portfolio
    assert stats.positions_fetches == positions
    assert stats.cash_fetches == cash
