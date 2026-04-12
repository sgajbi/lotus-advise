from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from scripts.validate_live_runtime_suite import LiveRuntimeSuiteResult


def result_to_json_dict(result: "LiveRuntimeSuiteResult") -> dict[str, object]:
    return cast(dict[str, object], json.loads(json.dumps(asdict(result))))


def _format_decision_summary_lines(
    decision: dict[str, Any],
    *,
    title: str,
) -> list[str]:
    approval_types = decision.get("approval_requirement_types") or []
    approvals = ", ".join(f"`{item}`" for item in approval_types) if approval_types else "`NONE`"
    return [
        f"### {title}",
        f"- top-level status: `{decision['top_level_status']}`",
        f"- decision status: `{decision['decision_status']}`",
        f"- primary reason: `{decision['primary_reason_code']}`",
        f"- next action: `{decision['recommended_next_action']}`",
        f"- approval requirements: {approvals}",
        "",
    ]


def build_markdown_summary(result: "LiveRuntimeSuiteResult") -> str:
    lines = [
        "# Live Runtime Suite",
        "",
        "## Parity",
        f"- complete issuer portfolio: `{result.parity.complete_issuer_portfolio}`",
        f"- degraded issuer portfolio: `{result.parity.degraded_issuer_portfolio}`",
        f"- changed-state portfolio: `{result.parity.changed_state_portfolio}`",
        f"- changed-state security: `{result.parity.changed_state_security_id}`",
        f"- cross-currency security: `{result.parity.cross_currency_security_id}`",
        f"- non-held security: `{result.parity.non_held_security_id}`",
        f"- lifecycle portfolio: `{result.parity.lifecycle_portfolio}`",
        f"- lifecycle current state: `{result.parity.lifecycle_current_state}`",
        f"- lifecycle latest version: `{result.parity.lifecycle_latest_version_no}`",
        f"- async lifecycle portfolio: `{result.parity.async_lifecycle_portfolio}`",
        f"- async lifecycle current state: `{result.parity.async_lifecycle_current_state}`",
        f"- async lifecycle latest version: `{result.parity.async_lifecycle_latest_version_no}`",
        f"- execution handoff status: `{result.parity.execution_handoff_status}`",
        f"- execution terminal status: `{result.parity.execution_terminal_status}`",
        f"- report status: `{result.parity.report_status}`",
        f"- cold duration ms: `{result.parity.cold_duration_ms:.2f}`",
        f"- warm duration ms: `{result.parity.warm_duration_ms:.2f}`",
        "",
        "## Decision Paths",
        "",
        *_format_decision_summary_lines(asdict(result.parity.ready_decision), title="Ready Path"),
        *_format_decision_summary_lines(asdict(result.parity.review_decision), title="Review Path"),
        *_format_decision_summary_lines(
            asdict(result.parity.blocked_decision),
            title="Blocked Path",
        ),
        "## Degraded Runtime",
        f"- risk drill portfolio: `{result.degraded.risk_drill_portfolio}`",
        f"- risk degraded reason: `{result.degraded.risk_degraded_reason}`",
        f"- core degraded reason: `{result.degraded.core_degraded_reason}`",
        f"- fallback mode: `{result.degraded.fallback_mode}`",
        "",
        "## Insufficient Evidence Path",
        "",
        *_format_decision_summary_lines(
            asdict(result.degraded.insufficient_evidence_decision),
            title="Lotus-Risk Unavailable",
        ),
    ]
    return "\n".join(lines)


def write_live_runtime_suite_artifact(
    result: "LiveRuntimeSuiteResult",
    *,
    output_path: str | None,
) -> None:
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result_to_json_dict(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_live_runtime_suite_bundle(
    result: "LiveRuntimeSuiteResult",
    *,
    output_dir: str | None,
) -> Path | None:
    if not output_dir:
        return None
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = Path(output_dir) / f"live-runtime-suite-{timestamp}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    write_live_runtime_suite_artifact(
        result,
        output_path=str(bundle_dir / "result.json"),
    )
    (bundle_dir / "summary.md").write_text(
        build_markdown_summary(result),
        encoding="utf-8",
    )
    return bundle_dir


def load_result_json(path: str | Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))


def resolve_bundle_dir(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_dir() and (candidate / "result.json").exists():
        return candidate
    bundle_dirs = sorted(
        [item for item in candidate.iterdir() if item.is_dir() and (item / "result.json").exists()],
        key=lambda item: item.name,
    )
    if not bundle_dirs:
        raise FileNotFoundError(f"No live runtime suite bundle found under {candidate}")
    return bundle_dirs[-1]


def build_pr_summary(
    bundle_dir: str | Path,
    *,
    result_payload: dict[str, Any] | None = None,
) -> str:
    bundle_path = resolve_bundle_dir(bundle_dir)
    payload = result_payload or load_result_json(bundle_path / "result.json")
    parity = payload["parity"]
    degraded = payload["degraded"]
    lines = [
        "## Live Runtime Evidence",
        "",
        "### Outcome",
        f"- complete parity portfolio: `{parity['complete_issuer_portfolio']}`",
        f"- degraded parity portfolio: `{parity['degraded_issuer_portfolio']}`",
        (
            "- changed-state risk parity: "
            f"`{parity['changed_state_portfolio']}` via "
            f"`{parity['changed_state_security_id']}`"
        ),
        f"- cross-currency changed-state parity: `{parity['cross_currency_security_id']}`",
        f"- non-held changed-state parity: `{parity['non_held_security_id']}`",
        (
            "- sync lifecycle: "
            f"`{parity['lifecycle_current_state']}` at version "
            f"`{parity['lifecycle_latest_version_no']}`"
        ),
        (
            "- async lifecycle: "
            f"`{parity['async_lifecycle_current_state']}` at version "
            f"`{parity['async_lifecycle_latest_version_no']}`"
        ),
        f"- execution terminal status: `{parity['execution_terminal_status']}`",
        f"- report status: `{parity['report_status']}`",
        "",
        "### Decision Summary Paths",
        f"- ready path: `{parity['ready_decision']['decision_status']}` / "
        f"`{parity['ready_decision']['primary_reason_code']}`",
        f"- review path: `{parity['review_decision']['decision_status']}` / "
        f"`{parity['review_decision']['primary_reason_code']}`",
        f"- blocked path: `{parity['blocked_decision']['decision_status']}` / "
        f"`{parity['blocked_decision']['primary_reason_code']}`",
        (
            "- insufficient-evidence path: "
            f"`{degraded['insufficient_evidence_decision']['decision_status']}` / "
            f"`{degraded['insufficient_evidence_decision']['primary_reason_code']}`"
        ),
        "",
        "### Degraded Drills",
        f"- lotus-risk unavailable: `{degraded['risk_degraded_reason']}`",
        f"- lotus-core unavailable: `{degraded['core_degraded_reason']}`",
        f"- fallback mode: `{degraded['fallback_mode']}`",
        "",
        "### Performance",
        f"- cold duration ms: `{float(parity['cold_duration_ms']):.2f}`",
        f"- warm duration ms: `{float(parity['warm_duration_ms']):.2f}`",
        "",
        "### Evidence Bundle",
        f"- bundle: `{bundle_path}`",
        f"- result: `{bundle_path / 'result.json'}`",
        f"- summary: `{bundle_path / 'summary.md'}`",
        "",
    ]
    return "\n".join(lines)


def write_pr_summary_for_bundle(
    bundle_dir: str | Path,
    *,
    output_path: str | Path | None = None,
    result_payload: dict[str, Any] | None = None,
) -> Path:
    bundle_path = resolve_bundle_dir(bundle_dir)
    destination = Path(output_path) if output_path is not None else bundle_path / "pr-summary.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        build_pr_summary(bundle_path, result_payload=result_payload) + "\n",
        encoding="utf-8",
    )
    return destination
