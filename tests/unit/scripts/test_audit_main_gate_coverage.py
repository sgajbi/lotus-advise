import pytest

import scripts.audit_main_gate_coverage as audit
from scripts.audit_main_gate_coverage import (
    MainGateRun,
    MainGateRunHistory,
    _classify_coverage,
    _latest_applicable_terminal_verdict,
    _parse_run,
)


def _history(*runs: MainGateRun, complete: bool = True) -> MainGateRunHistory:
    return MainGateRunHistory(runs=runs, complete=complete)


def _run(
    identifier: int,
    verdict: str | None,
    updated_at: str,
    *,
    status: str = "completed",
) -> MainGateRun:
    return MainGateRun(
        database_id=identifier,
        conclusion=verdict,
        status=status,
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_main_gate_audit_uses_latest_terminal_verdict_and_preserves_failed_history() -> None:
    commits = [
        "a" * 40 + " aaaaaaa latest failure",
        "b" * 40 + " bbbbbbb latest success",
        "c" * 40 + " ccccccc cancelled revision",
        "d" * 40 + " ddddddd ungated revision",
        "e" * 40 + " eeeeeee unreadable revision",
    ]
    histories = {
        "a" * 40: _history(
            _run(1, "success", "2026-09-13T09:00:00Z"),
            _run(2, "failure", "2026-09-13T09:01:00Z"),
        ),
        "b" * 40: _history(
            _run(3, "failure", "2026-09-13T09:00:00Z"),
            _run(4, "success", "2026-09-13T09:01:00Z"),
        ),
        "c" * 40: _history(_run(5, "cancelled", "2026-09-13T09:00:00Z")),
        "d" * 40: _history(),
        "e" * 40: None,
    }

    ungated, unknown, failing, passing = _classify_coverage(
        commits,
        histories_for_sha=histories,
    )

    assert passing == 1
    assert failing == ["aaaaaaa  latest failure"]
    assert ungated == ["ddddddd  ungated revision"]
    assert unknown == ["ccccccc", "eeeeeee"]


def test_main_gate_audit_rejects_truncated_and_ambiguous_terminal_history() -> None:
    truncated = _history(_run(1, "success", "2026-09-13T09:00:00Z"), complete=False)
    ambiguous = _history(
        _run(2, "success", "2026-09-13T09:01:00Z"),
        _run(3, "failure", "2026-09-13T09:01:00Z"),
    )

    assert _latest_applicable_terminal_verdict(truncated) is None
    assert _latest_applicable_terminal_verdict(ambiguous) is None


def test_main_gate_audit_treats_newer_pending_run_as_unknown() -> None:
    history = _history(
        _run(1, "success", "2026-09-13T09:00:00Z"),
        _run(2, None, "2026-09-13T09:01:00Z", status="in_progress"),
    )

    assert _latest_applicable_terminal_verdict(history) is None


def test_main_gate_audit_rejects_unreadable_run_ordering_evidence() -> None:
    with pytest.raises(ValueError, match="MAIN_GATE_RUN_HISTORY_UNREADABLE"):
        _parse_run(
            {
                "databaseId": 1,
                "conclusion": "success",
                "status": "completed",
                "createdAt": "2026-09-13T09:00:00Z",
                "updatedAt": None,
            }
        )


def test_main_gate_audit_retains_ordered_run_identity_from_github(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completed:
        returncode = 0
        stdout = (
            '[{"databaseId":2,"conclusion":"failure","status":"completed",'
            '"headBranch":"main-releasability-abc","createdAt":"2026-09-13T09:00:00Z",'
            '"updatedAt":"2026-09-13T09:01:00Z"}]'
        )

    monkeypatch.setattr(audit.subprocess, "run", lambda *_, **__: Completed())

    history = audit._run_history("abc")

    assert history is not None
    assert history.complete is True
    assert history.runs[0].database_id == 2
    assert _latest_applicable_terminal_verdict(history) == "failure"


@pytest.mark.parametrize("stdout", ("not-json", "{}"))
def test_main_gate_audit_fails_closed_on_unreadable_github_history(
    monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    class Completed:
        returncode = 0

    completed = Completed()
    completed.stdout = stdout
    monkeypatch.setattr(audit.subprocess, "run", lambda *_, **__: completed)

    assert audit._run_history("abc") is None


def test_main_gate_audit_main_reports_coverage_and_fails_on_gaps(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sha = "a" * 40
    monkeypatch.setattr(audit.shutil, "which", lambda _: "gh")
    monkeypatch.setattr(audit, "_git", lambda *_: [f"{sha} aaaaaaa revision"])
    monkeypatch.setattr(
        audit,
        "_run_history",
        lambda _: _history(_run(1, "failure", "2026-09-13T09:00:00Z")),
    )
    monkeypatch.setattr(audit.sys, "argv", ["audit", "--fail-on-gap"])

    assert audit.main() == 0
    assert "FAILING  aaaaaaa  revision" in capsys.readouterr().out
