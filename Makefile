.PHONY: install install-ci check check-all test test-unit test-integration test-e2e test-all test-fast test-all-fast test-all-no-cov test-all-parallel ci ci-local ci-local-docker ci-local-docker-down typecheck lint monetary-float-guard architecture-boundaries complexity-regression-gate observability-diagnostics advisory-domain-golden-regressions demo-assurance-gate format clean run verify-dependencies check-deps check-deps-strict security-audit bandit-high-severity-gate openapi-gate openapi-spectral-report no-alias-gate api-vocabulary-gate domain-data-products-gate engineering-health engineering-health-json quality-baseline quality-baseline-check migration-smoke migration-apply coverage-combined postgres-runtime-contracts-local production-profile-guardrail-negatives-local pre-commit docker-build docker-up docker-down

install: install-ci
	python -m pre_commit install

install-ci:
	python -m pip install -r requirements.txt
	python -m pip install -r requirements-dev.txt
	python -m pip install pre-commit

pre-commit:
	python -m pre_commit run --all-files

check: lint typecheck openapi-gate no-alias-gate api-vocabulary-gate domain-data-products-gate quality-baseline-check test

ci: verify-dependencies lint typecheck openapi-gate no-alias-gate api-vocabulary-gate domain-data-products-gate quality-baseline-check migration-smoke security-audit coverage-combined docker-build postgres-runtime-contracts-local production-profile-guardrail-negatives-local

test:
	$(MAKE) test-unit

test-unit:
	python -m pytest tests/unit

test-integration:
	python -m pytest tests/integration

test-e2e:
	python -m pytest tests/e2e

test-all:
	python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=97

# Fast local loop: unit tests only (no coverage)
test-fast:
	python -m pytest tests/unit -q

# Full suite with coverage gate, but without term-missing output overhead
test-all-fast:
	python -m pytest --cov=src --cov-report= --cov-fail-under=97

# Full suite without coverage for quickest full functional signal
test-all-no-cov:
	python -m pytest

# Full suite, optional parallel workers when pytest-xdist is installed
test-all-parallel:
	python -c "import importlib.util, subprocess, sys; args=[sys.executable,'-m','pytest','--cov=src','--cov-report=','--cov-fail-under=97']; args += (['-n','auto','--dist','loadscope'] if importlib.util.find_spec('xdist') else []); raise SystemExit(subprocess.call(args))"

# Local execution flow aligned with the Pull Request Merge Gate
ci-local: verify-dependencies lint typecheck openapi-gate no-alias-gate api-vocabulary-gate domain-data-products-gate quality-baseline-check migration-smoke security-audit coverage-combined

ci-local-docker:
	docker compose -f docker-compose.ci-local.yml up --build --abort-on-container-exit --exit-code-from ci-local ci-local

ci-local-docker-down:
	docker compose -f docker-compose.ci-local.yml down -v --remove-orphans

check-all: lint typecheck test-all

typecheck:
	python -m mypy --config-file mypy.ini

openapi-gate:
	python scripts/openapi_quality_gate.py
	python -m pytest tests/unit/advisory/contracts/test_contract_openapi_lifecycle_docs.py -q
	$(MAKE) openapi-spectral-report

openapi-spectral-report:
	python scripts/openapi_spectral_report.py --output output/openapi-spectral-report.json

no-alias-gate:
	python scripts/no_alias_contract_guard.py

api-vocabulary-gate:
	python scripts/api_vocabulary_inventory.py
	python scripts/api_vocabulary_inventory.py --validate-only

domain-data-products-gate:
	python scripts/validate_domain_data_product_declarations.py

engineering-health:
	python scripts/engineering_health_report.py --output docs/architecture/ENGINEERING-HEALTH-BASELINE.md

engineering-health-json:
	python scripts/engineering_health_report.py --format json --output output/engineering-health-current.json

quality-baseline:
	python scripts/quality_baseline_report.py --output-dir quality

quality-baseline-check:
	python scripts/quality_baseline_report.py --output-dir quality --check

migration-smoke:
	python -m pytest tests/unit/shared/dependencies/test_runtime_persistence.py tests/unit/shared/dependencies/test_production_cutover_contract.py tests/unit/shared/dependencies/test_postgres_migrate_targets.py -q

migration-apply:
	python scripts/postgres_migrate.py --target all

lint:
	python -m ruff check .
	python -m ruff format --check .
	$(MAKE) monetary-float-guard
	$(MAKE) architecture-boundaries
	$(MAKE) complexity-regression-gate

monetary-float-guard:
	python scripts/check_monetary_float_usage.py

architecture-boundaries:
	python -c "from importlinter.cli import lint_imports_command; lint_imports_command(args=['--config','.importlinter'], standalone_mode=True)"

complexity-regression-gate:
	python scripts/radon_complexity_gate.py --fail-rank C

observability-diagnostics:
	python -m pytest tests/unit/advisory/api/test_api_observability.py -q

advisory-domain-golden-regressions:
	python -m pytest tests/unit/advisory/golden -q

demo-assurance-gate: openapi-gate no-alias-gate api-vocabulary-gate domain-data-products-gate observability-diagnostics advisory-domain-golden-regressions
	@echo "Demo assurance gate passed"

format:
	python -m ruff format .

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['__pycache__', '.pytest_cache', 'htmlcov', '.ruff_cache', '.mypy_cache']]; pathlib.Path('.coverage').unlink(missing_ok=True)"

run:
	python -m uvicorn src.api.main:app --reload --port 8000

verify-dependencies:
	python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct --skip-audit

check-deps:
	python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct

check-deps-strict:
	python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct --fail-on-outdated

security-audit:
	python scripts/dependency_health_check.py --requirements requirements.txt --dev-requirements requirements-dev.txt --outdated-scope direct
	$(MAKE) bandit-high-severity-gate

bandit-high-severity-gate:
	python scripts/bandit_high_severity_gate.py

coverage-combined:
	COVERAGE_FILE=.coverage.unit python -m pytest tests/unit --cov=src --cov-report=
	COVERAGE_FILE=.coverage.integration python -m pytest tests/integration --cov=src --cov-report=
	COVERAGE_FILE=.coverage.e2e python -m pytest tests/e2e --cov=src --cov-report=
	python -m coverage combine .coverage.unit .coverage.integration .coverage.e2e
	python -m coverage report --fail-under=97

postgres-runtime-contracts-local:
	python scripts/run_runtime_smoke_checks.py postgres-runtime-contracts

production-profile-guardrail-negatives-local:
	python scripts/run_runtime_smoke_checks.py production-profile-guardrail-negatives

docker-build:
	docker build -t lotus-advise:ci-test .

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down
