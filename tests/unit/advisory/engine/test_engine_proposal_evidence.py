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
    result = cast(
        ProposalResult,
        _ProposalResult(
            {
                "risk_lens": {
                    "source_service": "lotus-risk",
                    "drawdown": {"proposed": "0.08"},
                }
            }
        ),
    )

    bundle = build_proposal_evidence_bundle(
        artifact_evidence_bundle=_ArtifactEvidenceBundle(),
        proposal_result=result,
        context_resolution={"source": "CANONICAL"},
        context_resolution_override={"source": "WORKSPACE_HANDOFF"},
        replay_lineage={"operation_id": "pop_replay"},
    )

    assert bundle == {
        "hashes": {"artifact_hash": "sha256:artifact"},
        "context_resolution": {"source": "WORKSPACE_HANDOFF"},
        "risk_lens": {
            "source_service": "lotus-risk",
            "drawdown": {"proposed": "0.08"},
        },
        "replay_lineage": {"operation_id": "pop_replay"},
    }


def test_build_proposal_evidence_bundle_uses_context_resolution_without_override():
    result = cast(ProposalResult, _ProposalResult({"risk_lens": {"source_service": ""}}))

    bundle = build_proposal_evidence_bundle(
        artifact_evidence_bundle=_ArtifactEvidenceBundle(),
        proposal_result=result,
        context_resolution={"source": "STATEFUL"},
    )

    assert bundle["context_resolution"] == {"source": "STATEFUL"}
    assert bundle["risk_lens"] is None
    assert "replay_lineage" not in bundle
