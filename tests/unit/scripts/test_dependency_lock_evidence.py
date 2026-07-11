from __future__ import annotations

from pathlib import Path

import pytest

from scripts.dependency_lock_evidence import (
    build_dependency_lock,
    validate_dependency_lock,
)


def test_dependency_lock_records_direct_and_transitive_packages(tmp_path: Path) -> None:
    runtime, development, install, inventory = _fixture_files(tmp_path)

    lock_payload = build_dependency_lock(
        requirement_groups={"install": install, "runtime": runtime, "development": development},
        license_inventory_path=inventory,
    )

    packages = {package["name"]: package for package in lock_payload["package"]}

    assert packages["fastapi"]["direct"] is True
    assert packages["fastapi"]["groups"] == ["development", "install", "runtime"]
    assert packages["starlette"]["direct"] is False
    assert lock_payload["summary"]["package-count"] == 2


def test_dependency_lock_fails_missing_package(tmp_path: Path) -> None:
    runtime, development, install, inventory = _fixture_files(tmp_path)
    expected = build_dependency_lock(
        requirement_groups={"install": install, "runtime": runtime, "development": development},
        license_inventory_path=inventory,
    )
    current = {**expected, "package": expected["package"][:1]}

    failures = validate_dependency_lock(current, expected)

    assert "uv.lock missing packages: starlette" in failures


def test_dependency_lock_fails_when_direct_requirement_is_missing_from_inventory(
    tmp_path: Path,
) -> None:
    runtime, development, install, inventory = _fixture_files(tmp_path)
    inventory.write_text(
        """
{
  "packages": [
    {"name": "starlette", "version": "4.5.6", "dependency_groups": ["runtime"]}
  ]
}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Direct requirement fastapi is missing"):
        build_dependency_lock(
            requirement_groups={
                "install": install,
                "runtime": runtime,
                "development": development,
            },
            license_inventory_path=inventory,
        )


def test_dependency_lock_fails_version_mismatch(tmp_path: Path) -> None:
    runtime, development, install, inventory = _fixture_files(tmp_path)
    expected = build_dependency_lock(
        requirement_groups={"install": install, "runtime": runtime, "development": development},
        license_inventory_path=inventory,
    )
    current = {**expected, "package": [dict(package) for package in expected["package"]]}
    current["package"][0]["version"] = "0.1.0"

    failures = validate_dependency_lock(current, expected)

    assert any("uv.lock version mismatch" in failure for failure in failures)


def test_dependency_lock_fails_stale_manifest_hash(tmp_path: Path) -> None:
    runtime, development, install, inventory = _fixture_files(tmp_path)
    expected = build_dependency_lock(
        requirement_groups={"install": install, "runtime": runtime, "development": development},
        license_inventory_path=inventory,
    )
    current = {
        **expected,
        "requirement-files": [
            {**item, "sha256": "stale"} if item["group"] == "runtime" else item
            for item in expected["requirement-files"]
        ],
    }

    failures = validate_dependency_lock(current, expected)

    assert "uv.lock is stale. Regenerate with `make dependency-lock`." in failures


def test_dependency_lock_requires_python_compatible_with_ci_runtime(tmp_path: Path) -> None:
    runtime, development, install, inventory = _fixture_files(tmp_path)
    expected = build_dependency_lock(
        requirement_groups={"install": install, "runtime": runtime, "development": development},
        license_inventory_path=inventory,
    )
    current = {**expected, "requires-python": ">=3.12"}

    failures = validate_dependency_lock(current, expected)

    assert "uv.lock requires-python must support Python 3.11" in failures


def _fixture_files(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    runtime = tmp_path / "requirements-prod.txt"
    development = tmp_path / "requirements-dev.txt"
    install = tmp_path / "requirements.txt"
    inventory = tmp_path / "license-ip-inventory.v1.json"
    runtime.write_text("fastapi==1.2.3\n", encoding="utf-8")
    development.write_text("-r requirements-prod.txt\n", encoding="utf-8")
    install.write_text("fastapi==1.2.3\n", encoding="utf-8")
    inventory.write_text(
        """
{
  "packages": [
    {"name": "fastapi", "version": "1.2.3", "dependency_groups": ["runtime"]},
    {"name": "starlette", "version": "4.5.6", "dependency_groups": ["runtime"]}
  ]
}
""",
        encoding="utf-8",
    )
    return runtime, development, install, inventory
