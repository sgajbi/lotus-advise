from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationRecord,
)

ADAPTER_VERSION = "policy-evidence-lotus-ai-adapter.v1"
WORKFLOW_PACK_ID = "policy_evidence_summary.pack"
WORKFLOW_PACK_VERSION = "v1"
WORKFLOW_SURFACE = "policy-evidence-summary"


class LotusAIPolicyEvidenceUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class PolicyAiEvidenceDraft:
    status: str
    sections: tuple[dict[str, Any], ...]
    lineage: dict[str, Any]
    review_guidance: tuple[str, ...]


def build_policy_ai_unavailable_evidence(reason: str) -> PolicyAiEvidenceDraft:
    return PolicyAiEvidenceDraft(
        status="UNAVAILABLE",
        sections=(),
        lineage={
            "adapter_version": ADAPTER_VERSION,
            "workflow_pack_id": WORKFLOW_PACK_ID,
            "workflow_pack_version": WORKFLOW_PACK_VERSION,
            "workflow_surface": WORKFLOW_SURFACE,
            "workflow_run_id": None,
            "model_version": None,
            "fallback_reason": reason,
        },
        review_guidance=(
            "AI policy evidence is unavailable; use persisted policy evaluation and sign-off "
            "evidence only.",
            "Do not infer missing approvals, disclosures, consents, waivers, suitability, "
            "best-interest, or client-ready posture.",
        ),
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
