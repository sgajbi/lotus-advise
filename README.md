
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
* RFC-0016 (DPM idempotency replay and conflict contract for `POST /rebalance/simulate` with canonical request hash validation)
* RFC-0017 (DPM supportability APIs for run lookup by run id, correlation id, and idempotency key)
* RFC-0018 (DPM async operations phase-1 via `POST /rebalance/analyze/async` with operation lookup by id/correlation)
* RFC-0019 (DPM run artifact phase-1 via `GET /rebalance/runs/{rebalance_run_id}/artifact` with deterministic artifact hashing)
* RFC-0021 (DPM OpenAPI hardening phase-1 with contract tests for async/supportability/artifact endpoint schemas)
* RFC-0014A (advisory proposal simulation via `POST /rebalance/proposals/simulate`, feature-flagged via `options.enable_proposal_simulation`)
* RFC-0014B (advisory proposal auto-funding via generated `FX_SPOT` intents and dependencies)
* RFC-0014C (advisory drift analytics via inline `reference_model` in `POST /rebalance/proposals/simulate`)
* RFC-0014D (advisory suitability scanner with NEW/RESOLVED/PERSISTENT issue classification and gate recommendation)
* RFC-0014E (advisory proposal artifact via `POST /rebalance/proposals/artifact` with deterministic evidence hash)
* RFC-0014G (advisory proposal persistence and workflow lifecycle via `/rebalance/proposals` endpoint family, in-memory adapter with repository port)
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

# Dependency security/freshness checks
python scripts/dependency_health_check.py --requirements requirements.txt
# Optional strict mode (fails if any package is outdated)
python scripts/dependency_health_check.py --requirements requirements.txt --fail-on-outdated

```

Testing strategy:
* Default: keep unit tests lightweight for fast iteration.
* Critical persistence parity: run live Postgres integration tests in CI.
* Optional deep validation: nightly/manual Postgres full-suite workflow.
* Decision record: `docs/adr/ADR-0010-testing-strategy-fast-unit-and-postgres-parity.md`

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

### Postgres-First Local Runtime (RFC-0025 continuation)

```bash
# Start API + Postgres (default local runtime)
docker-compose up -d --build
```

Production-style compose override (RFC-0025):

```bash
docker-compose --profile postgres -f docker-compose.yml -f docker-compose.production.yml up -d --build
```

Environment variables for Postgres supportability backend:

```bash
APP_PERSISTENCE_PROFILE=PRODUCTION
DPM_SUPPORTABILITY_STORE_BACKEND=POSTGRES
DPM_SUPPORTABILITY_POSTGRES_DSN=postgresql://dpm:dpm@postgres:5432/dpm_supportability
PROPOSAL_STORE_BACKEND=POSTGRES
PROPOSAL_POSTGRES_DSN=postgresql://dpm:dpm@postgres:5432/dpm_supportability
DPM_POLICY_PACK_CATALOG_BACKEND=POSTGRES
DPM_POLICY_PACK_POSTGRES_DSN=postgresql://dpm:dpm@postgres:5432/dpm_supportability
```

Note:
* `APP_PERSISTENCE_PROFILE=PRODUCTION` enforces Postgres-only guardrails at startup.
  Startup fails fast with explicit reason codes if non-Postgres backends are configured.
* Profile guidance:
  * `LOCAL`: legacy in-memory/SQLite runtime backends are still available but deprecated.
  * `PRODUCTION`: requires Postgres for DPM supportability and advisory stores, plus
    policy-pack catalog when policy packs/admin APIs are enabled.
* Runtime backend deprecation policy:
  * `IN_MEMORY` / `SQL` / `SQLITE` / `ENV_JSON` runtime backends emit `DeprecationWarning`.
  * Use Postgres-backed runtime as the default for local and production operations.
* Postgres backends for DPM supportability and advisory proposal lifecycle are implemented.
* Apply forward-only migrations before enabling Postgres-backed runtime:
  * `python scripts/postgres_migrate.py --target all`
* Validate production cutover contract (profile + env + migration readiness):
  * `python scripts/production_cutover_check.py --check-migrations`
* Rollout and sequencing guidance:
  * `docs/documentation/postgres-migration-rollout-runbook.md`

### Accessing the Container

* **API Root:** `http://localhost:8000`
* **API Docs:** `http://localhost:8000/docs`

> **Note:** This Docker setup generates a production-optimized image (excluding tests and docs).
> PostgreSQL persistence is implemented and governed by RFC-0024/RFC-0025 for
> production-profile enforcement and cutover controls.

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

### DPM Run Supportability and Artifact Endpoints

* `GET /rebalance/runs/{rebalance_run_id}`: retrieve persisted run payload and metadata.
* `GET /rebalance/runs/by-correlation/{correlation_id}`: lookup latest run by correlation id.
* `GET /rebalance/runs/idempotency/{idempotency_key}`: lookup idempotency mapping to run id.
* `GET /rebalance/runs/{rebalance_run_id}/artifact`: retrieve deterministic run artifact for business/support workflows.

Runtime toggles:
* `DPM_SUPPORT_APIS_ENABLED` (`true` by default)
* `DPM_ARTIFACTS_ENABLED` (`true` by default)
* `DPM_ASYNC_OPERATIONS_ENABLED` (`true` by default)
* `DPM_ASYNC_OPERATIONS_TTL_SECONDS` (`86400` by default)
* `DPM_ASYNC_EXECUTION_MODE` (`INLINE` or `ACCEPT_ONLY`, default `INLINE`)
* `DPM_ASYNC_MANUAL_EXECUTION_ENABLED` (`true` by default)
* `DPM_STRICT_OPENAPI_VALIDATION` (`true` by default in CI; can be set `false` locally to skip strict contract tests)

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

### Proposal Persistence and Lifecycle Endpoints

* `POST /rebalance/proposals`: create persisted proposal aggregate + immutable version, idempotent by `Idempotency-Key` and canonical request hash.
* `GET /rebalance/proposals/{proposal_id}`: read proposal + current version (`include_evidence` query supported).
* `GET /rebalance/proposals`: list proposals with filters and cursor pagination.
* `GET /rebalance/proposals/{proposal_id}/versions/{version_no}`: read specific immutable version.
* `POST /rebalance/proposals/{proposal_id}/versions`: create version `N+1` by rerunning simulation+artifact.
* `POST /rebalance/proposals/{proposal_id}/transitions`: apply workflow transition with optimistic `expected_state`.
* `POST /rebalance/proposals/{proposal_id}/approvals`: record structured approval/consent and workflow event.

Lifecycle runtime configuration (environment variables):
* `PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED` (`true` by default)
* `PROPOSAL_STORE_EVIDENCE_BUNDLE` (`true` by default)
* `PROPOSAL_REQUIRE_EXPECTED_STATE` (`true` by default)
* `PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION` (`false` by default)
* `PROPOSAL_REQUIRE_SIMULATION_FLAG` (`true` by default)

---

## 🧪 Regression Testing (Golden Scenarios)

We maintain a set of "Gold Standard" inputs and outputs in `tests/dpm/golden_data/` and
`tests/advisory/golden_data/`. These ensure that complex math never changes unexpectedly.

Solver-mode golden scenarios (RFC-0012):
* `tests/dpm/golden_data/scenario_12_solver_conflict.json`
* `tests/dpm/golden_data/scenario_12_solver_infeasible.json`

**To Regenerate Golden Files:**
(Only do this if you have intentionally changed the business logic via an RFC).

```bash
python update_goldens.py

```
