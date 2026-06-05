# Lotus Advise Engineering Health Baseline

- Generated At: `2026-06-05T00:03:56.315215+00:00`
- Branch: `harden/quality-gate-calibration`
- Head: `f1077260281518ecdf42f7e21fd17c94942842b5`
- Python Files: `918`
- Packages: `38`
- Modules: `880`
- Total Python Lines: `138796`

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
| 11 | `scripts/quality_baseline_report.py` | 1015 |
| 12 | `tests/unit/advisory/engine/test_engine_advisory_proposal_simulation.py` | 975 |
| 13 | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | 862 |
| 14 | `tests/unit/advisory/api/test_api_advisory_copilot.py` | 830 |
| 15 | `tests/unit/advisory/engine/test_advisory_copilot_application.py` | 817 |
| 16 | `tests/unit/advisory/api/test_api_integration_capabilities.py` | 812 |
| 17 | `tests/unit/advisory/engine/test_engine_proposal_alternatives.py` | 787 |
| 18 | `tests/unit/advisory/api/test_api_internal_guards.py` | 752 |
| 19 | `tests/unit/advisory/contracts/test_contract_workspace_models.py` | 727 |
| 20 | `tests/unit/shared/contracts/test_contract_models.py` | 721 |

## Largest Functions

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
| 10 | `render_baseline_report` | `scripts/quality_baseline_report.py` | 488 | 221 |
| 11 | `render_refactor_health_report` | `scripts/quality_baseline_report.py` | 711 | 209 |
| 12 | `test_proof_pack_indexes_assets_and_blocks_sensitive_committed_material` | `tests/unit/advisory/engine/test_engine_bank_demo_proof_models.py` | 370 | 200 |
| 13 | `_live_runtime_payload` | `tests/unit/advisory/engine/test_engine_bank_demo_proof_capture.py` | 23 | 187 |
| 14 | `test_openapi_enrichment_adds_operation_docs_tags_errors_and_schema_examples` | `tests/unit/advisory/api/test_openapi_enrichment.py` | 6 | 179 |
| 15 | `test_lifecycle_endpoints_use_separate_request_and_response_objects` | `tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py` | 396 | 178 |
| 16 | `_assert_live_proposal_narrative_flow` | `scripts/validate_cross_service_parity_live.py` | 2053 | 174 |
| 17 | `_assert_workspace_flow` | `scripts/validate_cross_service_parity_live.py` | 3052 | 173 |
| 18 | `_assert_mixed_approval_routes_remain_version_scoped` | `scripts/validate_cross_service_parity_live.py` | 1616 | 170 |
| 19 | `test_live_postgres_proposal_repository_parity_contract` | `tests/integration/advisory/engine/test_engine_proposal_repository_postgres_integration.py` | 38 | 169 |
| 20 | `test_copilot_evidence_packet_model_normalizes_and_bounds_audit_fields` | `tests/unit/advisory/engine/test_engine_advisory_copilot_foundation.py` | 823 | 168 |

## Router Hotspots

| Rank | Router File | Route Decorators | Lines |
| ---: | --- | ---: | ---: |
| 1 | `src/api/proposals/routes_lifecycle.py` | 10 | 319 |
| 2 | `src/api/workspaces/routes_session.py` | 9 | 244 |
| 3 | `src/api/proposals/routes_advisory_copilot.py` | 8 | 260 |
| 4 | `src/api/proposals/routes_advisor_cockpit.py` | 6 | 230 |
| 5 | `src/api/proposals/routes_delivery.py` | 6 | 156 |
| 6 | `src/api/proposals/routes_support.py` | 6 | 147 |
| 7 | `src/api/proposals/routes_policy_evaluation_reads.py` | 5 | 155 |
| 8 | `src/api/proposals/routes_policy_packs.py` | 4 | 143 |
| 9 | `src/api/proposals/routes_memo_reads.py` | 4 | 139 |
| 10 | `src/api/proposals/routes_async.py` | 4 | 124 |
| 11 | `tests/unit/advisory/api/test_api_internal_guards.py` | 3 | 752 |
| 12 | `src/api/proposals/routes_memo_commands.py` | 3 | 141 |
| 13 | `src/api/routers/bank_demo_proof.py` | 3 | 94 |
| 14 | `src/api/proposals/routes_memo_packages.py` | 2 | 107 |
| 15 | `src/api/proposals/routes_policy_evaluation_commands.py` | 2 | 100 |
| 16 | `src/api/proposals/routes_policy_evaluation_packages.py` | 2 | 97 |
| 17 | `src/api/routers/advisory_simulation.py` | 2 | 90 |
| 18 | `src/api/proposals/routes_policy_evaluation_workflow.py` | 2 | 79 |
| 19 | `src/api/workspaces/routes_assistant.py` | 2 | 69 |
| 20 | `src/api/workspaces/routes_handoff.py` | 1 | 70 |

## Repo-Native Gate Inventory

| Make Target | Command |
| --- | --- |
| `test-unit` | `python -m pytest tests/unit` |
| `test-integration` | `python -m pytest tests/integration` |
| `test-e2e` | `python -m pytest tests/e2e` |
| `typecheck` | `python -m mypy --config-file mypy.ini` |
| `openapi-gate` | `python scripts/openapi_quality_gate.py` |
| `openapi-gate` | `python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py -q` |
| `openapi-gate` | `$(MAKE) openapi-spectral-report` |
| `no-alias-gate` | `python scripts/no_alias_contract_guard.py` |
| `api-vocabulary-gate` | `python scripts/api_vocabulary_inventory.py` |
| `api-vocabulary-gate` | `python scripts/api_vocabulary_inventory.py --validate-only` |
| `domain-data-products-gate` | `python scripts/validate_domain_data_product_declarations.py` |
| `quality-baseline` | `python scripts/quality_baseline_report.py --output-dir quality` |
| `lint` | `python -m ruff check .` |
| `lint` | `python -m ruff format --check .` |
| `lint` | `$(MAKE) monetary-float-guard` |
| `lint` | `$(MAKE) architecture-boundaries` |
| `lint` | `$(MAKE) complexity-regression-gate` |
| `verify-dependencies` | `python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct --skip-audit` |
| `security-audit` | `python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct` |
| `security-audit` | `$(MAKE) bandit-high-severity-gate` |
| `coverage-combined` | `COVERAGE_FILE=.coverage.unit python -m pytest tests/unit --cov=src --cov-report=` |
| `coverage-combined` | `COVERAGE_FILE=.coverage.integration python -m pytest tests/integration --cov=src --cov-report=` |
| `coverage-combined` | `COVERAGE_FILE=.coverage.e2e python -m pytest tests/e2e --cov=src --cov-report=` |
| `coverage-combined` | `python -m coverage combine .coverage.unit .coverage.integration .coverage.e2e` |
| `coverage-combined` | `python -m coverage report --fail-under=97` |

## Interpretation

- This baseline captures deterministic structural metrics from the current branch.
- Use `--format json` to save a phase snapshot and `--compare-to <snapshot.json>`
  to render structural metric deltas in later refactoring phases.
- External scanner inventories should move from measurement to repo-native gates in
  calibrated slices; coverage, import-linter, Spectral, Bandit high severity,
  and Radon E/F-ranked complexity now have enforced paths while vulture, deptry,
  interrogate, and stricter complexity thresholds remain measured backlog.
