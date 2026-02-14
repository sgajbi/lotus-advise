"""
FILE: update_goldens.py
"""

import json
import os
from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)

OUTPUT_DIR = "tests/golden_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_golden(name: str, inputs: dict, result):
    """Saves the inputs and expected output to a JSON file."""
    output_json = json.loads(result.model_dump_json())

    # Strip dynamic IDs to ensure deterministic comparison in tests
    output_json["rebalance_run_id"] = "rr_golden"
    output_json["universe"]["universe_id"] = "uni_golden"
    output_json["target"]["target_id"] = "tgt_golden"
    output_json["lineage"]["request_hash"] = "hash_golden"

    data = {
        "scenario_name": name,
        "inputs": json.loads(json.dumps(inputs, default=str)),
        "expected_outputs": output_json,
    }

    filename = f"{name.lower().replace(' ', '_')}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {filepath}")


def generate_scenarios():
    print("Generating Golden Scenarios (RFC-0004 Institution-Grade)...")

    # --- Shared Data Helpers ---
    def money(amt, ccy):
        return Money(amount=Decimal(str(amt)), currency=ccy)

    def price(iid, p, ccy):
        return Price(instrument_id=iid, price=Decimal(str(p)), currency=ccy)

    def fx(pair, r):
        return FxRate(pair=pair, rate=Decimal(str(r)))

    # 101: Simple Drift Rebalance
    pf_101 = PortfolioSnapshot(
        portfolio_id="pf_101",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_SGD_1", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    md_101 = MarketDataSnapshot(
        prices=[price("EQ_SGD_1", 100.0, "SGD"), price("EQ_SGD_2", 50.0, "SGD")]
    )
    model_101 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_SGD_1", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_SGD_2", weight=Decimal("0.5")),
        ]
    )
    shelf_101 = [
        ShelfEntry(instrument_id="EQ_SGD_1", status="APPROVED", asset_class="EQUITY"),
        ShelfEntry(instrument_id="EQ_SGD_2", status="APPROVED", asset_class="EQUITY"),
    ]
    res_101 = run_simulation(pf_101, md_101, model_101, shelf_101, EngineOptions())
    save_golden(
        "scenario_101_drift_rebalance",
        {
            "portfolio_snapshot": pf_101.model_dump(),
            "market_data_snapshot": md_101.model_dump(),
            "model_portfolio": model_101.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_101],
            "options": EngineOptions().model_dump(),
        },
        res_101,
    )

    # 102: Cash Inflow
    pf_102 = PortfolioSnapshot(
        portfolio_id="pf_102",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_SGD_1", quantity=Decimal("50"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("15000.0"))],
    )
    md_102 = MarketDataSnapshot(prices=[price("EQ_SGD_1", 100.0, "SGD")])
    model_102 = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_SGD_1", weight=Decimal("1.0"))]
    )
    shelf_102 = [ShelfEntry(instrument_id="EQ_SGD_1", status="APPROVED", asset_class="EQUITY")]
    res_102 = run_simulation(pf_102, md_102, model_102, shelf_102, EngineOptions())
    save_golden(
        "scenario_102_cash_inflow",
        {
            "portfolio_snapshot": pf_102.model_dump(),
            "market_data_snapshot": md_102.model_dump(),
            "model_portfolio": model_102.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_102],
            "options": EngineOptions().model_dump(),
        },
        res_102,
    )

    # 103: Sell to Fund
    pf_103 = PortfolioSnapshot(
        portfolio_id="pf_103",
        base_currency="SGD",
        positions=[Position(instrument_id="BOND_SGD", quantity=Decimal("1000"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("100.0"))],
    )
    md_103 = MarketDataSnapshot(
        prices=[price("BOND_SGD", 100.0, "SGD"), price("EQ_SGD", 50.0, "SGD")]
    )
    model_103 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="BOND_SGD", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_SGD", weight=Decimal("0.5")),
        ]
    )
    shelf_103 = [
        ShelfEntry(instrument_id="BOND_SGD", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_SGD", status="APPROVED"),
    ]
    res_103 = run_simulation(pf_103, md_103, model_103, shelf_103, EngineOptions())
    save_golden(
        "scenario_103_sell_to_fund",
        {
            "portfolio_snapshot": pf_103.model_dump(),
            "market_data_snapshot": md_103.model_dump(),
            "model_portfolio": model_103.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_103],
            "options": EngineOptions().model_dump(),
        },
        res_103,
    )

    # 104: Multi-Currency FX
    pf_104 = PortfolioSnapshot(
        portfolio_id="pf_104",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("20000.0"))],
    )
    md_104 = MarketDataSnapshot(
        prices=[price("US_ETF", 100.0, "USD")], fx_rates=[fx("USD/SGD", 1.35)]
    )
    model_104 = ModelPortfolio(targets=[ModelTarget(instrument_id="US_ETF", weight=Decimal("1.0"))])
    shelf_104 = [ShelfEntry(instrument_id="US_ETF", status="APPROVED")]
    opts_104 = EngineOptions(fx_buffer_pct=Decimal("0.01"))
    res_104 = run_simulation(pf_104, md_104, model_104, shelf_104, opts_104)
    save_golden(
        "scenario_104_multicurrency_fx",
        {
            "portfolio_snapshot": pf_104.model_dump(),
            "market_data_snapshot": md_104.model_dump(),
            "model_portfolio": model_104.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_104],
            "options": opts_104.model_dump(),
        },
        res_104,
    )

    # 105: SELL_ONLY
    pf_105 = PortfolioSnapshot(
        portfolio_id="pf_105",
        base_currency="SGD",
        positions=[Position(instrument_id="BAD_ASSET", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("9000.0"))],
    )
    md_105 = MarketDataSnapshot(
        prices=[price("BAD_ASSET", 10.0, "SGD"), price("GOOD_ASSET", 10.0, "SGD")]
    )
    model_105 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="BAD_ASSET", weight=Decimal("0.5")),
            ModelTarget(instrument_id="GOOD_ASSET", weight=Decimal("0.5")),
        ]
    )
    shelf_105 = [
        ShelfEntry(instrument_id="BAD_ASSET", status="SELL_ONLY"),
        ShelfEntry(instrument_id="GOOD_ASSET", status="APPROVED"),
    ]
    res_105 = run_simulation(pf_105, md_105, model_105, shelf_105, EngineOptions())
    save_golden(
        "scenario_105_sell_only",
        {
            "portfolio_snapshot": pf_105.model_dump(),
            "market_data_snapshot": md_105.model_dump(),
            "model_portfolio": model_105.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_105],
            "options": EngineOptions().model_dump(),
        },
        res_105,
    )

    # 107: Missing Price
    pf_107 = PortfolioSnapshot(
        portfolio_id="pf_107",
        base_currency="SGD",
        positions=[Position(instrument_id="UNKNOWN_ASSET", quantity=Decimal("10"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("100.0"))],
    )
    md_107 = MarketDataSnapshot(prices=[])
    model_107 = ModelPortfolio(
        targets=[ModelTarget(instrument_id="UNKNOWN_ASSET", weight=Decimal("1.0"))]
    )
    shelf_107 = [ShelfEntry(instrument_id="UNKNOWN_ASSET", status="APPROVED")]
    res_107 = run_simulation(pf_107, md_107, model_107, shelf_107, EngineOptions())
    save_golden(
        "scenario_107_missing_price",
        {
            "portfolio_snapshot": pf_107.model_dump(),
            "market_data_snapshot": md_107.model_dump(),
            "model_portfolio": model_107.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_107],
            "options": EngineOptions().model_dump(),
        },
        res_107,
    )

    # 110: Dust Suppression
    pf_110 = PortfolioSnapshot(
        portfolio_id="pf_110",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )
    md_110 = MarketDataSnapshot(
        prices=[price("BIG_ASSET", 100.0, "SGD"), price("DUST_ASSET", 10.0, "SGD")]
    )
    model_110 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="BIG_ASSET", weight=Decimal("0.99")),
            ModelTarget(instrument_id="DUST_ASSET", weight=Decimal("0.01")),
        ]
    )
    shelf_110 = [
        ShelfEntry(instrument_id="BIG_ASSET", status="APPROVED"),
        ShelfEntry(instrument_id="DUST_ASSET", status="APPROVED", min_notional=money(500, "SGD")),
    ]
    opts_110 = EngineOptions(suppress_dust_trades=True)
    res_110 = run_simulation(pf_110, md_110, model_110, shelf_110, opts_110)
    save_golden(
        "scenario_110_dust_suppression",
        {
            "portfolio_snapshot": pf_110.model_dump(),
            "market_data_snapshot": md_110.model_dump(),
            "model_portfolio": model_110.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_110],
            "options": opts_110.model_dump(),
        },
        res_110,
    )

    # 111: Fee Buffer
    pf_111 = PortfolioSnapshot(
        portfolio_id="pf_111",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_SGD_1", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    md_111 = MarketDataSnapshot(
        prices=[price("EQ_SGD_1", 100.0, "SGD"), price("EQ_SGD_2", 50.0, "SGD")]
    )
    model_111 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_SGD_1", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_SGD_2", weight=Decimal("0.5")),
        ]
    )
    shelf_111 = [
        ShelfEntry(instrument_id="EQ_SGD_1", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_SGD_2", status="APPROVED"),
    ]
    opts_111 = EngineOptions(min_cash_buffer_pct=Decimal("0.005"))
    res_111 = run_simulation(pf_111, md_111, model_111, shelf_111, opts_111)
    save_golden(
        "scenario_111_fee_buffer",
        {
            "portfolio_snapshot": pf_111.model_dump(),
            "market_data_snapshot": md_111.model_dump(),
            "model_portfolio": model_111.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_111],
            "options": opts_111.model_dump(),
        },
        res_111,
    )

    # 112: Cross-Currency Switch
    pf_112 = PortfolioSnapshot(
        portfolio_id="pf_112",
        base_currency="SGD",
        positions=[Position(instrument_id="US_TECH", quantity=Decimal("100"))],
        cash_balances=[
            CashBalance(currency="SGD", amount=Decimal("0.0")),
            CashBalance(currency="USD", amount=Decimal("0.0")),
            CashBalance(currency="EUR", amount=Decimal("0.0")),
        ],
    )
    md_112 = MarketDataSnapshot(
        prices=[price("US_TECH", 100.0, "USD"), price("EU_BOND", 100.0, "EUR")],
        fx_rates=[fx("USD/SGD", 1.50), fx("EUR/SGD", 1.60)],
    )
    model_112 = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EU_BOND", weight=Decimal("1.0"))]
    )
    shelf_112 = [
        ShelfEntry(instrument_id="US_TECH", status="APPROVED"),
        ShelfEntry(instrument_id="EU_BOND", status="APPROVED"),
    ]
    res_112 = run_simulation(pf_112, md_112, model_112, shelf_112, EngineOptions())
    save_golden(
        "scenario_112_cross_currency_switch",
        {
            "portfolio_snapshot": pf_112.model_dump(),
            "market_data_snapshot": md_112.model_dump(),
            "model_portfolio": model_112.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_112],
            "options": EngineOptions().model_dump(),
        },
        res_112,
    )

    # 113: Capped Rotation (FX Netting)
    pf_113 = PortfolioSnapshot(
        portfolio_id="pf_113",
        base_currency="SGD",
        positions=[Position(instrument_id="USD_OLD", quantity=Decimal("100"))],
        cash_balances=[
            CashBalance(currency="SGD", amount=Decimal("0.0")),
            CashBalance(currency="USD", amount=Decimal("0.0")),
            CashBalance(currency="EUR", amount=Decimal("0.0")),
        ],
    )
    md_113 = MarketDataSnapshot(
        prices=[
            price("USD_OLD", 100.0, "USD"),
            price("USD_NEW", 100.0, "USD"),
            price("EUR_NEW", 100.0, "EUR"),
        ],
        fx_rates=[fx("USD/SGD", 1.50), fx("EUR/SGD", 1.60)],
    )
    model_113 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="USD_NEW", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EUR_NEW", weight=Decimal("0.5")),
        ]
    )
    shelf_113 = [
        ShelfEntry(instrument_id="USD_OLD", status="APPROVED"),
        ShelfEntry(instrument_id="USD_NEW", status="APPROVED"),
        ShelfEntry(instrument_id="EUR_NEW", status="APPROVED"),
    ]
    opts_113 = EngineOptions(single_position_max_weight=Decimal("0.30"))
    res_113 = run_simulation(pf_113, md_113, model_113, shelf_113, opts_113)
    save_golden(
        "scenario_113_capped_rotation",
        {
            "portfolio_snapshot": pf_113.model_dump(),
            "market_data_snapshot": md_113.model_dump(),
            "model_portfolio": model_113.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_113],
            "options": opts_113.model_dump(),
        },
        res_113,
    )

    # 114: Frozen Asset (Regulatory Locking)
    pf_114 = PortfolioSnapshot(
        portfolio_id="pf_114",
        base_currency="SGD",
        positions=[Position(instrument_id="RUSSIA_ETF", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )
    md_114 = MarketDataSnapshot(
        prices=[price("RUSSIA_ETF", 100.0, "SGD"), price("US_BOND", 100.0, "SGD")]
    )
    model_114 = ModelPortfolio(
        targets=[ModelTarget(instrument_id="US_BOND", weight=Decimal("1.0"))]
    )
    shelf_114 = [
        ShelfEntry(instrument_id="RUSSIA_ETF", status="SUSPENDED"),
        ShelfEntry(instrument_id="US_BOND", status="APPROVED"),
    ]
    res_114 = run_simulation(pf_114, md_114, model_114, shelf_114, EngineOptions())
    save_golden(
        "scenario_114_frozen_asset",
        {
            "portfolio_snapshot": pf_114.model_dump(),
            "market_data_snapshot": md_114.model_dump(),
            "model_portfolio": model_114.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_114],
            "options": EngineOptions().model_dump(),
        },
        res_114,
    )

    print("Golden scenarios generated successfully.")


if __name__ == "__main__":
    generate_scenarios()
