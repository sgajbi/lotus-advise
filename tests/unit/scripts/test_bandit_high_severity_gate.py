from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from scripts import bandit_high_severity_gate
from scripts.bandit_high_severity_gate import (
    build_current_baseline_payload,
    parse_bandit_findings,
    parse_bandit_report,
    validate_bandit_report_against_baseline,
)


def _payload(*severities: str) -> str:
    return json.dumps(
        {
            "results": [
                {
                    "code": f"{index} value = 'stable-{index}'",
                    "filename": f"src/example_{index}.py",
                    "issue_confidence": "LOW",
                    "issue_severity": severity,
                    "issue_text": "Possible issue.",
                    "line_number": index + 10,
                    "test_id": "B608",
                    "test_name": "hardcoded_sql_expressions",
                }
                for index, severity in enumerate(severities)
            ]
        }
    )


def _baseline_payload(payload: str, *, expires_on: str = "2026-12-31") -> dict[str, object]:
    return build_current_baseline_payload(
        payload,
        owner="lotus-advise-security",
        rationale="Accepted fixture baseline.",
        expires_on=date.fromisoformat(expires_on),
        linked_remediation="https://github.com/sgajbi/lotus-advise/issues/435",
        compensating_control="Regression gate blocks new or worsened findings.",
    )


def _write_baseline(tmp_path: Path, payload: dict[str, object]) -> Path:
    baseline = tmp_path / "bandit-baseline.json"
    baseline.write_text(json.dumps(payload), encoding="utf-8")
    return baseline


def test_parse_bandit_report_counts_result_severities() -> None:
    summary = parse_bandit_report(_payload("HIGH", "MEDIUM", "MEDIUM", "LOW"))

    assert summary.issue_count == 4
    assert summary.high_count == 1
    assert summary.medium_count == 2
    assert summary.low_count == 1


def test_parse_bandit_findings_uses_stable_line_independent_fingerprint() -> None:
    payload_a = _payload("MEDIUM")
    result = json.loads(payload_a)
    result["results"][0]["code"] = "99 value = 'stable-0'"
    result["results"][0]["line_number"] = 99
    payload_b = json.dumps(result)

    assert (
        parse_bandit_findings(payload_a)[0].fingerprint
        == parse_bandit_findings(payload_b)[0].fingerprint
    )


def test_main_passes_when_bandit_findings_match_active_baseline(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    payload = _payload("MEDIUM", "LOW")
    baseline_path = _write_baseline(tmp_path, _baseline_payload(payload))
    monkeypatch.setattr(
        bandit_high_severity_gate,
        "run_bandit",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=payload,
            stderr="",
        ),
    )

    exit_code = bandit_high_severity_gate.main(
        ["--repo-root", str(tmp_path), "--baseline", str(baseline_path)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "high=0, medium=1, low=1, total=2" in captured.out


def test_main_fails_when_bandit_reports_high_severity(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        bandit_high_severity_gate,
        "run_bandit",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=_payload("HIGH", "MEDIUM"),
            stderr="",
        ),
    )

    exit_code = bandit_high_severity_gate.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "high=1, medium=1, low=0, total=2" in captured.out
    assert "Bandit high-severity finding is never baselined" in captured.err
    assert "Bandit severity-regression gate failed." in captured.err


def test_validate_baseline_fails_on_new_medium_or_low_finding(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path, _baseline_payload(_payload("MEDIUM")))

    summary, failures = validate_bandit_report_against_baseline(
        _payload("MEDIUM", "LOW"),
        baseline,
        today=date(2026, 7, 11),
    )

    assert summary.medium_count == 1
    assert summary.low_count == 1
    assert any("New Bandit LOW finding" in failure for failure in failures)


def test_validate_baseline_fails_on_resolved_stale_finding(tmp_path: Path) -> None:
    baseline = _write_baseline(tmp_path, _baseline_payload(_payload("MEDIUM", "LOW")))

    _, failures = validate_bandit_report_against_baseline(
        _payload("MEDIUM"),
        baseline,
        today=date(2026, 7, 11),
    )

    assert any("Stale Bandit baseline entry" in failure for failure in failures)


def test_validate_baseline_fails_on_severity_increase(tmp_path: Path) -> None:
    baseline_payload = _baseline_payload(_payload("LOW"))
    baseline = _write_baseline(tmp_path, baseline_payload)
    current = json.loads(_payload("LOW"))
    current["results"][0]["issue_severity"] = "MEDIUM"

    _, failures = validate_bandit_report_against_baseline(
        json.dumps(current),
        baseline,
        today=date(2026, 7, 11),
    )

    assert any("Bandit severity increased" in failure for failure in failures)


def test_validate_baseline_fails_on_expired_exception(tmp_path: Path) -> None:
    payload = _payload("MEDIUM")
    baseline = _write_baseline(tmp_path, _baseline_payload(payload, expires_on="2026-01-01"))

    _, failures = validate_bandit_report_against_baseline(
        payload,
        baseline,
        today=date(2026, 7, 11),
    )

    assert any("expired on 2026-01-01" in failure for failure in failures)


def test_validate_baseline_reports_invalid_baseline_metadata(tmp_path: Path) -> None:
    payload = _payload("MEDIUM")
    baseline_payload = _baseline_payload(payload)
    baseline_payload["entries"][0]["severity"] = "UNKNOWN"
    baseline_payload["entries"][0]["confidence"] = "UNKNOWN"
    baseline = _write_baseline(tmp_path, baseline_payload)

    _, failures = validate_bandit_report_against_baseline(
        payload,
        baseline,
        today=date(2026, 7, 11),
    )

    assert any("invalid severity" in failure for failure in failures)
    assert any("invalid confidence" in failure for failure in failures)


def test_main_fails_when_bandit_output_is_not_valid_json(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        bandit_high_severity_gate,
        "run_bandit",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="{", stderr=""),
    )

    exit_code = bandit_high_severity_gate.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Bandit did not return valid JSON." in captured.err


def test_main_reports_bandit_stderr_when_report_is_empty(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        bandit_high_severity_gate,
        "run_bandit",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="No module named bandit",
        ),
    )

    exit_code = bandit_high_severity_gate.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No module named bandit" in captured.err
