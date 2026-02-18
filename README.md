
# Private Banking Rebalance Engine (DPM)

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Compliance](https://img.shields.io/badge/RFC-0003%20Audit%20Bundle-Compliant-gold)

A deterministic, production-grade **Discretionary Portfolio Management (DPM)** rebalancing engine. Designed for Private Banking, it ensures mathematically precise trade generation, strict audit traceability, and zero-regression stability.

---

## 📖 Core Philosophy: "No-Throw" Architecture

Unlike traditional engines that crash (HTTP 500) or reject (HTTP 400) on complex domain states, this engine follows a **"No-Throw" Protocol (RFC-0003)**.

* **Returns 200 OK for Domain Outcomes:** Valid simulation requests return `READY`, `PENDING_REVIEW`, or `BLOCKED` in a 200 response. Malformed payloads or missing required headers return 422.
* **Status-Driven Flow:** The `status` field (`READY`, `PENDING_REVIEW`, `BLOCKED`) dictates the next step.
* **Audit Bundle:** Every response contains the *complete context* needed to reconstruct the decision:
    * `before`: The starting valuation.
    * `target`: The "Why" trace (Model Weight vs. Final Constrained Weight).
    * `diagnostics`: Specific reasons for blockage and constraint events
      (e.g., `price_missing: ["EQ_1"]`, `group_constraint_events`).

---

## 🏗 Architecture: The 5-Stage Pipeline

The core engine (`src/core/engine.py`) processes every request through a strictly ordered, functional pipeline:

1.  **Valuation:** Normalizes all positions to Base Currency (Currency Truth Model).
2.  **Universe:** Filters Shelf (Banned/Restricted checks).
3.  **Targets:** Applies constraints using either:
    * `HEURISTIC` (legacy redistribution path), or
    * `SOLVER` (convex optimization via `cvxpy`, RFC-0012).
    Active method is controlled by `options.target_method` (default: `HEURISTIC`).
4.  **Intents:** Translates weights to trades, suppressing dust (`min_notional`).
5.  **Simulation:** Generates FX trades (Hub-and-Spoke) and validates the After-State.

---

## 🚀 Quick Start

### Prerequisites
* Python 3.11+
* `pip`
* Docker (Optional)

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

```

### Running the API

Use `uvicorn` to start the server locally:

```bash
uvicorn src.api.main:app --reload --port 8000

```

* **API Docs:** `http://127.0.0.1:8000/docs`

### Testing

```bash
# Run full test suite with coverage
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=100

# Linting & Formatting
ruff check .
ruff format .

```

---

## 🐳 Docker Deployment (Ephemeral)

The current version runs as a stateless container. Data (Idempotency keys and Rebalance Runs) is stored in-memory and will be lost if the container restarts.

### Build and Run

```bash
# Build and start the service in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f

```

### Accessing the Container

* **API Root:** `http://localhost:8000`
* **API Docs:** `http://localhost:8000/docs`

> **Note:** This Docker setup generates a production-optimized image (excluding tests and docs). To persist data, a PostgreSQL service will be introduced in **RFC-0004**.

---

## 📡 API Reference

### POST `/rebalance/simulate`

Performs a full rebalance simulation.

**Headers:**

* `Idempotency-Key` (Required): Unique SHA-256 or UUID for the request.
* `X-Correlation-Id` (Optional): Trace ID for logging.

**Request Body:** (See `docs/sample_request.json`)

* `portfolio_snapshot`: Current holdings.
* `market_data_snapshot`: Prices and FX rates.
* `model_portfolio`: Target weights.
* `shelf_entries`: Regulatory status of assets.
* `options`: Constraints and execution controls (e.g., `suppress_dust_trades`, `group_constraints`, `target_method`).
  `group_constraints` keys must use `<attribute_key>:<attribute_value>`.
  Invalid keys or invalid `max_weight` values return 422.

**Response Status Codes:**

| Status | Meaning | Action Required |
| --- | --- | --- |
| **READY** | Success. Trades generated. | Approve and execute. |
| **PENDING_REVIEW** | Soft Rule Breach (e.g., High Cash). | Human review required. |
| **BLOCKED** | Hard Failure (Data/Constraint). | Fix data or relax constraints. |

Notes:
* `X-Correlation-Id` is currently used for logging and is not echoed in the response body.

---

## 🧪 Regression Testing (Golden Scenarios)

We maintain a set of "Gold Standard" inputs and outputs in `tests/golden_data/`. These ensure that complex math (e.g., redistribution logic) never changes unexpectedly.

Solver-mode golden scenarios (RFC-0012):
* `tests/golden_data/scenario_12_solver_conflict.json`
* `tests/golden_data/scenario_12_solver_infeasible.json`

**To Regenerate Golden Files:**
(Only do this if you have intentionally changed the business logic via an RFC).

```bash
python update_goldens.py

```
