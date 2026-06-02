# Lotus Advise Quality Baseline Report

- Generated At: `2026-06-02T00:22:51.569698+00:00`
- Branch: `advise-enterprise-hardening-slice-15`
- Head: `061e951b3e174be45cad03b6f4e72074bb41cc74`
- Branch Commits Over Main: `3`
- CI Phase: `baseline/report-only`

## Code Size

- Python files: `759`
- Packages: `37`
- Modules: `722`
- Total Python lines: `130203`

## Largest Files

| Rank | File | Lines |
| ---: | --- | ---: |
| 1 | `scripts/validate_cross_service_parity_live.py` | 4010 |
| 2 | `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` | 3859 |
| 3 | `tests/unit/advisory/api/test_api_workspace.py` | 2536 |
| 4 | `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` | 2368 |
| 5 | `tests/unit/advisory/api/test_lotus_core_stateful_context.py` | 1870 |
| 6 | `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py` | 1731 |
| 7 | `tests/unit/advisory/engine/test_advisory_copilot_persistence.py` | 1570 |
| 8 | `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` | 1447 |
| 9 | `tests/unit/advisory/engine/test_engine_advisory_copilot_foundation.py` | 1181 |
| 10 | `tests/integration/advisory/api/test_proposal_api_workflow_integration.py` | 1173 |

## Largest Functions And Maintainability Hotspots

| Rank | Function | File | Line | Lines |
| ---: | --- | --- | ---: | ---: |
| 1 | `execute` | `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` | 56 | 478 |
| 2 | `test_lifecycle_async_and_support_schemas_have_descriptions_and_examples` | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | 62 | 332 |
| 3 | `_build_sections` | `src/core/proposals/memo_builder.py` | 122 | 300 |
| 4 | `build_default_supported_claim_register` | `src/core/bank_demo_proof/supported_claim_register.py` | 18 | 294 |
| 5 | `validate_live_cross_service_parity` | `scripts/validate_cross_service_parity_live.py` | 3695 | 274 |
| 6 | `_assert_persisted_read_surfaces` | `scripts/validate_cross_service_parity_live.py` | 3422 | 271 |
| 7 | `_assert_live_policy_evaluation_flow` | `scripts/validate_cross_service_parity_live.py` | 2491 | 252 |
| 8 | `_assert_lifecycle_and_delivery_flow` | `scripts/validate_cross_service_parity_live.py` | 1788 | 249 |
| 9 | `build_feature_capabilities` | `src/api/capabilities/feature_catalog.py` | 20 | 238 |
| 10 | `_validate_live_proposal_alternatives_paths` | `scripts/validate_cross_service_parity_live.py` | 608 | 230 |

## Complexity

- Current baseline uses largest-function and router-hotspot evidence as deterministic
  complexity proxies.
- `radon` and `xenon` are tracked as report-only follow-up tools until installed and
  calibrated against current Lotus Advise behavior.

## Lint And Type Issues

- Ruff configured: `True`
- Mypy configured: `True`
- Current enforcement remains repo-native through `make lint` and `make typecheck`.

## Coverage

- Unit/integration/E2E coverage gate is repo-native through `make coverage-combined`.
- Configured fail-under target: `97`.

## Dead Code

- `vulture` is tracked as report-only pending installation and allowlist calibration.
- Current dead-code cleanup remains code-led through review-ledger slices.

## Dependencies

- Dependency verification configured: `True`
- Security audit configured: `True`
- Available dependency/security tools: `ruff, mypy, pytest, coverage.py, pip-audit, radon, xenon, vulture, deptry, bandit, interrogate`
- Pending optional tools: ``

## Security

- `pip-audit` is present in development requirements.
- `bandit` config is present in `pyproject.toml` for report-only rollout.
- Sensitive-data handling remains governed by API error redaction and structured
  payload tests until the security report gate is calibrated.

## OpenAPI Gaps

- Repo-native OpenAPI gate configured: `True`
- Spectral rules present: `True`
- Spectral is report-only until Node/Spectral execution is added to CI.

## Architecture Violations

- Import-linter contracts present: `True`
- Contracts are report-only until import-linter is installed and current violations
  are baselined.

## Documentation Gaps

- Requested docs present: `docs/architecture.md, docs/api-governance.md, docs/observability.md, docs/security.md, docs/operations-runbook.md, docs/supported-features.md`
- Requested docs missing: `none`

## Observability Gaps

- Observability documentation and service-level diagnostics are tracked as baseline
  gaps until `docs/observability.md` and operational diagnostics gates are added.
