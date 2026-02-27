from pathlib import Path

from scripts.dependency_health_check import (
    _filter_outdated_to_requirements,
    _parse_requirements_file,
)


def test_parse_requirements_file_resolves_nested_requirements(tmp_path: Path) -> None:
    base = tmp_path / "requirements.txt"
    prod = tmp_path / "requirements-prod.txt"
    dev = tmp_path / "requirements-dev.txt"

    prod.write_text(
        "fastapi==0.129.2\n" "psycopg[binary]==3.3.3\n",
        encoding="utf-8",
    )
    dev.write_text(
        "-r requirements-prod.txt\n" "pytest==9.0.2\n" "ruff==0.15.4\n",
        encoding="utf-8",
    )
    base.write_text(
        "-r requirements-dev.txt\n" "httpx==0.28.1\n",
        encoding="utf-8",
    )

    names = _parse_requirements_file(base, visited=set())
    assert names == {"fastapi", "httpx", "psycopg", "pytest", "ruff"}


def test_filter_outdated_to_requirements_uses_normalized_names() -> None:
    requirement_names = {"prometheus-client", "ruff", "typing-extensions"}
    rows = [
        {"name": "prometheus_client", "version": "0.20.0", "latest_version": "0.24.1"},
        {"name": "ruff", "version": "0.15.2", "latest_version": "0.15.4"},
        {"name": "typing_extensions", "version": "4.14.0", "latest_version": "4.15.0"},
        {"name": "virtualenv", "version": "20.32.0", "latest_version": "21.0.0"},
    ]

    filtered = _filter_outdated_to_requirements(rows, requirement_names)
    assert [row["name"] for row in filtered] == [
        "prometheus_client",
        "ruff",
        "typing_extensions",
    ]
