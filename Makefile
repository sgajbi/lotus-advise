.PHONY: install check check-all test test-unit test-integration test-e2e test-all typecheck lint format clean run check-deps pre-commit docker-up docker-down

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install pre-commit
	pre-commit install

pre-commit:
	pre-commit run --all-files

check: lint typecheck test

test:
	$(MAKE) test-unit

test-unit:
	python -m pytest tests/unit

test-integration:
	python -m pytest tests/integration

test-e2e:
	python -m pytest tests/e2e

test-all:
	python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=99

check-all: lint typecheck test-all

typecheck:
	mypy --config-file mypy.ini

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['__pycache__', '.pytest_cache', 'htmlcov', '.ruff_cache', '.mypy_cache']]; pathlib.Path('.coverage').unlink(missing_ok=True)"

run:
	uvicorn src.api.main:app --reload --port 8000

check-deps:
	python scripts/dependency_health_check.py --requirements requirements.txt

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down
