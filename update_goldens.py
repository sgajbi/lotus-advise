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
    # --- Shared Objects ---
    base_pf = PortfolioSnapshot(
        portfolio_id="pf_001",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )

    # 01. Cash Inflow (Simple Buy)
    # ---------------------------------------------------------
    print("Generating Scenario 01...")
    model_01 = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf_01 = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    md_01 = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts_01 = EngineOptions()

    res_01 = run_simulation(base_pf, md_01, model_01, shelf_01, opts_01)
    save_golden(
        "scenario_01_cash_inflow",
        {
            "portfolio_snapshot": base_pf.model_dump(),
            "market_data_snapshot": md_01.model_dump(),
            "model_portfolio": model_01.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_01],
            "options": opts_01.model_dump(),
        },
        res_01,
    )

    # 02. Constraint Capping (Redistribution)
    # ---------------------------------------------------------
    print("Generating Scenario 02...")
    model_02 = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_1", weight=Decimal("0.6")),
            ModelTarget(instrument_id="EQ_2", weight=Decimal("0.4")),
        ]
    )
    shelf_02 = [
        ShelfEntry(instrument_id="EQ_1", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_2", status="APPROVED"),
    ]
    md_02 = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_2", price=Decimal("50.0"), currency="SGD"),
        ]
    )
    # EQ_1 capped at 0.5
    opts_02 = EngineOptions(single_position_max_weight=Decimal("0.5"))

    res_02 = run_simulation(base_pf, md_02, model_02, shelf_02, opts_02)
    save_golden(
        "scenario_02_constraint_cap",
        {
            "portfolio_snapshot": base_pf.model_dump(),
            "market_data_snapshot": md_02.model_dump(),
            "model_portfolio": model_02.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_02],
            "options": opts_02.model_dump(),
        },
        res_02,
    )

    # 03. FX Funding
    # ---------------------------------------------------------
    print("Generating Scenario 03...")
    pf_03 = PortfolioSnapshot(
        portfolio_id="pf_003",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )
    model_03 = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("0.5"))])
    shelf_03 = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    md_03 = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("100.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.35"))],
    )
    opts_03 = EngineOptions(fx_buffer_pct=Decimal("0.01"))

    res_03 = run_simulation(pf_03, md_03, model_03, shelf_03, opts_03)
    save_golden(
        "scenario_03_fx_funding",
        {
            "portfolio_snapshot": pf_03.model_dump(),
            "market_data_snapshot": md_03.model_dump(),
            "model_portfolio": model_03.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_03],
            "options": opts_03.model_dump(),
        },
        res_03,
    )

    # 04. Data Quality Failure (Audit Bundle)
    # ---------------------------------------------------------
    print("Generating Scenario 04 (DQ Failure)...")
    # Missing Price for EQ_1
    model_04 = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf_04 = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    md_04 = MarketDataSnapshot(prices=[])
    opts_04 = EngineOptions(block_on_missing_prices=True)

    res_04 = run_simulation(base_pf, md_04, model_04, shelf_04, opts_04)
    save_golden(
        "scenario_04_dq_failure",
        {
            "portfolio_snapshot": base_pf.model_dump(),
            "market_data_snapshot": md_04.model_dump(),
            "model_portfolio": model_04.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_04],
            "options": opts_04.model_dump(),
        },
        res_04,
    )

    # 05. Constraint Failure (Infeasible)
    # ---------------------------------------------------------
    print("Generating Scenario 05 (Constraint Fail)...")
    # Cap 40%, Target 100% -> Excess 60% has nowhere to go
    model_05 = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf_05 = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    md_05 = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts_05 = EngineOptions(single_position_max_weight=Decimal("0.4"))

    res_05 = run_simulation(base_pf, md_05, model_05, shelf_05, opts_05)
    save_golden(
        "scenario_05_constraint_fail",
        {
            "portfolio_snapshot": base_pf.model_dump(),
            "market_data_snapshot": md_05.model_dump(),
            "model_portfolio": model_05.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_05],
            "options": opts_05.model_dump(),
        },
        res_05,
    )

    # 06. Suppression (Dust Trades)
    # ---------------------------------------------------------
    print("Generating Scenario 06 (Suppression)...")
    model_06 = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    # Min notional 50k, but we only have 10k cash
    shelf_06 = [
        ShelfEntry(
            instrument_id="EQ_1",
            status="APPROVED",
            min_notional=Money(amount=Decimal("50000.0"), currency="SGD"),
        )
    ]
    md_06 = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts_06 = EngineOptions(suppress_dust_trades=True)

    res_06 = run_simulation(base_pf, md_06, model_06, shelf_06, opts_06)
    save_golden(
        "scenario_06_suppression",
        {
            "portfolio_snapshot": base_pf.model_dump(),
            "market_data_snapshot": md_06.model_dump(),
            "model_portfolio": model_06.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_06],
            "options": opts_06.model_dump(),
        },
        res_06,
    )

    # 07. Audit Trace (The "Why")
    # ---------------------------------------------------------
    print("Generating Scenario 07 (Audit Trace)...")
    # Model 60/40 -> Capped 50/50. Trace should show tags.
    # Re-using logic from 02 but specifically for the trace output verification
    res_07 = run_simulation(base_pf, md_02, model_02, shelf_02, opts_02)
    save_golden(
        "scenario_07_audit_trace",
        {
            "portfolio_snapshot": base_pf.model_dump(),
            "market_data_snapshot": md_02.model_dump(),
            "model_portfolio": model_02.model_dump(),
            "shelf_entries": [s.model_dump() for s in shelf_02],
            "options": opts_02.model_dump(),
        },
        res_07,
    )


if __name__ == "__main__":
    generate_scenarios()
