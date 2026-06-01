from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.api_limits import (
    COPILOT_CURSOR_MAX_LENGTH,
    COPILOT_REQUESTED_INTENT_LIMIT,
    COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT,
    COPILOT_SUPPORTABILITY_BOUNDARY_MAX_LENGTH,
    COPILOT_SUPPORTABILITY_STATUS_MAX_LENGTH,
)
from src.core.advisory_copilot.api_validation import normalize_bounded_copilot_string_tuple
from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.packet_records import AdvisoryCopilotEvidencePacketRecord
from src.core.advisory_copilot.pagination import COPILOT_RUN_MAX_PAGE_SIZE
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.type_models import CopilotActionFamily


class AdvisoryCopilotEvidencePacketResponse(BaseModel):
    evidence_packet: CopilotEvidencePacket = Field(
        description="Bounded, redacted copilot evidence packet."
    )
    record: AdvisoryCopilotEvidencePacketRecord = Field(
        description="Durable evidence-packet record and audit context."
    )


class AdvisoryCopilotRunResponse(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(description="Persisted advisory copilot run.")
    reviews: tuple[AdvisoryCopilotReviewRecord, ...] = Field(
        default=(),
        description="Ordered review audit events for the run.",
    )
    replayed: bool = Field(
        default=False,
        description="Whether the action request replayed an existing idempotent run.",
    )


class AdvisoryCopilotReviewResponse(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(description="Run after review processing.")
    review: AdvisoryCopilotReviewRecord = Field(description="Persisted review event.")
    replayed: bool = Field(description="Whether this was an idempotent replay.")


class AdvisoryCopilotSupportabilityResponse(BaseModel):
    support_status: str = Field(
        description="Current support posture for the Advise copilot API surface.",
        examples=["ADVISE_COPILOT_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"],
        min_length=1,
        max_length=COPILOT_SUPPORTABILITY_STATUS_MAX_LENGTH,
    )
    client_ready_publication: str = Field(
        description="Client-ready publication posture for supported copilot output.",
        examples=["BLOCKED"],
        min_length=1,
        max_length=COPILOT_SUPPORTABILITY_STATUS_MAX_LENGTH,
    )
    supported_action_families: tuple[CopilotActionFamily, ...] = Field(
        description="Action families exposed by the Advise copilot API.",
        max_length=COPILOT_REQUESTED_INTENT_LIMIT,
    )
    boundaries: tuple[str, ...] = Field(
        description="Unsupported claims and system-of-record boundaries.",
        max_length=COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT,
    )

    @field_validator("boundaries", mode="before")
    @classmethod
    def _normalize_boundaries(cls, value: Any) -> tuple[str, ...]:
        return normalize_bounded_copilot_string_tuple(
            value,
            error_code="COPILOT_SUPPORTABILITY_BOUNDARY_INVALID",
            max_items=COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT,
            max_item_length=COPILOT_SUPPORTABILITY_BOUNDARY_MAX_LENGTH,
            allow_empty=True,
        )


class AdvisoryCopilotRunPage(BaseModel):
    items: tuple[AdvisoryCopilotRunRecord, ...] = Field(
        description=(
            "Newest-first copilot runs for the requested proposal version scope, bounded by "
            "the requested page size."
        ),
        max_length=COPILOT_RUN_MAX_PAGE_SIZE,
    )
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor to request the next page, or null when the page is complete.",
        max_length=COPILOT_CURSOR_MAX_LENGTH,
    )


__all__ = [
    "AdvisoryCopilotEvidencePacketResponse",
    "AdvisoryCopilotReviewResponse",
    "AdvisoryCopilotRunPage",
    "AdvisoryCopilotRunResponse",
    "AdvisoryCopilotSupportabilityResponse",
]
