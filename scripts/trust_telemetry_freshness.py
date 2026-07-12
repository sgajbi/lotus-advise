"""Validate and refresh repo-owned trust telemetry freshness posture."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TELEMETRY_DIR = REPO_ROOT / "contracts" / "trust-telemetry"
DEFAULT_REFERENCE_TIME_UTC = "2026-07-11T00:00:00Z"
DEFAULT_RUNTIME_OUTPUT_DIR = REPO_ROOT / "output" / "trust-telemetry" / "runtime"
STALE_BLOCK_REASON = "TRUST_TELEMETRY_STALE"
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


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


def certified_runtime_snapshot(
    payload: dict[str, Any],
    *,
    certified_at_utc: datetime,
    repository_commit_sha: str,
    validation_run_id: str,
) -> dict[str, Any]:
    if not FULL_GIT_SHA.fullmatch(repository_commit_sha):
        raise ValueError("runtime certification requires a full lowercase Git commit SHA")
    if not validation_run_id.strip() or validation_run_id.startswith("local"):
        raise ValueError("runtime certification requires a non-local CI validation run id")
    product_id = payload.get("product_id")
    if not isinstance(product_id, str) or not product_id.startswith("lotus-advise:"):
        raise ValueError("runtime certification requires a lotus-advise product_id")
    if payload.get("completeness_status") != "complete":
        raise ValueError(f"{product_id}: incomplete product evidence cannot be certified")
    if payload.get("data_quality_status") != "quality_passed":
        raise ValueError(f"{product_id}: failed data quality evidence cannot be certified")
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict) or lineage.get("lineage_materialized") is not True:
        raise ValueError(f"{product_id}: materialized lineage is required")
    evidence_uris = lineage.get("evidence_uris")
    if not isinstance(evidence_uris, list) or not evidence_uris:
        raise ValueError(f"{product_id}: non-empty lineage evidence_uris are required")
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict) or not evidence.get("validation_lanes"):
        raise ValueError(f"{product_id}: governed validation lanes are required")

    certified = deepcopy(payload)
    certified_at = format_utc_timestamp(certified_at_utc)
    freshness = cast(dict[str, Any], certified["freshness"])
    freshness["observed_at_utc"] = certified_at
    certified = expected_freshness_patch(
        certified,
        reference_time_utc=certified_at_utc,
        repository_commit_sha=repository_commit_sha,
        validation_run_id=validation_run_id,
    )
    metadata = certified.get("observed_trust_metadata")
    if isinstance(metadata, dict) and "generated_at" in metadata:
        metadata["generated_at"] = certified_at
    certified["lineage"]["lineage_bundle_id"] = f"lineage:{product_id}:{repository_commit_sha}"
    certified["evidence"]["source_event_id"] = (
        f"source-event:{product_id}:ci-certification:{validation_run_id}"
    )
    certified["evidence"]["certification_basis"] = [
        "repo-native trust telemetry contract validation",
        "materialized lineage and source-safe evidence references",
        "complete product evidence and passed data-quality posture",
        "immutable repository commit and CI run identity",
    ]
    certified["evidence"]["source_fixture_observed_at_utc"] = payload.get("freshness", {}).get(
        "observed_at_utc"
    )
    return certified


def certify_runtime_path(
    path: Path = DEFAULT_TELEMETRY_DIR,
    *,
    output_directory: Path = DEFAULT_RUNTIME_OUTPUT_DIR,
    certified_at_utc: datetime,
    repository_commit_sha: str,
    validation_run_id: str,
) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    for existing in output_directory.glob("*.json"):
        existing.unlink()
    for snapshot_path in iter_snapshot_paths(path):
        certified = certified_runtime_snapshot(
            load_json(snapshot_path),
            certified_at_utc=certified_at_utc,
            repository_commit_sha=repository_commit_sha,
            validation_run_id=validation_run_id,
        )
        write_json(output_directory / snapshot_path.name, certified)


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
        choices=("check", "write", "certify"),
        help=(
            "Use check to validate committed snapshots, write to refresh derived fixture "
            "freshness, or certify to emit current CI-backed runtime snapshots."
        ),
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_TELEMETRY_DIR)
    parser.add_argument(
        "--reference-time-utc",
        default=os.getenv("TRUST_TELEMETRY_REFERENCE_TIME_UTC", DEFAULT_REFERENCE_TIME_UTC),
    )
    parser.add_argument("--repository-commit-sha", default=current_commit_sha())
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_RUNTIME_OUTPUT_DIR)
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
    if args.mode == "certify":
        try:
            certify_runtime_path(
                args.path,
                output_directory=args.output_directory,
                certified_at_utc=reference_time_utc,
                repository_commit_sha=args.repository_commit_sha,
                validation_run_id=args.validation_run_id,
            )
        except ValueError as exc:
            print(exc)
            return 1
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
