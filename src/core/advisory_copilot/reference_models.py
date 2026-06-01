from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.type_models import CopilotEvidenceAccessClass

_COPILOT_SOURCE_SYSTEM_MAX_LENGTH = 64
_COPILOT_SOURCE_TYPE_MAX_LENGTH = 96
_COPILOT_SOURCE_ID_MAX_LENGTH = 160
_COPILOT_CONTENT_HASH_MAX_LENGTH = 128
_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_LINEAGE_TYPE_MAX_LENGTH = 96


class CopilotSourceRef(BaseModel):
    source_system: str = Field(
        description="Authoritative Lotus system that owns the cited evidence.",
        examples=["lotus-advise"],
        min_length=1,
        max_length=_COPILOT_SOURCE_SYSTEM_MAX_LENGTH,
    )
    source_type: str = Field(
        description="Evidence family emitted by the source authority.",
        examples=["POLICY_EVALUATION"],
        min_length=1,
        max_length=_COPILOT_SOURCE_TYPE_MAX_LENGTH,
    )
    source_id: str = Field(
        description="Stable source evidence identifier safe for audit use.",
        examples=["policy_eval_sg_001"],
        min_length=1,
        max_length=_COPILOT_SOURCE_ID_MAX_LENGTH,
    )
    content_hash: str | None = Field(
        default=None,
        description="Source content hash when the source authority exposes one.",
        examples=["sha256:policy-evaluation"],
        min_length=1,
        max_length=_COPILOT_CONTENT_HASH_MAX_LENGTH,
    )
    access_class: CopilotEvidenceAccessClass = Field(
        description="Projection and access class for this evidence ref.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )

    @field_validator("source_system", "source_type", "source_id")
    @classmethod
    def _normalize_required_ref_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_SOURCE_REF_REQUIRED")

    @field_validator("content_hash")
    @classmethod
    def _normalize_optional_ref_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, error_code="COPILOT_SOURCE_REF_REQUIRED")


class CopilotLineageRef(BaseModel):
    lineage_type: str = Field(
        description="Lineage reference family, such as evidence packet, workflow run, or review.",
        examples=["EVIDENCE_PACKET"],
        min_length=1,
        max_length=_COPILOT_LINEAGE_TYPE_MAX_LENGTH,
    )
    lineage_id: str = Field(
        description="Stable lineage reference identifier.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    source_system: str = Field(
        description="System that owns the lineage reference.",
        examples=["lotus-advise"],
        min_length=1,
        max_length=_COPILOT_SOURCE_SYSTEM_MAX_LENGTH,
    )

    @field_validator("lineage_type", "lineage_id", "source_system")
    @classmethod
    def _normalize_required_lineage_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_LINEAGE_REF_REQUIRED")


def _normalize_required_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized
