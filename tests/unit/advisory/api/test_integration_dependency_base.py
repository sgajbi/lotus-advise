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
