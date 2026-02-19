# Advisory Proposal Engine Know-How

Implementation scope:
- API: `src/api/main.py` (`/rebalance/proposals/simulate`)
- Models: `src/core/models.py`
- Core orchestration: `src/core/advisory_engine.py` (`run_proposal_simulation`)
- Advisory modular internals:
  - `src/core/advisory/ids.py` (deterministic run id generation)
  - `src/core/advisory/intents.py` (proposal cash/trade intent construction helpers)
  - `src/core/advisory/funding.py` (RFC-0014B auto-funding planner)
- Shared simulation primitives: `src/core/common/simulation_shared.py`
- Shared diagnostics builders: `src/core/common/diagnostics.py`
- Valuation: `src/core/valuation.py`
- Rules: `src/core/compliance.py`

## API Surface

### `POST /rebalance/proposals/simulate`
- Purpose: simulate advisor-entered manual cash flows and manual security trades.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id` (generated when missing)
- Output: `ProposalResult` with status `READY | PENDING_REVIEW | BLOCKED`
- Unhandled errors: `500` with `application/problem+json` payload.
- Idempotency behavior:
  - same key + same canonical payload: cached response
  - same key + different canonical payload: `409 Conflict`

## Pipeline (`run_proposal_simulation`)

1. Validate and gate
- Requires `options.enable_proposal_simulation=true` at API layer.
- Validates proposal input models (`ProposedCashFlow`, `ProposedTrade`).

2. Before-state valuation
- Uses the same valuation stack as DPM (`build_simulated_state`).

3. Apply proposal intents
- Cash flows can be applied before trades (`proposal_apply_cash_flows_first`).
- Trades are manually supplied and priced from market data.
- For notional-driven trades, `notional.currency` must match priced instrument currency; mismatch blocks with `PROPOSAL_INVALID_TRADE_INPUT`.
- RFC-0014B auto-funding:
  - Build funding plan per BUY currency.
  - Generate `FX_SPOT` intents for deficits using `BASE_ONLY` or `ANY_CASH` policy.
  - Apply deterministic dependencies from BUY intents to generated FX intent ids.
- Deterministic ordering:
  - `CASH_FLOW` (as provided)
  - `SECURITY_TRADE` SELL (instrument ascending)
  - `FX_SPOT` (pair ascending)
  - `SECURITY_TRADE` BUY (instrument ascending)

4. Safety and shelf guards
- Blocks on withdrawal-driven negative cash when enabled (`proposal_block_negative_cash`).
- Blocks disallowed BUY trades (`SELL_ONLY`, `BANNED`, `SUSPENDED`, and `RESTRICTED` unless `allow_restricted=true`).

5. After-state, rules, reconciliation
- Simulates portfolio mutation using shared primitives.
- Runs standard rule engine (`RuleEngine.evaluate`).
- Performs proposal reconciliation against expected cash-flow-adjusted total.
- Derives deterministic `proposal_run_id` from request hash when provided.

## Advisory Feature Flags

- `enable_proposal_simulation`
- `proposal_apply_cash_flows_first`
- `proposal_block_negative_cash`
- `enable_drift_analytics`
- `enable_instrument_drift`
- `drift_top_contributors_limit`
- `drift_unmodeled_exposure_threshold`
- `auto_funding`
- `funding_mode`
- `fx_funding_source_currency`
- `fx_generation_policy`
- plus shared controls:
  - `block_on_missing_prices`
  - `block_on_missing_fx`
  - `allow_restricted`
  - cash-band options (affect final status via rule engine)

## Proposal-Specific Diagnostics/Outcomes

- `PROPOSAL_WITHDRAWAL_NEGATIVE_CASH`
- `PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF`
- `PROPOSAL_INVALID_TRADE_INPUT`
- `PROPOSAL_MISSING_FX_FOR_FUNDING`
- `PROPOSAL_INSUFFICIENT_FUNDING_CASH`
- `REFERENCE_MODEL_BASE_CURRENCY_MISMATCH`
- `diagnostics.missing_fx_pairs`
- `diagnostics.funding_plan`
- `diagnostics.insufficient_cash`
- `drift_analysis` (when `reference_model` is provided and drift analytics is enabled)
- standard safety/data-quality rules continue to apply (`NO_SHORTING`, `INSUFFICIENT_CASH`, etc.)

## Tests That Lock Advisory Behavior

- API: `tests/advisory/api/test_api_advisory_proposal_simulate.py`
- Contract: `tests/advisory/contracts/test_contract_advisory_models.py`
- Engine: `tests/advisory/engine/test_engine_advisory_proposal_simulation.py`
- Proposal golden: `tests/advisory/golden/test_golden_advisory_proposal_scenarios.py`
