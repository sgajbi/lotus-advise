from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.live_runtime_suite_artifacts import (
    load_result_json,
    resolve_bundle_dir,
    result_to_json_dict,
    write_live_runtime_suite_bundle,
)
from scripts.validate_live_runtime_suite import validate_live_runtime_suite


def load_or_run_live_suite(
    *,
    live_suite_json: str | None,
    live_suite_bundle: str | None,
    run_live_suite: bool,
    skip_degraded: bool,
    output_dir: Path,
) -> tuple[dict[str, Any], str, str | None]:
    if live_suite_json:
        result_path = Path(live_suite_json)
        return load_result_json(result_path), display_path(result_path), None
    if live_suite_bundle:
        bundle_dir = resolve_bundle_dir(live_suite_bundle)
        result_path = bundle_dir / "result.json"
        return load_result_json(result_path), display_path(result_path), display_path(bundle_dir)
    if run_live_suite:
        result = validate_live_runtime_suite(include_degraded=not skip_degraded)
        live_bundle_dir = write_live_runtime_suite_bundle(result, output_dir=str(output_dir))
        if live_bundle_dir is None:
            raise RuntimeError("RFC0028_LIVE_SUITE_BUNDLE_NOT_WRITTEN")
        return (
            result_to_json_dict(result),
            display_path(live_bundle_dir / "result.json"),
            display_path(live_bundle_dir),
        )
    raise SystemExit(
        "Provide --live-suite-json, --live-suite-bundle, or --run-live-suite for repeatable proof."
    )


def display_path(path: Path) -> str:
    return path.as_posix()
