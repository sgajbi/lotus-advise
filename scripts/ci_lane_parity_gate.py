"""Verify selected aggregate Make controls remain live in applicable CI lanes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SCHEMA_VERSION = "lotus.advise.ci-lane-parity.v1"
_TARGET = re.compile(r"^(?P<target>[A-Za-z0-9_-]+):(?P<dependencies>.*)$")


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
            workflow = (repo_root / workflow_path).read_text(encoding="utf-8")
            if not any(isinstance(signal, str) and signal in workflow for signal in signals):
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
