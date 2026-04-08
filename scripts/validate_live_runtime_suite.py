from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validate_cross_service_parity_live import (  # noqa: E402
    LiveParityResult,
    validate_live_cross_service_parity,
)
from scripts.validate_degraded_runtime_live import (  # noqa: E402
    DegradedRuntimeResult,
    validate_live_degraded_runtime,
)


@dataclass(frozen=True)
class LiveRuntimeSuiteResult:
    parity: LiveParityResult
    degraded: DegradedRuntimeResult


def _result_to_json_dict(result: LiveRuntimeSuiteResult) -> dict[str, object]:
    return asdict(result)


def write_live_runtime_suite_artifact(
    result: LiveRuntimeSuiteResult,
    *,
    output_path: str | None,
) -> None:
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_result_to_json_dict(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_markdown_summary(result: LiveRuntimeSuiteResult) -> str:
    return "\n".join(
        [
            "# Live Runtime Suite",
            "",
            "## Parity",
            f"- complete issuer portfolio: `{result.parity.complete_issuer_portfolio}`",
            f"- degraded issuer portfolio: `{result.parity.degraded_issuer_portfolio}`",
            f"- lifecycle portfolio: `{result.parity.lifecycle_portfolio}`",
            f"- lifecycle current state: `{result.parity.lifecycle_current_state}`",
            f"- lifecycle latest version: `{result.parity.lifecycle_latest_version_no}`",
            f"- execution handoff status: `{result.parity.execution_handoff_status}`",
            f"- execution terminal status: `{result.parity.execution_terminal_status}`",
            f"- report status: `{result.parity.report_status}`",
            f"- cold duration ms: `{result.parity.cold_duration_ms:.2f}`",
            f"- warm duration ms: `{result.parity.warm_duration_ms:.2f}`",
            "",
            "## Degraded Runtime",
            f"- risk drill portfolio: `{result.degraded.risk_drill_portfolio}`",
            f"- risk degraded reason: `{result.degraded.risk_degraded_reason}`",
            f"- core degraded reason: `{result.degraded.core_degraded_reason}`",
            f"- fallback mode: `{result.degraded.fallback_mode}`",
            "",
        ]
    )


def write_live_runtime_suite_bundle(
    result: LiveRuntimeSuiteResult,
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
        _build_markdown_summary(result),
        encoding="utf-8",
    )
    return bundle_dir


def validate_live_runtime_suite(*, include_degraded: bool = True) -> LiveRuntimeSuiteResult:
    parity = validate_live_cross_service_parity()
    degraded = (
        validate_live_degraded_runtime()
        if include_degraded
        else DegradedRuntimeResult(
            risk_drill_portfolio="SKIPPED",
            risk_degraded_reason="SKIPPED",
            core_degraded_reason="SKIPPED",
            fallback_mode="SKIPPED",
        )
    )
    return LiveRuntimeSuiteResult(parity=parity, degraded=degraded)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the live proposal runtime validation suite sequentially. "
            "Parity runs first, then degraded-runtime drills."
        )
    )
    parser.add_argument(
        "--skip-degraded",
        action="store_true",
        help="Run only the normal live parity validation and skip degraded-runtime drills.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path for writing the suite result as a JSON artifact.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory for writing a timestamped evidence bundle.",
    )
    args = parser.parse_args()

    result = validate_live_runtime_suite(include_degraded=not args.skip_degraded)
    write_live_runtime_suite_artifact(result, output_path=args.output_json)
    bundle_dir = write_live_runtime_suite_bundle(result, output_dir=args.output_dir)
    print(
        "Live runtime suite passed "
        f"(complete={result.parity.complete_issuer_portfolio}, "
        f"degraded_portfolio={result.parity.degraded_issuer_portfolio}, "
        f"report_status={result.parity.report_status}, "
        f"risk_drill={result.degraded.risk_degraded_reason}, "
        f"core_drill={result.degraded.core_degraded_reason}, "
        f"bundle={bundle_dir if bundle_dir is not None else 'NONE'})"
    )


if __name__ == "__main__":
    main()
