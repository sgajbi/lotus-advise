from __future__ import annotations

from typing import Any, cast, get_args

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.business_text import (
    normalize_required_copilot_business_text,
)
from src.core.advisory_copilot.reference_models import CopilotSourceRef
from src.core.advisory_copilot.section_tuple_normalization import (
    normalize_summary_items,
    normalize_unique_literal_items,
)
from src.core.advisory_copilot.type_models import CopilotAudience, CopilotEvidenceAccessClass

_COPILOT_SECTION_KEY_MAX_LENGTH = 96
_COPILOT_SECTION_TITLE_MAX_LENGTH = 160
_COPILOT_SUMMARY_ITEM_LIMIT = 8
_COPILOT_SUMMARY_ITEM_MAX_LENGTH = 1000
_COPILOT_SOURCE_REF_LIMIT = 8
COPILOT_AUDIENCE_LIMIT = 5
_COPILOT_ALLOWED_AUDIENCES = set(get_args(CopilotAudience))


class CopilotEvidencePacketSection(BaseModel):
    section_key: str = Field(
        description="Stable evidence section key included in the packet.",
        examples=["POLICY_POSTURE"],
        min_length=1,
        max_length=_COPILOT_SECTION_KEY_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing section title.",
        examples=["Policy posture"],
        min_length=1,
        max_length=_COPILOT_SECTION_TITLE_MAX_LENGTH,
    )
    evidence_class: CopilotEvidenceAccessClass = Field(
        description="Access class for this evidence section.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )
    source_refs: tuple[CopilotSourceRef, ...] = Field(
        description="Source refs used to build this evidence section.",
        min_length=1,
        max_length=_COPILOT_SOURCE_REF_LIMIT,
    )
    summary_items: tuple[str, ...] = Field(
        default=(),
        description="Business-safe evidence statements allowed for the requested projection.",
        examples=[["Policy evaluation requires compliance review."]],
        max_length=_COPILOT_SUMMARY_ITEM_LIMIT,
    )

    @field_validator("section_key", "title")
    @classmethod
    def _normalize_required_section_text(cls, value: str) -> str:
        return cast(
            str,
            normalize_required_copilot_business_text(
                value,
                error_code="COPILOT_EVIDENCE_SECTION_REQUIRED",
            ),
        )

    @field_validator("summary_items", mode="before")
    @classmethod
    def _normalize_summary_items(cls, value: Any) -> tuple[str, ...]:
        return _normalize_summary_tuple(value, allow_empty=True)


class CopilotEvidenceSectionInput(BaseModel):
    section_key: str = Field(
        description="Stable evidence section key offered by the source projection.",
        examples=["POLICY_POSTURE"],
        min_length=1,
        max_length=_COPILOT_SECTION_KEY_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing section title.",
        examples=["Policy posture"],
        min_length=1,
        max_length=_COPILOT_SECTION_TITLE_MAX_LENGTH,
    )
    evidence_class: CopilotEvidenceAccessClass = Field(
        description="Access class for this source section.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )
    source_refs: tuple[CopilotSourceRef, ...] = Field(
        description="Source refs used to build this evidence section.",
        min_length=1,
        max_length=_COPILOT_SOURCE_REF_LIMIT,
    )
    summary_items: tuple[str, ...] = Field(
        description="Business-safe evidence statements emitted by the source projection.",
        examples=[["Policy evaluation requires compliance review."]],
        min_length=1,
        max_length=_COPILOT_SUMMARY_ITEM_LIMIT,
    )
    allowed_audiences: tuple[CopilotAudience, ...] = Field(
        description="Audiences allowed to receive this evidence section.",
        examples=[["ADVISOR", "COMPLIANCE_REVIEWER"]],
        min_length=1,
        max_length=COPILOT_AUDIENCE_LIMIT,
    )

    @field_validator("section_key", "title")
    @classmethod
    def _normalize_required_section_text(cls, value: str) -> str:
        return cast(
            str,
            normalize_required_copilot_business_text(
                value,
                error_code="COPILOT_EVIDENCE_SECTION_REQUIRED",
            ),
        )

    @field_validator("summary_items", mode="before")
    @classmethod
    def _normalize_summary_items(cls, value: Any) -> tuple[str, ...]:
        return _normalize_summary_tuple(value, allow_empty=False)

    @field_validator("allowed_audiences", mode="before")
    @classmethod
    def _normalize_allowed_audiences(cls, value: Any) -> tuple[CopilotAudience, ...]:
        return _normalize_audience_tuple(value)


def _normalize_summary_tuple(value: Any, *, allow_empty: bool) -> tuple[str, ...]:
    return normalize_summary_items(
        value,
        allow_empty=allow_empty,
        item_limit=_COPILOT_SUMMARY_ITEM_LIMIT,
        item_max_length=_COPILOT_SUMMARY_ITEM_MAX_LENGTH,
    )


def _normalize_audience_tuple(value: Any) -> tuple[CopilotAudience, ...]:
    return cast(
        tuple[CopilotAudience, ...],
        normalize_unique_literal_items(
            value,
            allowed=_COPILOT_ALLOWED_AUDIENCES,
            limit=COPILOT_AUDIENCE_LIMIT,
            invalid_error_code="COPILOT_AUDIENCE_INVALID",
            empty_error_code="COPILOT_AUDIENCE_REQUIRED",
            too_large_error_code="COPILOT_AUDIENCE_TOO_LARGE",
        ),
    )
