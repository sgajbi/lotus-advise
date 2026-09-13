import json
from datetime import date
from pathlib import Path

import pytest

from scripts.dependency_health_check import (
    _filter_outdated_to_requirements,
    _latest_python_compatible_version_from_releases,
    _parse_requirements_file,
    _venv_python,
    apply_freshness_exceptions,
    load_freshness_exceptions,
)


def test_parse_requirements_file_resolves_nested_requirements(tmp_path: Path) -> None:
    base = tmp_path / "requirements.txt"
    prod = tmp_path / "requirements-prod.txt"
    dev = tmp_path / "requirements-dev.txt"

    prod.write_text(
        "fastapi==0.129.2\npsycopg[binary]==3.3.3\n",
        encoding="utf-8",
    )
    dev.write_text(
        "-r requirements-prod.txt\npytest==9.0.2\nruff==0.15.4\n",
        encoding="utf-8",
    )
    base.write_text(
        "-r requirements-dev.txt\nhttpx==0.28.1\n",
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


def test_latest_python_compatible_version_ignores_incompatible_latest_release() -> None:
    releases = {
        "2.4.5": [{"requires_python": ">=3.11"}],
        "2.4.6": [{"requires_python": ">=3.11"}],
        "2.5.0": [{"requires_python": ">=3.12"}],
    }

    latest = _latest_python_compatible_version_from_releases(
        releases,
        python_version="3.11",
    )

    assert latest == "2.4.6"


def test_latest_python_compatible_version_ignores_all_yanked_latest_release() -> None:
    releases = {
        "1.9.1": [{"requires_python": ">=3.11"}],
        "1.9.2": [{"requires_python": ">=3.11", "yanked": True}],
    }

    latest = _latest_python_compatible_version_from_releases(
        releases,
        python_version="3.11",
    )

    assert latest == "1.9.1"


def test_venv_python_uses_expected_windows_layout() -> None:
    venv_path = Path("C:/tmp/lotus-advise-venv")

    python_bin = _venv_python(venv_path)

    assert python_bin == venv_path / "Scripts" / "python.exe"


def test_freshness_exception_allows_only_the_exact_reviewed_pin(tmp_path: Path) -> None:
    policy_path = tmp_path / "dependency-freshness-policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "schema_version": "lotus.advise.dependency-freshness-policy.v1",
                "exceptions": [
                    {
                        "package": "anyio",
                        "pinned_version": "4.14.2",
                        "latest_version": "4.15.1",
                        "owner": "sgajbi",
                        "reason": "lotus-gateway#704 compatibility cap.",
                        "expires_on": "2026-10-13",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    exceptions = load_freshness_exceptions(policy_path, today=date(2026, 9, 13))

    remaining, applied = apply_freshness_exceptions(
        [
            {"name": "anyio", "version": "4.14.2", "latest_version": "4.15.1"},
            {"name": "ruff", "version": "0.16.5", "latest_version": "0.16.7"},
        ],
        exceptions=exceptions,
    )

    assert [row["name"] for row in remaining] == ["ruff"]
    assert applied[0]["exception"]["reason"] == "lotus-gateway#704 compatibility cap."


def test_freshness_exception_fails_closed_when_expired_or_the_drift_changes(tmp_path: Path) -> None:
    policy_path = tmp_path / "dependency-freshness-policy.json"
    policy = {
        "schema_version": "lotus.advise.dependency-freshness-policy.v1",
        "exceptions": [
            {
                "package": "anyio",
                "pinned_version": "4.14.2",
                "latest_version": "4.15.1",
                "owner": "sgajbi",
                "reason": "lotus-gateway#704 compatibility cap.",
                "expires_on": "2026-10-13",
            }
        ],
    }
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    exceptions = load_freshness_exceptions(policy_path, today=date(2026, 9, 13))

    with pytest.raises(ValueError, match="must match a current direct dependency drift"):
        apply_freshness_exceptions(
            [{"name": "anyio", "version": "4.14.2", "latest_version": "4.16.0"}],
            exceptions=exceptions,
        )

    policy["exceptions"][0]["expires_on"] = "2026-09-12"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(ValueError, match="Expired dependency freshness exception"):
        load_freshness_exceptions(policy_path, today=date(2026, 9, 13))
