# RFC-0013: "What-If" Analysis Mode (Multi-Scenario Simulation)

**Status:** DRAFT
**Created:** 2026-02-17
**Depends On:** RFC-0003 (No-Throw Architecture)

---

## 0. Executive Summary

This RFC enables the engine to simulate **multiple scenarios** in a single API call. Instead of receiving one set of trades, the consumer receives a comparative analysis of different strategies.

**Key Capabilities:**
1.  **Batch Simulation:** The API accepts a map of named scenarios (e.g., `{"full_rebalance": OptionsA, "tax_safe": OptionsB}`).
2.  **Comparative Output:** Returns a result for each scenario, allowing the frontend to display a "Side-by-Side" comparison (Drift Reduction vs. Tax Impact vs. Turnover).
3.  **Efficiency:** Leverages the stateless nature of the engine to reuse the same Portfolio/Market snapshots across all scenarios, minimizing data overhead.

---

## 1. Problem Statement

Currently, the engine provides a single, binary outcome based on one set of options.
* **Scenario:** An advisor wants to know: "What happens if I respect the tax budget?" vs "What happens if I ignore taxes but minimize tracking error?"
* **Current Friction:** The frontend must make multiple HTTP calls, sending the large `PortfolioSnapshot` and `MarketDataSnapshot` payload every time.
* **Risk:** Network latency or data drift between calls could make comparisons invalid.

---

## 2. Goals

### 2.1 Functional Requirements
* **API Extension:** Create a wrapper request model that accepts `common_data` (Portfolio/Market) and `scenarios` (Map of Options).
* **Logic:** Iterate through scenarios, calling the core `run_simulation` logic for each using the shared data.
* **Output:** A `SimulationBatchResult` containing a map of results.

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

**1. Define Batch Request**
We separate the "Heavy" data (Common) from the "Light" configuration (Scenarios).

```python
class SimulationScenario(BaseModel):
    description: str
    options: EngineOptions

class BatchRebalanceRequest(BaseModel):
    # Common Data (Shared across all scenarios)
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    
    # Variations
    scenarios: Dict[str, SimulationScenario]

```

**2. Define Batch Result**

```python
class BatchRebalanceResult(BaseModel):
    batch_run_id: str
    results: Dict[str, RebalanceResult]

```

### 3.2 Logic Changes (`src/api/main.py`)

We introduce a new endpoint to handle the batch processing. This keeps the core `engine.py` simple (single run) while the API layer handles the orchestration.

```python
# src/api/main.py

@app.post("/rebalance/analyze", response_model=BatchRebalanceResult)
def analyze_scenarios(request: BatchRebalanceRequest):
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    results = {}

    for name, scenario in request.scenarios.items():
        # Reuse the common data, apply specific options
        result = run_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            model=request.model_portfolio,
            shelf=request.shelf_entries,
            options=scenario.options,
            request_hash=batch_id # Link them via hash
        )
        results[name] = result

    return BatchRebalanceResult(
        batch_run_id=batch_id,
        results=results
    )

```

---

## 4. Test Plan (Golden Scenarios)

We will create `tests/golden_data/scenario_13_what_if_analysis.json`.

**Scenario:**

* **Portfolio:** Holds `Tech_Stock` (Huge unrealized gain).
* **Model:** Sell `Tech_Stock`.
* **Input Scenarios:**
1. **"Ignore Tax"**: `max_realized_capital_gains: None`.
2. **"Tax Safe"**: `max_realized_capital_gains: 0`.



**Expected Outcome:**

* **Result "Ignore Tax"**:
* Status: `READY`.
* Trade: SELL 100% of `Tech_Stock`.
* Tax Impact: High.


* **Result "Tax Safe"**:
* Status: `READY`.
* Trade: NONE (or small sell).
* Tax Impact: $0.
* Diagnostics: Warning about high drift.



**Client Value:**
The advisor sees both and decides: *"The drift is too dangerous, let's take the tax hit."* OR *"The client hates taxes, let's stick with the safe option."*

```

```