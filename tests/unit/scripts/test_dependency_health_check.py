import json
import sys
from datetime import date
from pathlib import Path

import pytest

from scripts.dependency_health_check import (
    CheckResult,
    _filter_outdated_to_requirements,
    _latest_python_compatible_version_from_releases,
    _parse_requirements_file,
    _venv_python,
    apply_freshness_exceptions,
    load_freshness_exceptions,
    main,
    parse_pip_audit_vulnerabilities,
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


def test_pip_audit_parser_retains_nested_advisories_with_dependency_identity() -> None:
    vulnerabilities = parse_pip_audit_vulnerabilities(
        json.dumps(
            {
                "dependencies": [
                    {
                        "name": "anyio",
                        "version": "4.14.2",
                        "vulns": [{"id": "CVE-2026-0001", "fix_versions": ["4.15.1"]}],
                    }
                ],
                "fixes": [],
            }
        )
    )

    assert vulnerabilities == [
        {
            "dependency": "anyio",
            "version": "4.14.2",
            "vulnerability": {"id": "CVE-2026-0001", "fix_versions": ["4.15.1"]},
        }
    ]


@pytest.mark.parametrize("arguments", [[], ["--fail-on-outdated"]])
def test_security_audit_and_check_deps_strict_fail_closed_for_nested_advisory(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    """Exercise the script entry point used by security-audit and check-deps-strict."""

    audit_output = json.dumps(
        {
            "dependencies": [
                {
                    "name": "anyio",
                    "version": "4.14.2",
                    "vulns": [{"id": "CVE-2026-0001"}],
                }
            ]
        }
    )

    def _run(command: list[str], **_: object) -> CheckResult:
        if command[-2:] == ["pip", "check"]:
            return CheckResult(command, 0, "No broken requirements found.", "")
        if "pip_audit" in command:
            return CheckResult(command, 1, audit_output, "vulnerabilities found")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("scripts.dependency_health_check.venv.EnvBuilder.create", lambda *_: None)
    monkeypatch.setattr(
        "scripts.dependency_health_check._install_requirement_files",
        lambda **_: None,
    )
    monkeypatch.setattr("scripts.dependency_health_check._run", _run)
    monkeypatch.setattr(sys, "argv", ["dependency_health_check.py", *arguments])

    assert main() == 1


@pytest.mark.parametrize(
    "stdout",
    [
        "{",
        json.dumps({"vulns": []}),
        json.dumps({"dependencies": [{"name": "anyio"}]}),
        json.dumps({"dependencies": [], "fixes": "not-a-list"}),
        json.dumps({"dependencies": [], "unexpected": []}),
    ],
)
def test_pip_audit_parser_rejects_malformed_or_unsupported_results(stdout: str) -> None:
    with pytest.raises(ValueError):
        parse_pip_audit_vulnerabilities(stdout)
