import os

import pytest

from scripts.validate_live_runtime_suite import validate_live_runtime_suite


@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_RUNTIME_SUITE") != "1",
    reason="set RUN_LIVE_RUNTIME_SUITE=1 to run the sequential live runtime suite",
)
def test_live_runtime_suite():
    result = validate_live_runtime_suite()

    assert result.parity.complete_issuer_portfolio
    assert result.parity.lifecycle_current_state == "EXECUTED"
    assert result.degraded.risk_degraded_reason == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    assert result.degraded.core_degraded_reason == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    assert result.degraded.fallback_mode == "NONE"
