from pathlib import Path

from scripts.documentation_source_reference_check import (
    _extract_documented_paths,
    validate_documentation_source_references,
)


def test_live_documentation_source_references_resolve() -> None:
    assert validate_documentation_source_references(Path(".")) == []


def test_extract_documented_paths_ignores_commands_and_historical_prose() -> None:
    line = (
        "Run `python -m pytest tests/unit -q` and prefer "
        "`src/core/advisory_engine.py`; historical names without backticked paths stay prose."
    )

    assert _extract_documented_paths(line) == ["src/core/advisory_engine.py"]
