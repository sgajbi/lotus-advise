from typing import Any, cast

from src.core.models import ProposalResult
from src.core.proposals.evidence import build_proposal_evidence_bundle


class _ArtifactEvidenceBundle:
    def __init__(self) -> None:
        self.payload = {"hashes": {"artifact_hash": "sha256:artifact"}}

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return dict(self.payload)


class _ProposalResult:
    def __init__(self, explanation: dict[str, Any] | None) -> None:
        self.explanation = explanation


def test_build_proposal_evidence_bundle_preserves_lineage_and_risk_lens():
    explanation = {
        "risk_lens": {
            "source_service": "lotus-risk",
            "drawdown": {"proposed": "0.08"},
        }
    }
    context_resolution_override = {"source": "WORKSPACE_HANDOFF", "lineage": {"step": "handoff"}}
    replay_lineage = {"operation_id": "pop_replay", "attempt": {"count": 1}}
    result = cast(
        ProposalResult,
        _ProposalResult(explanation),
    )

    bundle = build_proposal_evidence_bundle(
        artifact_evidence_bundle=_ArtifactEvidenceBundle(),
        proposal_result=result,
        context_resolution={"source": "CANONICAL"},
        context_resolution_override=context_resolution_override,
        replay_lineage=replay_lineage,
    )

    explanation["risk_lens"]["drawdown"]["proposed"] = "0.99"
    context_resolution_override["lineage"]["step"] = "tampered"
    replay_lineage["attempt"]["count"] = 9

    assert bundle["hashes"] == {"artifact_hash": "sha256:artifact"}
    assert bundle["context_resolution"] == {
        "source": "WORKSPACE_HANDOFF",
        "lineage": {"step": "handoff"},
    }
    assert bundle["risk_lens"] == {
        "source_service": "lotus-risk",
        "drawdown": {"proposed": "0.08"},
    }
    assert bundle["memo_source_readiness"]["contract_version"] == (
        "rfc0024.memo-source-readiness.v1"
    )
    assert bundle["memo_source_readiness"]["capability_posture"] == (
        "SOURCE_READINESS_ONLY_MEMO_GENERATION_NOT_IMPLEMENTED"
    )
    assert bundle["replay_lineage"] == {"operation_id": "pop_replay", "attempt": {"count": 1}}


def test_build_proposal_evidence_bundle_uses_context_resolution_without_override():
    result = cast(ProposalResult, _ProposalResult({"risk_lens": {"source_service": ""}}))
    context_resolution = {"source": "STATEFUL", "policy": {"jurisdiction": "SG"}}

    bundle = build_proposal_evidence_bundle(
        artifact_evidence_bundle=_ArtifactEvidenceBundle(),
        proposal_result=result,
        context_resolution=context_resolution,
    )

    context_resolution["policy"]["jurisdiction"] = "US"

    assert bundle["context_resolution"] == {"source": "STATEFUL", "policy": {"jurisdiction": "SG"}}
    assert bundle["risk_lens"] is None
    assert bundle["memo_source_readiness"]["overall_posture"] == "BLOCKED"
    assert "replay_lineage" not in bundle
