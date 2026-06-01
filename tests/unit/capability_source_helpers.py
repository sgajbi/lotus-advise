from __future__ import annotations

from pathlib import Path

CAPABILITY_MODULE_PATHS = (
    Path("src/api/capabilities/service.py"),
    Path("src/api/capabilities/feature_catalog.py"),
    Path("src/api/capabilities/workflow_catalog.py"),
)


def read_capability_source(*, repo_root: Path | None = None) -> str:
    base_path = repo_root or Path(".")
    return "\n".join(
        (base_path / relative_path).read_text(encoding="utf-8")
        for relative_path in CAPABILITY_MODULE_PATHS
    )


__all__ = ["CAPABILITY_MODULE_PATHS", "read_capability_source"]
