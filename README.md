# Private Banking Rebalance Engine (DPM)

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Compliance](https://img.shields.io/badge/RFC-0003%20Audit%20Bundle-Compliant-gold)

A deterministic, production-grade **Discretionary Portfolio Management (DPM)** rebalancing engine. Designed for Private Banking, it ensures mathematically precise trade generation, strict audit traceability, and zero-regression stability.

---

## 📖 Core Philosophy: "No-Throw" Architecture

Unlike traditional engines that crash (HTTP 500) or reject (HTTP 400) on complex domain states, this engine follows a **"No-Throw" Protocol (RFC-0003)**.

* **Always Returns 200 OK:** Even if the run is blocked by data quality or mathematical infeasibility.
* **Status-Driven Flow:** The `status` field (`READY`, `PENDING_REVIEW`, `BLOCKED`) dictates the next step.
* **Audit Bundle:** Every response contains the *complete context* needed to reconstruct the decision:
    * `before`: The starting valuation.
    * `target`: The "Why" trace (Model Weight vs. Final Constrained Weight).
    * `diagnostics`: Specific reasons for blockage (e.g., `price_missing: ["EQ_1"]`).

---

## 🏗 Architecture: The 5-Stage Pipeline

The core engine (`src/core/engine.py`) processes every request through a strictly ordered, functional pipeline.

### Stage 1: Valuation & Context
* **Input:** Raw positions and cash.
* **Action:** Normalizes everything to Base Currency using provided FX rates.
* **Audit:** Captures the "Before State" snapshot.

### Stage 2: Universe Construction
* **Input:** Model targets and Shelf (Approved List).
* **Action:** Filters assets based on `BANNED`, `RESTRICTED`, or `SELL_ONLY` status.
* **Output:** A clean list of `eligible_targets` and a list of `excluded` assets with reason codes.

### Stage 3: Target Generation (The "Why" Trace)
* **Input:** Eligible targets and constraints (e.g., `single_position_max_weight`).
* **Action:**
    1.  Maps Model Weights to Targets.
    2.  Applies **Capping** (Hard Constraints).
    3.  Performs **Redistribution** (reallocating capped weight to other eligible assets).
* **Output:** A `TargetInstrument` list showing the lineage from `model_weight` -> `final_weight`.

### Stage 4: Intent Translation
* **Input:** Final Weights vs. Current Valuation.
* **Action:**
    1.  Calculates the delta (buy/sell).
    2.  Applies **Dust Suppression** (`min_notional`).
    3.  Generates `OrderIntent` objects.

### Stage 5: Simulation & Final Compliance
* **Action:**
    1.  **FX Hub-and-Spoke:** Auto-generates FX Spot trades to fund foreign security purchases.
    2.  **Simulation:** Applies all intents to create a theoretical `AfterState`.
    3.  **Rule Engine:** Checks soft limits (e.g., Cash Band > 5%) on the *simulated* state.

---

## 🚀 Quick Start

### Prerequisites
* Python 3.11+
* `pip`

### Installation

```bash
# Clone the repository
git clone [https://github.com/org/dpm-rebalance-engine.git](https://github.com/org/dpm-rebalance-engine.git)
cd dpm-rebalance-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

```

### Running the API

```bash
fastapi dev src/api/main.py

```

The documentation will be available at `http://127.0.0.1:8000/docs`.

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
* `options`: Constraints (e.g., `suppress_dust_trades`).

**Response Status Codes:**

| Status | Meaning | Action Required |
| --- | --- | --- |
| **READY** | Success. Trades generated. | Approve and execute. |
| **PENDING_REVIEW** | Soft Rule Breach (e.g., High Cash). | Human review required. |
| **BLOCKED** | Hard Failure (Data/Constraint). | Fix data or relax constraints. |

---

## 🧪 Testing & Quality Assurance

This project enforces **100% Code Coverage** and uses **Golden Regression Testing**.

### Running Unit Tests

```bash
# Run tests with coverage report
pytest --cov=src --cov-report=term-missing --cov-fail-under=100

```

### Golden Scenarios (Regression)

We maintain a set of "Gold Standard" inputs and outputs in `tests/golden_data/`. These ensure that complex math (e.g., redistribution logic) never changes unexpectedly.

**To Regenerate Golden Files:**
(Only do this if you have intentionally changed the business logic via an RFC).

```bash
python update_goldens.py

```
