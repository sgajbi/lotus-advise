from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from scripts.trust_telemetry_freshness import (
    STALE_BLOCK_REASON,
    certified_runtime_snapshot,
    expected_freshness_patch,
    main,
    parse_utc_timestamp,
    validate_snapshot,
)

REFERENCE_TIME = parse_utc_timestamp("2026-07-11T00:00:00Z", field_name="test")


def _snapshot(*, observed_at_utc: str = "2026-07-10T12:00:00Z") -> dict[str, Any]:
    return {
        "product_id": "lotus-advise:TestProduct:v1",
        "emitted_at_utc": observed_at_utc,
        "freshness": {
            "freshness_class": "event_driven",
            "freshness_state": "current",
            "evaluated_at_utc": observed_at_utc,
            "observed_at_utc": observed_at_utc,
            "age_seconds": 0,
            "max_allowed_age_seconds": 86400,
        },
        "blocking": {"blocked": False},
        "completeness_status": "complete",
        "data_quality_status": "quality_passed",
        "lineage": {
            "lineage_materialized": True,
            "lineage_bundle_id": "lineage:historical",
            "evidence_uris": ["lotus-advise://tests/evidence"],
        },
        "observed_trust_metadata": {"generated_at": observed_at_utc},
        "evidence": {"correlation_id": "test", "validation_lanes": ["feature"]},
    }


def test_expected_freshness_patch_preserves_current_posture_with_current_evidence() -> None:
    payload = _snapshot(observed_at_utc="2026-07-11T00:00:00Z")

    patched = expected_freshness_patch(
        payload,
        reference_time_utc=REFERENCE_TIME,
        repository_commit_sha="abc123",
        validation_run_id="run-1",
    )

    assert patched["freshness"]["freshness_state"] == "current"
    assert patched["freshness"]["age_seconds"] == 0
    assert patched["blocking"] == {"blocked": False}
    assert patched["evidence"]["repository_commit_sha"] == "abc123"
    assert patched["evidence"]["validation_run_id"] == "run-1"


def test_expected_freshness_patch_marks_stale_evidence_blocked() -> None:
    payload = _snapshot(observed_at_utc="2026-07-09T00:00:00Z")

    patched = expected_freshness_patch(
        payload,
        reference_time_utc=REFERENCE_TIME,
        repository_commit_sha="abc123",
        validation_run_id="run-1",
    )

    assert patched["freshness"]["freshness_state"] == "stale"
    assert patched["freshness"]["age_seconds"] == 172800
    assert patched["freshness"]["evaluated_at_utc"] == "2026-07-11T00:00:00Z"
    assert patched["blocking"]["blocked"] is True
    assert patched["blocking"]["blocked_reason"] == STALE_BLOCK_REASON


def test_validate_snapshot_rejects_current_age_zero_when_evidence_is_stale() -> None:
    payload = _snapshot(observed_at_utc="2026-07-09T00:00:00Z")

    failures = validate_snapshot(
        Path("snapshot.json"),
        payload,
        reference_time_utc=REFERENCE_TIME,
        repository_commit_sha="abc123",
        validation_run_id="run-1",
    )

    assert "snapshot.json: freshness.age_seconds must be 172800" in failures
    assert "snapshot.json: freshness.freshness_state must be 'stale'" in failures
    assert "snapshot.json: blocking posture must match derived freshness state" in failures


def test_validate_snapshot_rejects_future_dated_observation() -> None:
    payload = _snapshot(observed_at_utc="2026-07-12T00:00:00Z")

    failures = validate_snapshot(
        Path("snapshot.json"),
        payload,
        reference_time_utc=REFERENCE_TIME,
        repository_commit_sha="abc123",
        validation_run_id="run-1",
    )

    assert "snapshot.json: freshness.observed_at_utc cannot be future-dated" in failures


def test_validate_snapshot_rejects_missing_freshness_object() -> None:
    payload = _snapshot()
    del payload["freshness"]

    failures = validate_snapshot(
        Path("snapshot.json"),
        payload,
        reference_time_utc=REFERENCE_TIME,
        repository_commit_sha="abc123",
        validation_run_id="run-1",
    )

    assert "snapshot.json: freshness must be an object" in failures


def test_validate_snapshot_rejects_missing_evidence_identity() -> None:
    payload = expected_freshness_patch(
        _snapshot(observed_at_utc="2026-07-09T00:00:00Z"),
        reference_time_utc=REFERENCE_TIME,
        repository_commit_sha="abc123",
        validation_run_id="run-1",
    )
    mutated = deepcopy(payload)
    mutated["evidence"]["repository_commit_sha"] = ""

    failures = validate_snapshot(
        Path("snapshot.json"),
        mutated,
        reference_time_utc=REFERENCE_TIME,
        repository_commit_sha="abc123",
        validation_run_id="run-1",
    )

    assert "snapshot.json: evidence.repository_commit_sha must be a non-empty string" in failures


def test_cli_writes_and_checks_snapshot_directory(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "example.telemetry.v1.json"
    snapshot_path.write_text(
        '{"freshness":{"freshness_class":"event_driven","freshness_state":"current",'
        '"evaluated_at_utc":"2026-07-09T00:00:00Z",'
        '"observed_at_utc":"2026-07-09T00:00:00Z","age_seconds":0,'
        '"max_allowed_age_seconds":86400},"blocking":{"blocked":false},'
        '"evidence":{"correlation_id":"test","validation_lanes":["feature"]}}',
        encoding="utf-8",
    )

    common_args = [
        "--path",
        str(tmp_path),
        "--reference-time-utc",
        "2026-07-11T00:00:00Z",
        "--repository-commit-sha",
        "abc123",
        "--validation-run-id",
        "run-1",
    ]

    assert main(["check", *common_args]) == 1
    assert main(["write", *common_args]) == 0
    assert main(["check", *common_args]) == 0


def test_parse_utc_timestamp_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="must include timezone"):
        parse_utc_timestamp("2026-07-11T00:00:00", field_name="test")


def test_certified_runtime_snapshot_emits_current_commit_bound_evidence() -> None:
    source = _snapshot(observed_at_utc="2026-05-01T00:00:00Z")

    certified = certified_runtime_snapshot(
        source,
        certified_at_utc=REFERENCE_TIME,
        repository_commit_sha="a" * 40,
        validation_run_id="github-12345",
    )

    assert certified["freshness"]["freshness_state"] == "current"
    assert certified["freshness"]["age_seconds"] == 0
    assert certified["freshness"]["observed_at_utc"] == "2026-07-11T00:00:00Z"
    assert certified["blocking"] == {"blocked": False}
    assert certified["evidence"]["repository_commit_sha"] == "a" * 40
    assert certified["evidence"]["source_fixture_observed_at_utc"] == "2026-05-01T00:00:00Z"
    assert certified["lineage"]["lineage_bundle_id"].endswith("a" * 40)
    assert source["freshness"]["observed_at_utc"] == "2026-05-01T00:00:00Z"


@pytest.mark.parametrize(
    ("sha", "run_id", "message"),
    [
        ("abc123", "github-1", "full lowercase Git commit SHA"),
        ("a" * 40, "local-certification", "non-local CI validation run id"),
    ],
)
def test_certified_runtime_snapshot_rejects_weak_provenance(
    sha: str, run_id: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        certified_runtime_snapshot(
            _snapshot(),
            certified_at_utc=REFERENCE_TIME,
            repository_commit_sha=sha,
            validation_run_id=run_id,
        )


def test_certified_runtime_snapshot_rejects_missing_lineage() -> None:
    source = _snapshot()
    source["lineage"]["lineage_materialized"] = False

    with pytest.raises(ValueError, match="materialized lineage is required"):
        certified_runtime_snapshot(
            source,
            certified_at_utc=REFERENCE_TIME,
            repository_commit_sha="a" * 40,
            validation_run_id="github-12345",
        )
