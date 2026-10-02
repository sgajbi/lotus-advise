import pytest

from src.integrations.lotus_core.benchmark_assignment import (
    LotusCoreBenchmarkAssignmentUnavailableError as BenchmarkUnavailable,
)
from src.runtime import advisory_provider_ports

_resolve = advisory_provider_ports._resolve_benchmark_assignment_evidence_with_lotus_core_port
_FETCH = "fetch_benchmark_assignment_with_lotus_core"


def test_runtime_port_maps_admitted_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", " tenant-sg ")
    monkeypatch.setattr(
        advisory_provider_ports,
        _FETCH,
        lambda **kwargs: captured.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        advisory_provider_ports,
        "asdict",
        lambda _assignment: {
            "effective_benchmark_id": "BM_1",
            "source_tenant_id": "tenant-sg",
            "source_content_hash": "sha256:" + "a" * 64,
            "source_references": ("core://assignment/1",),
            "supportability": "READY",
        },
    )
    evidence = _resolve("PF_554", "2026-03-25", "USD", {"tenant_id": "caller-choice"}, "corr-554")
    assert captured["tenant_id"] == evidence.source_tenant_id == "tenant-sg"
    assert evidence.benchmark_assignment_content_hash == "sha256:" + "a" * 64


def test_runtime_port_refuses_missing_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOTUS_ADVISE_TENANT_ID", raising=False)

    def _unexpected(**_kwargs: object) -> None:
        raise AssertionError("unexpected Core request")

    monkeypatch.setattr(advisory_provider_ports, _FETCH, _unexpected)
    evidence = _resolve("PF_554", "2026-03-25", None, None, "corr-554")
    assert evidence.reason_code == "BENCHMARK_EVIDENCE_TENANT_REQUIRED"


def test_runtime_port_preserves_typed_source_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "tenant-sg")

    def _refuse(**_kwargs: object) -> object:
        raise BenchmarkUnavailable("CORE_BENCHMARK_ASSIGNMENT_SOURCE_NOT_FOUND")

    monkeypatch.setattr(advisory_provider_ports, _FETCH, _refuse)
    evidence = _resolve("PF_554", "2026-03-25", None, None, "corr-554")
    assert evidence.reason_code == "BENCHMARK_EVIDENCE_SOURCE_NOT_FOUND"
