
# Private Banking Rebalance Engine (DPM)

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Compliance](https://img.shields.io/badge/RFC-0003%20Audit%20Bundle-Compliant-gold)

A deterministic, production-grade **Discretionary Portfolio Management (DPM)** rebalancing engine. Designed for Private Banking, it ensures mathematically precise trade generation, strict audit traceability, and zero-regression stability.

---

## Implemented RFCs

* RFC-0001 to RFC-0008
* RFC-0009 (tax-aware HIFO sell budget controls, feature-flagged via `options.enable_tax_awareness`)
* RFC-0010 (turnover cap control via `options.max_turnover_pct`)
* RFC-0011 (settlement ladder & overdraft protection, feature-flagged via `options.enable_settlement_awareness`)
* RFC-0012 (solver integration, feature-flagged via `options.target_method`)
* RFC-0013 (what-if batch analysis via `POST /rebalance/analyze`)
* RFC-0014A (advisory proposal simulation via `POST /rebalance/proposals/simulate`, feature-flagged via `options.enable_proposal_simulation`)
* RFC-0014B (advisory proposal auto-funding via generated `FX_SPOT` intents and dependencies)
* RFC-0014C (advisory drift analytics via inline `reference_model` in `POST /rebalance/proposals/simulate`)
* RFC-0014D (advisory suitability scanner with NEW/RESOLVED/PERSISTENT issue classification and gate recommendation)
* RFC-0014E (advisory proposal artifact via `POST /rebalance/proposals/artifact` with deterministic evidence hash)
* Shared workflow gate decision semantics (deterministic `gate_decision` block in DPM/advisory outputs, configurable through `EngineOptions`)

---
## Engine Know-How

Primary implementation guide:
* `docs/documentation/engine-know-how-dpm.md`
* `docs/documentation/engine-know-how-advisory.md`

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

The DPM engine (`src/core/dpm/engine.py`) processes rebalance requests through a strictly ordered, functional pipeline:

1.  **Valuation:** Normalizes all positions to Base Currency (Currency Truth Model).
2.  **Universe:** Filters Shelf (Banned/Restricted checks).
3.  **Targets:** Applies constraints using either:
    * `HEURISTIC` (legacy redistribution path), or
    * `SOLVER` (convex optimization via `cvxpy`, RFC-0012).
    Active method is controlled by `options.target_method` (default: `HEURISTIC`).
    Optional dual-path comparison is available via `options.compare_target_methods`.
4.  **Intents:** Translates weights to trades, suppressing dust (`min_notional`).
5.  **Simulation:** Generates FX trades (Hub-and-Spoke), optionally evaluates settlement-time cash ladder, and validates the After-State.

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
* `options`: Constraints and execution controls (e.g., `suppress_dust_trades`, `group_constraints`, `target_method`, `enable_settlement_awareness`, `enable_tax_awareness`).
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

### POST `/rebalance/analyze`

Runs multiple named what-if scenarios in one call using shared snapshots.

**Request Body:**

* Same shared fields as `/rebalance/simulate`:
  `portfolio_snapshot`, `market_data_snapshot`, `model_portfolio`, `shelf_entries`.
* `scenarios`: map of scenario name to:
  * `description` (optional)
  * `options` (scenario-specific `EngineOptions` payload)

**Scenario key rules:**

* Must match `[a-z0-9_\\-]{1,64}`
* At least one scenario is required
* Maximum scenarios per request: `20`
* Scenarios are executed in sorted key order for deterministic orchestration

**Snapshot IDs:**

* `portfolio_snapshot.snapshot_id` and `market_data_snapshot.snapshot_id` are supported.
* `base_snapshot_ids` in batch response uses these IDs when provided.

**Response:**

* `batch_run_id`, `run_at_utc`, `base_snapshot_ids`
* `results`: per-scenario simulation results
* `comparison_metrics`: per-scenario quick-compare fields
  (`status`, `security_intent_count`, `gross_turnover_notional_base`)
* `failed_scenarios`: per-scenario validation/runtime failures
* `warnings`: includes `PARTIAL_BATCH_FAILURE` when applicable

Notes:
* Batch comparison metrics currently expose turnover proxy only; tax-impact aggregation is not included in batch metrics.

### POST `/rebalance/proposals/simulate`

Simulates advisor-entered manual `proposed_cash_flows` and `proposed_trades` without model targeting.

**Headers:**

* `Idempotency-Key` (Required)
* `X-Correlation-Id` (Optional, auto-generated if missing)

**Request Body:**

* `portfolio_snapshot`
* `market_data_snapshot`
* `shelf_entries`
* `options`:
  `enable_proposal_simulation` must be `true` to activate this endpoint.
  `proposal_apply_cash_flows_first` controls whether cash flows apply before manual trades.
  `proposal_block_negative_cash` controls negative-cash withdrawal hard blocking.
* `proposed_cash_flows`: list of `CASH_FLOW` intents
* `proposed_trades`: list of `SECURITY_TRADE` intents (requires `quantity` or `notional`)
* `reference_model` (optional): inline target model for `drift_analysis` output

**Response Status Codes:**

* `200 OK`: domain status returned in payload (`READY`, `PENDING_REVIEW`, `BLOCKED`)
* `409 Conflict`: same `Idempotency-Key` used with a different canonical request payload
* `422`: validation/feature-flag errors

### POST `/rebalance/proposals/artifact`

Builds a deterministic advisory proposal package by running proposal simulation and assembling:
* `summary`
* `portfolio_impact`
* `trades_and_funding`
* `suitability_summary` (`NOT_AVAILABLE` when scanner disabled/unavailable)
* `assumptions_and_limits`
* `disclosures`
* `evidence_bundle` (inputs, proposal output, canonical hashes, engine version)

Hashing behavior:
* `evidence_bundle.hashes.artifact_hash` is computed from canonical JSON, excluding volatile fields (`created_at`, `artifact_hash`).
* This keeps hash stability across repeated requests with identical deterministic inputs.

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
