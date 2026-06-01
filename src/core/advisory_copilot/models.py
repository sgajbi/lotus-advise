from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.business_text import (
    assert_copilot_business_safe_text as assert_copilot_business_safe_text,
)
from src.core.advisory_copilot.business_text import (
    contains_copilot_business_technical_detail as contains_copilot_business_technical_detail,
)
from src.core.advisory_copilot.catalog_models import (
    CopilotActionDefinition as CopilotActionDefinition,
)
from src.core.advisory_copilot.catalog_models import (
    CopilotBusinessProjection as CopilotBusinessProjection,
)
from src.core.advisory_copilot.reference_models import (
    CopilotLineageRef as CopilotLineageRef,
)
from src.core.advisory_copilot.reference_models import (
    CopilotSourceRef as CopilotSourceRef,
)
from src.core.advisory_copilot.section_models import (
    COPILOT_AUDIENCE_LIMIT as COPILOT_AUDIENCE_LIMIT,
)
from src.core.advisory_copilot.section_models import (
    CopilotEvidencePacketSection as CopilotEvidencePacketSection,
)
from src.core.advisory_copilot.section_models import (
    CopilotEvidenceSectionInput as CopilotEvidenceSectionInput,
)
from src.core.advisory_copilot.type_models import (
    CopilotActionFamily as CopilotActionFamily,
)
from src.core.advisory_copilot.type_models import (
    CopilotAudience as CopilotAudience,
)
from src.core.advisory_copilot.type_models import (
    CopilotClientReadyPosture as CopilotClientReadyPosture,
)
from src.core.advisory_copilot.type_models import (
    CopilotEvidenceAccessClass as CopilotEvidenceAccessClass,
)
from src.core.advisory_copilot.type_models import (
    CopilotRetentionClass as CopilotRetentionClass,
)
from src.core.advisory_copilot.type_models import (
    CopilotReviewPosture as CopilotReviewPosture,
)
from src.core.advisory_copilot.type_models import (
    CopilotSourceDependency as CopilotSourceDependency,
)
from src.core.advisory_copilot.type_models import (
    CopilotUnsupportedEvidenceReason as CopilotUnsupportedEvidenceReason,
)
from src.core.advisory_copilot.unsupported_models import (
    CopilotUnsupportedEvidence as CopilotUnsupportedEvidence,
)

_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_HASH_MAX_LENGTH = 128
_COPILOT_LINEAGE_REF_LIMIT = 16
_COPILOT_UNSUPPORTED_EVIDENCE_LIMIT = 12
COPILOT_PACKET_SECTION_LIMIT = 12


class CopilotEvidencePacket(BaseModel):
    evidence_packet_id: str = Field(
        description="Stable evidence-packet identifier for copilot action execution.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_hash: str = Field(
        description="Deterministic hash of projected packet content and source refs.",
        examples=["sha256:copilot-packet"],
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    action_family: CopilotActionFamily = Field(
        description="Copilot action family this packet supports.",
        examples=["COMPLIANCE_REVIEW_SUMMARY"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for source-scoped advisory evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the copilot action is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    sections: tuple[CopilotEvidencePacketSection, ...] = Field(
        description="Redacted, source-backed evidence sections allowed for the action.",
        max_length=COPILOT_PACKET_SECTION_LIMIT,
    )
    unsupported_evidence: tuple[CopilotUnsupportedEvidence, ...] = Field(
        default=(),
        description="Controlled unsupported-evidence posture for missing or restricted sources.",
        max_length=_COPILOT_UNSUPPORTED_EVIDENCE_LIMIT,
    )
    lineage_refs: tuple[CopilotLineageRef, ...] = Field(
        default=(),
        description="Lineage refs for packet, source, workflow, review, and audit evidence.",
        max_length=_COPILOT_LINEAGE_REF_LIMIT,
    )
    retention_class: CopilotRetentionClass = Field(
        description="Retention class for evidence-packet handling.",
        examples=["ADVISORY_REVIEW_RECORD"],
    )
    client_ready_publication: CopilotClientReadyPosture = Field(
        default="BLOCKED",
        description="Client-ready publication posture for evidence produced by this packet.",
        examples=["BLOCKED"],
    )

    @field_validator("evidence_packet_id", "evidence_packet_hash", "portfolio_id")
    @classmethod
    def _normalize_required_packet_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_EVIDENCE_PACKET_REQUIRED")

    @field_validator("proposal_id")
    @classmethod
    def _normalize_optional_packet_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, error_code="COPILOT_EVIDENCE_PACKET_REQUIRED")


def _normalize_required_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized
