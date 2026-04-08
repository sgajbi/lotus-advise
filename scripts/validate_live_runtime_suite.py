from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
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
    args = parser.parse_args()

    result = validate_live_runtime_suite(include_degraded=not args.skip_degraded)
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
