from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PolicyPackActivationState = Literal["DRAFT", "ACTIVE", "SUPERSEDED", "DISABLED"]
PolicyPackValidationStatus = Literal["READY", "BLOCKED"]
PolicyPackEventType = Literal["POLICY_PACK_VALIDATED", "POLICY_PACK_ACTIVATED"]
PolicyEvaluationStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED", "NOT_APPLICABLE"]
PolicyApplicabilityStatus = Literal["APPLICABLE", "NOT_APPLICABLE", "BLOCKED"]
PolicyEvaluationEventType = Literal[
    "POLICY_EVALUATION_FINALIZED",
    "POLICY_EVALUATION_REVIEW_RECORDED",
    "POLICY_EVALUATION_SIGN_OFF_RECORDED",
    "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED",
]


class PolicyPackAuditEvent(BaseModel):
    event_id: str = Field(
        description="Deterministic audit event identifier for policy-pack catalog activity.",
        examples=["ppev_001"],
    )
    event_type: PolicyPackEventType = Field(
        description="Policy-pack catalog event type.",
        examples=["POLICY_PACK_VALIDATED"],
    )
    policy_pack_id: str = Field(
        description="Policy pack identifier.",
        examples=["SG_PRIVATE_BANKING_REFERENCE"],
    )
    policy_version: str = Field(
        description="Policy pack version.",
        examples=["2026.05"],
    )
    actor_id: str = Field(
        description="Actor that requested the validation or activation event.",
        examples=["policy_steward_1"],
    )
    occurred_at: str = Field(
        description="UTC ISO8601 timestamp for the event.",
        examples=["2026-05-26T01:00:00+00:00"],
    )
    content_hash: str = Field(
        description="Canonical hash of the source policy-pack definition at event time.",
        examples=["sha256:policy-pack-content"],
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Idempotency key supplied for replay-safe command handling.",
        examples=["activate-sg-reference-001"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured reason, diagnostics, and maker-checker posture for the event.",
        examples=[{"validation_status": "READY"}],
    )


class PolicyPackSummary(BaseModel):
    policy_pack_id: str = Field(
        description="Stable policy pack identifier.",
        examples=["GLOBAL_PRIVATE_BANKING_BASELINE"],
    )
    policy_version: str = Field(description="Policy pack version.", examples=["2026.05"])
    policy_family: str = Field(
        description="Policy family represented by this pack.",
        examples=["GLOBAL_PRIVATE_BANKING"],
    )
    display_name: str = Field(
        description="Advisor and operator friendly policy-pack name.",
        examples=["Global Private Banking Baseline"],
    )
    activation_state: PolicyPackActivationState = Field(
        description="Current activation posture of this immutable policy-pack version.",
        examples=["ACTIVE"],
    )
    reference_posture: str = Field(
        description="Reference-pack posture and legal-advice boundary.",
        examples=["REFERENCE_EXAMPLE_NOT_LEGAL_ADVICE"],
    )
    maker_checker_required: bool = Field(
        description="Whether activation requires a checker different from the validator.",
        examples=[True],
    )
    content_hash: str = Field(
        description="Canonical hash of the source policy-pack definition.",
        examples=["sha256:policy-pack-content"],
    )


class PolicyPackDetailResponse(BaseModel):
    policy_pack: PolicyPackSummary = Field(description="Policy pack metadata.")
    applicability: dict[str, Any] = Field(
        description=(
            "Applicability selectors for jurisdiction, booking, legal entity, client segment, "
            "and product scope."
        ),
        examples=[{"jurisdiction_scope": ["SG"]}],
    )
    source_requirements: list[str] = Field(
        description=(
            "Source-owned evidence required before later policy evaluation may claim outcomes."
        ),
        examples=[["client_classification", "risk_policy_metrics"]],
    )
    rules: list[dict[str, Any]] = Field(
        description="Rule summaries and required evidence. These are not legal advice.",
        examples=[[{"rule_id": "SG_AI_COMPLEX_PRODUCT_REVIEW"}]],
    )
    disclosure_templates: list[dict[str, Any]] = Field(
        description="Versioned disclosure template summaries for later review/sign-off flows.",
        examples=[[{"template_id": "SG_COMPLEX_PRODUCT_DISCLOSURE"}]],
    )
    consent_templates: list[dict[str, Any]] = Field(
        description="Versioned consent template summaries for later review/sign-off flows.",
        examples=[[{"template_id": "SG_COMPLEX_PRODUCT_CONSENT"}]],
    )
    approval_routes: list[dict[str, Any]] = Field(
        description="Configured approval route summaries for later policy result mapping.",
        examples=[[{"route_id": "INVESTMENT_COUNSELLOR_REVIEW"}]],
    )
    sample_fixture_refs: list[str] = Field(
        description="Synthetic sample fixtures used for dry-run validation.",
        examples=[["fixtures/policy-packs/sg-private-banking-reference.json"]],
    )
    supportability: dict[str, Any] = Field(
        description="Current RFC-0025 support boundary for this policy pack.",
        examples=[{"policy_evaluation": "NOT_IMPLEMENTED"}],
    )
    audit_events: list[PolicyPackAuditEvent] = Field(
        default_factory=list,
        description="Append-only validation and activation audit events for this pack version.",
    )


class PolicyPackListResponse(BaseModel):
    items: list[PolicyPackSummary] = Field(
        description="Policy pack versions visible to the caller.",
        examples=[[{"policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE"}]],
    )
    catalog_posture: dict[str, Any] = Field(
        description="Catalog support posture and RFC-0025 boundary.",
        examples=[{"policy_evaluation": "NOT_IMPLEMENTED"}],
    )


class PolicyPackValidationRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting policy-pack validation.",
        examples=["policy_steward_1"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured validation reason retained in audit evidence.",
        examples=[{"purpose": "pre-activation validation"}],
    )


class PolicyPackValidationResponse(BaseModel):
    policy_pack: PolicyPackSummary = Field(description="Validated policy pack metadata.")
    validation_status: PolicyPackValidationStatus = Field(
        description="Validation result for this policy-pack version.",
        examples=["READY"],
    )
    diagnostics: list[str] = Field(
        description="Validation diagnostics. Empty when validation is ready.",
        examples=[["RULE_ID_NOT_UPPER_SNAKE_CASE"]],
    )
    validation_event: PolicyPackAuditEvent = Field(
        description="Append-only validation audit event."
    )
    replayed: bool = Field(
        description="Whether this response replayed a prior idempotent validation event.",
        examples=[False],
    )


class PolicyPackActivationRequest(BaseModel):
    activated_by: str = Field(
        description="Actor requesting activation.",
        examples=["policy_checker_1"],
    )
    source_content_hash: str = Field(
        description="Expected canonical content hash from the validated policy pack.",
        examples=["sha256:policy-pack-content"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured activation reason retained in audit evidence.",
        examples=[{"purpose": "activate SG private banking reference pack"}],
    )


class PolicyPackActivationResponse(BaseModel):
    policy_pack: PolicyPackSummary = Field(description="Policy pack metadata after activation.")
    activation_event: PolicyPackAuditEvent = Field(
        description="Append-only activation audit event."
    )
    replayed: bool = Field(
        description="Whether this response replayed a prior idempotent activation event.",
        examples=[False],
    )


class PolicyPackApplicabilityResult(BaseModel):
    status: PolicyApplicabilityStatus = Field(
        description="Whether this policy pack applies to the proposal evidence.",
        examples=["APPLICABLE"],
    )
    matched_selectors: dict[str, str] = Field(
        default_factory=dict,
        description="Applicability selectors matched from source-owned proposal evidence.",
        examples=[{"jurisdiction": "SG", "client_segment": "ACCREDITED_INVESTOR"}],
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Source-owned selector evidence missing before applicability can be decided.",
        examples=[["jurisdiction"]],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Domain reason codes explaining applicability posture.",
        examples=[["POLICY_PACK_APPLIES_TO_PROPOSAL_CONTEXT"]],
    )


class PolicyRuleEvaluationResult(BaseModel):
    rule_id: str = Field(description="Policy-pack rule identifier.")
    status: PolicyEvaluationStatus = Field(
        description="Rule evaluation posture for this proposal evidence.",
        examples=["PENDING_REVIEW"],
    )
    severity: str = Field(description="Policy-pack rule severity.", examples=["BLOCKING"])
    outcome: str = Field(
        description="Domain outcome for the evaluated rule; never a generic pass/fail claim.",
        examples=["DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED"],
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Concrete proposal evidence references used by this result.",
    )
    source_authority_refs: list[str] = Field(
        default_factory=list,
        description="Source-owner references backing the rule result.",
        examples=[["lotus-core:core_product_eligibility_target_market_complexity"]],
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Missing evidence that prevents a positive policy outcome.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining rule status.",
    )
    required_actions: list[str] = Field(
        default_factory=list,
        description="Advisor, policy, compliance, or supervisory actions required by the rule.",
    )


class PolicyPackEvaluationResponse(BaseModel):
    contract_version: str = Field(
        description="Internal RFC-0025 policy evaluation engine contract version.",
        examples=["rfc0025.policy-evaluation-engine.v1"],
    )
    policy_pack: PolicyPackSummary = Field(description="Evaluated active policy pack.")
    evaluation_status: PolicyEvaluationStatus = Field(
        description="Aggregate evaluation posture across applicable rules.",
        examples=["PENDING_REVIEW"],
    )
    applicability: PolicyPackApplicabilityResult = Field(
        description="Source-backed applicability result for the policy pack."
    )
    source_posture: dict[str, Any] = Field(
        description="Policy source-readiness posture consumed by the evaluator.",
        examples=[{"contract_version": "rfc0025.policy-source-readiness.v1"}],
    )
    rule_results: list[PolicyRuleEvaluationResult] = Field(
        description="Material rule results with source refs, gaps, reasons, and required actions."
    )
    supportability: dict[str, Any] = Field(
        description="Current support boundary for the internal policy evaluation engine.",
        examples=[{"policy_evaluation_api": "NOT_IMPLEMENTED"}],
    )


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
        description="Stored versus replayed hash comparison for policy, source, and result truth.",
    )
    replay_metadata: dict[str, Any] = Field(description="Persisted replay metadata.")
