import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.advisory.provider_ports import (
    configure_advisory_benchmark_assignment_evidence_provider,
)
from src.core.proposals.context_ports import configure_proposal_stateful_context_resolver
from src.integrations.lotus_core import benchmark_assignment
from src.runtime.advisory_provider_ports import (
    _resolve_benchmark_assignment_evidence_with_lotus_core_port,
)
from tests.shared.stateful_context_builders import build_resolved_stateful_context


@pytest.mark.parametrize("revision", ["rfc_062_v1", "rfc_062_v999", None, 42])
def test_registered_benchmark_contract_admission_preserves_immutable_versions(
    monkeypatch: pytest.MonkeyPatch, revision: object
) -> None:
    fixture = Path("tests/fixtures/lotus_core/benchmark_assignment_v1.json")
    source = json.loads(fixture.read_text())
    source.pop("contract_version")
    if revision is not None:
        source["contract_version"] = revision
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["X-Tenant-Id"] == "tenant_sg"
        assert request.headers["X-Service-Identity"] == "lotus-advise"
        return httpx.Response(200, json=source)

    original_client = httpx.Client
    monkeypatch.setattr(
        benchmark_assignment.httpx,
        "Client",
        lambda **_kwargs: original_client(transport=httpx.MockTransport(respond)),
    )
    monkeypatch.setenv("LOTUS_ADVISE_TENANT_ID", "tenant_sg")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "")
    configure_advisory_benchmark_assignment_evidence_provider(
        _resolve_benchmark_assignment_evidence_with_lotus_core_port
    )
    configure_proposal_stateful_context_resolver(
        lambda request: build_resolved_stateful_context(request.portfolio_id, request.as_of)
    )
    payload = {
        "created_by": "advisor_554",
        "input_mode": "stateful",
        "stateful_input": {"portfolio_id": "PF_1", "as_of": "2026-03-25"},
    }
    try:
        with TestClient(app) as client:
            created = client.post(
                "/advisory/proposals",
                json=payload,
                headers={"Idempotency-Key": "benchmark-contract-create"},
            )
            assert created.status_code == 200, created.text
            proposal_id = created.json()["proposal"]["proposal_id"]
            original = created.json()["version"]
            evidence = original["proposal_result"]["proposal_review_evidence"]
            assignment = evidence["benchmark_assignment"]
            if revision == "rfc_062_v1":
                assert assignment["supportability"] == "READY"
                assert assignment["assignment_contract_version"] == "rfc_062_v1"
                assert assignment["source_tenant_id"] == "tenant_sg"
                assert assignment["source_lineage"] == source["source_lineage"]
                assert assignment["benchmark_assignment_content_hash"] == source["content_hash"]
                assert assignment["source_references"] == source["source_refs"]
            else:
                assert assignment["supportability"] == "UNAVAILABLE"
                assert assignment["reason_code"] == "BENCHMARK_EVIDENCE_SOURCE_INVALID"
                assert assignment["effective_benchmark_id"] is None
            assert evidence["current_mandate_limits"]["supportability"] == "UNAVAILABLE"
            assert evidence["simulated_mandate_limits"]["supportability"] == "UNAVAILABLE"

            source["contract_version"] = (
                "rfc_062_v999" if revision == "rfc_062_v1" else "rfc_062_v1"
            )
            versioned = client.post(
                f"/advisory/proposals/{proposal_id}/versions",
                json=payload,
                headers={"Idempotency-Key": "benchmark-contract-version"},
            )
            assert versioned.status_code == 200, versioned.text
            updated = versioned.json()["version"]["proposal_result"]["proposal_review_evidence"]
            assert updated["benchmark_assignment"]["supportability"] == (
                "UNAVAILABLE" if revision == "rfc_062_v1" else "READY"
            )
            retained = client.get(f"/advisory/proposals/{proposal_id}/versions/1")
            replay = client.get(f"/advisory/proposals/{proposal_id}/versions/1/replay-evidence")
            assert retained.status_code == replay.status_code == 200
            assert retained.json() == original
            assert replay.json()["hashes"]["request_hash"] == original["request_hash"]
            assert replay.json()["hashes"]["artifact_hash"] == original["artifact_hash"]
            assert len(calls) == 2
    finally:
        configure_advisory_benchmark_assignment_evidence_provider(None)
        configure_proposal_stateful_context_resolver(None)
