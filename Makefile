.PHONY: install check test typecheck lint format clean run check-deps pre-commit

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install pre-commit
	pre-commit install

pre-commit:
	pre-commit run --all-files

check: lint typecheck test

test:
	python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=99

typecheck:
	mypy --config-file mypy.ini

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .ruff_cache

run:
	uvicorn src.api.main:app --reload --port 8000

check-deps:
	python scripts/dependency_health_check.py --requirements requirements.txt

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down
