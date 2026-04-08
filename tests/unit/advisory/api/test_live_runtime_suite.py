from scripts.validate_live_runtime_suite import validate_live_runtime_suite


def test_live_runtime_suite_runs_parity_before_degraded(monkeypatch):
    calls: list[str] = []

    def _parity():
        calls.append("parity")
        return type(
            "ParityResult",
            (),
            {
                "complete_issuer_portfolio": "PB_SG_GLOBAL_BAL_001",
                "degraded_issuer_portfolio": "DEMO_ADV_USD_001",
                "degraded_issuer_coverage_status": "unavailable",
                "cold_duration_ms": 100.0,
                "warm_duration_ms": 90.0,
                "workspace_handoff_portfolio": "PB_SG_GLOBAL_BAL_001",
                "lifecycle_portfolio": "PB_SG_GLOBAL_BAL_001",
                "lifecycle_latest_version_no": 2,
                "lifecycle_current_state": "EXECUTED",
                "execution_handoff_status": "REQUESTED",
                "execution_terminal_status": "EXECUTED",
                "report_status": "READY",
            },
        )()

    def _degraded():
        calls.append("degraded")
        return type(
            "DegradedResult",
            (),
            {
                "risk_drill_portfolio": "PB_SG_GLOBAL_BAL_001",
                "risk_degraded_reason": "LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
                "core_degraded_reason": "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
                "fallback_mode": "NONE",
            },
        )()

    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_cross_service_parity",
        _parity,
    )
    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_degraded_runtime",
        _degraded,
    )

    result = validate_live_runtime_suite()

    assert calls == ["parity", "degraded"]
    assert result.parity.lifecycle_current_state == "EXECUTED"
    assert result.degraded.fallback_mode == "NONE"


def test_live_runtime_suite_can_skip_degraded(monkeypatch):
    calls: list[str] = []

    def _parity():
        calls.append("parity")
        return type(
            "ParityResult",
            (),
            {
                "complete_issuer_portfolio": "PB_SG_GLOBAL_BAL_001",
                "degraded_issuer_portfolio": "DEMO_ADV_USD_001",
                "degraded_issuer_coverage_status": "unavailable",
                "cold_duration_ms": 100.0,
                "warm_duration_ms": 90.0,
                "workspace_handoff_portfolio": "PB_SG_GLOBAL_BAL_001",
                "lifecycle_portfolio": "PB_SG_GLOBAL_BAL_001",
                "lifecycle_latest_version_no": 2,
                "lifecycle_current_state": "EXECUTED",
                "execution_handoff_status": "REQUESTED",
                "execution_terminal_status": "EXECUTED",
                "report_status": "READY",
            },
        )()

    def _degraded():
        calls.append("degraded")
        raise AssertionError("degraded validator should have been skipped")

    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_cross_service_parity",
        _parity,
    )
    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_degraded_runtime",
        _degraded,
    )

    result = validate_live_runtime_suite(include_degraded=False)

    assert calls == ["parity"]
    assert result.degraded.risk_degraded_reason == "SKIPPED"
    assert result.degraded.core_degraded_reason == "SKIPPED"
