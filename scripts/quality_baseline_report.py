from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
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
    deptry_config_valid: bool
    deptry_issue_count: int | None
    bandit_config_valid: bool
    bandit_issue_count: int | None
    bandit_high_count: int | None
    bandit_medium_count: int | None
    bandit_low_count: int | None
    importlinter_config_valid: bool
    importlinter_contract_count: int | None
    importlinter_kept_count: int | None
    importlinter_broken_count: int | None
    radon_config_valid: bool
    radon_analyzed_block_count: int | None
    radon_rank_counts: dict[str, int]
    radon_worst_rank: str | None
    radon_worst_complexity: int | None
    vulture_config_valid: bool
    vulture_issue_count: int | None
    vulture_confidence_counts: dict[str, int]
    spectral_config_valid: bool
    spectral_issue_count: int | None
    spectral_severity_counts: dict[str, int]
    spectral_openapi_path_count: int | None
    interrogate_config_valid: bool
    interrogate_total_count: int | None
    interrogate_missing_count: int | None
    interrogate_covered_count: int | None
    interrogate_coverage_percent: str | None


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


def _deptry_issue_count(repo_root: Path) -> tuple[bool, int | None]:
    if not _tool_available("deptry") or not (repo_root / "pyproject.toml").exists():
        return False, None
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        output_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "deptry",
                ".",
                "--config",
                "pyproject.toml",
                "--json-output",
                str(output_path),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if not output_path.exists() or completed.returncode not in {0, 1}:
            return False, None
        try:
            findings = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False, None
        if not isinstance(findings, list):
            return False, None
        return True, len(findings)
    finally:
        output_path.unlink(missing_ok=True)


def _bandit_issue_counts(
    repo_root: Path,
) -> tuple[bool, int | None, int | None, int | None, int | None]:
    if not _tool_available("bandit") or not (repo_root / "pyproject.toml").exists():
        return False, None, None, None, None
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-q",
            "-r",
            "src",
            "-c",
            "pyproject.toml",
            "-f",
            "json",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        return False, None, None, None, None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False, None, None, None, None
    if not isinstance(payload, dict):
        return False, None, None, None, None
    results = payload.get("results")
    metrics = payload.get("metrics")
    if not isinstance(results, list) or not isinstance(metrics, dict):
        return False, None, None, None, None
    totals = metrics.get("_totals")
    if not isinstance(totals, dict):
        return False, None, None, None, None
    return (
        True,
        len(results),
        int(totals.get("SEVERITY.HIGH", 0)),
        int(totals.get("SEVERITY.MEDIUM", 0)),
        int(totals.get("SEVERITY.LOW", 0)),
    )


def _importlinter_contract_counts(
    repo_root: Path,
) -> tuple[bool, int | None, int | None, int | None]:
    if not _tool_available("importlinter") or not (repo_root / ".importlinter").exists():
        return False, None, None, None
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from importlinter.cli import lint_imports_command; "
                "lint_imports_command(args=['--config','.importlinter'], standalone_mode=True)"
            ),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    contract_match = re.search(
        r"Contracts:\s+(?P<kept>\d+)\s+kept,\s+(?P<broken>\d+)\s+broken",
        completed.stdout,
    )
    if contract_match is None:
        return False, None, None, None
    kept = int(contract_match.group("kept"))
    broken = int(contract_match.group("broken"))
    return completed.returncode in {0, 1}, kept + broken, kept, broken


def _radon_complexity_inventory(
    repo_root: Path,
) -> tuple[bool, int | None, dict[str, int], str | None, int | None]:
    if not _tool_available("radon"):
        return False, None, {}, None, None
    completed = subprocess.run(
        [sys.executable, "-m", "radon", "cc", "src", "-s", "-j"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return False, None, {}, None, None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return False, None, {}, None, None
    if not isinstance(payload, dict):
        return False, None, {}, None, None
    blocks: list[dict[str, object]] = []

    def _collect(block: object) -> None:
        if not isinstance(block, dict):
            return
        blocks.append(block)
        for child_key in ("methods", "closures"):
            children = block.get(child_key)
            if isinstance(children, list):
                for child in children:
                    _collect(child)

    for file_blocks in payload.values():
        if isinstance(file_blocks, list):
            for block in file_blocks:
                _collect(block)
    rank_counts = Counter(
        str(block.get("rank"))
        for block in blocks
        if isinstance(block.get("rank"), str) and block.get("rank")
    )

    def _complexity(block: dict[str, object]) -> int:
        value = block.get("complexity")
        return value if isinstance(value, int) else 0

    worst_block = max(blocks, key=_complexity, default=None)
    if worst_block is None:
        return True, 0, {}, None, None
    worst_complexity_value = worst_block.get("complexity")
    worst_rank = worst_block.get("rank")
    worst_complexity = worst_complexity_value if isinstance(worst_complexity_value, int) else None
    return (
        True,
        len(blocks),
        dict(sorted(rank_counts.items())),
        str(worst_rank) if isinstance(worst_rank, str) else None,
        worst_complexity,
    )


def _vulture_issue_inventory(repo_root: Path) -> tuple[bool, int | None, dict[str, int]]:
    if not _tool_available("vulture"):
        return False, None, {}
    completed = subprocess.run(
        [sys.executable, "-m", "vulture", "src", "scripts", "--min-confidence", "80"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in {0, 1, 3}:
        return False, None, {}
    findings = [line for line in completed.stdout.splitlines() if line.strip()]
    confidence_counts: Counter[str] = Counter()
    for finding in findings:
        confidence_match = re.search(r"\((?P<confidence>\d+)% confidence\)", finding)
        if confidence_match is not None:
            confidence_counts[confidence_match.group("confidence")] += 1
    return True, len(findings), dict(sorted(confidence_counts.items()))


def _interrogate_inventory(
    repo_root: Path,
) -> tuple[bool, int | None, int | None, int | None, str | None]:
    if not _tool_available("interrogate") or not (repo_root / "pyproject.toml").exists():
        return False, None, None, None, None
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "interrogate",
            "src",
            "scripts",
            "--config",
            "pyproject.toml",
            "-v",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        return False, None, None, None, None
    total_match = re.search(
        r"\|\s+TOTAL\s+\|\s+(?P<total>\d+)\s+\|\s+(?P<miss>\d+)\s+\|"
        r"\s+(?P<cover>\d+)\s+\|\s+(?P<percent>[0-9.]+%)\s+\|",
        completed.stdout,
    )
    if total_match is None:
        return False, None, None, None, None
    return (
        True,
        int(total_match.group("total")),
        int(total_match.group("miss")),
        int(total_match.group("cover")),
        total_match.group("percent"),
    )


def _spectral_openapi_inventory(
    repo_root: Path,
) -> tuple[bool, int | None, dict[str, int], int | None]:
    if (
        not (repo_root / ".spectral.yaml").exists()
        or not (repo_root / "scripts" / "openapi_spectral_report.py").exists()
    ):
        return False, None, {}, None
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        output_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/openapi_spectral_report.py",
                "--output",
                str(output_path),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if not output_path.exists() or completed.returncode not in {0, 1}:
            return False, None, {}, None
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False, None, {}, None
        if not isinstance(payload, dict) or payload.get("spectralExecutable") is not True:
            return False, None, {}, None
        issue_count = payload.get("issueCount")
        path_count = payload.get("openapiPathCount")
        severity_inventory = payload.get("severityInventory")
        if not isinstance(issue_count, int) or not isinstance(severity_inventory, dict):
            return False, None, {}, None
        severity_counts = {
            str(severity): int(count)
            for severity, count in severity_inventory.items()
            if isinstance(count, int)
        }
        return (
            True,
            issue_count,
            severity_counts,
            path_count if isinstance(path_count, int) else None,
        )
    finally:
        output_path.unlink(missing_ok=True)


def build_quality_context(repo_root: Path) -> QualityContext:
    available_tools = tuple(name for name, module in QUALITY_TOOLS if _tool_available(module))
    unavailable_tools = tuple(name for name, module in QUALITY_TOOLS if not _tool_available(module))
    requested_docs_present = tuple(path for path in REQUESTED_DOCS if (repo_root / path).exists())
    requested_docs_missing = tuple(
        path for path in REQUESTED_DOCS if not (repo_root / path).exists()
    )
    deptry_config_valid, deptry_issue_count = _deptry_issue_count(repo_root)
    (
        bandit_config_valid,
        bandit_issue_count,
        bandit_high_count,
        bandit_medium_count,
        bandit_low_count,
    ) = _bandit_issue_counts(repo_root)
    (
        importlinter_config_valid,
        importlinter_contract_count,
        importlinter_kept_count,
        importlinter_broken_count,
    ) = _importlinter_contract_counts(repo_root)
    (
        radon_config_valid,
        radon_analyzed_block_count,
        radon_rank_counts,
        radon_worst_rank,
        radon_worst_complexity,
    ) = _radon_complexity_inventory(repo_root)
    vulture_config_valid, vulture_issue_count, vulture_confidence_counts = _vulture_issue_inventory(
        repo_root
    )
    (
        spectral_config_valid,
        spectral_issue_count,
        spectral_severity_counts,
        spectral_openapi_path_count,
    ) = _spectral_openapi_inventory(repo_root)
    (
        interrogate_config_valid,
        interrogate_total_count,
        interrogate_missing_count,
        interrogate_covered_count,
        interrogate_coverage_percent,
    ) = _interrogate_inventory(repo_root)
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
        deptry_config_valid=deptry_config_valid,
        deptry_issue_count=deptry_issue_count,
        bandit_config_valid=bandit_config_valid,
        bandit_issue_count=bandit_issue_count,
        bandit_high_count=bandit_high_count,
        bandit_medium_count=bandit_medium_count,
        bandit_low_count=bandit_low_count,
        importlinter_config_valid=importlinter_config_valid,
        importlinter_contract_count=importlinter_contract_count,
        importlinter_kept_count=importlinter_kept_count,
        importlinter_broken_count=importlinter_broken_count,
        radon_config_valid=radon_config_valid,
        radon_analyzed_block_count=radon_analyzed_block_count,
        radon_rank_counts=radon_rank_counts,
        radon_worst_rank=radon_worst_rank,
        radon_worst_complexity=radon_worst_complexity,
        vulture_config_valid=vulture_config_valid,
        vulture_issue_count=vulture_issue_count,
        vulture_confidence_counts=vulture_confidence_counts,
        spectral_config_valid=spectral_config_valid,
        spectral_issue_count=spectral_issue_count,
        spectral_severity_counts=spectral_severity_counts,
        spectral_openapi_path_count=spectral_openapi_path_count,
        interrogate_config_valid=interrogate_config_valid,
        interrogate_total_count=interrogate_total_count,
        interrogate_missing_count=interrogate_missing_count,
        interrogate_covered_count=interrogate_covered_count,
        interrogate_coverage_percent=interrogate_coverage_percent,
    )


def _gate_commands(context: QualityContext) -> dict[str, list[str]]:
    gates: dict[str, list[str]] = {}
    for gate in context.report.gate_inventory:
        gates.setdefault(gate.make_target, []).append(gate.command)
    return gates


def render_baseline_report(context: QualityContext) -> str:
    gates = _gate_commands(context)
    report = context.report
    deptry_issue_count = (
        str(context.deptry_issue_count) if context.deptry_issue_count is not None else "not run"
    )
    bandit_issue_count = (
        str(context.bandit_issue_count) if context.bandit_issue_count is not None else "not run"
    )
    bandit_high_count = (
        str(context.bandit_high_count) if context.bandit_high_count is not None else "not run"
    )
    bandit_medium_count = (
        str(context.bandit_medium_count) if context.bandit_medium_count is not None else "not run"
    )
    bandit_low_count = (
        str(context.bandit_low_count) if context.bandit_low_count is not None else "not run"
    )
    importlinter_contract_count = (
        str(context.importlinter_contract_count)
        if context.importlinter_contract_count is not None
        else "not run"
    )
    importlinter_kept_count = (
        str(context.importlinter_kept_count)
        if context.importlinter_kept_count is not None
        else "not run"
    )
    importlinter_broken_count = (
        str(context.importlinter_broken_count)
        if context.importlinter_broken_count is not None
        else "not run"
    )
    radon_block_count = (
        str(context.radon_analyzed_block_count)
        if context.radon_analyzed_block_count is not None
        else "not run"
    )
    radon_rank_inventory = ", ".join(
        f"{rank}={count}" for rank, count in context.radon_rank_counts.items()
    )
    if not radon_rank_inventory:
        radon_rank_inventory = "not run"
    radon_worst = (
        f"rank={context.radon_worst_rank}, complexity={context.radon_worst_complexity}"
        if context.radon_worst_rank is not None and context.radon_worst_complexity is not None
        else "not run"
    )
    vulture_issue_count = (
        str(context.vulture_issue_count) if context.vulture_issue_count is not None else "not run"
    )
    vulture_confidence_inventory = ", ".join(
        f"{confidence}%={count}" for confidence, count in context.vulture_confidence_counts.items()
    )
    if not vulture_confidence_inventory:
        vulture_confidence_inventory = "not run"
    interrogate_total_count = (
        str(context.interrogate_total_count)
        if context.interrogate_total_count is not None
        else "not run"
    )
    interrogate_missing_count = (
        str(context.interrogate_missing_count)
        if context.interrogate_missing_count is not None
        else "not run"
    )
    interrogate_covered_count = (
        str(context.interrogate_covered_count)
        if context.interrogate_covered_count is not None
        else "not run"
    )
    interrogate_coverage_percent = context.interrogate_coverage_percent or "not run"
    spectral_issue_count = (
        str(context.spectral_issue_count) if context.spectral_issue_count is not None else "not run"
    )
    spectral_path_count = (
        str(context.spectral_openapi_path_count)
        if context.spectral_openapi_path_count is not None
        else "not run"
    )
    spectral_severity_inventory = ", ".join(
        f"{severity}={count}" for severity, count in context.spectral_severity_counts.items()
    )
    if not spectral_severity_inventory:
        spectral_severity_inventory = "none" if context.spectral_issue_count == 0 else "not run"
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
            f"- Radon config executable: `{context.radon_config_valid}`",
            f"- Radon analyzed block inventory: `{radon_block_count}`",
            f"- Radon complexity rank inventory: `{radon_rank_inventory}`",
            f"- Radon worst complexity: `{radon_worst}`",
            "- Radon E/F-ranked block enforcement is repo-native through",
            "  `make complexity-regression-gate` and the `lint` lane.",
            "- Xenon and stricter Radon thresholds remain report-only until current",
            "  D-ranked helpers are classified.",
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
            f"- Vulture config executable: `{context.vulture_config_valid}`",
            f"- Vulture current issue inventory: `{vulture_issue_count}`",
            f"- Vulture confidence inventory: `{vulture_confidence_inventory}`",
            "- Vulture remains report-only until validator false positives and compatibility",
            "  facade imports are classified.",
            "- Current dead-code cleanup remains code-led through review-ledger slices.",
            "",
            "## Dependencies",
            "",
            f"- Dependency verification configured: `{'verify-dependencies' in gates}`",
            f"- Security audit configured: `{'security-audit' in gates}`",
            f"- Available dependency/security tools: `{', '.join(context.available_tools)}`",
            f"- Pending optional tools: `{', '.join(context.unavailable_tools)}`",
            f"- Deptry config executable: `{context.deptry_config_valid}`",
            f"- Deptry current issue inventory: `{deptry_issue_count}`",
            f"- Bandit config executable: `{context.bandit_config_valid}`",
            f"- Bandit current issue inventory: `{bandit_issue_count}`",
            f"- Bandit severity inventory: `high={bandit_high_count}, "
            f"medium={bandit_medium_count}, low={bandit_low_count}`",
            "",
            "## Security",
            "",
            "- `pip-audit` is present in development requirements.",
            "- `bandit` high-severity enforcement is repo-native through",
            "  `make bandit-high-severity-gate` and the `security-audit` lane.",
            "- Medium and low Bandit findings remain an inventoried classification backlog.",
            "- Sensitive-data handling remains governed by API error redaction and structured",
            "  payload tests until the security report gate is calibrated.",
            "",
            "## OpenAPI Gaps",
            "",
            f"- Repo-native OpenAPI gate configured: `{'openapi-gate' in gates}`",
            f"- Spectral rules present: `{context.spectral_present}`",
            f"- Spectral config executable: `{context.spectral_config_valid}`",
            f"- Spectral OpenAPI path inventory: `{spectral_path_count}`",
            f"- Spectral current issue inventory: `{spectral_issue_count}`",
            f"- Spectral severity inventory: `{spectral_severity_inventory}`",
            "- Spectral is enforced through `make openapi-gate`; the inventory remains recorded",
            "  for before/after scorecard evidence.",
            "",
            "## Architecture Violations",
            "",
            f"- Import-linter contracts present: `{context.importlinter_present}`",
            f"- Import-linter config executable: `{context.importlinter_config_valid}`",
            f"- Import-linter contract inventory: `total={importlinter_contract_count}, "
            f"kept={importlinter_kept_count}, broken={importlinter_broken_count}`",
            "- Contracts remain report-only until the kept inventory is wired into a CI gate.",
            "",
            "## Documentation Gaps",
            "",
            f"- Requested docs present: `{', '.join(context.requested_docs_present) or 'none'}`",
            f"- Requested docs missing: `{', '.join(context.requested_docs_missing) or 'none'}`",
            f"- Interrogate config executable: `{context.interrogate_config_valid}`",
            f"- Interrogate docstring inventory: `total={interrogate_total_count}, "
            f"missing={interrogate_missing_count}, covered={interrogate_covered_count}, "
            f"coverage={interrogate_coverage_percent}`",
            "- Interrogate remains report-only until public API and module ownership thresholds",
            "  are classified.",
            "",
            "## Observability Gaps",
            "",
            "- Observability documentation is present.",
            "- Observability diagnostics target: `make observability-diagnostics`",
            "- Focused diagnostics currently verify correlation, request, trace,",
            "  and structured-log propagation.",
            "- Dashboard, alert, SLO, and distributed-tracing evidence remain tracked gaps.",
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
        "- Proposal input models are split into focused context DTOs, request-envelope DTOs,",
        "  and a compatibility facade.",
        "- Proposal context resolution, canonical request hashing, and context evidence",
        "  projection are split into focused owner modules with a compatibility facade.",
        "- Advisory-copilot API DTOs are split into request, response, limits, and compatibility",
        "  modules.",
        "- Advisory-copilot source projections and run-record limits have focused owner modules.",
        "- Advisory simulation orchestration is split into intent planning, review policy,",
        "  and decision-support modules with focused boundary tests.",
        "- Feature capability catalog assembly is split into foundation, evidence-product,",
        "  and operational capability groups.",
        "- Workflow capability catalog assembly is split into foundation, evidence-product,",
        "  and operational workflow groups.",
        "- Proposal memo section assembly is split into foundational, policy-review,",
        "  operational, and appendix section groups.",
        "- Bank-demo supported-claim register assembly is split into artifact policy,",
        "  backend-evidence, product-surface, and boundary claim groups.",
        "- Compliance rule evaluation is split into focused cash-band, concentration,",
        "  data-quality, trade-size, shorting, and cash-sufficiency evaluators.",
        "- Target-generation solver orchestration delegates sell-only redistribution, solver",
        "  indexing, constraint assembly, and solved-weight application to focused helpers.",
        "- Proposal memo source-readiness assembly is split into core, risk, and Advise",
        "  source-owner section groups.",
        "- Proposal memo source-readiness owner groups are split into focused Lotus Core,",
        "  Lotus Risk, and Lotus Advise modules with a compatibility facade.",
        "- Bank-demo runtime summary sanitization is split into access helpers and",
        "  focused projection builders.",
        "- Bank-demo commercial material pack assembly delegates governed material rows to",
        "  a focused catalog module.",
        "- Bank-demo journey integration proof DTOs and validators are split into a focused",
        "  model owner while preserving the proof summary builder and public import path.",
        "- Proposal artifact assembly delegates portfolio, summary, trade/funding, review,",
        "  evidence-bundle, and hash finalization to focused artifact modules.",
        "- Advisory auto-funding planning delegates FX source selection and missing-rate",
        "  diagnostics to a focused funding-selection module.",
        "- Policy source-readiness assembly is split into Lotus Core, product-policy,",
        "  and Lotus Risk source-owner section modules.",
        "- Proposal memo foundational sections are split into focused per-section builders",
        "  outside the shared memo section group coordinator.",
        "- Proposal memo foundational sections delegate summary extraction and value",
        "  normalization to a focused helper module while preserving section construction.",
        "- Proposal memo evidence-pack assembly delegates deterministic section, appendix,",
        "  and material-claim construction to a focused section factory.",
        "- Proposal memo API orchestration delegates report-package and AI-evidence payloads",
        "  to a focused external-package module.",
        "- Proposal memo API routes are split into command, external-package, and read/projection",
        "  route modules while preserving the route loader and OpenAPI surface.",
        "- Policy evaluation API routes are split into command, read/projection, workflow,",
        "  and external-package route modules while preserving the route loader and OpenAPI",
        "  surface.",
        "- Proposal memo API response assembly delegates memo, audit-event, report replay,",
        "  AI commentary, archive-ref, section, and replay-metadata projection to a",
        "  focused response projection module.",
        "- Proposal memo API external request orchestration delegates report-package and",
        "  AI-commentary integration flows to a focused operations module.",
        "- Alternative strategy construction delegates input DTOs, base mechanics,",
        "  objective classes, selection helpers, trade-payload formatting, and notional math",
        "  to focused strategy modules.",
        "- Alternatives objective strategies are split into portfolio/cash, baseline-trade,",
        "  currency-alignment, and deferred restricted-product modules.",
        "- Proposal alternatives models are split into vocabulary, request-validation,",
        "  response/evidence, and compatibility facade modules.",
        "- Proposal alternatives projection delegates request-to-strategy input mapping",
        "  to a focused projection module.",
        "- Proposal alternatives comparison evidence delegates approval, risk, cash,",
        "  currency, and tradeoff deltas to a focused projection module.",
        "- Proposal alternatives ranking delegates comparator, reason-code, rank,",
        "  and selected-alternative projection to a focused ranking module.",
        "- Proposal memo request DTOs and memo vocabulary literals are split from",
        "  response, lineage, and replay evidence models.",
        "- Proposal memo persistence records are split into a focused owner module",
        "  while preserving the existing persistence model facade.",
        "- Proposal memo section assembly delegates source evidence and hash-payload",
        "  collection to focused factory helpers.",
        "- Proposal memo audit event DTOs are split into a focused append-only",
        "  event model module.",
        "- Proposal memo lineage and replay evidence DTOs are split into a",
        "  focused lineage response module.",
        "- Policy evaluation result builders are split from specialized rule",
        "  evaluation logic.",
        "- Policy evaluation product evidence helpers are split from specialized",
        "  rule evaluation logic.",
        "- Policy evaluation Singapore product rule implementations are split",
        "  into a focused rule-family module.",
        "- Policy evaluation cost and conflict review rules are split into a",
        "  focused review-rule module.",
        "- Policy evaluation source-readiness and mandate rules are split into",
        "  a focused source-rule module.",
        "- Policy evaluation source-readiness rule handling delegates policy-posture",
        "  aggregation and section evidence collection to focused helpers.",
        "- Proposal artifact summary DTOs are split into a focused summary model module",
        "  while preserving the existing artifact model facade.",
        "- Proposal artifact portfolio-impact DTOs are split into a focused portfolio model",
        "  module while preserving the existing artifact model facade.",
        "- Proposal artifact trade/funding DTOs are split into a focused execution-evidence",
        "  model module while preserving the existing artifact model facade.",
        "- Proposal artifact review DTOs are split into a focused suitability/risk-lens",
        "  model module while preserving the existing artifact model facade.",
        "- Proposal artifact assumptions and disclosure DTOs are split into a focused",
        "  model module while preserving the existing artifact model facade.",
        "- Proposal artifact evidence DTOs are split into a focused lineage/evidence",
        "  model module while preserving the existing artifact model facade.",
        "- Proposal artifact builders import focused DTO owner modules directly instead of",
        "  routing section DTOs through the artifact model facade.",
        "- Proposal narrative vocabulary Literal aliases are split into a focused type",
        "  module while preserving the existing narrative model facade.",
        "- Proposal narrative request DTOs are split into a focused request model module",
        "  while preserving the existing narrative model facade.",
        "- Proposal narrative grounding DTOs are split into a focused evidence model module",
        "  while preserving the existing narrative model facade.",
        "- Proposal narrative section DTOs are split into a focused section model module",
        "  while preserving the existing narrative model facade.",
        "- Proposal narrative policy and guardrail DTOs are split into a focused policy",
        "  model module while preserving the existing narrative model facade.",
        "- Proposal narrative AI-lineage DTOs are split into a focused AI model module",
        "  while preserving the existing narrative model facade.",
        "- Proposal narrative envelope DTOs are split into a focused envelope model module",
        "  while preserving the existing narrative model facade.",
        "- Proposal narrative review DTOs are split into a focused review model module",
        "  while preserving the existing narrative model facade.",
        "- Proposal narrative runtime modules import focused DTO owner modules directly",
        "  instead of routing DTOs through the narrative model facade.",
        "- Proposal narrative grounding fact projection delegates decision-summary and",
        "  alternatives fact assembly to focused helpers.",
        "- Advisor cockpit source read models delegate source projection helpers to a focused",
        "  source-projection module while preserving the existing read-model facade.",
        "- Advisor cockpit source projection delegates policy-review and memo package blockage",
        "  source rules to a focused policy/memo projection module.",
        "- Advisor cockpit source projection delegates proposal meeting-preparation, client",
        "  follow-up, and approval-dependency rules to a focused proposal projection module.",
        "- Advisor cockpit source projection delegates report/archive readiness and execution",
        "  handoff/status rules to focused source-family projection modules.",
        "- Advisor cockpit service delegates repository-backed source loading and tactical",
        "  house-view source mapping to a focused source-loader module.",
        "- In-memory proposal repository adapters delegate pure filtering, ordering,",
        "  batching, recoverable-operation selection, and copy semantics to focused helpers.",
        "- Advisor cockpit service delegates acknowledgement idempotency, replay,",
        "  persistence payload, and response projection to a focused service boundary.",
        "- Engine option models delegate suitability threshold DTOs, group constraints,",
        "  and reusable validators to focused owner modules while preserving public imports.",
        "- Tactical house-view source products delegate DTOs and eligibility/supportability",
        "  rules to focused owner modules while preserving the public cohort facade.",
        "- Policy evaluation workflow commands delegate projection and sign-off decision",
        "  validation to focused workflow owner modules.",
        "- Integration capability response models delegate feature/workflow, readiness,",
        "  and supportability DTO families to focused owner modules while preserving",
        "  the public response facade.",
        "- Proposal workflow service construction delegates operation-owner wiring to",
        "  a focused registry while preserving the public service facade.",
        "- Proposal workflow service async submission, execution, replay, correlation",
        "  lookup, recovery, and test-stat facade methods live in a focused mixin.",
        "- Proposal workflow service read, timeline, approval, lineage, version, replay,",
        "  and idempotency lookup facade methods live in a focused read mixin.",
        "- Advisory workspace routes are split into session/version, assistant-rationale,",
        "  and lifecycle-handoff route modules behind the public aggregate router.",
        "- Workspace draft action request validation delegates trade, cash-flow, options,",
        "  and identifier-scope rules to focused helpers.",
        "- Local valuation state assembly delegates position summary collection, cash",
        "  conversion, shelf allocation, and allocation-metric rendering to focused helpers.",
        "- Policy-pack catalog state delegates validation/activation commands, audit-event",
        "  mechanics, and detail projection to focused owner modules.",
        "- Proposal decision-summary assembly delegates status, reason, next-action,",
        "  and confidence rules to a focused decision-status module.",
        "- Proposal workflow delivery operations delegate execution handoff, status, summary,",
        "  history, and execution-update replay behavior to a focused service boundary.",
        "- Proposal workflow narrative operations delegate narrative read/regeneration/review",
        "  and report-request event recording to a focused service boundary.",
        "- Proposal workflow read operations delegate proposal, timeline, approval, lineage,",
        "  idempotency, version, and replay views to a focused service boundary.",
        "- Proposal workflow command operations delegate create, version, transition, and",
        "  approval commands to a focused service boundary.",
        "- Policy evaluation persistence delegates lineage/posture projection and audit-event",
        "  attachment mapping to a focused projection module.",
        "- Policy evaluation persistence delegates replay hash comparison and replay response",
        "  assembly to a focused replay module.",
        "- Policy evaluation persistence delegates mutable record storage, idempotency replay,",
        "  event construction, and store-backed projections to a focused record-store module.",
        "- Engineering-health and quality-baseline reporting now provide repeatable evidence.",
        "",
        "## Remaining Enterprise-Readiness Work",
        "",
        "- Calibrate remaining report-only tools: xenon and optional schemathesis/load testing.",
        "- Keep Spectral OpenAPI enforcement green while route and schema contracts evolve.",
        "- Convert the Interrogate docstring inventory into a targeted documentation-quality gate",
        "  after classifying public API and module ownership thresholds.",
        "- Convert the Vulture dead-code inventory into a fail-on-new-regression gate after",
        "  classifying validator and compatibility-facade findings.",
        "- Expand Radon complexity enforcement beyond E/F-ranked blocks after classifying",
        "  current high-complexity blocks.",
        "- Expand Bandit security enforcement beyond high severity after classifying current",
        "  SQL-construction findings and resolving true positives.",
        "- Convert the deptry dependency inventory into a fail-on-new-regression gate after",
        "  classifying current dependency findings.",
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
        (
            "Complexity",
            "No-E/F gate plus Radon inventory",
            "complexity-regression-gate + radon rank and worst-complexity counts",
        ),
        ("Maintainability", "Improving", "modularity slices and review ledger"),
        ("Lint", "Enforced", "make lint"),
        ("Type safety", "Enforced", "make typecheck"),
        ("Coverage", "Enforced", "make coverage-combined fail-under 97"),
        (
            "Dead code",
            "Executable Vulture inventory",
            "vulture issue and confidence counts",
        ),
        (
            "Dependencies",
            "Enforced plus deptry inventory",
            "dependency health check + pip-audit posture + deptry issue count",
        ),
        (
            "Security",
            "High-severity enforced plus Bandit inventory",
            "security-audit + bandit-high-severity-gate + Bandit severity counts",
        ),
        (
            "OpenAPI",
            "Enforced with Spectral",
            "openapi-gate + Spectral zero-finding inventory",
        ),
        (
            "Architecture boundaries",
            "Enforced",
            "make lint runs import-linter architecture contracts",
        ),
        (
            "Docs",
            "Gap tracked plus Interrogate inventory",
            "requested docs + docstring coverage inventory",
        ),
        (
            "Observability",
            "Diagnostics target added",
            "make observability-diagnostics",
        ),
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
        render_baseline_report(context), encoding="utf-8", newline="\n"
    )
    (output_dir / "refactor_health_report.md").write_text(
        render_refactor_health_report(context), encoding="utf-8", newline="\n"
    )
    (output_dir / "quality_scorecard.md").write_text(
        render_quality_scorecard(context), encoding="utf-8", newline="\n"
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
