from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field

SourceCompletenessStatus = Literal["COMPLETE", "DEGRADED", "INCOMPLETE"]


class SourceCollectionCompleteness(BaseModel):
    source_collection: str = Field(
        description="Upstream source collection represented by this completeness summary."
    )
    required: bool = Field(
        description="Whether rejected rows in this collection block stateful context resolution."
    )
    received_count: int = Field(
        ge=0,
        description="Number of upstream rows or expected source references considered.",
    )
    accepted_count: int = Field(
        ge=0,
        description="Number of rows accepted for advisory normalization or optional enrichment.",
    )
    rejected_count: int = Field(
        ge=0,
        description="Number of rows rejected from advisory normalization.",
    )
    duplicate_count: int = Field(
        default=0,
        ge=0,
        description="Number of duplicate source references detected during normalization.",
    )
    rejection_reasons: Dict[str, int] = Field(
        default_factory=dict,
        description="Bounded reason-code counts for rejected rows.",
    )
    affected_refs: List[str] = Field(
        default_factory=list,
        description="Bounded non-sensitive row references for operator reconciliation.",
    )
    status: SourceCompletenessStatus = Field(
        description="Collection-level source completeness posture."
    )


class SourceCompletenessReport(BaseModel):
    schema_version: Literal["lotus.source-completeness.v1"] = Field(
        default="lotus.source-completeness.v1",
        description="Versioned Advise source-completeness envelope schema.",
    )
    source_system: str = Field(description="Authoritative upstream source system.")
    portfolio_id: str = Field(description="Portfolio identifier resolved from the source context.")
    as_of: str = Field(description="Business as-of date or timestamp for the source context.")
    status: SourceCompletenessStatus = Field(
        description="Overall source completeness posture across required and optional collections."
    )
    collections: List[SourceCollectionCompleteness] = Field(
        description="Per-source collection completeness summaries."
    )
    raw_payload_stored: Literal[False] = Field(
        default=False,
        description="Always false; raw upstream payloads are not stored in completeness reports.",
    )

    def has_required_rejections(self) -> bool:
        return any(
            collection.required and collection.rejected_count > 0 for collection in self.collections
        )


__all__ = [
    "SourceCollectionCompleteness",
    "SourceCompletenessReport",
    "SourceCompletenessStatus",
]
