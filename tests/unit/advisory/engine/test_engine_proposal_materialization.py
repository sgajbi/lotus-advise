from datetime import datetime, timezone
from typing import Any, cast

from src.core.models import ProposalResult, ProposalSimulateRequest
from src.core.proposals.materialization import build_proposal_version_materialization


class _ArtifactEvidenceBundle:
    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return {"hashes": {"artifact_hash": "sha256:artifact"}}


class _Artifact:
    evidence_bundle = _ArtifactEvidenceBundle()

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return {"artifact": "payload"}


def _simulate_request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest(
        portfolio_snapshot={
            "portfolio_id": "pf_materialization",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        market_data_snapshot={
            "prices": [{"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        shelf_entries=[{"instrument_id": "EQ_OLD", "status": "APPROVED"}],
        options={"enable_proposal_simulation": True},
        proposed_trades=[],
        proposed_cash_flows=[],
    )


def test_build_proposal_version_materialization_builds_artifact_and_evidence(monkeypatch):
    calls: dict[str, Any] = {}

    def _build_proposal_artifact(**kwargs):
        calls["artifact"] = kwargs
        return _Artifact()

    def _build_proposal_evidence_bundle(**kwargs):
        calls["evidence"] = kwargs
        return {"lineage": "complete"}

    monkeypatch.setattr(
        "src.core.proposals.materialization.build_proposal_artifact",
        _build_proposal_artifact,
    )
    monkeypatch.setattr(
        "src.core.proposals.materialization.build_proposal_evidence_bundle",
        _build_proposal_evidence_bundle,
    )

    proposal_result = cast(ProposalResult, object())
    created_at = datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc)

    materialization = build_proposal_version_materialization(
        request=_simulate_request(),
        proposal_result=proposal_result,
        created_at=created_at,
        context_resolution={"source": "LOTUS_CORE"},
        context_resolution_override={"source": "WORKSPACE_HANDOFF"},
        replay_lineage={"operation_id": "pop_materialization"},
    )

    assert materialization.artifact.model_dump(mode="json") == {"artifact": "payload"}
    assert materialization.evidence_bundle == {"lineage": "complete"}
    assert calls["artifact"]["created_at"] == "2026-05-21T10:00:00+00:00"
    assert calls["evidence"]["artifact_evidence_bundle"] is materialization.artifact.evidence_bundle
    assert calls["evidence"]["proposal_result"] is proposal_result
    assert calls["evidence"]["context_resolution"] == {"source": "LOTUS_CORE"}
    assert calls["evidence"]["context_resolution_override"] == {"source": "WORKSPACE_HANDOFF"}
    assert calls["evidence"]["replay_lineage"] == {"operation_id": "pop_materialization"}
