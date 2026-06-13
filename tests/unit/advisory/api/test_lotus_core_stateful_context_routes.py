from __future__ import annotations

from src.integrations.lotus_core.stateful_context_routes import resolve_control_plane_base_url


def test_control_plane_base_url_derives_from_query_service_name(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", "http://lotus-core-query/api/")

    assert resolve_control_plane_base_url() == "http://lotus-core-control/api"
