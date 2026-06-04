from pathlib import Path

from src.core.advisory import narrative_models, narrative_types
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket as OwnedProposalNarrativeGroundingPacket,
)
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeMissingEvidence as OwnedProposalNarrativeMissingEvidence,
)
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeSourceRef as OwnedProposalNarrativeSourceRef,
)
from src.core.advisory.narrative_request_models import (
    ProposalNarrativeRequest as OwnedProposalNarrativeRequest,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_proposal_narrative_vocabulary_types_keep_stable_facade_imports() -> None:
    assert narrative_models.ProposalNarrativeAudience is narrative_types.ProposalNarrativeAudience
    assert (
        narrative_models.ProposalNarrativeClientAudience
        is narrative_types.ProposalNarrativeClientAudience
    )
    assert (
        narrative_models.ProposalNarrativeSectionKey is narrative_types.ProposalNarrativeSectionKey
    )
    assert (
        narrative_models.ProposalNarrativeReviewAction
        is narrative_types.ProposalNarrativeReviewAction
    )


def test_proposal_narrative_vocabulary_types_are_split_from_model_facade() -> None:
    source_root = REPO_ROOT / "src" / "core" / "advisory"
    facade = (source_root / "narrative_models.py").read_text(encoding="utf-8")
    types = (source_root / "narrative_types.py").read_text(encoding="utf-8")

    assert "ProposalNarrativeAudience = Literal" not in facade
    assert "ProposalNarrativeReviewAction = Literal" not in facade
    assert "ProposalNarrativeAudience = Literal" in types
    assert "ProposalNarrativeReviewAction = Literal" in types


def test_proposal_narrative_request_model_keeps_stable_facade_import() -> None:
    assert narrative_models.ProposalNarrativeRequest is OwnedProposalNarrativeRequest
    assert (
        narrative_models.ProposalNarrativeRequest.__module__
        == "src.core.advisory.narrative_request_models"
    )


def test_proposal_narrative_grounding_models_keep_stable_facade_imports() -> None:
    assert narrative_models.ProposalNarrativeGroundingPacket is (
        OwnedProposalNarrativeGroundingPacket
    )
    assert narrative_models.ProposalNarrativeMissingEvidence is (
        OwnedProposalNarrativeMissingEvidence
    )
    assert narrative_models.ProposalNarrativeSourceRef is OwnedProposalNarrativeSourceRef
    assert (
        narrative_models.ProposalNarrativeGroundingPacket.__module__
        == "src.core.advisory.narrative_grounding_models"
    )
