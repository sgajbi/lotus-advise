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


# Setup Pydantic to serialize Decimals as strings for JSON
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
            # Rehydrate Models
            portfolio = PortfolioSnapshot(**inputs["portfolio_snapshot"])
            market = MarketDataSnapshot(**inputs["market_data_snapshot"])
            model = ModelPortfolio(**inputs["model_portfolio"])
            shelf = [ShelfEntry(**s) for s in inputs["shelf_entries"]]
            options = EngineOptions(**inputs["options"])

            # Run Simulation
            result = run_simulation(portfolio, market, model, shelf, options)

            # Update Expected Outputs
            # We use model_dump(mode='json') to get a clean dict with basic types
            # Pydantic v2 mode='json' converts Decimals to strings automatically
            output_dict = result.model_dump(mode="json", exclude_none=True)

            # We only want to save the fields we actually verify in goldens
            # usually: status, intents, after_simulated, diagnostics (maybe)

            # Preserve the input structure, just update outputs
            data["expected_outputs"] = {
                "status": output_dict["status"],
                "intents": output_dict["intents"],
                "after_simulated": output_dict["after_simulated"],
                "diagnostics": output_dict["diagnostics"],
                "universe": output_dict["universe"],
            }

            # Write back
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"FAILED to update {filepath}: {e}")

    print("Done. All goldens updated.")


if __name__ == "__main__":
    main()
