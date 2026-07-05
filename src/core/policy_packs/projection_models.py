from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationRecord,
)


class PolicyEvaluationLineageResponse(BaseModel):
    evaluation_id: str = Field(
        description="Policy evaluation record identifier.",
        examples=["pev_123abc"],
    )
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.",
        examples=["ppv_001"],
    )
    policy_pack_id: str = Field(
        description="Policy pack identifier.",
        examples=["SG_PRIVATE_BANKING_REFERENCE"],
    )
    policy_version: str = Field(description="Pinned policy-pack version.", examples=["2026.05"])
    policy_content_hash: str = Field(
        description="Pinned policy-pack content hash.",
        examples=["sha256:policy-pack-content"],
    )
    source_evidence_hash: str = Field(
        description="Source evidence hash evaluated.",
        examples=["sha256:source-evidence"],
    )
    evaluation_hash: str = Field(
        description="Immutable policy evaluation hash.",
        examples=["sha256:policy-evaluation"],
    )
    rule_result_hashes: dict[str, str] = Field(
        description="Per-rule result hashes retained for material field certification.",
        examples=[{"SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW": "sha256:rule-result"}],
    )
    source_refs: list[str] = Field(
        description="Source authority and evidence refs used.",
        examples=[["lotus-core:core_product_eligibility_target_market_complexity"]],
    )
    source_gaps: list[str] = Field(
        description="Missing source evidence retained in the record.",
        examples=[["client_consent:SG_STRUCTURED_NOTE"]],
    )
    audit_events: list[PolicyEvaluationAuditEvent] = Field(
        description="Append-only finalization, review, sign-off, and report/archive events.",
        examples=[[{"event_type": "POLICY_EVALUATION_FINALIZED"}]],
    )
    lineage_posture: dict[str, Any] = Field(
        description="Support boundary and publication posture for this policy lineage.",
        examples=[{"client_ready_publication": "BLOCKED"}],
    )


class PolicyEvaluationReviewQueueResponse(BaseModel):
    items: list[PolicyEvaluationRecord] = Field(
        description=(
            "Policy evaluation records requiring advisor, compliance, or supervisory review."
        ),
        examples=[[{"evaluation_id": "pev_123abc", "evaluation_status": "PENDING_REVIEW"}]],
    )
    queue_posture: dict[str, Any] = Field(
        description="Review queue support boundary and unsupported downstream surfaces.",
        examples=[
            {
                "gateway_supported": True,
                "gateway_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF",
                "workbench_supported": True,
                "workbench_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI",
                "client_ready_publication": "BLOCKED",
            }
        ],
    )


class PolicyEvaluationSignOffPackageResponse(BaseModel):
    evaluation: PolicyEvaluationRecord = Field(
        description="Finalized policy evaluation record used as the sign-off source.",
        examples=[{"evaluation_id": "pev_123abc"}],
    )
    lineage: PolicyEvaluationLineageResponse = Field(
        description="Hash-backed lineage and append-only event trail for sign-off review.",
        examples=[{"evaluation_id": "pev_123abc"}],
    )
    package_posture: dict[str, Any] = Field(
        description=(
            "Current sign-off package realization boundary. Advise exposes the certified source "
            "package and signed-off report-package handoff, but client-ready publication remains "
            "blocked."
        ),
        examples=[
            {
                "report_render_archive_realization": (
                    "SUPPORTED_BY_RFC0025_SLICE10_SIGNED_OFF_PACKAGE_HANDOFF"
                ),
                "client_ready_publication": "BLOCKED",
            }
        ],
    )


class PolicyEvaluationDiagnosticsResponse(BaseModel):
    evaluation_id: str = Field(description="Policy evaluation record identifier.")
    proposal_id: str = Field(description="Proposal identifier.")
    evaluation_status: str = Field(description="Current aggregate policy evaluation status.")
    sign_off_status: str = Field(description="Current sign-off workflow posture.")
    latest_events: dict[str, Any] = Field(
        default_factory=dict,
        description="Safe latest review, sign-off, report, and AI event summaries.",
    )
    report_package_posture: dict[str, Any] = Field(
        default_factory=dict,
        description="Safe report-package handoff posture and replay guidance.",
    )
    ai_evidence_posture: dict[str, Any] = Field(
        default_factory=dict,
        description="Safe AI evidence posture, fallback reason, and review guidance.",
    )
    replay_posture: dict[str, Any] = Field(
        default_factory=dict,
        description="Hash and idempotency replay posture for support operators.",
    )
    safe_next_action: str = Field(
        description="Bounded operator next action derived from current posture."
    )
    runbook_ref: str = Field(description="Repository-authored runbook reference.")
    diagnostics_contract_version: str = Field(
        description="Diagnostics projection contract version."
    )
