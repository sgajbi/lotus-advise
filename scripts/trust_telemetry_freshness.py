"""Validate and refresh repo-owned trust telemetry freshness posture."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TELEMETRY_DIR = REPO_ROOT / "contracts" / "trust-telemetry"
DEFAULT_REFERENCE_TIME_UTC = "2026-07-11T00:00:00Z"
STALE_BLOCK_REASON = "TRUST_TELEMETRY_STALE"


def parse_utc_timestamp(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty UTC timestamp")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone")
    return parsed.astimezone(timezone.utc)


def format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def iter_snapshot_paths(path: Path = DEFAULT_TELEMETRY_DIR) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        candidate
        for candidate in path.glob("*.json")
        if candidate.name != "trust-telemetry-snapshot.schema.json"
    )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: trust telemetry snapshot must be an object")
    return cast(dict[str, Any], payload)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def derived_age_seconds(*, observed_at_utc: datetime, reference_time_utc: datetime) -> int:
    return int((reference_time_utc - observed_at_utc).total_seconds())


def derived_freshness_state(*, age_seconds: int, max_allowed_age_seconds: int | None) -> str:
    if age_seconds < 0:
        return "unknown"
    if max_allowed_age_seconds is None:
        return "unknown"
    return "current" if age_seconds <= max_allowed_age_seconds else "stale"


def _freshness_observed_at(freshness: dict[str, Any]) -> datetime:
    observed = freshness.get("observed_at_utc") or freshness.get("evaluated_at_utc")
    return parse_utc_timestamp(observed, field_name="freshness.observed_at_utc")


def _max_allowed_age_seconds(freshness: dict[str, Any]) -> int | None:
    value = freshness.get("max_allowed_age_seconds")
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("freshness.max_allowed_age_seconds must be a positive integer")
    return value


def expected_freshness_patch(
    payload: dict[str, Any],
    *,
    reference_time_utc: datetime,
    repository_commit_sha: str,
    validation_run_id: str,
) -> dict[str, Any]:
    patched = deepcopy(payload)
    freshness = patched.get("freshness")
    if not isinstance(freshness, dict):
        raise ValueError("freshness must be an object")

    observed_at_utc = _freshness_observed_at(freshness)
    max_allowed_age_seconds = _max_allowed_age_seconds(freshness)
    age_seconds = derived_age_seconds(
        observed_at_utc=observed_at_utc,
        reference_time_utc=reference_time_utc,
    )
    state = derived_freshness_state(
        age_seconds=age_seconds,
        max_allowed_age_seconds=max_allowed_age_seconds,
    )

    freshness["evaluated_at_utc"] = format_utc_timestamp(reference_time_utc)
    freshness["age_seconds"] = max(age_seconds, 0)
    freshness["freshness_state"] = state
    patched["emitted_at_utc"] = format_utc_timestamp(reference_time_utc)

    evidence = patched.setdefault("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    evidence["freshness_reference_time_utc"] = format_utc_timestamp(reference_time_utc)
    evidence["repository_commit_sha"] = repository_commit_sha
    evidence["validation_run_id"] = validation_run_id

    if state == "stale":
        patched["blocking"] = {
            "blocked": True,
            "blocked_reason": STALE_BLOCK_REASON,
            "blocked_summary": (
                "Trust telemetry evidence is older than the declared maximum age and must be "
                "regenerated from current implementation evidence before promotion."
            ),
        }
    elif state == "current":
        patched["blocking"] = {"blocked": False}
    else:
        patched["blocking"] = {
            "blocked": True,
            "blocked_reason": "TRUST_TELEMETRY_FRESHNESS_UNKNOWN",
            "blocked_summary": (
                "Trust telemetry freshness cannot be derived from the committed snapshot."
            ),
        }
    return patched


def validate_snapshot(
    path: Path,
    payload: dict[str, Any],
    *,
    reference_time_utc: datetime,
    repository_commit_sha: str,
    validation_run_id: str,
) -> list[str]:
    failures: list[str] = []
    try:
        expected = expected_freshness_patch(
            payload,
            reference_time_utc=reference_time_utc,
            repository_commit_sha=repository_commit_sha,
            validation_run_id=validation_run_id,
        )
    except ValueError as exc:
        return [f"{path}: {exc}"]

    freshness = payload.get("freshness")
    if not isinstance(freshness, dict):
        return [f"{path}: freshness must be an object"]

    observed_at = freshness.get("observed_at_utc") or freshness.get("evaluated_at_utc")
    try:
        observed_at_utc = parse_utc_timestamp(observed_at, field_name="freshness.observed_at_utc")
    except ValueError as exc:
        failures.append(f"{path}: {exc}")
        observed_at_utc = reference_time_utc
    if observed_at_utc > reference_time_utc:
        failures.append(f"{path}: freshness.observed_at_utc cannot be future-dated")

    expected_freshness = expected["freshness"]
    for field_name in ("evaluated_at_utc", "age_seconds", "freshness_state"):
        if freshness.get(field_name) != expected_freshness[field_name]:
            failures.append(
                f"{path}: freshness.{field_name} must be {expected_freshness[field_name]!r}"
            )

    expected_blocking = expected["blocking"]
    if payload.get("blocking") != expected_blocking:
        failures.append(f"{path}: blocking posture must match derived freshness state")

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        failures.append(f"{path}: evidence must be an object")
    else:
        expected_reference_time = expected["evidence"]["freshness_reference_time_utc"]
        if evidence.get("freshness_reference_time_utc") != expected_reference_time:
            failures.append(
                f"{path}: evidence.freshness_reference_time_utc must be {expected_reference_time!r}"
            )
        for field_name in ("repository_commit_sha", "validation_run_id"):
            if not isinstance(evidence.get(field_name), str) or not evidence[field_name].strip():
                failures.append(f"{path}: evidence.{field_name} must be a non-empty string")
    return failures


def validate_path(
    path: Path = DEFAULT_TELEMETRY_DIR,
    *,
    reference_time_utc: datetime,
    repository_commit_sha: str,
    validation_run_id: str,
) -> list[str]:
    failures: list[str] = []
    snapshot_paths = iter_snapshot_paths(path)
    if not snapshot_paths:
        return [f"{path}: no trust telemetry snapshot files found"]
    for snapshot_path in snapshot_paths:
        failures.extend(
            validate_snapshot(
                snapshot_path,
                load_json(snapshot_path),
                reference_time_utc=reference_time_utc,
                repository_commit_sha=repository_commit_sha,
                validation_run_id=validation_run_id,
            )
        )
    return failures


def refresh_path(
    path: Path = DEFAULT_TELEMETRY_DIR,
    *,
    reference_time_utc: datetime,
    repository_commit_sha: str,
    validation_run_id: str,
) -> None:
    for snapshot_path in iter_snapshot_paths(path):
        patched = expected_freshness_patch(
            load_json(snapshot_path),
            reference_time_utc=reference_time_utc,
            repository_commit_sha=repository_commit_sha,
            validation_run_id=validation_run_id,
        )
        write_json(snapshot_path, patched)


def current_commit_sha() -> str:
    configured = os.getenv("GIT_SHA")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "local"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate or refresh Lotus Advise trust telemetry freshness posture."
    )
    parser.add_argument(
        "mode",
        choices=("check", "write"),
        help="Use check to validate committed snapshots or write to refresh derived freshness.",
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_TELEMETRY_DIR)
    parser.add_argument(
        "--reference-time-utc",
        default=os.getenv("TRUST_TELEMETRY_REFERENCE_TIME_UTC", DEFAULT_REFERENCE_TIME_UTC),
    )
    parser.add_argument("--repository-commit-sha", default=current_commit_sha())
    parser.add_argument(
        "--validation-run-id",
        default=os.getenv("CI_PIPELINE_ID", "local-trust-telemetry-freshness"),
    )
    args = parser.parse_args(argv)

    reference_time_utc = parse_utc_timestamp(
        args.reference_time_utc,
        field_name="reference_time_utc",
    )
    if args.mode == "write":
        refresh_path(
            args.path,
            reference_time_utc=reference_time_utc,
            repository_commit_sha=args.repository_commit_sha,
            validation_run_id=args.validation_run_id,
        )
        return 0

    failures = validate_path(
        args.path,
        reference_time_utc=reference_time_utc,
        repository_commit_sha=args.repository_commit_sha,
        validation_run_id=args.validation_run_id,
    )
    if failures:
        for failure in failures:
            print(failure)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
