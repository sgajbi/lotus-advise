from __future__ import annotations

import argparse
import importlib.util
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.engineering_health_report import EngineeringHealthReport, build_report
except ModuleNotFoundError:
    from engineering_health_report import EngineeringHealthReport, build_report


QUALITY_TOOLS: tuple[tuple[str, str], ...] = (
    ("ruff", "ruff"),
    ("mypy", "mypy"),
    ("pytest", "pytest"),
    ("coverage.py", "coverage"),
    ("pip-audit", "pip_audit"),
    ("radon", "radon"),
    ("xenon", "xenon"),
    ("vulture", "vulture"),
    ("deptry", "deptry"),
    ("bandit", "bandit"),
    ("interrogate", "interrogate"),
)

REQUESTED_DOCS = (
    "docs/architecture.md",
    "docs/api-governance.md",
    "docs/observability.md",
    "docs/security.md",
    "docs/operations-runbook.md",
    "docs/supported-features.md",
)


@dataclass(frozen=True)
class QualityContext:
    report: EngineeringHealthReport
    branch_commit_count: int
    pyproject_present: bool
    importlinter_present: bool
    spectral_present: bool
    ci_quality_workflow_present: bool
    requested_docs_present: tuple[str, ...]
    requested_docs_missing: tuple[str, ...]
    available_tools: tuple[str, ...]
    unavailable_tools: tuple[str, ...]


def _run_git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip()


def _branch_commit_count(repo_root: Path) -> int:
    value = _run_git(repo_root, ["rev-list", "--count", "origin/main..HEAD"])
    try:
        return int(value)
    except ValueError:
        return 0


def _tool_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def build_quality_context(repo_root: Path) -> QualityContext:
    available_tools = tuple(name for name, module in QUALITY_TOOLS if _tool_available(module))
    unavailable_tools = tuple(name for name, module in QUALITY_TOOLS if not _tool_available(module))
    requested_docs_present = tuple(path for path in REQUESTED_DOCS if (repo_root / path).exists())
    requested_docs_missing = tuple(
        path for path in REQUESTED_DOCS if not (repo_root / path).exists()
    )
    return QualityContext(
        report=build_report(repo_root),
        branch_commit_count=_branch_commit_count(repo_root),
        pyproject_present=(repo_root / "pyproject.toml").exists(),
        importlinter_present=(repo_root / ".importlinter").exists(),
        spectral_present=(repo_root / ".spectral.yaml").exists(),
        ci_quality_workflow_present=(
            repo_root / ".github" / "workflows" / "quality-baseline-report.yml"
        ).exists(),
        requested_docs_present=requested_docs_present,
        requested_docs_missing=requested_docs_missing,
        available_tools=available_tools,
        unavailable_tools=unavailable_tools,
    )


def _gate_commands(context: QualityContext) -> dict[str, list[str]]:
    gates: dict[str, list[str]] = {}
    for gate in context.report.gate_inventory:
        gates.setdefault(gate.make_target, []).append(gate.command)
    return gates


def render_baseline_report(context: QualityContext) -> str:
    gates = _gate_commands(context)
    report = context.report
    lines = [
        "# Lotus Advise Quality Baseline Report",
        "",
        f"- Generated At: `{report.generated_at}`",
        f"- Branch: `{report.git_branch}`",
        f"- Head: `{report.git_head}`",
        f"- Branch Commits Over Main: `{context.branch_commit_count}`",
        "- CI Phase: `baseline/report-only`",
        "",
        "## Code Size",
        "",
        f"- Python files: `{report.python_file_count}`",
        f"- Packages: `{report.package_count}`",
        f"- Modules: `{report.module_count}`",
        f"- Total Python lines: `{report.total_python_lines}`",
        "",
        "## Largest Files",
        "",
        "| Rank | File | Lines |",
        "| ---: | --- | ---: |",
    ]
    for index, file_metric in enumerate(report.largest_files[:10], start=1):
        lines.append(f"| {index} | `{file_metric.path}` | {file_metric.lines} |")
    lines.extend(
        [
            "",
            "## Largest Functions And Maintainability Hotspots",
            "",
            "| Rank | Function | File | Line | Lines |",
            "| ---: | --- | --- | ---: | ---: |",
        ]
    )
    for index, function_metric in enumerate(report.largest_functions[:10], start=1):
        lines.append(
            f"| {index} | `{function_metric.name}` | `{function_metric.path}` | "
            f"{function_metric.lineno} | {function_metric.lines} |"
        )
    lines.extend(
        [
            "",
            "## Complexity",
            "",
            "- Current baseline uses largest-function and router-hotspot evidence as deterministic",
            "  complexity proxies.",
            "- `radon` and `xenon` are tracked as report-only follow-up tools until installed and",
            "  calibrated against current Lotus Advise behavior.",
            "",
            "## Lint And Type Issues",
            "",
            f"- Ruff configured: `{'lint' in gates}`",
            f"- Mypy configured: `{'typecheck' in gates}`",
            "- Current enforcement remains repo-native through `make lint` and `make typecheck`.",
            "",
            "## Coverage",
            "",
            "- Unit/integration/E2E coverage gate is repo-native through `make coverage-combined`.",
            "- Configured fail-under target: `97`.",
            "",
            "## Dead Code",
            "",
            "- `vulture` is tracked as report-only pending installation and allowlist calibration.",
            "- Current dead-code cleanup remains code-led through review-ledger slices.",
            "",
            "## Dependencies",
            "",
            f"- Dependency verification configured: `{'verify-dependencies' in gates}`",
            f"- Security audit configured: `{'security-audit' in gates}`",
            f"- Available dependency/security tools: `{', '.join(context.available_tools)}`",
            f"- Pending optional tools: `{', '.join(context.unavailable_tools)}`",
            "",
            "## Security",
            "",
            "- `pip-audit` is present in development requirements.",
            "- `bandit` config is present in `pyproject.toml` for report-only rollout.",
            "- Sensitive-data handling remains governed by API error redaction and structured",
            "  payload tests until the security report gate is calibrated.",
            "",
            "## OpenAPI Gaps",
            "",
            f"- Repo-native OpenAPI gate configured: `{'openapi-gate' in gates}`",
            f"- Spectral rules present: `{context.spectral_present}`",
            "- Spectral is report-only until Node/Spectral execution is added to CI.",
            "",
            "## Architecture Violations",
            "",
            f"- Import-linter contracts present: `{context.importlinter_present}`",
            "- Contracts are report-only until import-linter is installed and current violations",
            "  are baselined.",
            "",
            "## Documentation Gaps",
            "",
            f"- Requested docs present: `{', '.join(context.requested_docs_present) or 'none'}`",
            f"- Requested docs missing: `{', '.join(context.requested_docs_missing) or 'none'}`",
            "",
            "## Observability Gaps",
            "",
            "- Observability documentation and service-level diagnostics are tracked as baseline",
            "  gaps until `docs/observability.md` and operational diagnostics gates are added.",
            "",
        ]
    )
    return "\n".join(lines)


def render_refactor_health_report(context: QualityContext) -> str:
    report = context.report
    lines = [
        "# Lotus Advise Refactor Health Report",
        "",
        f"- Branch: `{report.git_branch}`",
        f"- Head: `{report.git_head}`",
        f"- Branch Commits Over Main: `{context.branch_commit_count}`",
        "- Current Phase: `feature-branch modularity and quality-baseline hardening`",
        "",
        "## Current Progress Signals",
        "",
        "- Advisory-copilot API DTOs are split into request, response, limits, and compatibility",
        "  modules.",
        "- Advisory-copilot source projections and run-record limits have focused owner modules.",
        "- Engineering-health and quality-baseline reporting now provide repeatable evidence.",
        "",
        "## Remaining Enterprise-Readiness Work",
        "",
        "- Calibrate report-only tools: radon/xenon, vulture, deptry, bandit, import-linter,",
        "  Spectral, interrogate, and optional schemathesis/load testing.",
        "- Convert baseline reports into fail-on-new-regression gates before enforcing absolute",
        "  thresholds.",
        "- Continue moving oversized proposal/advisory service modules into focused use-case and",
        "  policy modules with tests.",
        "- Complete requested docs and wiki updates only when they describe implemented truth.",
        "",
    ]
    return "\n".join(lines)


def render_quality_scorecard(context: QualityContext) -> str:
    rows = [
        ("Code size and hotspots", "Baseline active", "engineering-health + quality baseline"),
        ("Complexity", "Report-only gap", "radon/xenon pending calibration"),
        ("Maintainability", "Improving", "modularity slices and review ledger"),
        ("Lint", "Enforced", "make lint"),
        ("Type safety", "Enforced", "make typecheck"),
        ("Coverage", "Enforced", "make coverage-combined fail-under 97"),
        ("Dead code", "Report-only gap", "vulture pending calibration"),
        ("Dependencies", "Enforced", "dependency health check + pip-audit posture"),
        ("Security", "Partially enforced", "security-audit plus pending bandit baseline"),
        ("OpenAPI", "Enforced plus report-only", "openapi-gate + Spectral config"),
        ("Architecture boundaries", "Report-only gap", "import-linter config added"),
        ("Docs", "Gap tracked", "requested docs tracked in baseline report"),
        ("Observability", "Gap tracked", "observability doc and diagnostics gates pending"),
    ]
    lines = [
        "# Lotus Advise Quality Scorecard",
        "",
        f"- Branch: `{context.report.git_branch}`",
        f"- Head: `{context.report.git_head}`",
        "- Progressive Gate Phase: `1 - baseline/report-only`",
        "",
        "| Area | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for area, status, evidence in rows:
        lines.append(f"| {area} | {status} | {evidence} |")
    lines.append("")
    return "\n".join(lines)


def write_quality_reports(repo_root: Path, output_dir: Path) -> None:
    context = build_quality_context(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "baseline_report.md").write_text(
        render_baseline_report(context), encoding="utf-8"
    )
    (output_dir / "refactor_health_report.md").write_text(
        render_refactor_health_report(context), encoding="utf-8"
    )
    (output_dir / "quality_scorecard.md").write_text(
        render_quality_scorecard(context), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Lotus Advise quality baseline reports.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("quality"))
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    write_quality_reports(repo_root, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
