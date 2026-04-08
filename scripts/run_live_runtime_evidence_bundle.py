from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.live_runtime_suite_artifacts import (  # noqa: E402
    write_live_runtime_suite_bundle,
    write_pr_summary_for_bundle,
)
from scripts.validate_live_runtime_suite import validate_live_runtime_suite  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the live runtime suite and emit a timestamped evidence bundle plus "
            "PR-ready markdown summary."
        )
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the timestamped evidence bundle should be written.",
    )
    parser.add_argument(
        "--skip-degraded",
        action="store_true",
        help="Run only the normal live parity validation and skip degraded-runtime drills.",
    )
    parser.add_argument(
        "--pr-summary-output",
        default=None,
        help=(
            "Optional explicit path for the PR-ready markdown summary. "
            "Defaults to <bundle>/pr-summary.md."
        ),
    )
    args = parser.parse_args()

    result = validate_live_runtime_suite(include_degraded=not args.skip_degraded)
    bundle_dir = write_live_runtime_suite_bundle(result, output_dir=args.output_dir)
    if bundle_dir is None:
        raise RuntimeError("LIVE_RUNTIME_EVIDENCE_BUNDLE_OUTPUT_REQUIRED")
    pr_summary_path = write_pr_summary_for_bundle(
        bundle_dir,
        output_path=args.pr_summary_output,
    )
    print(
        f"Live runtime evidence bundle written (bundle={bundle_dir}, pr_summary={pr_summary_path})"
    )


if __name__ == "__main__":
    main()
