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

    # 101: Simple Drift Rebalance (Holdings exist, same currency)
    # ----------------------------------------------------------------
    print("Generating 101: Drift Rebalance...")
    pf_101 = PortfolioSnapshot(
        portfolio_id="pf_101",
        base_currency="SGD",
        positions=[
            Position(instrument_id="EQ_SGD_1", quantity=Decimal("100")),  # Value 10k
        ],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    # Total Value ~11k. Target: 50% EQ_1 (5.5k), 50% EQ_2 (5.5k).
    # Current EQ_1 is 10k. Need to Sell ~4.5k of EQ_1, Buy ~5.5k of EQ_2.
    md_101 = MarketDataSnapshot(
        prices=[
            price("EQ_SGD_1", 100.0, "SGD"),
            price("EQ_SGD_2", 50.0, "SGD"),
        ]
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
    opts_101 = EngineOptions()

    res_101 = run_simulation(pf_101, md_101, model_101, shelf_101, opts_101)
    save_golden(
        "scenario_101_drift_rebalance",
        {
            "portfolio_snapshot": pf_101.model_dump(),
            "market_data_snapshot": md_101.model_dump(),
            "model_portfolio": model_101.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_101],
            "options": opts_101.model_dump(),
        },
        res_101,
    )

    # 102: Cash Inflow (Holdings + High Cash)
    # ----------------------------------------------------------------
    print("Generating 102: Cash Inflow...")
    pf_102 = PortfolioSnapshot(
        portfolio_id="pf_102",
        base_currency="SGD",
        positions=[
            Position(instrument_id="EQ_SGD_1", quantity=Decimal("50")),  # Value 5k
        ],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("15000.0"))],  # High cash
    )
    # Total ~20k. Target 100% Equity. Should Buy 15k more.
    md_102 = MarketDataSnapshot(prices=[price("EQ_SGD_1", 100.0, "SGD")])
    model_102 = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_SGD_1", weight=Decimal("1.0"))])
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

    # 103: Sell to Fund (Low Cash)
    # ----------------------------------------------------------------
    print("Generating 103: Sell to Fund...")
    pf_103 = PortfolioSnapshot(
        portfolio_id="pf_103",
        base_currency="SGD",
        positions=[
            Position(instrument_id="BOND_SGD", quantity=Decimal("1000")), # Val 100k
        ],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("100.0"))], # No cash
    )
    # Target: 50/50 Bond/Equity. Must Sell 50k Bond -> Buy 50k Equity.
    md_103 = MarketDataSnapshot(
        prices=[
            price("BOND_SGD", 100.0, "SGD"),
            price("EQ_SGD", 50.0, "SGD"),
        ]
    )
    model_103 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="BOND_SGD", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_SGD", weight=Decimal("0.5")),
        ]
    )
    shelf_103 = [
        ShelfEntry(instrument_id="BOND_SGD", status="APPROVED", asset_class="FIXED_INCOME"),
        ShelfEntry(instrument_id="EQ_SGD", status="APPROVED", asset_class="EQUITY"),
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

    # 104: Multi-Currency FX Funding
    # ----------------------------------------------------------------
    print("Generating 104: Multi-Currency FX...")
    pf_104 = PortfolioSnapshot(
        portfolio_id="pf_104",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("20000.0"))],
    )
    # Buy USD Asset. 1 USD = 1.35 SGD.
    # Target 100% US_ETF.
    md_104 = MarketDataSnapshot(
        prices=[price("US_ETF", 100.0, "USD")],
        fx_rates=[fx("USD/SGD", 1.35)]
    )
    model_104 = ModelPortfolio(targets=[ModelTarget(instrument_id="US_ETF", weight=Decimal("1.0"))])
    shelf_104 = [ShelfEntry(instrument_id="US_ETF", status="APPROVED", asset_class="EQUITY")]
    opts_104 = EngineOptions(fx_buffer_pct=Decimal("0.01")) # 1% buffer

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

    # 105: SELL_ONLY Asset
    # ----------------------------------------------------------------
    print("Generating 105: SELL_ONLY...")
    pf_105 = PortfolioSnapshot(
        portfolio_id="pf_105",
        base_currency="SGD",
        positions=[Position(instrument_id="BAD_ASSET", quantity=Decimal("100"))], # Val 1000
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("9000.0"))],
    )
    # Total 10k. Target 50% Good, 50% Bad (Request).
    # Shelf says Bad is SELL_ONLY.
    # Engine should: Set Bad Target to 0%. Distrib 50% excess to Good -> Good gets 100%.
    # Action: Sell 100 Bad_Asset. Buy Good_Asset with proceeds + cash.
    md_105 = MarketDataSnapshot(
        prices=[
            price("BAD_ASSET", 10.0, "SGD"),
            price("GOOD_ASSET", 10.0, "SGD"),
        ]
    )
    model_105 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="BAD_ASSET", weight=Decimal("0.5")),
            ModelTarget(instrument_id="GOOD_ASSET", weight=Decimal("0.5")),
        ]
    )
    shelf_105 = [
        ShelfEntry(instrument_id="BAD_ASSET", status="SELL_ONLY", asset_class="EQUITY"),
        ShelfEntry(instrument_id="GOOD_ASSET", status="APPROVED", asset_class="EQUITY"),
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

    # 107: Missing Price (Blocked)
    # ----------------------------------------------------------------
    print("Generating 107: Missing Price...")
    pf_107 = PortfolioSnapshot(
        portfolio_id="pf_107",
        base_currency="SGD",
        positions=[Position(instrument_id="UNKNOWN_ASSET", quantity=Decimal("10"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("100.0"))],
    )
    md_107 = MarketDataSnapshot(prices=[]) # Empty
    model_107 = ModelPortfolio(targets=[ModelTarget(instrument_id="UNKNOWN_ASSET", weight=Decimal("1.0"))])
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
    # ----------------------------------------------------------------
    print("Generating 110: Dust Suppression...")
    pf_110 = PortfolioSnapshot(
        portfolio_id="pf_110",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )
    # Buy 1% of small asset = $100. Min trade $500.
    md_110 = MarketDataSnapshot(
        prices=[
            price("BIG_ASSET", 100.0, "SGD"),
            price("DUST_ASSET", 10.0, "SGD"),
        ]
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

    print("Golden scenarios generated successfully.")

if __name__ == "__main__":
    generate_scenarios()