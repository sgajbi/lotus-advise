from __future__ import annotations

from email.message import Message
from pathlib import Path

from scripts.license_ip_evidence import (
    LicensePolicy,
    build_license_inventory,
    validate_license_inventory,
    validate_license_inventory_against_expected,
)


class FakeDistribution:
    def __init__(
        self,
        *,
        name: str,
        version: str = "1.0.0",
        license_expression: str | None = "MIT",
        requires: list[str] | None = None,
    ) -> None:
        self.metadata = Message()
        self.metadata["Name"] = name
        if license_expression is not None:
            self.metadata["License-Expression"] = license_expression
        self.version = version
        self.requires = requires or []


def test_license_inventory_includes_transitive_dependency(tmp_path: Path) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("directpkg==1.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")

    inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="abc123",
        image_digest="sha256:abc123",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[
            FakeDistribution(name="directpkg", requires=["childpkg>=1"]),
            FakeDistribution(name="childpkg"),
        ],
    )

    packages = {package["name"]: package for package in inventory["packages"]}

    assert packages["directpkg"]["relationship"] == "direct"
    assert packages["childpkg"]["relationship"] == "transitive"
    assert packages["childpkg"]["policy_classification"] == "ALLOWED"


def test_license_inventory_records_direct_requirement_pin(tmp_path: Path) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("directpkg==2.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")

    inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="abc123",
        image_digest="sha256:abc123",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[FakeDistribution(name="directpkg", version="1.0.0")],
    )

    packages = {package["name"]: package for package in inventory["packages"]}

    assert packages["directpkg"]["version"] == "2.0.0"


def test_license_inventory_fails_direct_pin_metadata_mismatch(tmp_path: Path) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("directpkg==2.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")

    inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="abc123",
        image_digest="sha256:abc123",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[FakeDistribution(name="directpkg", version="1.0.0")],
    )

    failures = validate_license_inventory(inventory, _policy())

    assert inventory["packages"][0]["metadata_available"] is False
    assert (
        "directpkg installed metadata version 1.0.0 does not match pinned version 2.0.0; "
        "install requirements before regenerating license/IP inventory."
    ) in failures


def test_license_inventory_uses_repo_relative_release_graph_paths() -> None:
    inventory = build_license_inventory(
        runtime_requirements=Path("requirements-prod.txt"),
        development_requirements=Path("requirements-dev.txt"),
        policy=_policy(),
        commit_sha="abc123",
        image_digest="sha256:abc123",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[
            FakeDistribution(name="anyio"),
            FakeDistribution(name="coverage"),
            FakeDistribution(name="fastapi"),
            FakeDistribution(name="httpx"),
            FakeDistribution(name="orjson"),
            FakeDistribution(name="pandas"),
            FakeDistribution(name="pydantic"),
            FakeDistribution(name="pydantic-settings"),
            FakeDistribution(name="python-dotenv"),
            FakeDistribution(name="sqlalchemy"),
            FakeDistribution(name="structlog"),
            FakeDistribution(name="uvicorn"),
        ],
    )

    assert inventory["release_graphs"] == {
        "runtime": "requirements-prod.txt",
        "development": "requirements-dev.txt",
    }


def test_license_inventory_fails_stale_package_version(tmp_path: Path) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("directpkg==2.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")

    expected_inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="expected",
        image_digest="expected",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[FakeDistribution(name="directpkg", version="2.0.0")],
    )
    stale_inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="stale",
        image_digest="stale",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-10T00:00:00Z",
        distributions=[FakeDistribution(name="directpkg", version="2.0.0")],
    )
    stale_inventory["packages"][0]["version"] = "1.0.0"

    failures = validate_license_inventory_against_expected(
        stale_inventory,
        expected_inventory,
        _policy(),
    )

    assert "License/IP inventory is stale. Regenerate with `make license-ip-inventory`." in failures


def test_license_inventory_staleness_ignores_transitive_platform_metadata(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("directpkg==1.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")

    expected_inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="expected",
        image_digest="expected",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[
            FakeDistribution(name="directpkg", requires=["childpkg>=1"]),
            FakeDistribution(name="childpkg", version="1.0.0"),
        ],
    )
    current_inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="current",
        image_digest="current",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-12T00:00:00Z",
        distributions=[
            FakeDistribution(name="directpkg", requires=["childpkg>=1"]),
            FakeDistribution(name="childpkg", version="1.0.1"),
        ],
    )

    failures = validate_license_inventory_against_expected(
        current_inventory,
        expected_inventory,
        _policy(),
    )

    assert failures == []


def test_license_inventory_fails_missing_package_metadata(tmp_path: Path) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("missingpkg==1.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")

    inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="abc123",
        image_digest="sha256:abc123",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[],
    )

    failures = validate_license_inventory(inventory, _policy())

    assert inventory["packages"][0]["metadata_available"] is False
    assert "missingpkg requires license/IP review for UNKNOWN" in failures


def test_license_inventory_allows_owned_unexpired_exception(tmp_path: Path) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("reviewpkg==1.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")

    inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=_policy(),
        commit_sha="abc123",
        image_digest="sha256:abc123",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[FakeDistribution(name="reviewpkg", license_expression="LGPL-3.0-only")],
    )

    package = inventory["packages"][0]
    failures = validate_license_inventory(inventory, _policy())

    assert package["policy_classification"] == "APPROVED_EXCEPTION"
    assert package["exception_id"] == "TEST-LIC-001"
    assert failures == []


def test_license_inventory_blocks_expired_exception(tmp_path: Path) -> None:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    runtime.write_text("reviewpkg==1.0.0\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")
    policy = _policy(exception_expiry="2020-01-01")

    inventory = build_license_inventory(
        runtime_requirements=runtime,
        development_requirements=development,
        policy=policy,
        commit_sha="abc123",
        image_digest="sha256:abc123",
        repository_url="https://github.com/sgajbi/lotus-advise",
        generated_at_utc="2026-07-11T00:00:00Z",
        distributions=[FakeDistribution(name="reviewpkg", license_expression="LGPL-3.0-only")],
    )

    failures = validate_license_inventory(inventory, policy)

    assert "reviewpkg license exception TEST-LIC-001 expired on 2020-01-01" in failures


def _policy(*, exception_expiry: str = "2099-01-01") -> LicensePolicy:
    return LicensePolicy(
        allowed_terms=frozenset({"MIT", "Apache-2.0"}),
        review_required_terms=frozenset({"LGPL-3.0-only", "UNKNOWN"}),
        prohibited_terms=frozenset({"AGPL-3.0-only"}),
        exceptions=(
            {
                "id": "TEST-LIC-001",
                "package": "reviewpkg",
                "license_term": "LGPL-3.0-only",
                "owner": "test-owner",
                "expires_on": exception_expiry,
            },
        ),
    )
