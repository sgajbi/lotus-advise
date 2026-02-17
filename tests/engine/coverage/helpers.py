from decimal import Decimal

from src.core.models import CashBalance, DiagnosticsData, PortfolioSnapshot


def usd_cash_portfolio(portfolio_id: str, amount: str = "1000") -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolio_id=portfolio_id,
        base_currency="USD",
        positions=[],
        cash_balances=[CashBalance(currency="USD", amount=Decimal(amount))],
    )


def empty_diagnostics() -> DiagnosticsData:
    return DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[])
