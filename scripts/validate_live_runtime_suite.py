from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.live_runtime_decision_summary import LiveDecisionSnapshot  # noqa: E402
from scripts.live_runtime_proposal_alternatives import (  # noqa: E402
    LiveProposalAlternativesSnapshot,
)
from scripts.live_runtime_suite_artifacts import (  # noqa: E402
    write_live_runtime_suite_artifact,
    write_live_runtime_suite_bundle,
)
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
            insufficient_evidence_decision=LiveDecisionSnapshot(
                path_name="insufficient_evidence_path",
                top_level_status="SKIPPED",
                decision_status="SKIPPED",
                primary_reason_code="SKIPPED",
                recommended_next_action="SKIPPED",
                approval_requirement_types=(),
            ),
            risk_unavailable_alternatives=LiveProposalAlternativesSnapshot(
                path_name="risk_unavailable_alternatives_path",
                requested_objectives=(),
                feasible_count=0,
                feasible_with_review_count=0,
                rejected_count=0,
                selected_alternative_id=None,
                selected_rank=None,
                top_ranked_alternative_id=None,
                top_ranked_objective=None,
                top_ranked_reason_codes=(),
                rejected_reason_codes=(),
                latency_ms=0.0,
            ),
            core_unavailable_alternatives=LiveProposalAlternativesSnapshot(
                path_name="core_unavailable_alternatives_path",
                requested_objectives=(),
                feasible_count=0,
                feasible_with_review_count=0,
                rejected_count=0,
                selected_alternative_id=None,
                selected_rank=None,
                top_ranked_alternative_id=None,
                top_ranked_objective=None,
                top_ranked_reason_codes=(),
                rejected_reason_codes=(),
                latency_ms=0.0,
            ),
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
