from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_PATH = str(PROJECT_ROOT)
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

from src.api.main import app  # noqa: E402

SEVERITY_LABELS = {
    0: "error",
    1: "warn",
    2: "info",
    3: "hint",
}


def _spectral_command(repo_root: Path) -> list[str]:
    executable_name = "spectral.cmd" if sys.platform.startswith("win") else "spectral"
    local_executable = repo_root / "node_modules" / ".bin" / executable_name
    if local_executable.exists():
        return [str(local_executable)]
    return ["npx", "--yes", "@stoplight/spectral-cli@6.16.0"]


def _severity_label(value: object) -> str:
    if isinstance(value, int):
        return SEVERITY_LABELS.get(value, f"unknown-{value}")
    if isinstance(value, str) and value:
        return value
    return "unknown"


def _normalize_finding(finding: dict[str, Any]) -> dict[str, object]:
    path = finding.get("path")
    if isinstance(path, list):
        path_text = ".".join(str(segment) for segment in path)
    else:
        path_text = str(path or "")
    return {
        "code": str(finding.get("code") or ""),
        "severity": _severity_label(finding.get("severity")),
        "path": path_text,
        "message": str(finding.get("message") or ""),
    }


def build_spectral_report(repo_root: Path) -> dict[str, object]:
    schema = app.openapi()
    paths = schema.get("paths", {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
        schema_path = Path(handle.name)
        json.dump(schema, handle, indent=2, sort_keys=True)

    try:
        completed = subprocess.run(
            [
                *_spectral_command(repo_root),
                "lint",
                str(schema_path),
                "--ruleset",
                str(repo_root / ".spectral.yaml"),
                "--format",
                "json",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        schema_path.unlink(missing_ok=True)

    if completed.returncode not in {0, 1}:
        return {
            "spectralExecutable": False,
            "returnCode": completed.returncode,
            "openapiPathCount": len(paths) if isinstance(paths, dict) else 0,
            "issueCount": None,
            "severityInventory": {},
            "findings": [],
            "stderr": completed.stderr.strip(),
        }

    try:
        payload = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return {
            "spectralExecutable": False,
            "returnCode": completed.returncode,
            "openapiPathCount": len(paths) if isinstance(paths, dict) else 0,
            "issueCount": None,
            "severityInventory": {},
            "findings": [],
            "stderr": "Spectral did not emit valid JSON.",
        }

    if not isinstance(payload, list):
        return {
            "spectralExecutable": False,
            "returnCode": completed.returncode,
            "openapiPathCount": len(paths) if isinstance(paths, dict) else 0,
            "issueCount": None,
            "severityInventory": {},
            "findings": [],
            "stderr": "Spectral JSON payload was not a finding list.",
        }

    findings = [_normalize_finding(finding) for finding in payload if isinstance(finding, dict)]
    severity_counts = Counter(str(finding["severity"]) for finding in findings)
    return {
        "spectralExecutable": True,
        "returnCode": completed.returncode,
        "openapiPathCount": len(paths) if isinstance(paths, dict) else 0,
        "issueCount": len(findings),
        "severityInventory": dict(sorted(severity_counts.items())),
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run report-only Spectral OpenAPI inventory.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("output/openapi-spectral-report.json"))
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    output_path = args.output
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = build_spectral_report(repo_root)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if report.get("spectralExecutable") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
