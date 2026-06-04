from pathlib import Path

from scripts.quality_baseline_report import (
    build_quality_context,
    main,
    render_baseline_report,
    render_quality_scorecard,
    render_refactor_health_report,
)


def test_quality_baseline_report_captures_required_quality_sections(tmp_path: Path) -> None:
    src = tmp_path / "src" / "api"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "routes_demo.py").write_text(
        "\n".join(
            [
                "router = object()",
                "@router.get('/demo')",
                "def demo_route():",
                "    return {'ok': True}",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text(
        "\n".join(
            [
                "lint:",
                "\tpython -m ruff check .",
                "typecheck:",
                "\tpython -m mypy --config-file mypy.ini",
                "openapi-gate:",
                "\tpython scripts/openapi_quality_gate.py",
                "coverage-combined:",
                "\tpython -m coverage report --fail-under=97",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
    (tmp_path / ".importlinter").write_text(
        "[importlinter]\nroot_package = src\n",
        encoding="utf-8",
    )
    (tmp_path / ".spectral.yaml").write_text("rules: {}\n", encoding="utf-8")

    context = build_quality_context(tmp_path)
    baseline = render_baseline_report(context)
    scorecard = render_quality_scorecard(context)
    refactor_health = render_refactor_health_report(context)

    assert "Code Size" in baseline
    assert "Complexity" in baseline
    assert "Dead Code" in baseline
    assert "OpenAPI Gaps" in baseline
    assert "Architecture Violations" in baseline
    assert "Documentation Gaps" in baseline
    assert "Observability Gaps" in baseline
    assert "Progressive Gate Phase" in scorecard
    assert "Advisory simulation orchestration is split" in refactor_health
    assert "Feature capability catalog assembly is split" in refactor_health
    assert "Workflow capability catalog assembly is split" in refactor_health
    assert "Proposal memo section assembly is split" in refactor_health
    assert "Bank-demo supported-claim register assembly is split" in refactor_health
    assert "Compliance rule evaluation is split" in refactor_health
    assert "Proposal memo source-readiness assembly is split" in refactor_health
    assert "Bank-demo runtime summary sanitization is split" in refactor_health
    assert "Bank-demo commercial material pack assembly delegates" in refactor_health
    assert "evidence-bundle, and hash finalization" in refactor_health
    assert "Advisory auto-funding planning delegates FX source selection" in refactor_health
    assert "Policy source-readiness assembly is split" in refactor_health
    assert "Proposal memo foundational sections are split" in refactor_health
    assert "Proposal memo API orchestration delegates report-package" in refactor_health
    assert "Proposal memo API response assembly delegates memo" in refactor_health
    assert "Proposal memo API external request orchestration delegates" in refactor_health
    assert "Alternative strategy construction delegates input DTOs" in refactor_health
    assert "Alternatives objective strategies are split" in refactor_health
    assert "Proposal alternatives models are split" in refactor_health
    assert "Proposal alternatives projection delegates request-to-strategy" in refactor_health
    assert "Proposal alternatives comparison evidence delegates approval" in refactor_health
    assert "Proposal alternatives ranking delegates comparator" in refactor_health
    assert "Proposal memo request DTOs and memo vocabulary literals are split" in refactor_health
    assert "Proposal memo audit event DTOs are split" in refactor_health
    assert "Proposal memo lineage and replay evidence DTOs are split" in refactor_health
    assert "Policy evaluation result builders are split" in refactor_health
    assert "Policy evaluation product evidence helpers are split" in refactor_health
    assert "Policy evaluation Singapore product rule implementations are split" in refactor_health
    assert (
        "Advisor cockpit source read models delegate source projection helpers" in refactor_health
    )
    assert "Advisor cockpit service delegates repository-backed source loading" in refactor_health
    assert "Proposal workflow delivery operations delegate execution handoff" in refactor_health
    assert "Proposal workflow narrative operations delegate narrative read" in refactor_health
    assert "Proposal workflow read operations delegate proposal" in refactor_health
    assert "Proposal workflow command operations delegate create" in refactor_health
    assert "Policy evaluation persistence delegates lineage/posture projection" in refactor_health
    assert "Policy evaluation persistence delegates replay hash comparison" in refactor_health
    assert "Remaining Enterprise-Readiness Work" in refactor_health


def test_quality_baseline_report_cli_writes_requested_reports(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    output_dir = tmp_path / "quality"

    exit_code = main(["--repo-root", str(tmp_path), "--output-dir", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "baseline_report.md").exists()
    assert (output_dir / "refactor_health_report.md").exists()
    assert (output_dir / "quality_scorecard.md").exists()
