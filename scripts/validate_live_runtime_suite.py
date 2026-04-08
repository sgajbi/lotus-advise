from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
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
    args = parser.parse_args()

    result = validate_live_runtime_suite(include_degraded=not args.skip_degraded)
    write_live_runtime_suite_artifact(result, output_path=args.output_json)
    print(
        "Live runtime suite passed "
        f"(complete={result.parity.complete_issuer_portfolio}, "
        f"degraded_portfolio={result.parity.degraded_issuer_portfolio}, "
        f"report_status={result.parity.report_status}, "
        f"risk_drill={result.degraded.risk_degraded_reason}, "
        f"core_drill={result.degraded.core_degraded_reason})"
    )


if __name__ == "__main__":
    main()
