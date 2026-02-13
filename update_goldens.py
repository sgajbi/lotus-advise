import json
from pathlib import Path

from src.core.engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)


def main():
    for filepath in Path("tests/golden_data").glob("*.json"):
        data = json.loads(filepath.read_text(encoding="utf-8"))
        inputs = data["inputs"]

        portfolio = PortfolioSnapshot(**inputs["portfolio_snapshot"])
        market_data = MarketDataSnapshot(**inputs["market_data_snapshot"])
        model = ModelPortfolio(**inputs["model_portfolio"])
        shelf = [ShelfEntry(**s) for s in inputs["shelf_entries"]]
        options = EngineOptions(**inputs["options"])

        try:
            result = run_simulation(portfolio, market_data, model, shelf, options)
            data["expected_outputs"] = json.loads(result.model_dump_json())
        except ValueError as e:
            data["expected_outputs"] = {"error": str(e)}

        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Successfully re-baselined all Golden Scenario JSONs.")


if __name__ == "__main__":
    main()
