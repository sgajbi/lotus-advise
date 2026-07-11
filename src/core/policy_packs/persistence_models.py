from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.policy_packs.evaluation_models import PolicyEvaluationStatus

PolicyEvaluationEventType = Literal[
    "POLICY_EVALUATION_FINALIZED",
    "POLICY_EVALUATION_REVIEW_RECORDED",
    "POLICY_EVALUATION_SIGN_OFF_RECORDED",
    "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED",
    "POLICY_EVALUATION_AI_EVIDENCE_RECORDED",
]

PolicyEvaluationReviewEventType = Literal["POLICY_EVALUATION_REVIEW_RECORDED"]


class PolicyEvaluationAuditEvent(BaseModel):
    event_id: str = Field(
        description="Append-only policy evaluation event identifier.",
        examples=["peev_000001"],
    )
    evaluation_id: str = Field(
        description="Policy evaluation record identifier.",
        examples=["pev_123abc"],
    )
    proposal_id: str = Field(
        description="Proposal identifier evaluated by the policy record.",
        examples=["pp_001"],
    )
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier evaluated by the policy record.",
        examples=["ppv_001"],
    )
    event_type: PolicyEvaluationEventType = Field(
        description="Policy evaluation event type.",
        examples=["POLICY_EVALUATION_FINALIZED"],
    )
    actor_id: str = Field(
        description="Actor that created the event.",
        examples=["advisor_1"],
    )
    occurred_at: str = Field(
        description="UTC ISO8601 timestamp for the event.",
        examples=["2026-05-26T01:00:00+00:00"],
    )
    content_hash: str = Field(
        description="Canonical hash of the immutable finalized policy evaluation record.",
        examples=["sha256:policy-evaluation-record"],
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Idempotency key supplied for replay-safe event handling.",
        examples=["policy-evaluation-finalize-001"],
    )
    reason_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured policy event reason, source refs, and downstream refs.",
    )


class PolicyEvaluationRecord(BaseModel):
    evaluation_id: str = Field(
        description="Deterministic policy evaluation record identifier.",
        examples=["pev_123abc"],
    )
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.",
        examples=["ppv_001"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier from the evaluated source evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    policy_pack_id: str = Field(
        description="Policy pack identifier used for the evaluation.",
        examples=["SG_PRIVATE_BANKING_REFERENCE"],
    )
    policy_version: str = Field(
        description="Policy pack version used for the evaluation.",
        examples=["2026.05"],
    )
    generated_at: str = Field(
        description="UTC ISO8601 timestamp when the evaluation record was finalized.",
        examples=["2026-05-26T01:00:00+00:00"],
    )
    created_by: str = Field(
        description="Actor that finalized the policy evaluation record.",
        examples=["advisor_1"],
    )
    evaluation_status: PolicyEvaluationStatus = Field(
        description="Aggregate evaluation posture persisted for replay and audit.",
        examples=["PENDING_REVIEW"],
    )
    policy_content_hash: str = Field(
        description="Canonical content hash of the policy-pack version at evaluation time.",
        examples=["sha256:policy-pack-content"],
    )
    source_evidence_hash: str = Field(
        description="Canonical hash of the source evidence evaluated by the policy pack.",
        examples=["sha256:source-evidence"],
    )
    evaluation_hash: str = Field(
        description="Canonical hash of immutable policy evaluation truth.",
        examples=["sha256:policy-evaluation"],
    )
    rule_result_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Canonical hash of each persisted rule result by rule identifier.",
    )
    evaluation_json: dict[str, Any] = Field(
        description="Persisted `PolicyPackEvaluationResponse` JSON.",
    )
    source_refs: list[str] = Field(
        default_factory=list,
        description="Source authority and evidence references used by the evaluation.",
    )
    source_gaps: list[str] = Field(
        default_factory=list,
        description="Missing source evidence retained in the finalized record.",
    )
    approval_dependencies: list[str] = Field(
        default_factory=list,
        description="Policy-driven approval or review actions required by the evaluation.",
    )
    disclosure_requirements: list[str] = Field(
        default_factory=list,
        description="Disclosure requirements identified by policy evaluation.",
    )
    consent_requirements: list[str] = Field(
        default_factory=list,
        description="Client consent requirements identified by policy evaluation.",
    )
    review_events_json: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only review events attached to this evaluation.",
    )
    sign_off_events_json: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only sign-off events attached to this evaluation.",
    )
    report_archive_refs_json: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only report, render, and archive refs attached to this evaluation.",
    )
    replay_metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Replay metadata proving policy version, hashes, and source refs.",
    )


class PolicyEvaluationPersistenceResult(BaseModel):
    record: PolicyEvaluationRecord = Field(description="Persisted policy evaluation record.")
    created: bool = Field(description="Whether this call created the finalized record.")
    replayed: bool = Field(
        description="Whether this call replayed a prior idempotent finalize request."
    )
    audit_event: PolicyEvaluationAuditEvent | None = Field(
        default=None,
        description="Audit event created or replayed for this persistence command.",
    )


class PolicyEvaluationReplayResponse(BaseModel):
    evaluation_id: str = Field(description="Policy evaluation record identifier.")
    replay_contract_version: str = Field(
        description="Internal replay contract version.",
        examples=["rfc0025.policy-evaluation-persistence.v1"],
    )
    policy_pack_id: str = Field(description="Policy pack identifier.")
    policy_version: str = Field(description="Policy version pinned by the record.")
    source_refs: list[str] = Field(description="Persisted source refs used for replay proof.")
    source_gaps: list[str] = Field(description="Persisted source gaps used for replay proof.")
    hash_comparison: dict[str, Any] = Field(
        description=(
            "Stored versus replayed hash comparison for policy, source, and result truth, "
            "including policy lifecycle state and replay reason code. Historical replay pins the "
            "stored policy version and never substitutes the current active version."
        ),
    )
    replay_metadata: dict[str, Any] = Field(description="Persisted replay metadata.")


class PolicyEvaluationCreateRequest(BaseModel):
    policy_pack_id: str = Field(
        description="Policy pack identifier to evaluate against the supplied proposal evidence.",
        examples=["GLOBAL_PRIVATE_BANKING_BASELINE"],
    )
    policy_version: str = Field(
        description="Immutable policy-pack version to evaluate.",
        examples=["2026.05"],
    )
    created_by: str = Field(
        description=(
            "Compatibility actor echo for finalization. The route authorizes and records the "
            "trusted advisor principal from policy-control headers and rejects a mismatch."
        ),
        examples=["advisor_1"],
    )
    evidence_bundle: dict[str, Any] = Field(
        description=(
            "Source-backed proposal evidence bundle containing advisory context, proposed trades, "
            "source-readiness posture, risk evidence, disclosures, and conflict evidence."
        ),
        examples=[
            {
                "context_resolution": {
                    "advisory_policy_context": {
                        "jurisdiction": "SG",
                        "client_classification": "ACCREDITED_INVESTOR",
                        "booking_center_code": "SG",
                        "legal_entity_code": "REFERENCE",
                    }
                },
                "inputs": {"proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}]},
            }
        ],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured business reason retained in the finalized audit event.",
        examples=[{"purpose": "advisor suitability review"}],
    )


class PolicyEvaluationEventRequest(BaseModel):
    event_type: PolicyEvaluationReviewEventType = Field(
        description=(
            "Append-only non-privileged policy review event type. Sign-off, report/archive, "
            "AI-evidence, and finalized events are created only by their specialized commands."
        ),
        examples=["POLICY_EVALUATION_REVIEW_RECORDED"],
    )
    actor_id: str = Field(
        description=(
            "Compatibility actor echo for the non-privileged policy review event. The route "
            "authorizes and records the trusted compliance or policy-steward principal from "
            "policy-control headers and rejects a mismatch."
        ),
        examples=["compliance_1"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured event reason, decision posture, and downstream reference details.",
        examples=[{"review_action": "REQUEST_MORE_EVIDENCE"}],
    )


class PolicyEvaluationReplayRequest(BaseModel):
    evidence_bundle: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional current evidence bundle for hash comparison against the finalized record. "
            "Omit to compare only pinned policy-version and stored source/evaluation hashes."
        ),
        examples=[{"inputs": {"proposed_trades": [{"instrument_id": "US_EQ_ETF"}]}}],
    )
