from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BanditSeveritySummary:
    issue_count: int
    high_count: int
    medium_count: int
    low_count: int


def parse_bandit_report(payload_text: str) -> BanditSeveritySummary:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Bandit did not return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Bandit JSON payload must be an object.")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("Bandit JSON payload is missing a results array.")

    severities: Counter[str] = Counter()
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Bandit result entries must be objects.")
        severity = result.get("issue_severity")
        if isinstance(severity, str):
            severities[severity.upper()] += 1

    return BanditSeveritySummary(
        issue_count=len(results),
        high_count=severities["HIGH"],
        medium_count=severities["MEDIUM"],
        low_count=severities["LOW"],
    )


def run_bandit(
    repo_root: Path,
    source_path: str,
    config_path: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-q",
            "-r",
            source_path,
            "-c",
            config_path,
            "-f",
            "json",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when Bandit reports high-severity findings.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing the Bandit configuration.",
    )
    parser.add_argument("--source-path", default="src", help="Path to scan from the repo root.")
    parser.add_argument(
        "--config",
        default="pyproject.toml",
        help="Bandit configuration path relative to the repo root.",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    completed = run_bandit(repo_root, args.source_path, args.config)
    if completed.returncode not in {0, 1}:
        print(completed.stderr.strip() or "Bandit execution failed.", file=sys.stderr)
        return 1

    try:
        summary = parse_bandit_report(completed.stdout)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        "Bandit high-severity gate: "
        f"high={summary.high_count}, medium={summary.medium_count}, "
        f"low={summary.low_count}, total={summary.issue_count}"
    )
    if summary.high_count > 0:
        print("Bandit high-severity gate failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
