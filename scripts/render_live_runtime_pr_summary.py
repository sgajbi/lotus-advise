from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.live_runtime_suite_artifacts import build_pr_summary  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a PR-ready markdown summary from a live runtime suite bundle."
    )
    parser.add_argument(
        "bundle_path",
        help=(
            "Path to a live runtime suite bundle directory or a parent directory "
            "containing timestamped bundles."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output path for the rendered markdown summary.",
    )
    args = parser.parse_args()

    summary = build_pr_summary(args.bundle_path)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary + "\n", encoding="utf-8")
    else:
        print(summary)


if __name__ == "__main__":
    main()
