import httpx
import pytest

from src.integrations.base import (
    build_dependency_state,
    probe_dependency_health,
    runtime_dependency_probing_enabled,
)


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeClient:
    def __init__(self, *args, responses: dict[str, object], **kwargs) -> None:
        self._responses = responses
        self._enter_error = kwargs.get("enter_error")

    def __enter__(self) -> "_FakeClient":
        if isinstance(self._enter_error, Exception):
            raise self._enter_error
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False

    def get(self, url: str) -> _FakeResponse:
        response = self._responses.get(url, httpx.ConnectError("unavailable"))
        if isinstance(response, Exception):
            raise response
        return response


def test_runtime_dependency_probing_enabled_respects_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTUS_DEPENDENCY_RUNTIME_PROBES", "yes")
    assert runtime_dependency_probing_enabled() is True

    monkeypatch.setenv("LOTUS_DEPENDENCY_RUNTIME_PROBES", "off")
    assert runtime_dependency_probing_enabled() is False

    monkeypatch.delenv("LOTUS_DEPENDENCY_RUNTIME_PROBES", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert runtime_dependency_probing_enabled() is True


def test_probe_dependency_health_checks_ready_then_health(monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "http://service.dev.lotus"
    monkeypatch.setattr(
        "src.integrations.base.httpx.Client",
        lambda *args, **kwargs: _FakeClient(
            *args,
            responses={
                f"{base_url}/health/ready": httpx.ReadTimeout("not ready"),
                f"{base_url}/health": _FakeResponse(200),
            },
            **kwargs,
        ),
    )

    assert probe_dependency_health(base_url) is True


def test_probe_dependency_health_reports_false_for_not_ready_and_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = "http://service.dev.lotus"
    monkeypatch.setattr(
        "src.integrations.base.httpx.Client",
        lambda *args, **kwargs: _FakeClient(
            *args,
            responses={f"{base_url}/health/ready": _FakeResponse(503)},
            **kwargs,
        ),
    )
    assert probe_dependency_health(base_url) is False

    monkeypatch.setattr(
        "src.integrations.base.httpx.Client",
        lambda *args, **kwargs: _FakeClient(
            *args,
            responses={},
            **kwargs,
        ),
    )
    assert probe_dependency_health(base_url) is False

    monkeypatch.setattr(
        "src.integrations.base.httpx.Client",
        lambda *args, **kwargs: _FakeClient(
            *args,
            responses={},
            enter_error=httpx.ConnectError("client unavailable"),
            **kwargs,
        ),
    )
    assert probe_dependency_health(base_url) is False


def test_build_dependency_state_respects_configuration_and_probe_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOTUS_AI_BASE_URL", raising=False)
    unconfigured = build_dependency_state(
        key="lotus-ai",
        service_name="lotus-ai",
        description="AI runtime",
        base_url_env="LOTUS_AI_BASE_URL",
    )
    assert unconfigured.configured is False
    assert unconfigured.operational_ready is False

    monkeypatch.setenv("LOTUS_AI_BASE_URL", "http://lotus-ai.dev.lotus")
    monkeypatch.setattr("src.integrations.base.runtime_dependency_probing_enabled", lambda: False)
    configured = build_dependency_state(
        key="lotus-ai",
        service_name="lotus-ai",
        description="AI runtime",
        base_url_env="LOTUS_AI_BASE_URL",
    )
    assert configured.configured is True
    assert configured.operational_ready is True

    monkeypatch.setattr("src.integrations.base.runtime_dependency_probing_enabled", lambda: True)
    monkeypatch.setattr("src.integrations.base.probe_dependency_health", lambda base_url: False)
    degraded = build_dependency_state(
        key="lotus-ai",
        service_name="lotus-ai",
        description="AI runtime",
        base_url_env="LOTUS_AI_BASE_URL",
    )
    assert degraded.configured is True
    assert degraded.operational_ready is False
