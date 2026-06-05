from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import bandit_high_severity_gate
from scripts.bandit_high_severity_gate import parse_bandit_report


def _payload(*severities: str) -> str:
    return json.dumps(
        {
            "results": [
                {"issue_severity": severity, "filename": f"src/example_{index}.py"}
                for index, severity in enumerate(severities)
            ]
        }
    )


def test_parse_bandit_report_counts_result_severities() -> None:
    summary = parse_bandit_report(_payload("HIGH", "MEDIUM", "MEDIUM", "LOW"))

    assert summary.issue_count == 4
    assert summary.high_count == 1
    assert summary.medium_count == 2
    assert summary.low_count == 1


def test_main_passes_when_bandit_reports_no_high_severity(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        bandit_high_severity_gate,
        "run_bandit",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=_payload("MEDIUM", "LOW"),
            stderr="",
        ),
    )

    exit_code = bandit_high_severity_gate.main(["--repo-root", str(tmp_path)])

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
    assert "Bandit high-severity gate failed." in captured.err


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
