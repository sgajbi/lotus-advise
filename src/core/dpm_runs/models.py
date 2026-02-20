from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.core.models import RebalanceResult


class DpmRunRecord(BaseModel):
    rebalance_run_id: str = Field(
        description="Internal DPM run identifier.", examples=["rr_abc12345"]
    )
    correlation_id: str = Field(
        description="Internal correlation identifier.", examples=["corr-1234-abcd"]
    )
    request_hash: str = Field(
        description="Canonical request hash associated with the run.",
        examples=["sha256:abc123"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with run when available.",
        examples=["demo-idem-001"],
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    created_at: datetime = Field(
        description="Run creation timestamp (UTC).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    result_json: Dict[str, Any] = Field(
        description="Serialized DPM simulation result payload.",
        examples=[{"rebalance_run_id": "rr_abc12345", "status": "READY"}],
    )


class DpmRunIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key supplied to simulate endpoint.",
        examples=["demo-idem-001"],
    )
    request_hash: str = Field(
        description="Canonical request hash associated with idempotency key.",
        examples=["sha256:abc123"],
    )
    rebalance_run_id: str = Field(
        description="Run identifier mapped by idempotency key.",
        examples=["rr_abc12345"],
    )
    created_at: datetime = Field(
        description="Timestamp when idempotency mapping was stored.",
        examples=["2026-02-20T12:00:00+00:00"],
    )


class DpmRunLookupResponse(BaseModel):
    rebalance_run_id: str = Field(description="DPM run identifier.", examples=["rr_abc12345"])
    correlation_id: str = Field(
        description="Correlation identifier for the run.", examples=["corr-1234-abcd"]
    )
    request_hash: str = Field(
        description="Canonical request hash associated with this run.",
        examples=["sha256:abc123"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with this run when available.",
        examples=["demo-idem-001"],
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    created_at: str = Field(
        description="Run creation timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    result: RebalanceResult = Field(
        description="Full DPM simulation result payload for investigation and audit."
    )


class DpmRunIdempotencyLookupResponse(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key supplied on simulation request.",
        examples=["demo-idem-001"],
    )
    request_hash: str = Field(
        description="Canonical request hash mapped to idempotency key.",
        examples=["sha256:abc123"],
    )
    rebalance_run_id: str = Field(
        description="Run identifier mapped to idempotency key.",
        examples=["rr_abc12345"],
    )
    created_at: str = Field(
        description="Idempotency mapping timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
