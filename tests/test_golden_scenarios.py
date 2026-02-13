import json
from pathlib import Path

import pytest

from src.core.engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)


def load_golden_scenarios():
    scenarios = []
    golden_dir = Path("tests/golden_data")
    for filepath in golden_dir.glob("*.json"):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            scenarios.append((filepath.name, data))
    return scenarios


@pytest.mark.parametrize("filename, scenario", load_golden_scenarios())
def test_golden_scenario(filename, scenario):
    inputs = scenario["inputs"]
    portfolio = PortfolioSnapshot(**inputs["portfolio_snapshot"])
    market_data = MarketDataSnapshot(**inputs["market_data_snapshot"])
    model = ModelPortfolio(**inputs["model_portfolio"])
    shelf = [ShelfEntry(**s) for s in inputs["shelf_entries"]]
    options = EngineOptions(**inputs["options"])

    if "error" in scenario["expected_outputs"]:
        with pytest.raises(ValueError, match=scenario["expected_outputs"]["error"]):
            run_simulation(portfolio, market_data, model, shelf, options)
    else:
        result = run_simulation(portfolio, market_data, model, shelf, options)
        expected = scenario["expected_outputs"]

        assert result.status == expected["status"]
        assert len(result.intents) == len(expected["intents"])

        for act_intent, exp_intent in zip(result.intents, expected["intents"]):
            assert act_intent.side == exp_intent["side"]
