# RFC-0013: "What-If" Analysis Mode (Multi-Scenario Simulation)

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-17 |
| **Target Release** | TBD |
| **Doc Location** | docs/rfcs/RFC-0013-what-if-analysis-mode-multi-scenario-simulation.md |

---

## 0. Executive Summary

This RFC adds a batch simulation API for side-by-side strategy analysis. One request carries shared snapshots and multiple option sets. The service returns one result per scenario with consistent baseline data.

Key outcomes:
1. Lower client overhead versus repeated single-scenario calls.
2. Comparable outputs under same portfolio and market snapshot.
3. Deterministic batch orchestration with per-scenario isolation.

---

## 1. Problem Statement

Advisors and PMs need quick comparison across policy choices (tax budget, turnover cap, strict constraints). Repeating large requests for each scenario adds latency and risks mismatch if snapshots differ between calls.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Introduce a batch endpoint that accepts shared snapshots and multiple scenarios.
2. Reuse existing single-run engine path for each scenario.
3. Return stable, named per-scenario results with common batch metadata.
4. Allow frontend to compare key metrics directly (drift, turnover, tax impact, status).

### 2.2 Non-Goals
1. Cross-scenario optimization.
2. Scenario dependency graphing (scenario B depends on A).
3. Asynchronous distributed execution in this RFC.

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

```python
class SimulationScenario(BaseModel):
    description: Optional[str] = None
    options: EngineOptions

class BatchRebalanceRequest(BaseModel):
    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    scenarios: Dict[str, SimulationScenario]

class BatchRebalanceResult(BaseModel):
    batch_run_id: str
    run_at_utc: str
    base_snapshot_ids: Dict[str, str]
    results: Dict[str, RebalanceResult]
```

Validation:
1. Require at least one scenario.
2. Enforce scenario name format (`[a-z0-9_\\-]{1,64}`) for stable keys.
3. Reject duplicate keys after case normalization.

### 3.2 API and Orchestration (`src/api/main.py`)

Add a batch endpoint while keeping core engine single-run.

```python
# src/api/main.py

@app.post("/rebalance/analyze", response_model=BatchRebalanceResult)
def analyze_scenarios(request: BatchRebalanceRequest):
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    results = {}

    for name in sorted(request.scenarios.keys()):
        scenario = request.scenarios[name]
        # Reuse the common data, apply specific options
        result = run_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            model=request.model_portfolio,
            shelf=request.shelf_entries,
            options=scenario.options,
            request_hash=f"{batch_id}:{name}"
        )
        results[name] = result

    return BatchRebalanceResult(
        batch_run_id=batch_id,
        run_at_utc=datetime.utcnow().isoformat(),
        base_snapshot_ids={
            "portfolio_snapshot_id": request.portfolio_snapshot.snapshot_id,
            "market_data_snapshot_id": request.market_data_snapshot.snapshot_id,
        },
        results=results
    )

```

---

## 4. Test Plan

Add `tests/golden_data/scenario_13_what_if_analysis.json`.

Scenario:
1. Portfolio holds highly appreciated `Tech_Stock`.
2. Model implies full exit.
3. Scenarios:
   1. `ignore_tax`: no gains limit.
   2. `tax_safe`: `max_realized_capital_gains = 0`.

Expected:
1. `ignore_tax` produces large sell and high realized gain.
2. `tax_safe` produces constrained/no sell and higher residual drift.
3. Both results share same snapshot IDs and batch ID context.

Add failure-case scenario with one invalid options payload and verify only that scenario fails while others still run.

---

## 5. Rollout and Compatibility

1. New endpoint is additive and backward compatible.
2. Keep existing single-run endpoint unchanged.
3. Document recommended max scenarios per request to prevent abuse.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical single-run endpoint remains `POST /rebalance/simulate`.
2. Batch endpoint follows same route style (`/rebalance/analyze`) and must not introduce alternate `/v1` simulate routes.
3. Per-scenario runs must preserve existing status and safety contract from current engine.
4. Baseline assumptions from implemented RFCs (RFC-0007A and RFC-0008) remain in effect for each scenario run.
5. Do not assume persistence-backed idempotency store for batch replay; deterministic result generation remains request-bound.

---

## 6. Open Questions

1. Should scenario execution be strictly sequential for reproducibility or parallel for latency?
2. Should batch response include normalized comparison metrics table for frontend convenience?

---

## 7. Status and Reason Code Conventions

1. Per-scenario result status values remain aligned to RFC-0007A: `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. Batch execution does not define a new scenario status vocabulary.
3. If needed, batch-level warnings should use upper snake case (for example `PARTIAL_BATCH_FAILURE`) while preserving per-scenario reason codes from underlying RFCs.
