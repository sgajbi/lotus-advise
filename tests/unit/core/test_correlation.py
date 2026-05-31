import re

from src.core.proposals.correlation import (
    normalize_optional_correlation_id,
    resolve_correlation_id,
)


def test_optional_correlation_id_is_trimmed_and_blank_values_are_absent() -> None:
    assert normalize_optional_correlation_id("  corr-001  ") == "corr-001"
    assert normalize_optional_correlation_id("   ") is None
    assert normalize_optional_correlation_id(None) is None


def test_resolve_correlation_id_preserves_meaningful_values_and_generates_fallback() -> None:
    assert resolve_correlation_id("  corr-001  ") == "corr-001"
    assert re.fullmatch(r"corr_[0-9a-f]{12}", resolve_correlation_id("   "))
