from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from src.core.models import RebalanceResult

DpmAsyncOperationType = Literal["ANALYZE_SCENARIOS"]
DpmAsyncOperationStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]


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


class DpmAsyncAcceptedResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["dop_001"],
    )
    operation_type: DpmAsyncOperationType = Field(
        description="Operation type accepted for asynchronous execution.",
        examples=["ANALYZE_SCENARIOS"],
    )
    status: DpmAsyncOperationStatus = Field(
        description="Initial operation status.",
        examples=["PENDING"],
    )
    correlation_id: str = Field(
        description="Correlation id assigned to asynchronous operation.",
        examples=["corr-dpm-async-001"],
    )
    created_at: str = Field(
        description="Operation acceptance timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    status_url: str = Field(
        description="Relative API path for operation status retrieval.",
        examples=["/rebalance/operations/dop_001"],
    )


class DpmAsyncError(BaseModel):
    code: str = Field(
        description="Stable operation error code.",
        examples=["SCENARIO_EXECUTION_ERROR"],
    )
    message: str = Field(
        description="Human-readable operation error message.",
        examples=["SCENARIO_EXECUTION_ERROR: RuntimeError"],
    )


class DpmAsyncOperationStatusResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["dop_001"],
    )
    operation_type: DpmAsyncOperationType = Field(
        description="Operation type.",
        examples=["ANALYZE_SCENARIOS"],
    )
    status: DpmAsyncOperationStatus = Field(
        description="Current operation status.",
        examples=["SUCCEEDED"],
    )
    correlation_id: str = Field(
        description="Correlation id associated with this operation.",
        examples=["corr-dpm-async-001"],
    )
    created_at: str = Field(
        description="Operation acceptance timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    started_at: Optional[str] = Field(
        default=None,
        description="Operation start timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:01+00:00"],
    )
    finished_at: Optional[str] = Field(
        default=None,
        description="Operation completion timestamp (UTC ISO8601).",
        examples=["2026-02-20T12:00:02+00:00"],
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Successful operation result payload when status is SUCCEEDED.",
        examples=[{"batch_run_id": "batch_abc12345", "results": {}}],
    )
    error: Optional[DpmAsyncError] = Field(
        default=None,
        description="Failure details when status is FAILED.",
        examples=[{"code": "RuntimeError", "message": "boom"}],
    )


class DpmAsyncOperationRecord(BaseModel):
    operation_id: str = Field(
        description="Internal async operation identifier.",
        examples=["dop_001"],
    )
    operation_type: DpmAsyncOperationType = Field(
        description="Internal async operation type.",
        examples=["ANALYZE_SCENARIOS"],
    )
    status: DpmAsyncOperationStatus = Field(
        description="Internal async operation status.",
        examples=["PENDING"],
    )
    correlation_id: str = Field(
        description="Internal operation correlation id.",
        examples=["corr-dpm-async-001"],
    )
    created_at: datetime = Field(
        description="Internal operation creation timestamp.",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="Internal operation start timestamp.",
        examples=["2026-02-20T12:00:01+00:00"],
    )
    finished_at: Optional[datetime] = Field(
        default=None,
        description="Internal operation completion timestamp.",
        examples=["2026-02-20T12:00:02+00:00"],
    )
    result_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Internal serialized success payload.",
        examples=[{"batch_run_id": "batch_abc12345"}],
    )
    error_json: Optional[Dict[str, str]] = Field(
        default=None,
        description="Internal serialized failure payload.",
        examples=[{"code": "RuntimeError", "message": "boom"}],
    )


class DpmRunArtifactHashes(BaseModel):
    request_hash: str = Field(
        description="Canonical request hash associated with this run artifact.",
        examples=["sha256:abc123"],
    )
    artifact_hash: str = Field(
        description="Canonical deterministic artifact hash.",
        examples=["sha256:def456"],
    )


class DpmRunArtifactEvidence(BaseModel):
    engine_version: str = Field(
        description="Engine version associated with the persisted run output.",
        examples=["0.1.0"],
    )
    run_created_at: str = Field(
        description="Run creation timestamp used as deterministic artifact creation time.",
        examples=["2026-02-20T12:00:00+00:00"],
    )
    hashes: DpmRunArtifactHashes = Field(
        description="Canonical hashes associated with this artifact."
    )


class DpmRunArtifactResponse(BaseModel):
    artifact_id: str = Field(
        description="Deterministic artifact identifier derived from run id.",
        examples=["dra_abc12345"],
    )
    artifact_version: str = Field(
        description="Artifact schema version for compatibility evolution.",
        examples=["1.0"],
    )
    rebalance_run_id: str = Field(description="DPM run identifier.", examples=["rr_abc12345"])
    correlation_id: str = Field(
        description="Correlation identifier associated with this run.",
        examples=["corr-1234-abcd"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with this run when available.",
        examples=["demo-idem-001"],
    )
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_123"])
    status: str = Field(
        description="Run business status represented by the persisted output.",
        examples=["READY"],
    )
    request_snapshot: Dict[str, Any] = Field(
        description="Deterministic request snapshot metadata captured for replayability.",
        examples=[{"portfolio_id": "pf_123", "request_hash": "sha256:abc123"}],
    )
    before_summary: Dict[str, Any] = Field(
        description="Before-state holdings and valuation summary from run output.",
        examples=[{"total_value_base": {"amount": "10000", "currency": "USD"}}],
    )
    after_summary: Dict[str, Any] = Field(
        description="After-state holdings and valuation summary from run output.",
        examples=[{"total_value_base": {"amount": "10000", "currency": "USD"}}],
    )
    order_intents: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="Order intent list captured in run output.",
        examples=[[{"intent_type": "SECURITY_TRADE", "side": "BUY", "instrument_id": "EQ_1"}]],
    )
    rule_outcomes: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rule outcomes captured in run output.",
        examples=[[{"rule_id": "NO_SHORTING", "severity": "HARD", "status": "PASS"}]],
    )
    diagnostics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostics payload captured in run output.",
        examples=[{"warnings": [], "data_quality": {"price_missing": [], "fx_missing": []}}],
    )
    result: RebalanceResult = Field(
        description="Full persisted DPM run output used as artifact source of truth.",
        examples=[{"rebalance_run_id": "rr_abc12345", "status": "READY"}],
    )
    evidence: DpmRunArtifactEvidence = Field(
        description="Evidence metadata and canonical hash information for the artifact.",
        examples=[
            {
                "engine_version": "0.1.0",
                "run_created_at": "2026-02-20T12:00:00+00:00",
                "hashes": {
                    "request_hash": "sha256:abc123",
                    "artifact_hash": "sha256:def456",
                },
            }
        ],
    )
