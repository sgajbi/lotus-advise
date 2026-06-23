from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

_WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass
class CheckResult:
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> CheckResult:
    completed = subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, check=False
    )
    return CheckResult(
        command=command,
        return_code=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _venv_python(venv_path: Path) -> Path:
    venv_path_text = str(venv_path)
    is_windows_layout = os.name == "nt" or bool(_WINDOWS_DRIVE_PATH_RE.match(venv_path_text))
    scripts_dir = "Scripts" if is_windows_layout else "bin"
    executable_name = "python.exe" if is_windows_layout else "python"
    return venv_path / scripts_dir / executable_name


def _print_section(title: str, body: str) -> None:
    print(f"\n=== {title} ===")
    print(body or "(no output)")


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _extract_requirement_name(line: str) -> str | None:
    no_comment = line.split("#", 1)[0].strip()
    if not no_comment:
        return None
    match = re.match(r"^([A-Za-z0-9_.-]+)", no_comment)
    if match is None:
        return None
    return _normalize_package_name(match.group(1))


def _parse_requirements_file(path: Path, visited: set[Path]) -> set[str]:
    resolved = path.resolve()
    if resolved in visited:
        return set()
    visited.add(resolved)

    requirement_names: set[str] = set()
    for raw_line in resolved.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r ") or line.startswith("--requirement "):
            _, include_target = line.split(maxsplit=1)
            include_path = (resolved.parent / include_target.strip()).resolve()
            requirement_names.update(_parse_requirements_file(include_path, visited))
            continue
        if line.startswith("-"):
            continue
        requirement_name = _extract_requirement_name(line)
        if requirement_name is not None:
            requirement_names.add(requirement_name)
    return requirement_names


def _filter_outdated_to_requirements(
    outdated_rows: Iterable[dict[str, str]], requirement_names: set[str]
) -> list[dict[str, str]]:
    filtered_rows: list[dict[str, str]] = []
    for row in outdated_rows:
        package_name = row.get("name")
        if not package_name:
            continue
        if _normalize_package_name(package_name) in requirement_names:
            filtered_rows.append(row)
    return filtered_rows


def _release_supports_python(
    release_files: Iterable[dict[str, object]], python_version: Version
) -> bool:
    for release_file in release_files:
        if release_file.get("yanked") is True:
            continue
        requires_python = str(release_file.get("requires_python") or "").strip()
        if not requires_python:
            return True
        try:
            if SpecifierSet(requires_python).contains(python_version, prereleases=True):
                return True
        except InvalidSpecifier:
            return True
    return False


def _latest_python_compatible_version_from_releases(
    releases: dict[str, list[dict[str, object]]], python_version: str
) -> str | None:
    target_python = Version(python_version)
    compatible_versions: list[Version] = []
    for version_text, release_files in releases.items():
        try:
            parsed_version = Version(version_text)
        except InvalidVersion:
            continue
        if parsed_version.is_prerelease:
            continue
        if _release_supports_python(release_files, target_python):
            compatible_versions.append(parsed_version)
    if not compatible_versions:
        return None
    return str(max(compatible_versions))


def _fetch_latest_python_compatible_version(package_name: str, python_version: str) -> str | None:
    url = f"https://pypi.org/pypi/{urllib.parse.quote(package_name)}/json"
    with urllib.request.urlopen(url, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    releases = payload.get("releases")
    if not isinstance(releases, dict):
        return None
    return _latest_python_compatible_version_from_releases(releases, python_version)


def _filter_outdated_to_python_compatible_latest(
    outdated_rows: Iterable[dict[str, str]],
    *,
    python_version: str,
) -> list[dict[str, str]]:
    filtered_rows: list[dict[str, str]] = []
    for row in outdated_rows:
        package_name = row.get("name")
        installed_version = row.get("version")
        if not package_name or not installed_version:
            filtered_rows.append(row)
            continue
        try:
            compatible_latest = _fetch_latest_python_compatible_version(
                package_name, python_version
            )
            if compatible_latest is None:
                filtered_rows.append(row)
                continue
            if Version(compatible_latest) <= Version(installed_version):
                continue
            filtered_row = dict(row)
            filtered_row["latest_version"] = compatible_latest
            filtered_rows.append(filtered_row)
        except (InvalidVersion, OSError, TimeoutError, json.JSONDecodeError):
            filtered_rows.append(row)
    return filtered_rows


def _install_requirement_files(
    *,
    python_bin: Path,
    repo_root: Path,
    env: dict[str, str],
    requirements_file: Path,
    dev_requirements_file: Path | None,
) -> None:
    install_commands: list[list[str]] = [
        [str(python_bin), "-m", "pip", "install", "--upgrade", "pip"],
        [str(python_bin), "-m", "pip", "install", "-r", str(requirements_file)],
    ]
    if dev_requirements_file is not None:
        install_commands.append(
            [str(python_bin), "-m", "pip", "install", "-r", str(dev_requirements_file)]
        )

    for command in install_commands:
        result = _run(command, cwd=repo_root, env=env)
        if result.return_code != 0:
            _print_section("Dependency install stdout", result.stdout)
            _print_section("Dependency install stderr", result.stderr)
            raise SystemExit(result.return_code)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency health checks for local and CI use")
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to the requirements file to audit",
    )
    parser.add_argument(
        "--dev-requirements",
        default="requirements-dev.txt",
        help="Optional path to the development requirements file",
    )
    parser.add_argument(
        "--outdated-scope",
        choices=("direct", "environment"),
        default="direct",
        help="Outdated scope: declared requirements graph or entire project-scoped environment",
    )
    parser.add_argument(
        "--fail-on-outdated",
        action="store_true",
        help="Fail when outdated packages are detected",
    )
    parser.add_argument(
        "--target-python-version",
        default=os.environ.get("PYTHON_VERSION", "3.11"),
        help=(
            "Supported runtime Python major.minor version used to filter incompatible latest "
            "package releases"
        ),
    )
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help=(
            "Skip vulnerability audit and only run project-scoped pip check plus outdated reporting"
        ),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    requirements_file = (repo_root / args.requirements).resolve()
    dev_requirements_file = (repo_root / args.dev_requirements).resolve()
    if not dev_requirements_file.exists():
        dev_requirements_file = None

    temp_dir = Path(tempfile.mkdtemp(prefix="lotus-advise-dependency-health-"))
    venv_path = temp_dir / "venv"
    env = os.environ.copy()
    env["PIP_NO_CACHE_DIR"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    try:
        venv.EnvBuilder(with_pip=True).create(venv_path)
        python_bin = _venv_python(venv_path)
        _install_requirement_files(
            python_bin=python_bin,
            repo_root=repo_root,
            env=env,
            requirements_file=requirements_file,
            dev_requirements_file=dev_requirements_file,
        )

        pip_check = _run([str(python_bin), "-m", "pip", "check"], cwd=repo_root, env=env)
        if pip_check.return_code != 0:
            _print_section("pip check stdout", pip_check.stdout)
            _print_section("pip check stderr", pip_check.stderr)
            return pip_check.return_code

        if not args.skip_audit:
            audit = _run(
                [str(python_bin), "-m", "pip_audit", "-r", str(requirements_file), "-f", "json"],
                cwd=repo_root,
                env=env,
            )
            if audit.return_code != 0 and not audit.stdout:
                _print_section("pip-audit stderr", audit.stderr)
                return audit.return_code

            vulnerabilities = []
            if audit.stdout:
                try:
                    payload = json.loads(audit.stdout)
                    vulnerabilities = payload.get("vulns", [])
                except json.JSONDecodeError:
                    _print_section("pip-audit output", audit.stdout)
                    _print_section("pip-audit stderr", audit.stderr)
                    return 1

            _print_section(
                "Vulnerability Summary",
                f"Known vulnerabilities: {len(vulnerabilities)}",
            )
            if vulnerabilities:
                _print_section("Vulnerabilities", json.dumps(vulnerabilities, indent=2))
                return 1

        outdated = _run(
            [str(python_bin), "-m", "pip", "list", "--outdated", "--format=json"],
            cwd=repo_root,
            env=env,
        )
        if outdated.return_code != 0:
            _print_section("pip outdated stderr", outdated.stderr)
            return outdated.return_code

        outdated_rows = json.loads(outdated.stdout) if outdated.stdout else []
        if args.outdated_scope == "direct":
            requirement_names = _parse_requirements_file(requirements_file, visited=set())
            outdated_rows = _filter_outdated_to_requirements(outdated_rows, requirement_names)
        outdated_rows = _filter_outdated_to_python_compatible_latest(
            outdated_rows,
            python_version=args.target_python_version,
        )

        _print_section(
            "Outdated Summary",
            f"Outdated packages ({args.outdated_scope} scope): {len(outdated_rows)}",
        )
        if outdated_rows:
            _print_section("Outdated Packages", json.dumps(outdated_rows, indent=2))

        if args.fail_on_outdated and outdated_rows:
            return 2
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
