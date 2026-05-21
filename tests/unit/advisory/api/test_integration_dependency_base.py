from src.integrations.base import build_dependency_state


def test_build_dependency_state_skips_network_probe_outside_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("TEST_BASE_URL", "http://dependency.example")
    calls: list[str] = []

    def _probe(base_url: str) -> bool:
        calls.append(base_url)
        return False

    monkeypatch.setattr("src.integrations.base.probe_dependency_health", _probe)

    state = build_dependency_state(
        key="lotus_test",
        service_name="lotus-test",
        description="Test dependency",
        base_url_env="TEST_BASE_URL",
    )

    assert state.configured is True
    assert state.operational_ready is True
    assert state.runtime_probe_enabled is False
    assert state.readiness_basis == "configuration_only"
    assert state.degraded_reason is None
    assert calls == []


def test_build_dependency_state_marks_dependency_unready_when_production_probe_fails(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TEST_BASE_URL", "http://dependency.example")
    monkeypatch.setattr("src.integrations.base.probe_dependency_health", lambda base_url: False)

    state = build_dependency_state(
        key="lotus_test",
        service_name="lotus-test",
        description="Test dependency",
        base_url_env="TEST_BASE_URL",
    )

    assert state.configured is True
    assert state.operational_ready is False
    assert state.runtime_probe_enabled is True
    assert state.readiness_basis == "probe_failed"
    assert state.degraded_reason == "LOTUS_TEST_DEPENDENCY_UNAVAILABLE"


def test_build_dependency_state_does_not_claim_probe_when_production_dependency_unconfigured(
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("TEST_BASE_URL", raising=False)

    state = build_dependency_state(
        key="lotus_test",
        service_name="lotus-test",
        description="Test dependency",
        base_url_env="TEST_BASE_URL",
    )

    assert state.configured is False
    assert state.operational_ready is False
    assert state.runtime_probe_enabled is False
    assert state.readiness_basis == "not_configured"
    assert state.degraded_reason == "LOTUS_TEST_DEPENDENCY_UNAVAILABLE"


def test_build_dependency_state_marks_dependency_ready_when_production_probe_succeeds(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TEST_BASE_URL", "http://dependency.example")
    monkeypatch.setattr("src.integrations.base.probe_dependency_health", lambda base_url: True)

    state = build_dependency_state(
        key="lotus_test",
        service_name="lotus-test",
        description="Test dependency",
        base_url_env="TEST_BASE_URL",
    )

    assert state.configured is True
    assert state.operational_ready is True
    assert state.runtime_probe_enabled is True
    assert state.readiness_basis == "probe_succeeded"
    assert state.degraded_reason is None
