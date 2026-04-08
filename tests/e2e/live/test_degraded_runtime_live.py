import os

import pytest

from scripts.validate_degraded_runtime_live import validate_live_degraded_runtime


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_DEGRADED_RUNTIME") != "1",
    reason="set RUN_LIVE_DEGRADED_RUNTIME=1 to exercise live degraded runtime validation",
)
def test_live_degraded_runtime_behavior():
    result = validate_live_degraded_runtime()
    assert result.risk_drill_portfolio == "PB_SG_GLOBAL_BAL_001"
    assert result.risk_degraded_reason == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    assert result.core_degraded_reason == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    assert result.fallback_mode == "NONE"
