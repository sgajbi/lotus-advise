from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SourceFreshnessStatus = Literal["CURRENT", "STALE", "PARTIAL", "UNKNOWN"]


class SourceProvenanceRecord(BaseModel):
    source_system: str = Field(description="Authoritative upstream source system.")
    source_kind: Literal["PORTFOLIO", "MARKET_DATA"] = Field(
        description="Business source family represented by this provenance record."
    )
    source_id: str = Field(description="Stable upstream snapshot, event, batch, or revision id.")
    as_of: str = Field(description="Business as-of date or timestamp for the source record.")
    contract_version: str = Field(description="Consumer contract version used to read the source.")
    source_version: str | None = Field(
        default=None,
        description="Upstream version or revision identifier when provided.",
    )
    source_event_id: str | None = Field(
        default=None,
        description="Upstream source-event identifier when provided.",
    )
    source_batch_id: str | None = Field(
        default=None,
        description="Upstream ingestion or publication batch identifier when provided.",
    )
    source_hash: str | None = Field(
        default=None,
        description="Upstream content hash when provided; raw source payloads are not stored.",
    )
    valuation_timestamp: str | None = Field(
        default=None,
        description="Valuation or generation timestamp for the source record when provided.",
    )
    freshness_status: SourceFreshnessStatus = Field(
        default="UNKNOWN",
        description="Source freshness posture reported or inferred for the source record.",
    )


class SourceProvenanceEnvelope(BaseModel):
    schema_version: Literal["lotus.source-provenance.v1"] = Field(
        default="lotus.source-provenance.v1",
        description="Versioned Advise source-provenance envelope schema.",
    )
    source_system: str = Field(description="Primary upstream source system.")
    portfolio: SourceProvenanceRecord = Field(
        description="Portfolio snapshot provenance used by the advisory result."
    )
    market_data: SourceProvenanceRecord = Field(
        description="Market-data snapshot provenance used by the advisory result."
    )
    raw_payload_stored: Literal[False] = Field(
        default=False,
        description="Always false; raw upstream payloads are not stored in provenance.",
    )


__all__ = [
    "SourceFreshnessStatus",
    "SourceProvenanceEnvelope",
    "SourceProvenanceRecord",
]
