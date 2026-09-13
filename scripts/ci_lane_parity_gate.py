"""Verify selected aggregate Make controls remain live in applicable CI lanes."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path
from typing import Any

_SCHEMA_VERSION = "lotus.advise.ci-lane-parity.v1"
_TARGET = re.compile(r"^(?P<target>[A-Za-z0-9_-]+):(?P<dependencies>.*)$")
_RUN_STEP = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*(?P<value>.*)$")
_MATRIX_PATH = re.compile(r"^\s*path:\s*(?P<value>tests/[A-Za-z0-9_/-]+)\s*$")
_GITHUB_EXPRESSION = re.compile(r"\$\{\{.*?\}\}")
_PYTHON_INTERPRETERS = frozenset({"python", "python3", "python3.11"})
_PYTEST_NON_EXECUTING_OR_FILTERING_OPTIONS = frozenset(
    {
        "--collect-only",
        "--co",
        "--help",
        "-h",
        "--version",
        "--fixtures",
        "--markers",
        "--setup-only",
        "--setup-plan",
        "--last-failed",
        "--lf",
        "-k",
        "--keyword",
        "-m",
        "--mark",
        "--ignore",
        "--deselect",
    }
)
_PYTEST_OPTIONS_WITH_VALUE = frozenset(
    {
        "--capture",
        "--color",
        "--confcutdir",
        "--cov",
        "--cov-config",
        "--cov-report",
        "--deselect",
        "--durations",
        "--ignore",
        "--junitxml",
        "--keyword",
        "--mark",
        "--maxfail",
        "--rootdir",
        "--tb",
    }
)
_CHANGED_COVERAGE_REQUIRED_OPTIONS = frozenset(
    {"--base-ref", "--head-ref", "--coverage-data", "--policy", "--output"}
)
_NONEXECUTING_MAKEFLAGS = ("--dry-run", "--just-print", "--recon", "--touch", "--question")


def _make_dependencies(path: Path) -> dict[str, set[str]]:
    dependencies: dict[str, set[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _TARGET.match(line)
        if match is not None:
            dependencies[match["target"]] = {
                value for value in match["dependencies"].split() if "$" not in value
            }
    return dependencies


def _closure(target: str, *, dependencies: dict[str, set[str]]) -> set[str]:
    result: set[str] = set()
    pending = [target]
    while pending:
        for dependency in dependencies.get(pending.pop(), set()):
            if dependency not in result:
                result.add(dependency)
                pending.append(dependency)
    return result


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or policy.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError("CI lane parity policy has an unsupported schema_version.")
    if not isinstance(policy.get("aggregate_targets"), list):
        raise ValueError("CI lane parity policy aggregate_targets must be a list.")
    if not isinstance(policy.get("lanes"), dict) or not isinstance(policy.get("controls"), list):
        raise ValueError("CI lane parity policy must define lanes and controls.")
    return policy


def _workflow_run_scripts(path: Path) -> list[str]:
    """Extract YAML ``run`` step bodies, excluding comments and metadata fields."""

    lines = path.read_text(encoding="utf-8").splitlines()
    scripts: list[str] = []
    index = 0
    while index < len(lines):
        match = _RUN_STEP.match(lines[index])
        if match is None or lines[index].lstrip().startswith("#"):
            index += 1
            continue
        value = match["value"].strip()
        if value and value not in {"|", ">", "|-", ">-", "|+", ">+"}:
            scripts.append(value)
            index += 1
            continue
        indentation = len(match["indent"])
        block_lines: list[str] = []
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indentation:
                break
            block_lines.append(candidate[indentation + 2 :])
            index += 1
        scripts.append("\n".join(block_lines))
    return scripts


def _workflow_matrix_paths(path: Path) -> set[str]:
    return {
        match["value"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := _MATRIX_PATH.match(line)) is not None and not line.lstrip().startswith("#")
    }


def _shell_commands(script: str) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = []
    current = ""
    for line in script.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        current = f"{current} {candidate}".strip()
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        for fragment in re.split(r"\s*(?:&&|\|\||;)\s*", _normalize_github_expressions(current)):
            try:
                tokens = tuple(shlex.split(fragment, comments=True, posix=True))
            except ValueError:
                continue
            if tokens:
                commands.append(tokens)
        current = ""
    if current:
        try:
            tokens = tuple(
                shlex.split(_normalize_github_expressions(current), comments=True, posix=True)
            )
        except ValueError:
            tokens = ()
        if tokens:
            commands.append(tokens)
    return commands


def _normalize_github_expressions(command: str) -> str:
    """Keep GitHub expressions atomic while tokenizing a shell command."""

    return _GITHUB_EXPRESSION.sub(
        lambda match: "matrix.path" if "matrix.path" in match.group(0) else "github.expression",
        command,
    )


def _workflow_has_nonexecuting_makeflags(path: Path) -> bool:
    """Fail closed when a workflow supplies a Make no-op mode through ``MAKEFLAGS``."""

    contents = path.read_text(encoding="utf-8")
    if "MAKEFLAGS" not in contents:
        return False
    normalized = contents.lower()
    return any(option in normalized for option in _NONEXECUTING_MAKEFLAGS) or bool(
        re.search(r"makeflags[^\n]*(?:^|\s)-[a-z]*[ntq][a-z]*", normalized)
    )


def _executes_python_script(command: tuple[str, ...], signal: str) -> bool:
    """Return whether ``command`` invokes exactly ``signal`` as a Python program.

    Arguments after ``python -c`` or ``python -m`` are data to a different program,
    not executable evidence for a script.  Support the direct interpreter and the
    explicit ``uv run <interpreter> <script>`` form without guessing at arbitrary
    wrapper flags.
    """

    command_index = 0
    if command[:2] == ("uv", "run"):
        command_index = 2
    if len(command) <= command_index or command[command_index] not in _PYTHON_INTERPRETERS:
        return False
    return len(command) > command_index + 1 and command[command_index + 1] == signal


def _pytest_program_index(command: tuple[str, ...]) -> int | None:
    """Return the pytest program position for supported executable forms."""

    if command and command[0] == "pytest":
        return 0
    if (
        len(command) >= 3
        and command[0] in _PYTHON_INTERPRETERS
        and command[1:3] == ("-m", "pytest")
    ):
        return 2
    if command[:3] == ("uv", "run", "pytest"):
        return 2
    if (
        len(command) >= 5
        and command[:2] == ("uv", "run")
        and command[2] in _PYTHON_INTERPRETERS
        and command[3:5] == ("-m", "pytest")
    ):
        return 4
    return None


def _pytest_collection_targets(arguments: tuple[str, ...]) -> set[str]:
    """Return positional pytest collection targets, excluding option values."""

    targets: set[str] = set()
    skip_next = False
    for argument in arguments:
        if skip_next:
            skip_next = False
            continue
        if argument == "--":
            continue
        if argument.startswith("-"):
            if "=" not in argument and argument in _PYTEST_OPTIONS_WITH_VALUE:
                skip_next = True
            continue
        targets.add(argument)
    return targets


def _executes_pytest_signal(command: tuple[str, ...], signal: str) -> bool:
    """Require the named test path to run without a non-executing/filtering mode."""

    pytest_index = _pytest_program_index(command)
    if pytest_index is None:
        return False
    arguments = command[pytest_index + 1 :]
    if signal not in _pytest_collection_targets(arguments):
        return False
    return not any(
        argument in _PYTEST_NON_EXECUTING_OR_FILTERING_OPTIONS
        or any(
            argument.startswith(f"{option}=")
            for option in _PYTEST_NON_EXECUTING_OR_FILTERING_OPTIONS
            if option.startswith("--")
        )
        for argument in arguments
    )


def _executes_changed_coverage_gate(command: tuple[str, ...]) -> bool:
    """Require the changed-coverage program to receive its attributable inputs."""

    if not _executes_python_script(command, "scripts/changed_coverage_gate.py"):
        return False
    options = set(command[2:])
    return "--skip-reason" not in options and _CHANGED_COVERAGE_REQUIRED_OPTIONS <= options


def _signal_has_executable_evidence(signal: str, *, path: Path) -> bool:
    commands = [
        command for script in _workflow_run_scripts(path) for command in _shell_commands(script)
    ]
    signal_tokens = tuple(shlex.split(signal, comments=True, posix=True))
    if not signal_tokens:
        return False
    if signal_tokens[0] == "make":
        return not _workflow_has_nonexecuting_makeflags(path) and any(
            command == signal_tokens for command in commands
        )
    if signal.startswith("scripts/"):
        if signal == "scripts/changed_coverage_gate.py":
            return any(_executes_changed_coverage_gate(command) for command in commands)
        return any(_executes_python_script(command, signal) for command in commands)
    if signal.startswith("tests/"):
        pytest_commands = [
            command for command in commands if _pytest_program_index(command) is not None
        ]
        return any(
            _executes_pytest_signal(command, signal)
            or (
                signal in _workflow_matrix_paths(path)
                and _executes_pytest_signal(command, "matrix.path")
            )
            for command in pytest_commands
        )
    return any(command[: len(signal_tokens)] == signal_tokens for command in commands)


def evaluate(*, repo_root: Path, policy: dict[str, Any], makefile: Path) -> list[str]:
    dependencies = _make_dependencies(makefile)
    aggregate_closures = {
        str(aggregate): _closure(str(aggregate), dependencies=dependencies)
        for aggregate in policy["aggregate_targets"]
    }
    failures: list[str] = []
    for control in policy["controls"]:
        target = str(control.get("target", "")) if isinstance(control, dict) else ""
        missing_aggregates = [
            aggregate for aggregate, closure in aggregate_closures.items() if target not in closure
        ]
        if missing_aggregates:
            failures.append(
                "CI lane parity target is not an aggregate prerequisite: "
                f"{target} missing from {', '.join(missing_aggregates)}"
            )
            continue
        lane_signals = control.get("lane_signals") if isinstance(control, dict) else None
        if not isinstance(lane_signals, dict):
            failures.append(f"CI lane parity target has no lane_signals: {target}")
            continue
        for lane, signals in lane_signals.items():
            workflow_path = policy["lanes"].get(lane)
            if not isinstance(workflow_path, str) or not isinstance(signals, list):
                failures.append(f"CI lane parity target has invalid lane mapping: {target}:{lane}")
                continue
            path = repo_root / workflow_path
            if not any(
                isinstance(signal, str) and _signal_has_executable_evidence(signal, path=path)
                for signal in signals
            ):
                failures.append(
                    f"CI lane parity missing executable evidence for {target} in {lane}"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="quality/ci-lane-parity.v1.json")
    parser.add_argument("--makefile", default="Makefile")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    failures = evaluate(
        repo_root=root,
        policy=load_policy(root / arguments.policy),
        makefile=root / arguments.makefile,
    )
    if failures:
        print("CI lane parity gate FAILED.")
        print(*[f"- {failure}" for failure in failures], sep="\n")
        return 1
    print("CI lane parity gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
