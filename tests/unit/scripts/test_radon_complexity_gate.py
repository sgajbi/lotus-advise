from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import radon_complexity_gate
from scripts.radon_complexity_gate import parse_radon_report


def _payload(*blocks: dict[str, object]) -> str:
    return json.dumps({"src/example.py": list(blocks)})


def test_parse_radon_report_counts_nested_blocks_and_failing_rank() -> None:
    summary = parse_radon_report(
        _payload(
            {
                "name": "Container",
                "rank": "C",
                "complexity": 12,
                "methods": [
                    {"name": "method", "rank": "F", "complexity": 42},
                ],
            }
        )
    )

    assert summary.block_count == 2
    assert summary.rank_counts == {"C": 1, "F": 1}
    assert summary.worst_rank == "F"
    assert summary.worst_complexity == 42
    assert summary.failing_blocks == ("src/example.py:method: rank=F, complexity=42",)


def test_main_passes_when_radon_reports_no_f_rank(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        radon_complexity_gate,
        "run_radon",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=_payload({"name": "ok", "rank": "E", "complexity": 32}),
            stderr="",
        ),
    )

    exit_code = radon_complexity_gate.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "blocks=1, ranks=E=1, worst=E/32, fail_rank=F" in captured.out


def test_main_fails_when_radon_reports_f_rank(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        radon_complexity_gate,
        "run_radon",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=_payload({"name": "too_complex", "rank": "F", "complexity": 45}),
            stderr="",
        ),
    )

    exit_code = radon_complexity_gate.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Radon complexity gate failed." in captured.err
    assert "src/example.py:too_complex: rank=F, complexity=45" in captured.err


def test_main_fails_when_radon_output_is_not_json(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        radon_complexity_gate,
        "run_radon",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="{", stderr=""),
    )

    exit_code = radon_complexity_gate.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Radon did not return valid JSON." in captured.err
