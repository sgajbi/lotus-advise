"""
FILE: update_goldens.py
SCRIPT: Regenerate all golden data files with the latest engine logic.
"""

import glob
import json
import os
from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)


def decimal_encoder(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def main():
    golden_dir = os.path.join("tests", "golden_data")
    files = glob.glob(os.path.join(golden_dir, "*.json"))

    print(f"Found {len(files)} golden scenarios to update...")

    for filepath in files:
        print(f"Updating {os.path.basename(filepath)}...")

        with open(filepath, "r") as f:
            data = json.load(f)

        inputs = data["inputs"]

        try:
            portfolio = PortfolioSnapshot(**inputs["portfolio_snapshot"])
            market = MarketDataSnapshot(**inputs["market_data_snapshot"])
            model = ModelPortfolio(**inputs["model_portfolio"])
            shelf = [ShelfEntry(**s) for s in inputs["shelf_entries"]]
            options = EngineOptions(**inputs["options"])

            result = run_simulation(portfolio, market, model, shelf, options)

            output_dict = result.model_dump(mode="json", exclude_none=True)

            data["expected_outputs"] = {
                "status": output_dict["status"],
                "intents": output_dict["intents"],
                "after_simulated": output_dict["after_simulated"],
                "diagnostics": output_dict["diagnostics"],
                "universe": output_dict["universe"],
            }

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"FAILED to update {filepath}: {e}")

    print("Done. All goldens updated.")


if __name__ == "__main__":
    main()
