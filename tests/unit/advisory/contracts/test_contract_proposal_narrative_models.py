from pathlib import Path

from src.core.advisory import narrative_models, narrative_types
from src.core.advisory.narrative_ai_models import (
    ProposalNarrativeAiLineage as OwnedProposalNarrativeAiLineage,
)
from src.core.advisory.narrative_envelope_models import (
    ProposalNarrative as OwnedProposalNarrative,
)
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket as OwnedProposalNarrativeGroundingPacket,
)
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeMissingEvidence as OwnedProposalNarrativeMissingEvidence,
)
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeSourceRef as OwnedProposalNarrativeSourceRef,
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativeDisclosure as OwnedProposalNarrativeDisclosure,
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativeGuardrailResult as OwnedProposalNarrativeGuardrailResult,
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativePolicy as OwnedProposalNarrativePolicy,
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativePolicyContext as OwnedProposalNarrativePolicyContext,
)
from src.core.advisory.narrative_request_models import (
    ProposalNarrativeRequest as OwnedProposalNarrativeRequest,
)
from src.core.advisory.narrative_review_models import (
    ProposalNarrativeReviewRecord as OwnedProposalNarrativeReviewRecord,
)
from src.core.advisory.narrative_review_models import (
    ProposalNarrativeReviewRequest as OwnedProposalNarrativeReviewRequest,
)
from src.core.advisory.narrative_section_models import (
    ProposalNarrativeSection as OwnedProposalNarrativeSection,
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


def test_proposal_narrative_section_model_keeps_stable_facade_import() -> None:
    assert narrative_models.ProposalNarrativeSection is OwnedProposalNarrativeSection
    assert (
        narrative_models.ProposalNarrativeSection.__module__
        == "src.core.advisory.narrative_section_models"
    )


def test_proposal_narrative_policy_models_keep_stable_facade_imports() -> None:
    assert narrative_models.ProposalNarrativeDisclosure is OwnedProposalNarrativeDisclosure
    assert narrative_models.ProposalNarrativeGuardrailResult is (
        OwnedProposalNarrativeGuardrailResult
    )
    assert narrative_models.ProposalNarrativePolicy is OwnedProposalNarrativePolicy
    assert narrative_models.ProposalNarrativePolicyContext is OwnedProposalNarrativePolicyContext
    assert (
        narrative_models.ProposalNarrativePolicy.__module__
        == "src.core.advisory.narrative_policy_models"
    )


def test_proposal_narrative_ai_lineage_model_keeps_stable_facade_import() -> None:
    assert narrative_models.ProposalNarrativeAiLineage is OwnedProposalNarrativeAiLineage
    assert (
        narrative_models.ProposalNarrativeAiLineage.__module__
        == "src.core.advisory.narrative_ai_models"
    )


def test_proposal_narrative_envelope_model_keeps_stable_facade_import() -> None:
    assert narrative_models.ProposalNarrative is OwnedProposalNarrative
    assert (
        narrative_models.ProposalNarrative.__module__
        == "src.core.advisory.narrative_envelope_models"
    )


def test_proposal_narrative_review_models_keep_stable_facade_imports() -> None:
    assert narrative_models.ProposalNarrativeReviewRecord is OwnedProposalNarrativeReviewRecord
    assert narrative_models.ProposalNarrativeReviewRequest is OwnedProposalNarrativeReviewRequest
    assert (
        narrative_models.ProposalNarrativeReviewRecord.__module__
        == "src.core.advisory.narrative_review_models"
    )


def test_proposal_narrative_runtime_uses_focused_model_imports() -> None:
    for path in (REPO_ROOT / "src").rglob("*.py"):
        if path.name == "narrative_models.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "from src.core.advisory.narrative_models import" not in source, path
