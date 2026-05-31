from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_route_modules_use_422_compatibility_constant() -> None:
    deprecated_constant = "HTTP_422_UNPROCESSABLE_ENTITY"
    route_modules = (REPO_ROOT / "src" / "api" / "proposals").glob("routes_*.py")

    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in route_modules
        if deprecated_constant in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
