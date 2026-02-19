# Advisory Proposal Engine Know-How

Implementation scope:
- API: `src/api/main.py` (`/rebalance/proposals/simulate`)
- Models: `src/core/models.py`
- Core orchestration: `src/core/advisory_engine.py` (`run_proposal_simulation`)
- Shared simulation primitives: `src/core/common/simulation_shared.py`
- Valuation: `src/core/valuation.py`
- Rules: `src/core/compliance.py`

## API Surface

### `POST /rebalance/proposals/simulate`
- Purpose: simulate advisor-entered manual cash flows and manual security trades.
- Required header: `Idempotency-Key`
- Optional header: `X-Correlation-Id` (generated when missing)
- Output: `ProposalResult` with status `READY | PENDING_REVIEW | BLOCKED`
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
- Deterministic ordering:
  - `CASH_FLOW` (as provided)
  - `SECURITY_TRADE` SELL (instrument ascending)
  - `SECURITY_TRADE` BUY (instrument ascending)

4. Safety and shelf guards
- Blocks on withdrawal-driven negative cash when enabled (`proposal_block_negative_cash`).
- Blocks disallowed BUY trades (`SELL_ONLY`, `BANNED`, `SUSPENDED`, and `RESTRICTED` unless `allow_restricted=true`).

5. After-state, rules, reconciliation
- Simulates portfolio mutation using shared primitives.
- Runs standard rule engine (`RuleEngine.evaluate`).
- Performs proposal reconciliation against expected cash-flow-adjusted total.

## Advisory Feature Flags

- `enable_proposal_simulation`
- `proposal_apply_cash_flows_first`
- `proposal_block_negative_cash`
- plus shared controls:
  - `block_on_missing_prices`
  - `block_on_missing_fx`
  - `allow_restricted`
  - cash-band options (affect final status via rule engine)

## Proposal-Specific Diagnostics/Outcomes

- `PROPOSAL_WITHDRAWAL_NEGATIVE_CASH`
- `PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF`
- standard safety/data-quality rules continue to apply (`NO_SHORTING`, `INSUFFICIENT_CASH`, etc.)

## Tests That Lock Advisory Behavior

- API: `tests/advisory/api/test_api_advisory_proposal_simulate.py`
- Contract: `tests/advisory/contracts/test_contract_advisory_models.py`
- Engine: `tests/advisory/engine/test_engine_advisory_proposal_simulation.py`
- Proposal golden: `tests/advisory/golden/test_golden_advisory_proposal_scenarios.py`
