import os

import pytest

from scripts.validate_cross_service_parity_live import validate_live_cross_service_parity


@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_CROSS_SERVICE_PARITY") != "1",
    reason="set RUN_LIVE_CROSS_SERVICE_PARITY=1 to run live cross-service parity validation",
)
def test_live_cross_service_allocation_and_risk_parity():
    result = validate_live_cross_service_parity()

    assert result.complete_issuer_portfolio
    assert result.degraded_issuer_portfolio
    assert result.degraded_issuer_coverage_status in {"partial", "unavailable"}
    assert result.warm_duration_ms <= result.cold_duration_ms * 1.25
