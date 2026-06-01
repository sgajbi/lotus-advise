from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationRecord,
)


class PolicyEvaluationAiEvidenceRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting bounded AI policy-evidence commentary.",
        examples=["policy_checker_1"],
    )
    source_evaluation_hash: str = Field(
        description="Immutable policy evaluation hash inspected by the requester.",
        examples=["sha256:policy-evaluation"],
    )
    requested_actions: list[str] = Field(
        default_factory=lambda: ["SUMMARIZE_POLICY_POSTURE"],
        min_length=1,
        description=(
            "Bounded AI evidence actions requested from lotus-ai. Mutation, approval, waiver, "
            "client-ready, and unsupported regulatory-claim actions are rejected."
        ),
        examples=[["SUMMARIZE_POLICY_POSTURE", "EXPLAIN_OPEN_REQUIREMENTS"]],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured AI evidence request reason retained in policy lineage.",
        examples=[{"purpose": "policy evidence explanation"}],
    )


class PolicyEvaluationAiEvidenceResponse(BaseModel):
    evaluation: PolicyEvaluationRecord = Field(
        description="Policy evaluation record after AI evidence lineage recording."
    )
    ai_event: PolicyEvaluationAuditEvent = Field(
        description="Created or replayed policy AI evidence event."
    )
    policy_evidence: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Bounded AI policy-evidence payload or deterministic unavailable posture. This "
            "payload is non-authoritative and cannot change policy status, rule results, "
            "approvals, waivers, disclosures, or consent posture."
        ),
    )
    replayed: bool = Field(
        description="Whether this request replayed an existing idempotent AI evidence event.",
        examples=[False],
    )
