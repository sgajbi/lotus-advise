from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.core.proposals.contract_types import (
    ProposalAsyncOperationStatus,
    ProposalAsyncOperationType,
)
from src.core.proposals.lifecycle_response_models import ProposalCreateResponse


class ProposalIdempotencyLookupResponse(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key supplied on create request.",
        examples=["proposal-create-idem-001"],
    )
    request_hash: str = Field(
        description="Canonical request hash mapped to the idempotency key.",
        examples=["sha256:abc123"],
    )
    proposal_id: str = Field(
        description="Proposal identifier mapped by idempotency key.",
        examples=["pp_001"],
    )
    proposal_version_no: int = Field(
        description="Proposal version number mapped by idempotency key.", examples=[1]
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp when idempotency mapping was persisted.",
        examples=["2026-02-19T12:00:00+00:00"],
    )


class ProposalAsyncAcceptedResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["pop_001"],
    )
    operation_type: ProposalAsyncOperationType = Field(
        description="Operation type queued for asynchronous execution.",
        examples=["CREATE_PROPOSAL"],
    )
    status: ProposalAsyncOperationStatus = Field(
        description="Initial operation status.",
        examples=["PENDING"],
    )
    correlation_id: str = Field(
        description="Correlation id used to trace asynchronous execution.",
        examples=["corr-proposal-async-001"],
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp when operation was accepted.",
        examples=["2026-02-20T10:00:00+00:00"],
    )
    attempt_count: int = Field(
        description="Number of execution attempts already recorded for this operation.",
        examples=[0],
    )
    max_attempts: int = Field(
        description="Maximum number of runtime execution attempts before terminal failure.",
        examples=[3],
    )
    status_url: str = Field(
        description="Relative API path for operation status retrieval.",
        examples=["/advisory/proposals/operations/pop_001"],
    )


class ProposalAsyncError(BaseModel):
    code: str = Field(
        description="Stable operation error code.",
        examples=["PROPOSAL_NOT_FOUND"],
    )
    message: str = Field(
        description="Human-readable operation error message.",
        examples=["PROPOSAL_NOT_FOUND"],
    )


class ProposalAsyncOperationStatusResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["pop_001"],
    )
    operation_type: ProposalAsyncOperationType = Field(
        description="Operation type.",
        examples=["CREATE_PROPOSAL_VERSION"],
    )
    status: ProposalAsyncOperationStatus = Field(
        description="Current operation status.",
        examples=["SUCCEEDED"],
    )
    correlation_id: str = Field(
        description="Correlation id associated with this operation.",
        examples=["corr-proposal-async-001"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with operation when relevant.",
        examples=["proposal-create-idem-001"],
    )
    proposal_id: Optional[str] = Field(
        default=None,
        description="Proposal identifier scope for the operation when applicable.",
        examples=["pp_001"],
    )
    created_by: str = Field(
        description="Actor id that submitted the asynchronous operation.",
        examples=["advisor_123"],
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp when operation was accepted.",
        examples=["2026-02-20T10:00:00+00:00"],
    )
    started_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when execution started.",
        examples=["2026-02-20T10:00:01+00:00"],
    )
    finished_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when execution finished.",
        examples=["2026-02-20T10:00:02+00:00"],
    )
    attempt_count: int = Field(
        description="Number of execution attempts already recorded for this operation.",
        examples=[1],
    )
    max_attempts: int = Field(
        description="Maximum number of runtime execution attempts before terminal failure.",
        examples=[3],
    )
    lease_expires_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when the current execution lease expires, when running.",
        examples=["2026-02-20T10:01:01+00:00"],
    )
    result: Optional[ProposalCreateResponse] = Field(
        default=None,
        description="Successful operation result payload when status is SUCCEEDED.",
        examples=[{"proposal": {"proposal_id": "pp_001", "current_state": "DRAFT"}}],
    )
    error: Optional[ProposalAsyncError] = Field(
        default=None,
        description="Failure details when status is FAILED.",
        examples=[{"code": "ProposalNotFoundError", "message": "PROPOSAL_NOT_FOUND"}],
    )
