
# Enterprise Rebalance Simulation Engine (DPM)

An audit-compliant, deterministic portfolio rebalancing engine for Private Banking.

## Core Features

* **Deterministic Simulation:** 100% reproducible results given the same inputs.
* **"No-Throw" Architecture:** All domain failures (data quality, infeasible constraints) return **HTTP 200** with a structured `BLOCKED` status and diagnostic traces.
* **Audit Bundle:** Every response includes the `before` state, `target` lineage (Model vs. Final weight), `after` simulated state, and `rule_results`.
* **FX Hub-and-Spoke:** Auto-generates FX spot trades to fund security purchases in non-base currencies.
* **Idempotency:** SHA-256 content hashing prevents duplicate runs.

## API Usage (RFC-0003)

### Endpoint: `POST /rebalance/simulate`

**Headers:**
* `Idempotency-Key`: Unique request ID.
* `X-Correlation-Id`: Distributed tracing ID.

**Response Status Codes:**
* `READY`: Simulation successful, trades generated.
* `PENDING_REVIEW`: Simulation successful, but soft rules (e.g., Cash Band) breached.
* `BLOCKED`: Simulation failed due to Data Quality or Hard Constraints. Check `diagnostics`.

## Developer Guide

### Prerequisites
* Python 3.11+
* Docker (optional)

### Setup & Testing
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run full test suite with coverage
pytest --cov=src --cov-report=term-missing --cov-fail-under=100

# Regenerate Golden Scenarios
python update_goldens.py

```

### Architecture (Modular Pipeline)

The engine (`src/core/engine.py`) processes requests in 5 strict stages:

1. **Valuation:** Calculates total portfolio value (Base Currency).
2. **Universe:** Filters Shelf (Banned/Restricted checks).
3. **Targets:** Applies Constraints (Max Weight) and Redistribution Logic.
4. **Intents:** Translates weights to trades, suppressing dust.
5. **Simulation:** Generates FX trades and validates the After-State.

```