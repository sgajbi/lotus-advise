import re

from src.core.proposals.correlation import resolve_correlation_id


def test_resolve_correlation_id_preserves_supplied_identifier():
    assert resolve_correlation_id("corr_external") == "corr_external"


def test_resolve_correlation_id_generates_governed_fallback_identifier():
    assert re.fullmatch(r"corr_[0-9a-f]{12}", resolve_correlation_id(None))
