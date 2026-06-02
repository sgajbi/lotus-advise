# Lotus Advise Engineering Health Baseline

- Generated At: `2026-06-01T23:53:06.600264+00:00`
- Branch: `advise-enterprise-hardening-slice-14`
- Head: `acc4e3bf23f3792b72b838659861471837b8bf3a`
- Python Files: `753`
- Packages: `37`
- Modules: `716`
- Total Python Lines: `129665`

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
| 11 | `tests/unit/advisory/engine/test_engine_advisory_proposal_simulation.py` | 972 |
| 12 | `src/core/proposals/memo_api.py` | 884 |
| 13 | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | 860 |
| 14 | `src/core/advisory/alternatives_strategies.py` | 859 |
| 15 | `tests/unit/advisory/api/test_api_advisory_copilot.py` | 829 |
| 16 | `tests/unit/advisory/engine/test_advisory_copilot_application.py` | 817 |
| 17 | `tests/unit/advisory/api/test_api_integration_capabilities.py` | 812 |
| 18 | `src/core/common/suitability.py` | 739 |
| 19 | `tests/unit/advisory/engine/test_engine_proposal_alternatives.py` | 733 |
| 20 | `tests/unit/advisory/contracts/test_contract_workspace_models.py` | 727 |

## Largest Functions

| Rank | Function | File | Line | Lines |
| ---: | --- | --- | ---: | ---: |
| 1 | `execute` | `tests/unit/advisory/engine/test_engine_proposal_repository_postgres.py` | 56 | 478 |
| 2 | `test_lifecycle_async_and_support_schemas_have_descriptions_and_examples` | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | 62 | 332 |
| 3 | `_build_sections` | `src/core/proposals/memo_builder.py` | 122 | 300 |
| 4 | `build_default_supported_claim_register` | `src/core/bank_demo_proof/supported_claim_register.py` | 18 | 294 |
| 5 | `run_proposal_simulation` | `src/core/advisory_engine.py` | 39 | 283 |
| 6 | `validate_live_cross_service_parity` | `scripts/validate_cross_service_parity_live.py` | 3695 | 274 |
| 7 | `_assert_persisted_read_surfaces` | `scripts/validate_cross_service_parity_live.py` | 3422 | 271 |
| 8 | `_assert_live_policy_evaluation_flow` | `scripts/validate_cross_service_parity_live.py` | 2491 | 252 |
| 9 | `_assert_lifecycle_and_delivery_flow` | `scripts/validate_cross_service_parity_live.py` | 1788 | 249 |
| 10 | `build_feature_capabilities` | `src/api/capabilities/feature_catalog.py` | 20 | 238 |
| 11 | `_validate_live_proposal_alternatives_paths` | `scripts/validate_cross_service_parity_live.py` | 608 | 230 |
| 12 | `_assert_live_proposal_memo_flow` | `scripts/validate_cross_service_parity_live.py` | 2261 | 228 |
| 13 | `test_resolve_stateful_context_with_lotus_core_builds_simulation_request` | `tests/unit/advisory/api/test_lotus_core_stateful_context.py` | 635 | 225 |
| 14 | `test_proof_pack_indexes_assets_and_blocks_sensitive_committed_material` | `tests/unit/advisory/engine/test_engine_bank_demo_proof_models.py` | 370 | 200 |
| 15 | `evaluate` | `src/core/compliance.py` | 22 | 199 |
| 16 | `build_memo_source_readiness` | `src/core/proposals/memo_source_readiness.py` | 19 | 195 |
| 17 | `build_workflow_capabilities` | `src/api/capabilities/workflow_catalog.py` | 20 | 187 |
| 18 | `_live_runtime_payload` | `tests/unit/advisory/engine/test_engine_bank_demo_proof_capture.py` | 23 | 187 |
| 19 | `test_lifecycle_endpoints_use_separate_request_and_response_objects` | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | 396 | 178 |
| 20 | `_assert_live_proposal_narrative_flow` | `scripts/validate_cross_service_parity_live.py` | 2053 | 174 |

## Router Hotspots

| Rank | Router File | Route Decorators | Lines |
| ---: | --- | ---: | ---: |
| 1 | `src/api/workspaces/router.py` | 12 | 363 |
| 2 | `src/api/proposals/routes_policy_evaluations.py` | 11 | 364 |
| 3 | `src/api/proposals/routes_lifecycle.py` | 10 | 319 |
| 4 | `src/api/proposals/routes_memo.py` | 9 | 338 |
| 5 | `src/api/proposals/routes_advisory_copilot.py` | 8 | 260 |
| 6 | `src/api/proposals/routes_advisor_cockpit.py` | 6 | 230 |
| 7 | `src/api/proposals/routes_delivery.py` | 6 | 156 |
| 8 | `src/api/proposals/routes_support.py` | 6 | 147 |
| 9 | `src/api/proposals/routes_policy_packs.py` | 4 | 143 |
| 10 | `src/api/proposals/routes_async.py` | 4 | 124 |
| 11 | `src/api/routers/bank_demo_proof.py` | 3 | 94 |
| 12 | `src/api/routers/advisory_simulation.py` | 2 | 90 |
| 13 | `src/api/routers/tactical_house_view.py` | 1 | 38 |
| 14 | `src/api/routers/integration_capabilities.py` | 1 | 33 |

## Repo-Native Gate Inventory

| Make Target | Command |
| --- | --- |
| `test-unit` | `python -m pytest tests/unit` |
| `test-integration` | `python -m pytest tests/integration` |
| `test-e2e` | `python -m pytest tests/e2e` |
| `typecheck` | `python -m mypy --config-file mypy.ini` |
| `openapi-gate` | `python scripts/openapi_quality_gate.py` |
| `openapi-gate` | `python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py -q` |
| `no-alias-gate` | `python scripts/no_alias_contract_guard.py` |
| `api-vocabulary-gate` | `python scripts/api_vocabulary_inventory.py` |
| `api-vocabulary-gate` | `python scripts/api_vocabulary_inventory.py --validate-only` |
| `domain-data-products-gate` | `python scripts/validate_domain_data_product_declarations.py` |
| `quality-baseline` | `python scripts/quality_baseline_report.py --output-dir quality` |
| `lint` | `python -m ruff check .` |
| `lint` | `python -m ruff format --check .` |
| `lint` | `$(MAKE) monetary-float-guard` |
| `verify-dependencies` | `python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct --skip-audit` |
| `security-audit` | `python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct` |
| `coverage-combined` | `COVERAGE_FILE=.coverage.unit python -m pytest tests/unit --cov=src --cov-report=` |
| `coverage-combined` | `COVERAGE_FILE=.coverage.integration python -m pytest tests/integration --cov=src --cov-report=` |
| `coverage-combined` | `COVERAGE_FILE=.coverage.e2e python -m pytest tests/e2e --cov=src --cov-report=` |
| `coverage-combined` | `python -m coverage combine .coverage.unit .coverage.integration .coverage.e2e` |
| `coverage-combined` | `python -m coverage report --fail-under=97` |

## Interpretation

- This baseline captures deterministic structural metrics from the current branch.
- Use `--format json` to save a phase snapshot and `--compare-to <snapshot.json>`
  to render structural metric deltas in later refactoring phases.
- External scanners such as coverage, radon, vulture, deptry, bandit, pip-audit,
  Spectral, import-linter, and interrogate should be added as follow-up CI phases
  when their repo-native configuration is introduced.
