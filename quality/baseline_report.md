# Lotus Advise Quality Baseline Report

- Generated At: `2026-06-04T16:30:44.719934+00:00`
- Branch: `harden/quality-gate-calibration`
- Head: `71d3c201ef071a27092f28621fd5d859ec09c823`
- Branch Commits Over Main: `9`
- CI Phase: `baseline/report-only`

## Code Size

- Python files: `914`
- Packages: `38`
- Modules: `876`
- Total Python lines: `137599`

## Largest Files

| Rank | File | Lines |
| ---: | --- | ---: |
| 1 | `scripts/validate_cross_service_parity_live.py` | 4010 |
| 2 | `tests/unit/advisory/api/test_api_advisory_proposal_lifecycle.py` | 3861 |
| 3 | `tests/unit/advisory/engine/test_engine_proposal_workflow_service.py` | 2566 |
| 4 | `tests/unit/advisory/api/test_api_workspace.py` | 2538 |
| 5 | `tests/unit/advisory/api/test_lotus_core_stateful_context.py` | 1870 |
| 6 | `tests/unit/advisory/api/test_api_advisory_proposal_simulate.py` | 1731 |
| 7 | `tests/unit/advisory/engine/test_advisory_copilot_persistence.py` | 1591 |
| 8 | `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` | 1447 |
| 9 | `tests/unit/advisory/engine/test_engine_advisory_copilot_foundation.py` | 1181 |
| 10 | `tests/integration/advisory/api/test_proposal_api_workflow_integration.py` | 1173 |

## Largest Functions And Maintainability Hotspots

| Rank | Function | File | Line | Lines |
| ---: | --- | --- | ---: | ---: |
| 1 | `execute` | `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` | 56 | 478 |
| 2 | `test_lifecycle_async_and_support_schemas_have_descriptions_and_examples` | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | 62 | 332 |
| 3 | `validate_live_cross_service_parity` | `scripts/validate_cross_service_parity_live.py` | 3695 | 274 |
| 4 | `_assert_persisted_read_surfaces` | `scripts/validate_cross_service_parity_live.py` | 3422 | 271 |
| 5 | `_assert_live_policy_evaluation_flow` | `scripts/validate_cross_service_parity_live.py` | 2491 | 252 |
| 6 | `_assert_lifecycle_and_delivery_flow` | `scripts/validate_cross_service_parity_live.py` | 1788 | 249 |
| 7 | `_validate_live_proposal_alternatives_paths` | `scripts/validate_cross_service_parity_live.py` | 608 | 230 |
| 8 | `_assert_live_proposal_memo_flow` | `scripts/validate_cross_service_parity_live.py` | 2261 | 228 |
| 9 | `test_resolve_stateful_context_with_lotus_core_builds_simulation_request` | `tests/unit/advisory/api/test_lotus_core_stateful_context.py` | 635 | 225 |
| 10 | `render_baseline_report` | `scripts/quality_baseline_report.py` | 488 | 216 |

## Complexity

- Current baseline uses largest-function and router-hotspot evidence as deterministic
  complexity proxies.
- Radon config executable: `True`
- Radon analyzed block inventory: `3009`
- Radon complexity rank inventory: `A=2715, B=225, C=60, D=7, E=2`
- Radon worst complexity: `rank=E, complexity=32`
- Xenon remains report-only until current Radon thresholds are classified.

## Lint And Type Issues

- Ruff configured: `True`
- Mypy configured: `True`
- Current enforcement remains repo-native through `make lint` and `make typecheck`.

## Coverage

- Unit/integration/E2E coverage gate is repo-native through `make coverage-combined`.
- Configured fail-under target: `97`.

## Dead Code

- Vulture config executable: `True`
- Vulture current issue inventory: `142`
- Vulture confidence inventory: `100%=135, 90%=7`
- Vulture remains report-only until validator false positives and compatibility
  facade imports are classified.
- Current dead-code cleanup remains code-led through review-ledger slices.

## Dependencies

- Dependency verification configured: `True`
- Security audit configured: `True`
- Available dependency/security tools: `ruff, mypy, pytest, coverage.py, pip-audit, radon, xenon, vulture, deptry, bandit, interrogate`
- Pending optional tools: ``
- Deptry config executable: `True`
- Deptry current issue inventory: `14`
- Bandit config executable: `True`
- Bandit current issue inventory: `27`
- Bandit severity inventory: `high=0, medium=26, low=1`

## Security

- `pip-audit` is present in development requirements.
- `bandit` config is present in `pyproject.toml` for report-only rollout.
- Sensitive-data handling remains governed by API error redaction and structured
  payload tests until the security report gate is calibrated.

## OpenAPI Gaps

- Repo-native OpenAPI gate configured: `True`
- Spectral rules present: `True`
- Spectral config executable: `True`
- Spectral OpenAPI path inventory: `84`
- Spectral current issue inventory: `277`
- Spectral severity inventory: `error=277`
- Spectral remains report-only until warning inventory is stable enough for
  fail-on-new-regression enforcement.

## Architecture Violations

- Import-linter contracts present: `True`
- Import-linter config executable: `True`
- Import-linter contract inventory: `total=3, kept=3, broken=0`
- Contracts remain report-only until the kept inventory is wired into a CI gate.

## Documentation Gaps

- Requested docs present: `docs/architecture.md, docs/api-governance.md, docs/observability.md, docs/security.md, docs/operations-runbook.md, docs/supported-features.md`
- Requested docs missing: `none`
- Interrogate config executable: `True`
- Interrogate docstring inventory: `total=3375, missing=3340, covered=35, coverage=1.0%`
- Interrogate remains report-only until public API and module ownership thresholds
  are classified.

## Observability Gaps

- Observability documentation is present.
- Observability diagnostics target: `make observability-diagnostics`
- Focused diagnostics currently verify correlation, request, trace,
  and structured-log propagation.
- Dashboard, alert, SLO, and distributed-tracing evidence remain tracked gaps.
