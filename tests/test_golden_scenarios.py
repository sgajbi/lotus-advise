import json
import pytest
from pathlib import Path
from src.core.models import (
    PortfolioSnapshot, MarketDataSnapshot, ModelPortfolio, 
    ShelfEntry, EngineOptions
)
from src.core.engine import run_simulation

# Force absolute path resolution
GOLDEN_DIR = Path(__file__).resolve().parent / "golden_data"

def load_golden_scenarios():
    scenarios = []
    if not GOLDEN_DIR.exists():
        return scenarios
        
    for filepath in GOLDEN_DIR.glob("*.json"):
        with open(filepath, "r", encoding="utf-8") as f:
            scenarios.append((filepath.name, json.load(f)))
    return scenarios

@pytest.mark.parametrize("filename, scenario", load_golden_scenarios())
def test_golden_scenario(filename, scenario):
    inputs = scenario["inputs"]
    
    # 1. Parse Inputs
    portfolio = PortfolioSnapshot(**inputs["portfolio_snapshot"])
    market_data = MarketDataSnapshot(**inputs["market_data_snapshot"])
    model = ModelPortfolio(**inputs["model_portfolio"])
    shelf = [ShelfEntry(**s) for s in inputs["shelf_entries"]]
    options = EngineOptions(**inputs["options"])
    
    # 2. Run Engine
    result = run_simulation(portfolio, market_data, model, shelf, options)
    
    # 3. Assert Outputs
    expected = scenario["expected_outputs"]
    assert result.status == expected["status"], f"Expected status {expected['status']}, got {result.status}"
    assert len(result.intents) == len(expected["intents"]), f"Expected {len(expected['intents'])} intents, got {len(result.intents)}"
    
    for act_intent, exp_intent in zip(result.intents, expected["intents"]):
        assert act_intent.action == exp_intent["action"]
        assert act_intent.intent_type == exp_intent.get("intent_type", "SECURITY")
        
        if act_intent.intent_type == "SECURITY":
            assert act_intent.instrument_id == exp_intent["instrument_id"]
            assert float(act_intent.quantity) == float(exp_intent["quantity"])
            assert float(act_intent.est_notional.amount) == float(exp_intent["est_notional"]["amount"])
        elif act_intent.intent_type == "FX":
            assert act_intent.currency_pair == exp_intent["currency_pair"]
            assert float(act_intent.buy_amount.amount) == float(exp_intent["buy_amount"]["amount"])
            assert float(act_intent.sell_amount.amount) == float(exp_intent["sell_amount"]["amount"])