from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_core_modules_do_not_import_concrete_integrations() -> None:
    offenders: list[str] = []
    for path in (REPO_ROOT / "src/core").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "src.integrations" in source:
            offenders.append(path.relative_to(REPO_ROOT).as_posix())

    assert offenders == []
