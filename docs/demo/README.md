# Lotus Advise Demo Scenarios

This folder contains advisory-only demo payloads for the Lotus Advise service.

Canonical local service identity:
- `http://advise.dev.lotus`

## Running Scenarios

For advisory proposal simulation demos, POST to `/advisory/proposals/simulate`:

```bash
curl -X POST "http://advise.dev.lotus/advisory/proposals/simulate" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-proposal-01" \
  --data-binary "@docs/demo/10_advisory_proposal_simulate.json"
```

For advisory proposal artifact demos, POST to `/advisory/proposals/artifact`:

```bash
curl -X POST "http://advise.dev.lotus/advisory/proposals/artifact" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-proposal-artifact-01" \
  --data-binary "@docs/demo/19_advisory_proposal_artifact.json"
```

For advisory proposal lifecycle creation demos, POST to `/advisory/proposals`:

```bash
curl -X POST "http://advise.dev.lotus/advisory/proposals" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-proposal-persist-01" \
  --data-binary "@docs/demo/20_advisory_proposal_persist_create.json"
```

## Scenario Index

| File | Scenario | Expected Status | Key Feature |
| --- | --- | --- | --- |
| `10_advisory_proposal_simulate.json` | Advisory Proposal Simulation | `READY` | Simulates manual cash flows and manual trades in `/advisory/proposals/simulate`. |
| `11_advisory_auto_funding_single_ccy.json` | Advisory Auto-Funding (Single CCY) | `READY` | Generates funding `FX_SPOT` and links BUY dependency. |
| `12_advisory_partial_funding.json` | Advisory Partial Funding | `READY` | Uses existing foreign cash first, then tops up with FX. |
| `13_advisory_missing_fx_blocked.json` | Advisory Missing FX (Blocked) | `BLOCKED` | Blocks advisory proposal when required FX funding pair is missing. |
| `14_advisory_drift_asset_class.json` | Advisory Drift Analytics (Asset Class) | `READY` | Returns `drift_analysis.asset_class` against inline `reference_model`. |
| `15_advisory_drift_instrument.json` | Advisory Drift Analytics (Instrument) | `READY` | Returns both asset-class and instrument drift with unmodeled exposures. |
| `16_advisory_suitability_resolved_single_position.json` | Suitability Resolved Concentration | `READY` | Returns a resolved single-position issue after proposal trades. |
| `17_advisory_suitability_new_issuer_breach.json` | Suitability New Issuer Breach | `READY` | Returns a new high-severity issuer concentration issue and gate recommendation. |
| `18_advisory_suitability_sell_only_violation.json` | Suitability Sell-Only Violation | `BLOCKED` | Returns a governance issue when proposal attempts BUY in `SELL_ONLY`. |
| `19_advisory_proposal_artifact.json` | Advisory Proposal Artifact | `READY` | Returns a deterministic proposal package with evidence bundle and hash. |
| `20_advisory_proposal_persist_create.json` | Proposal Persist Create | `DRAFT` lifecycle state | Creates persisted proposal aggregate and immutable version via `/advisory/proposals`. |
| `21_advisory_proposal_new_version.json` | Proposal New Version | `DRAFT` lifecycle state | Creates immutable version `N+1` via `/advisory/proposals/{proposal_id}/versions`. |
| `22_advisory_proposal_transition_to_compliance.json` | Proposal Transition | `COMPLIANCE_REVIEW` lifecycle state | Transitions proposal workflow using optimistic `expected_state`. |
| `23_advisory_proposal_approval_client_consent.json` | Proposal Consent Approval | `EXECUTION_READY` lifecycle state | Records structured client consent and emits workflow event. |
| `24_advisory_proposal_approval_compliance.json` | Proposal Compliance Approval | `AWAITING_CLIENT_CONSENT` lifecycle state | Records compliance approval and advances lifecycle. |
| `25_advisory_proposal_transition_executed.json` | Proposal Execution Transition | `EXECUTED` lifecycle state | Records execution confirmation transition from execution-ready state. |

## Feature Toggles Demonstrated

- `10_advisory_proposal_simulate.json`
  `options.enable_proposal_simulation=true`, `options.proposal_apply_cash_flows_first=true`, `options.proposal_block_negative_cash=true`
- `11_advisory_auto_funding_single_ccy.json`
  `options.auto_funding=true`, `options.funding_mode=AUTO_FX`, `options.fx_generation_policy=ONE_FX_PER_CCY`
- `13_advisory_missing_fx_blocked.json`
  `options.block_on_missing_fx=true`
- `14_advisory_drift_asset_class.json`
  `options.enable_drift_analytics=true`
- `15_advisory_drift_instrument.json`
  `options.enable_instrument_drift=true`
- `16_advisory_suitability_resolved_single_position.json`
  `options.enable_suitability_scanner=true`

