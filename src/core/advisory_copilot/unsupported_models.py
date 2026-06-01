from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.business_text import (
    contains_copilot_business_technical_detail,
)
from src.core.advisory_copilot.type_models import (
    CopilotSourceDependency,
    CopilotUnsupportedEvidenceReason,
)

_COPILOT_UNSUPPORTED_MESSAGE_MAX_LENGTH = 500


class CopilotUnsupportedEvidence(BaseModel):
    reason_code: CopilotUnsupportedEvidenceReason = Field(
        description="Stable reason code for unsupported or unavailable evidence.",
        examples=["SOURCE_NOT_AVAILABLE"],
    )
    source_dependency: CopilotSourceDependency | None = Field(
        default=None,
        description="Source dependency that prevented support when applicable.",
        examples=["RFC0025_POLICY_EVALUATION"],
    )
    advisor_message: str = Field(
        description="Business-facing explanation that avoids technical internals.",
        examples=["Policy evidence is not available for this request."],
        min_length=1,
        max_length=_COPILOT_UNSUPPORTED_MESSAGE_MAX_LENGTH,
    )

    @field_validator("advisor_message")
    @classmethod
    def _normalize_advisor_message(cls, value: str) -> str:
        normalized = _normalize_required_text(
            value,
            error_code="COPILOT_UNSUPPORTED_MESSAGE_REQUIRED",
        )
        if contains_copilot_business_technical_detail(normalized):
            raise ValueError("COPILOT_UNSUPPORTED_MESSAGE_TECHNICAL_DETAIL")
        return normalized


def _normalize_required_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized
