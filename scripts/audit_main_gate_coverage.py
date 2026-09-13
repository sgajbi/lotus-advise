"""Fail closed when a recent main revision lacks a determinable releasability verdict."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass

WORKFLOW = "main-releasability.yml"
_RUN_HISTORY_LIMIT = 100
_TERMINAL_CONCLUSIONS = frozenset(
    {
        "success",
        "failure",
        "cancelled",
        "skipped",
        "timed_out",
        "action_required",
        "neutral",
        "stale",
    }
)


@dataclass(frozen=True)
class MainGateRun:
    database_id: int
    conclusion: str | None
    status: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class MainGateRunHistory:
    runs: tuple[MainGateRun, ...]
    complete: bool


def _git(*arguments: str) -> list[str]:
    completed = subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _run_history(sha: str) -> MainGateRunHistory | None:
    completed = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            WORKFLOW,
            "--commit",
            sha,
            "--limit",
            str(_RUN_HISTORY_LIMIT),
            "--json",
            "databaseId,conclusion,status,headBranch,createdAt,updatedAt",
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    expected_branch = f"main-releasability-{sha}"
    matching = [
        run for run in payload if isinstance(run, dict) and run.get("headBranch") == expected_branch
    ]
    try:
        runs = tuple(_parse_run(run) for run in matching)
    except (KeyError, TypeError, ValueError):
        return None
    # The CLI exposes no continuation marker. A full page cannot prove complete evidence.
    return MainGateRunHistory(runs=runs, complete=len(payload) < _RUN_HISTORY_LIMIT)


def _parse_run(value: dict[str, object]) -> MainGateRun:
    database_id = value["databaseId"]
    created_at = value["createdAt"]
    updated_at = value["updatedAt"]
    if (
        not isinstance(database_id, int)
        or not isinstance(created_at, str)
        or not isinstance(updated_at, str)
    ):
        raise ValueError("MAIN_GATE_RUN_HISTORY_UNREADABLE")
    conclusion = value.get("conclusion")
    status = value.get("status")
    if conclusion is not None and not isinstance(conclusion, str):
        raise ValueError("MAIN_GATE_RUN_HISTORY_UNREADABLE")
    if status is not None and not isinstance(status, str):
        raise ValueError("MAIN_GATE_RUN_HISTORY_UNREADABLE")
    return MainGateRun(
        database_id=database_id,
        conclusion=conclusion,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )


def _latest_applicable_terminal_verdict(history: MainGateRunHistory) -> str | None:
    if not history.complete or not history.runs:
        return None
    latest_time = max(run.updated_at for run in history.runs)
    latest = [run for run in history.runs if run.updated_at == latest_time]
    if any(run.status != "completed" or run.conclusion is None for run in latest):
        return None
    conclusions = {str(run.conclusion).lower() for run in latest}
    if len(conclusions) != 1 or not conclusions <= _TERMINAL_CONCLUSIONS:
        return None
    # Identity retains retry ordering; different verdicts at one observed time are ambiguous.
    _ = max(run.database_id for run in latest)
    return conclusions.pop()


def _classify_coverage(
    commits: list[str], *, histories_for_sha: dict[str, MainGateRunHistory | None]
) -> tuple[list[str], list[str], list[str], int]:
    ungated: list[str] = []
    unknown: list[str] = []
    failing: list[str] = []
    passing = 0
    for entry in commits:
        sha, short, subject = entry.split(" ", 2)
        history = histories_for_sha[sha]
        if history is None:
            unknown.append(short)
            continue
        if not history.runs:
            ungated.append(f"{short}  {subject[:70]}")
            continue
        verdict = _latest_applicable_terminal_verdict(history)
        if verdict == "success":
            passing += 1
        elif verdict == "failure":
            failing.append(f"{short}  {subject[:70]}")
        else:
            unknown.append(short)
    return ungated, unknown, failing, passing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--fail-on-gap", action="store_true")
    arguments = parser.parse_args()
    if arguments.since_days < 1 or arguments.limit < 1:
        raise ValueError("--since-days and --limit must be positive.")
    if shutil.which("gh") is None:
        print("gh is not available; main-gate coverage is unverifiable.")
        return 1 if arguments.fail_on_gap else 0

    probed = _git(
        "log",
        f"--since-as-filter={arguments.since_days} days ago",
        f"-{arguments.limit + 1}",
        "--format=%H %h %s",
        "origin/main",
    )
    truncated = len(probed) > arguments.limit
    commits = probed[: arguments.limit]
    histories_for_sha = {
        entry.split(" ", 1)[0]: _run_history(entry.split(" ", 1)[0]) for entry in commits
    }
    ungated, unknown, failing, passing = _classify_coverage(
        commits,
        histories_for_sha=histories_for_sha,
    )
    for entry in ungated:
        print(f"UNGATED  {entry}")
    for short in unknown:
        print(
            f"UNKNOWN  {short}  "
            "(run history is unreadable, incomplete, or lacks one terminal verdict)"
        )
    for entry in failing:
        print(f"FAILING  {entry}")
    print(
        f"audited {len(commits)} commit(s): {len(ungated)} ungated, {len(unknown)} unknown, "
        f"{passing} passing, {len(failing)} failing latest verdict(s)."
    )
    if truncated:
        print("WINDOW TRUNCATED: raise --limit; an unexamined window is not covered.")
    return 1 if arguments.fail_on_gap and (ungated or unknown or truncated) else 0


if __name__ == "__main__":
    sys.exit(main())
