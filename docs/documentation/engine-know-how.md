# Rebalance Engine Know-How

This guide documents the current implementation under `src/core` and `src/api`.

## 1. Contract and Philosophy

- The API endpoint is `POST /rebalance/simulate` in `src/api/main.py`.
- `Idempotency-Key` header is required by FastAPI validation (missing header returns `422`).
- Domain outcomes are returned in `RebalanceResult.status`:
  - `READY`
  - `PENDING_REVIEW`
  - `BLOCKED`
- The engine is stateless for calculation: it computes from request payload only.

Important implementation note:
- The engine does not currently persist or replay idempotency keys. The key is passed into `lineage.request_hash`.

## 2. Request Shape (What You Must Send)

`RebalanceRequest` requires:
- `portfolio_snapshot`
- `market_data_snapshot`
- `model_portfolio`
- `shelf_entries`
- `options`

Core model locations:
- Request/response models: `src/core/models.py`
- API request wrapper: `src/api/main.py`

## 3. 5-Stage Execution Pipeline

The orchestration entrypoint is `run_simulation(...)` in `src/core/engine.py`.

### Stage 1: Valuation

Function: `build_simulated_state(...)` (`src/core/valuation.py`)

- Values positions and cash in `portfolio_snapshot.base_currency`.
- Supports:
  - `ValuationMode.CALCULATED`: `quantity * market price`
  - `ValuationMode.TRUST_SNAPSHOT`: uses `position.market_value` when provided
- Logs data quality issues:
  - `price_missing`
  - `fx_missing`

### Stage 2: Universe Build

Function: `_build_universe(...)`

- Intersects model targets with shelf permissions.
- Shelf behavior:
  - `APPROVED`: buy/sell eligible
  - `RESTRICTED`: excluded unless `options.allow_restricted=True`
  - `SELL_ONLY`: target forced to zero for buys; weight tracked as redistribution excess
  - `BANNED` / `SUSPENDED`: excluded
- Existing holdings not in model are handled explicitly:
  - Missing shelf entry -> `LOCKED_DUE_TO_MISSING_SHELF`
  - `SUSPENDED` / `BANNED` / `RESTRICTED` -> locked by status
  - Otherwise included with target 0 for sell-down path

### Stage 3: Target Generation and Constraints

Function: `_generate_targets(...)`

- Redistributes sell-only excess into buy-eligible targets when possible.
- Normalizes if effective target sum exceeds 100%.
- Applies optional constraints:
  - `single_position_max_weight`
  - `min_cash_buffer_pct`
- Builds target trace (`TargetInstrument`) with tags such as:
  - `CAPPED_BY_MAX_WEIGHT`
  - `REDISTRIBUTED_RECIPIENT`
  - `IMPLICIT_SELL_TO_ZERO`
  - `LOCKED_POSITION`
- Can set stage status to `PENDING_REVIEW` when constraints cannot be fully satisfied.

### Stage 4: Intent Generation

Function: `_generate_intents(...)`

- Converts target drift into `SECURITY_TRADE` intents.
- Quantity is integer floored from notional/price.
- Looks up threshold from:
  - `options.min_trade_notional`, else
  - `shelf_entry.min_notional`
- If `options.suppress_dust_trades=True` and below threshold:
  - no trade intent is emitted
  - a `SuppressedIntent` is added to diagnostics

### Stage 5: FX, Simulation, Rules, Reconciliation

Function: `_generate_fx_and_simulate(...)`

- Projects post-trade cash balances by currency.
- Creates `FX_SPOT` intents for:
  - funding deficits (`FUNDING`)
  - sweeping positive non-base balances (`SWEEP`)
- Adds dependencies from buy security intents to funding FX intents (and same-currency sell dependencies).
- Applies intents to a simulated portfolio state.
- Runs post-trade rule engine: `RuleEngine.evaluate(...)` (`src/core/compliance.py`).
- Performs value reconciliation:
  - tolerance = `0.5 + before_total * 0.0005`
  - mismatch adds hard rule `RECONCILIATION` with reason `VALUE_MISMATCH`

## 4. Worked Examples

These examples are aligned with current behavior in `src/core/engine.py`.

### Example A: Valuation in Base Currency (Stage 1)

- Base currency: `SGD`
- Position: `AAPL`, quantity `10`
- Price: `150 USD`
- FX: `USD/SGD = 1.35`

Result:
- Instrument value = `10 * 150 = 1500 USD`
- Base value = `1500 * 1.35 = 2025 SGD`

### Example B: `SELL_ONLY` Target Redistribution (Stages 2-3)

- Model targets:
  - `FUND_A = 0.60` (`SELL_ONLY`)
  - `FUND_B = 0.40` (`APPROVED`)
- `FUND_A` cannot be bought, so target weight for buy path becomes `0`.
- Excess `0.60` is redistributed to buy-eligible targets.

Result:
- `FUND_B` final weight moves toward `1.00` (subject to caps/buffers).
- Stage status can become `PENDING_REVIEW` if constraints cannot absorb excess cleanly.

### Example C: Single Position Cap (Stage 3)

- Model targets:
  - `EQ_A = 0.80`
  - `EQ_B = 0.20`
- Option: `single_position_max_weight = 0.30`

Result:
- `EQ_A` capped to `0.30` with tag `CAPPED_BY_MAX_WEIGHT`.
- Overflow redistributes to other eligible assets where possible.
- If overflow cannot be fully placed, run status trends to `PENDING_REVIEW`.

### Example D: Dust Suppression (Stage 4)

- Intended trade notional: `100 USD`
- Threshold: `min_trade_notional = 500 USD`
- `suppress_dust_trades = true`

Result:
- No `SECURITY_TRADE` intent emitted.
- Diagnostics includes one `SuppressedIntent` with reason `BELOW_MIN_NOTIONAL`.

### Example E: FX Funding and Dependencies (Stage 5)

- Buy intent requires `EUR`, but projected `EUR` cash is negative.
- Engine creates `FX_SPOT` with rationale code `FUNDING`.
- Buy security intent includes dependency on that FX intent.

Result:
- Intent ordering is sell trades, then FX, then buy trades.
- Prevents unfunded buy execution in the simulated sequence.

### Example F: Blocking Data Quality

- Target instrument has no price.
- `block_on_missing_prices = true` (default).

Result:
- Status becomes `BLOCKED`.
- Diagnostics shows `data_quality.price_missing`.

Reference payloads:
- Request example: `docs/sample_request.json`
- Response example: `docs/sample_response.json`

## 5. Status Semantics

`READY`
- No hard-rule failures and no stage-level pending conditions.

`PENDING_REVIEW`
- No hard-rule failures, but at least one soft fail or stage-3 pending condition exists.

`BLOCKED`
- Triggered by hard failures, including:
  - blocking data quality (`price_missing`, `fx_missing`, `shelf_missing` under relevant options)
  - rule failures like `NO_SHORTING`, `INSUFFICIENT_CASH`, `DATA_QUALITY`
  - reconciliation mismatch

## 6. Post-Trade Rules (Current Set)

From `src/core/compliance.py`:
- `CASH_BAND` (SOFT)
- `SINGLE_POSITION_MAX` (HARD)
- `DATA_QUALITY` (HARD)
- `MIN_TRADE_SIZE` (SOFT informational/pass-style signal)
- `NO_SHORTING` (HARD)
- `INSUFFICIENT_CASH` (HARD)

## 7. Diagnostics and Auditability

`RebalanceResult` contains:
- `before` and `after_simulated` states
- `universe` eligibility/exclusions
- `target` trace (`model_weight -> final_weight`)
- `intents` with dependencies
- `rule_results`
- `diagnostics`:
  - `warnings`
  - `suppressed_intents`
  - `data_quality`
- `lineage`

Current implementation details:
- `lineage.portfolio_snapshot_id` comes from input `portfolio_snapshot.portfolio_id`.
- `lineage.market_data_snapshot_id` is currently fixed to `"md"`.
- `correlation_id` in response is currently fixed to `"c_none"` (request header is logged but not propagated).

## 8. Key Engine Options

Defined in `EngineOptions` (`src/core/models.py`):

- `valuation_mode`
- `cash_band_min_weight`
- `cash_band_max_weight`
- `single_position_max_weight`
- `min_trade_notional`
- `allow_restricted`
- `suppress_dust_trades`
- `dust_trade_threshold` (present in model; currently not used in engine logic)
- `fx_buffer_pct`
- `block_on_missing_prices`
- `block_on_missing_fx`
- `min_cash_buffer_pct`

## 9. Practical Notes for Maintainers

- If docs or examples show behavior not listed here, verify against:
  - `src/core/engine.py`
  - `src/core/valuation.py`
  - `src/core/compliance.py`
  - `tests/engine/*` and `tests/api/*`
- For scenario-based regression, use golden tests under `tests/golden_data/`.
