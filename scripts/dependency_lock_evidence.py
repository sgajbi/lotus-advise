"""Generate and validate the Lotus Advise authoritative dependency lock mirror."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = Path("uv.lock")
LICENSE_INVENTORY_PATH = Path("docs/standards/license-ip-inventory.v1.json")
REQUIREMENT_GROUPS = {
    "install": Path("requirements.txt"),
    "runtime": Path("requirements-prod.txt"),
    "development": Path("requirements-dev.txt"),
}


@dataclass(frozen=True)
class DirectRequirement:
    name: str
    declared_name: str
    version: str
    extras: tuple[str, ...]
    group: str
    source_file: str
    requirement_hash: str


def build_dependency_lock(
    *,
    requirement_groups: dict[str, Path],
    license_inventory_path: Path,
    requires_python: str = ">=3.11",
) -> dict[str, Any]:
    direct_requirements = tuple(
        requirement
        for group, path in requirement_groups.items()
        for requirement in _parse_requirement_file(path.resolve(), group=group, visited=set())
    )
    package_records = _package_records(
        direct_requirements=direct_requirements,
        license_inventory=_load_license_inventory(license_inventory_path),
    )
    return {
        "version": 1,
        "revision": 4,
        "requires-python": requires_python,
        "authoritative-source": "requirements",
        "generated-by": "scripts/dependency_lock_evidence.py",
        "license-inventory": _display_path(license_inventory_path),
        "license-inventory-sha256": _file_sha256(license_inventory_path),
        "requirement-files": [
            {
                "group": group,
                "path": _display_path(path),
                "sha256": _file_sha256(path),
            }
            for group, path in sorted(requirement_groups.items())
        ],
        "package": package_records,
        "summary": {
            "package-count": len(package_records),
            "direct-package-count": sum(1 for package in package_records if package["direct"]),
            "transitive-package-count": sum(
                1 for package in package_records if not package["direct"]
            ),
        },
    }


def validate_dependency_lock(
    lock_payload: dict[str, Any], expected_payload: dict[str, Any]
) -> list[str]:
    failures: list[str] = []
    if lock_payload.get("authoritative-source") != "requirements":
        failures.append("uv.lock must declare authoritative-source = requirements")
    requires_python = str(lock_payload.get("requires-python") or "")
    if not SpecifierSet(requires_python).contains(Version("3.11")):
        failures.append("uv.lock requires-python must support Python 3.11")
    if _normalized_lock(lock_payload) != _normalized_lock(expected_payload):
        failures.append("uv.lock is stale. Regenerate with `make dependency-lock`.")
    failures.extend(_package_mismatch_failures(lock_payload, expected_payload))
    return failures


def write_dependency_lock(lock_payload: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(_to_toml(lock_payload), encoding="utf-8")


def _parse_requirement_file(
    path: Path,
    *,
    group: str,
    visited: set[Path],
) -> list[DirectRequirement]:
    if path in visited:
        return []
    visited.add(path)
    requirements: list[DirectRequirement] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("-r ") or line.startswith("--requirement "):
            _, include_target = line.split(maxsplit=1)
            requirements.extend(
                _parse_requirement_file(
                    (path.parent / include_target.strip()).resolve(),
                    group=group,
                    visited=visited,
                )
            )
            continue
        if line.startswith("-"):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        version = _exact_version(requirement)
        requirements.append(
            DirectRequirement(
                name=canonicalize_name(requirement.name),
                declared_name=requirement.name,
                version=version,
                extras=tuple(sorted(requirement.extras)),
                group=group,
                source_file=_display_path(path),
                requirement_hash=_sha256_text(line),
            )
        )
    return requirements


def _exact_version(requirement: Requirement) -> str:
    pins = [
        str(specifier.version) for specifier in requirement.specifier if specifier.operator == "=="
    ]
    if len(pins) != 1:
        raise ValueError(f"Requirement must have exactly one == pin: {requirement}")
    return pins[0]


def _package_records(
    *,
    direct_requirements: Iterable[DirectRequirement],
    license_inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    direct_by_name: dict[str, list[DirectRequirement]] = {}
    for requirement in direct_requirements:
        direct_by_name.setdefault(requirement.name, []).append(requirement)

    records: dict[str, dict[str, Any]] = {}
    for package in license_inventory.get("packages", []):
        if not isinstance(package, dict):
            continue
        name = canonicalize_name(str(package.get("name") or ""))
        if not name:
            continue
        direct_entries = direct_by_name.get(name, [])
        records[name] = {
            "name": name,
            "version": str(package.get("version") or _direct_version(direct_entries)),
            "direct": bool(direct_entries),
            "groups": sorted(
                set(package.get("dependency_groups") or ())
                | {entry.group for entry in direct_entries}
            ),
            "requirement-files": sorted({entry.source_file for entry in direct_entries}),
            "extras": sorted({extra for entry in direct_entries for extra in entry.extras}),
            "requirement-hashes": sorted({entry.requirement_hash for entry in direct_entries}),
        }
    for name, direct_entries in direct_by_name.items():
        if name not in records:
            raise ValueError(
                f"Direct requirement {name} is missing from "
                f"{LICENSE_INVENTORY_PATH.as_posix()}; regenerate with `make license-ip-inventory`."
            )
    return [records[name] for name in sorted(records)]


def _direct_version(entries: list[DirectRequirement]) -> str:
    versions = {entry.version for entry in entries}
    if len(versions) > 1:
        raise ValueError(f"Requirement version mismatch for {entries[0].name}: {sorted(versions)}")
    return next(iter(versions), "")


def _load_license_inventory(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _package_mismatch_failures(
    lock_payload: dict[str, Any],
    expected_payload: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    locked = {str(package.get("name")): package for package in lock_payload.get("package", [])}
    expected = {
        str(package.get("name")): package for package in expected_payload.get("package", [])
    }
    missing = sorted(set(expected) - set(locked))
    extra = sorted(set(locked) - set(expected))
    if missing:
        failures.append(f"uv.lock missing packages: {', '.join(missing)}")
    if extra:
        failures.append(f"uv.lock has stale packages: {', '.join(extra)}")
    for name in sorted(set(locked) & set(expected)):
        if str(locked[name].get("version")) != str(expected[name].get("version")):
            failures.append(
                f"uv.lock version mismatch for {name}: "
                f"{locked[name].get('version')} != {expected[name].get('version')}"
            )
    return failures


def _normalized_lock(lock_payload: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(json.dumps(lock_payload, sort_keys=True)))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPO_ROOT).as_posix()
        if path.is_relative_to(REPO_ROOT)
        else path.as_posix()
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _to_toml(lock_payload: dict[str, Any]) -> str:
    lines = [
        f"version = {lock_payload['version']}",
        f"revision = {lock_payload['revision']}",
        f"requires-python = {_quote(lock_payload['requires-python'])}",
        f"authoritative-source = {_quote(lock_payload['authoritative-source'])}",
        f"generated-by = {_quote(lock_payload['generated-by'])}",
        f"license-inventory = {_quote(lock_payload['license-inventory'])}",
        f"license-inventory-sha256 = {_quote(lock_payload['license-inventory-sha256'])}",
        "",
    ]
    for requirement_file in lock_payload["requirement-files"]:
        lines.extend(
            [
                "[[requirement-files]]",
                f"group = {_quote(requirement_file['group'])}",
                f"path = {_quote(requirement_file['path'])}",
                f"sha256 = {_quote(requirement_file['sha256'])}",
                "",
            ]
        )
    for package in lock_payload["package"]:
        lines.extend(
            [
                "[[package]]",
                f"name = {_quote(package['name'])}",
                f"version = {_quote(package['version'])}",
                f"direct = {str(package['direct']).lower()}",
                f"groups = {_array(package['groups'])}",
                f"requirement-files = {_array(package['requirement-files'])}",
                f"extras = {_array(package['extras'])}",
                f"requirement-hashes = {_array(package['requirement-hashes'])}",
                "",
            ]
        )
    summary = lock_payload["summary"]
    lines.extend(
        [
            "[summary]",
            f"package-count = {summary['package-count']}",
            f"direct-package-count = {summary['direct-package-count']}",
            f"transitive-package-count = {summary['transitive-package-count']}",
            "",
        ]
    )
    return "\n".join(lines)


def _quote(value: object) -> str:
    return json.dumps(str(value))


def _array(values: Iterable[object]) -> str:
    return "[" + ", ".join(_quote(value) for value in values) + "]"


def _build_expected(args: argparse.Namespace) -> dict[str, Any]:
    return build_dependency_lock(
        requirement_groups={group: REPO_ROOT / path for group, path in REQUIREMENT_GROUPS.items()},
        license_inventory_path=REPO_ROOT / args.license_inventory,
        requires_python=args.requires_python,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("write-lock", "check-lock"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--lock-path", default=LOCK_PATH.as_posix())
        subparser.add_argument("--license-inventory", default=LICENSE_INVENTORY_PATH.as_posix())
        subparser.add_argument("--requires-python", default=">=3.11")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    expected = _build_expected(args)
    if args.command == "write-lock":
        write_dependency_lock(expected, REPO_ROOT / args.lock_path)
        return 0
    current = tomllib.loads((REPO_ROOT / args.lock_path).read_text(encoding="utf-8"))
    failures = validate_dependency_lock(current, expected)
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
