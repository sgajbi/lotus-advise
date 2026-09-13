"""Verify selected aggregate Make controls remain live in applicable CI lanes."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_SCHEMA_VERSION = "lotus.advise.ci-lane-parity.v1"
_TARGET = re.compile(r"^(?P<target>[A-Za-z0-9_-]+):(?P<dependencies>.*)$")
_GITHUB_EXPRESSION = re.compile(r"\$\{\{.*?\}\}")
_PYTHON_INTERPRETERS = frozenset({"python", "python3", "python3.11"})
_PYTEST_SUPPORTED_FLAGS = frozenset({"-q", "--quiet"})
_PYTEST_SUPPORTED_VALUE_OPTIONS = frozenset(
    {
        "--capture",
        "--color",
        "--confcutdir",
        "--cov",
        "--cov-config",
        "--cov-report",
        "--durations",
        "--junitxml",
        "--maxfail",
        "--rootdir",
        "--tb",
    }
)
_CHANGED_COVERAGE_REQUIRED_OPTIONS = frozenset(
    {"--base-ref", "--head-ref", "--coverage-data", "--policy", "--output"}
)
_NONEXECUTING_MAKEFLAGS = frozenset(
    {"--dry-run", "--just-print", "--recon", "--touch", "--question"}
)
_NONEXECUTING_MAKEFLAG_SHORT_FORMS = frozenset({"n", "t", "q"})
_SHELL_CONTROL_OPERATORS = frozenset({"&&", "||", ";", "|", "&"})


@dataclass(frozen=True)
class WorkflowStep:
    """One parsed executable workflow step and the context that owns it."""

    job_name: str
    run: str
    condition: object | None
    environment: Mapping[str, str] | None
    matrix_paths: frozenset[str]


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


def _string_mapping(value: object) -> dict[str, str] | None:
    """Return a conservative workflow environment mapping.

    GitHub Actions accepts values beyond strings, but an unknown environment shape cannot be
    executable evidence.  The parity gate therefore refuses it rather than silently dropping a
    value such as ``MAKEFLAGS``.
    """

    if value is None:
        return {}
    if not isinstance(value, Mapping):
        return None
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, (str, int, float, bool)):
            return None
        result[key] = str(item)
    return result


def _matrix_paths(job: Mapping[str, object]) -> frozenset[str]:
    """Collect only effective test paths owned by this job's declared matrix."""

    strategy = job.get("strategy")
    if not isinstance(strategy, Mapping):
        return frozenset()
    matrix = strategy.get("matrix")
    if not isinstance(matrix, Mapping):
        return frozenset()
    values: set[str] = set()
    path_value = matrix.get("path")
    path_values = path_value if isinstance(path_value, list) else [path_value]
    values.update(
        value for value in path_values if isinstance(value, str) and value.startswith("tests/")
    )
    include = matrix.get("include")
    if isinstance(include, list):
        values.update(
            value
            for item in include
            if isinstance(item, Mapping)
            for value in [item.get("path")]
            if isinstance(value, str) and value.startswith("tests/")
        )
    exclude = matrix.get("exclude")
    if isinstance(exclude, list):
        excluded_paths = {
            value
            for item in exclude
            if isinstance(item, Mapping)
            for value in [item.get("path")]
            if isinstance(value, str) and value.startswith("tests/")
        }
        values.difference_update(excluded_paths)
    return frozenset(values)


def _workflow_steps(path: Path) -> list[WorkflowStep]:
    """Parse executable steps with their owning job, conditions, environment and matrix."""

    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"CI lane parity workflow is not valid YAML: {path}") from exc
    if not isinstance(document, Mapping) or not isinstance(document.get("jobs"), Mapping):
        raise ValueError(f"CI lane parity workflow has no jobs mapping: {path}")
    root_environment = _string_mapping(document.get("env"))
    if root_environment is None:
        return []
    result: list[WorkflowStep] = []
    for job_name, job_value in document["jobs"].items():
        if not isinstance(job_name, str) or not isinstance(job_value, Mapping):
            continue
        job_environment = _string_mapping(job_value.get("env"))
        if job_environment is None:
            continue
        job_condition = job_value.get("if")
        matrix_paths = _matrix_paths(job_value)
        steps = job_value.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, Mapping) or not isinstance(step.get("run"), str):
                continue
            step_environment = _string_mapping(step.get("env"))
            environment = None
            if step_environment is not None:
                environment = root_environment | job_environment | step_environment
            result.append(
                WorkflowStep(
                    job_name=job_name,
                    run=step["run"],
                    condition=(job_condition, step.get("if")),
                    environment=environment,
                    matrix_paths=matrix_paths,
                )
            )
    return result


def _normalize_github_expressions(command: str) -> str:
    """Keep GitHub expressions atomic while tokenizing a shell command."""

    return _GITHUB_EXPRESSION.sub(
        lambda match: "matrix.path" if "matrix.path" in match.group(0) else "github.expression",
        command,
    )


def _condition_may_execute(condition: object | None) -> bool:
    """Reject explicit-false conditions; do not guess at dynamic expressions."""

    if isinstance(condition, tuple):
        return all(_condition_may_execute(value) for value in condition)
    if condition is None:
        return True
    if isinstance(condition, bool):
        return condition
    if not isinstance(condition, str):
        return False
    expression = condition.strip().lower()
    if expression.startswith("${{") and expression.endswith("}}"):
        expression = expression[3:-2].strip()
    false_literals = {"false", "0", "null", "none"}
    if expression in false_literals:
        return False
    literal_values = {"false": False, "true": True, "0": False, "1": True}
    disjunctions = expression.split("||")
    conjunctions = [disjunction.split("&&") for disjunction in disjunctions]
    if all(term.strip() in literal_values for conjunction in conjunctions for term in conjunction):
        return any(
            all(literal_values[term.strip()] for term in conjunction)
            for conjunction in conjunctions
        )
    # A conjunction with a literal false operand is statically false.  We deliberately do not
    # evaluate general GitHub expressions or conditions containing disjunctions as shell-like
    # program text: those are runtime semantics, not parity evidence parsing.
    return not (
        "||" not in expression
        and any(term.strip() in false_literals for term in expression.split("&&"))
    )


def _commands_in_step(step: WorkflowStep) -> list[tuple[str, ...]]:
    """Extract direct command lines, refusing shell-control expressions as evidence.

    This deliberately supports command tokenization, continuations, and GitHub expression
    normalization only.  It is not a shell interpreter: short-circuiting, pipelines, and command
    lists are ambiguous evidence and cannot prove a blocking control ran.
    """

    if not _condition_may_execute(step.condition) or step.environment is None:
        return []
    commands: list[tuple[str, ...]] = []
    current = ""
    for line in step.run.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        current = f"{current} {candidate}".strip()
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        try:
            lexer = shlex.shlex(
                _normalize_github_expressions(current), posix=True, punctuation_chars="|&;"
            )
            lexer.whitespace_split = True
            lexer.commenters = "#"
            tokens = tuple(lexer)
        except ValueError:
            tokens = ()
        if tokens and not any(token in _SHELL_CONTROL_OPERATORS for token in tokens):
            commands.append(tokens)
        current = ""
    return commands


def _makeflags_may_execute(environment: Mapping[str, str]) -> bool:
    """Reject documented Make no-op flags in the environment owning a control step."""

    makeflags = environment.get("MAKEFLAGS")
    if makeflags is None:
        return True
    if "${{" in makeflags:
        return False
    try:
        flags = shlex.split(makeflags, comments=True, posix=True)
    except ValueError:
        return False
    for flag in flags:
        if flag in _NONEXECUTING_MAKEFLAGS:
            return False
        compact = flag[1:] if flag.startswith("-") and not flag.startswith("--") else flag
        if not flag.startswith("--") and any(
            character in _NONEXECUTING_MAKEFLAG_SHORT_FORMS for character in compact
        ):
            return False
    return True


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


def _python_script_arguments(command: tuple[str, ...]) -> tuple[str, ...] | None:
    """Return arguments after a supported Python script invocation."""

    command_index = 2 if command[:2] == ("uv", "run") else 0
    if (
        len(command) <= command_index + 1
        or command[command_index] not in _PYTHON_INTERPRETERS
        or command[command_index + 1].startswith("-")
    ):
        return None
    return command[command_index + 2 :]


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


def _pytest_collection_targets(arguments: tuple[str, ...]) -> set[str] | None:
    """Return collection targets for the bounded supported pytest option grammar.

    An unknown option is not interpreted as a harmless flag.  It could select no tests, display
    cached data, or otherwise change collection, so it is refused as executable evidence.
    """

    targets: set[str] = set()
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            return None
        if argument in _PYTEST_SUPPORTED_FLAGS:
            index += 1
            continue
        if argument.startswith("-"):
            option, separator, value = argument.partition("=")
            if option not in _PYTEST_SUPPORTED_VALUE_OPTIONS:
                return None
            if separator:
                if not value and option != "--cov-report":
                    return None
                index += 1
                continue
            if index + 1 >= len(arguments) or arguments[index + 1].startswith("-"):
                return None
            index += 2
            continue
        targets.add(argument)
        index += 1
    return targets


def _executes_pytest_signal(command: tuple[str, ...], signal: str) -> bool:
    """Require the named test path to run without a non-executing/filtering mode."""

    pytest_index = _pytest_program_index(command)
    if pytest_index is None:
        return False
    arguments = command[pytest_index + 1 :]
    targets = _pytest_collection_targets(arguments)
    return targets is not None and signal in targets


def _executes_changed_coverage_gate(command: tuple[str, ...]) -> bool:
    """Require the changed-coverage program to receive its attributable inputs."""

    if not _executes_python_script(command, "scripts/changed_coverage_gate.py"):
        return False
    arguments = _python_script_arguments(command)
    if arguments is None:
        return False
    values: dict[str, str] = {}
    allowed_options = _CHANGED_COVERAGE_REQUIRED_OPTIONS | {"--skip-reason"}
    index = 0
    while index < len(arguments):
        option, separator, value = arguments[index].partition("=")
        if option not in allowed_options:
            return False
        if separator:
            if not value:
                return False
        else:
            if index + 1 >= len(arguments) or arguments[index + 1].startswith("--"):
                return False
            value = arguments[index + 1]
            index += 1
        if option == "--skip-reason" or option in values:
            return False
        values[option] = value
        index += 1
    return _CHANGED_COVERAGE_REQUIRED_OPTIONS <= values.keys()


def _signal_has_executable_evidence(signal: str, *, path: Path) -> bool:
    steps = _workflow_steps(path)
    signal_tokens = tuple(shlex.split(signal, comments=True, posix=True))
    if not signal_tokens:
        return False
    if signal_tokens[0] == "make":
        return any(
            step.environment is not None
            and _makeflags_may_execute(step.environment)
            and any(command == signal_tokens for command in _commands_in_step(step))
            for step in steps
        )
    if signal.startswith("scripts/"):
        if signal == "scripts/changed_coverage_gate.py":
            return any(
                _executes_changed_coverage_gate(command)
                for step in steps
                for command in _commands_in_step(step)
            )
        return any(
            _executes_python_script(command, signal)
            for step in steps
            for command in _commands_in_step(step)
        )
    if signal.startswith("tests/"):
        return any(
            _executes_pytest_signal(command, signal)
            or (signal in step.matrix_paths and _executes_pytest_signal(command, "matrix.path"))
            for step in steps
            for command in _commands_in_step(step)
            if _pytest_program_index(command) is not None
        )
    return any(
        command[: len(signal_tokens)] == signal_tokens
        for step in steps
        for command in _commands_in_step(step)
    )


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
