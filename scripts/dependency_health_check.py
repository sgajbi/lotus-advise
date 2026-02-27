import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Iterable


@dataclass
class CheckResult:
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


def _run(command: list[str]) -> CheckResult:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return CheckResult(
        command=command,
        return_code=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency health checks for local and CI use")
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to the requirements file to audit",
    )
    parser.add_argument(
        "--outdated-scope",
        choices=("direct", "environment"),
        default="direct",
        help="Outdated scope: declared requirements graph or entire active environment",
    )
    parser.add_argument(
        "--fail-on-outdated",
        action="store_true",
        help="Fail when outdated packages are detected",
    )
    args = parser.parse_args()

    pip_audit_executable = which("pip-audit")
    if pip_audit_executable is None:
        candidate = Path(sys.executable).with_name("pip-audit.exe")
        if candidate.exists():
            pip_audit_executable = str(candidate)
    audit_command = (
        [pip_audit_executable, "-r", args.requirements, "-f", "json"]
        if pip_audit_executable is not None
        else [sys.executable, "-m", "pip_audit", "-r", args.requirements, "-f", "json"]
    )
    audit = _run(audit_command)
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

    outdated = _run([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if outdated.return_code != 0:
        _print_section("pip outdated stderr", outdated.stderr)
        return outdated.return_code

    outdated_rows = json.loads(outdated.stdout) if outdated.stdout else []
    if args.outdated_scope == "direct":
        requirement_names = _parse_requirements_file(Path(args.requirements), visited=set())
        outdated_rows = _filter_outdated_to_requirements(outdated_rows, requirement_names)

    _print_section(
        "Vulnerability Summary",
        f"Known vulnerabilities: {len(vulnerabilities)}",
    )
    if vulnerabilities:
        _print_section("Vulnerabilities", json.dumps(vulnerabilities, indent=2))

    _print_section(
        "Outdated Summary",
        f"Outdated packages ({args.outdated_scope} scope): {len(outdated_rows)}",
    )
    if outdated_rows:
        _print_section("Outdated Packages", json.dumps(outdated_rows, indent=2))

    if vulnerabilities:
        return 1
    if args.fail_on_outdated and outdated_rows:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
