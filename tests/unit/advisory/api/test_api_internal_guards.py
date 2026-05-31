import inspect

import pytest

from src.api.proposals.errors import raise_proposal_http_exception
from src.api.routers.advisory_simulation import (
    build_proposal_artifact_endpoint,
    simulate_proposal,
)
from src.integrations.lotus_core.simulation import (
    LotusCoreSimulationUnavailableError,
    simulate_with_lotus_core,
)


def test_raise_proposal_http_exception_re_raises_unknown_exception():
    with pytest.raises(ValueError, match="unexpected"):
        raise_proposal_http_exception(ValueError("unexpected"))


def test_lotus_core_simulation_raises_when_core_base_url_not_configured(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    with pytest.raises(
        LotusCoreSimulationUnavailableError,
        match="LOTUS_CORE_SIMULATION_UNAVAILABLE",
    ):
        simulate_with_lotus_core(
            request=object(),  # type: ignore[arg-type]
            request_hash="hash",
            idempotency_key=None,
            correlation_id="corr-test",
        )


def test_lotus_core_simulation_does_not_use_query_base_url(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", "http://core-query.dev.lotus")

    with pytest.raises(
        LotusCoreSimulationUnavailableError,
        match="LOTUS_CORE_SIMULATION_UNAVAILABLE",
    ):
        simulate_with_lotus_core(
            request=object(),  # type: ignore[arg-type]
            request_hash="hash",
            idempotency_key=None,
            correlation_id="corr-test",
        )


def test_advisory_simulation_routes_do_not_depend_on_legacy_db_session():
    for endpoint in (simulate_proposal, build_proposal_artifact_endpoint):
        assert "db" not in inspect.signature(endpoint).parameters
