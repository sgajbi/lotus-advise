from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.core.bank_demo_proof.document_proof import (
    AdvisoryDocumentProofSummary,
    build_document_proof_summary,
)
from src.core.bank_demo_proof.integration_proof import (
    AdvisoryJourneyIntegrationProofSummary,
    build_journey_integration_proof_summary,
)
from src.core.bank_demo_proof.models import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    AdvisoryBankDemoProofPack,
    AdvisoryDemoScenarioContract,
    AdvisorySupportedClaimRegister,
    ArtifactPolicy,
    DemoScenarioStep,
    ProofAsset,
    SupportedClaim,
    SupportedClaimProofRequirement,
)
from src.core.common.canonical import hash_canonical_payload

RFC28_SCENARIO_CONTRACT_REF = "lotus-advise://rfc0028/scenario-contract.v1.json"
RFC28_SUPPORTED_CLAIM_REGISTER_REF = "lotus-advise://rfc0028/supported-claim-register.v1.json"
RFC28_DEFAULT_OUTPUT_REF_PREFIX = "output/rfc0028/backend-proof"

RFC28_SOURCE_PRODUCT_REFS: tuple[str, ...] = (
    "ProposalNarrativeEvidence:v1",
    "AdvisoryProposalMemoEvidencePack:v1",
    "AdvisoryPolicyEvaluationRecord:v1",
    "AdvisorCockpitOperatingSnapshot:v1",
    "AdvisoryActionItemRegister:v1",
    "AdvisoryCopilotInteractionRecord:v1",
)

RFC28_UNSUPPORTED_BOUNDARIES: tuple[str, ...] = (
    "Client-ready publication remains blocked until publication controls, supported-claim review, "
    "Gateway/Workbench proof, and document controls are implemented and validated.",
    "External client communication is not owned or approved by RFC-0028 backend proof capture.",
    "OMS order, fill, settlement, and downstream execution system-of-record status remain outside "
    "lotus-advise ownership.",
    "RFP/security pack claims are not promoted until commercial artifacts are reviewed against the "
    "supported-claim register and implementation evidence.",
)


class BackendProofCaptureMetadata(BaseModel):
    generated_at: datetime = Field(description="UTC backend proof generation timestamp.")
    repository_sha: str = Field(description="lotus-advise commit SHA used for proof generation.")
    service_version: str = Field(description="lotus-advise service version.")
    environment: str = Field(description="Runtime environment label for the proof capture.")
    correlation_id: str = Field(description="Correlation id for the proof-capture run.")
    live_suite_result_ref: str | None = Field(
        default=None,
        description="Optional local path to the source live runtime suite result.",
    )
    live_suite_bundle_ref: str | None = Field(
        default=None,
        description="Optional local path to the source live runtime suite bundle.",
    )

    @model_validator(mode="after")
    def _generated_at_must_be_timezone_aware(self) -> BackendProofCaptureMetadata:
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware UTC")
        return self


class RuntimeEndpointEvidence(BaseModel):
    endpoint: str = Field(description="Runtime endpoint that was probed.")
    http_status: int | None = Field(
        default=None,
        description="Observed HTTP status, or null when the endpoint was not probed.",
    )
    posture: Literal["READY", "DEGRADED", "UNAVAILABLE", "NOT_PROBED"] = Field(
        description="Bounded runtime posture for this endpoint."
    )
    summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized, bounded endpoint summary.",
    )


class BackendRuntimePosture(BaseModel):
    service_name: Literal["lotus-advise"] = Field(default="lotus-advise")
    base_url: str = Field(description="Runtime base URL used for endpoint probes.")
    environment: str = Field(description="Runtime environment label.")
    endpoints: list[RuntimeEndpointEvidence] = Field(
        min_length=1,
        description="Sanitized health, readiness, and capability endpoint evidence.",
    )


class MaterialFieldReview(BaseModel):
    review_id: str = Field(description="Stable material field review identifier.")
    source_path: str = Field(description="Path in the sanitized live runtime suite payload.")
    observed_value: Any = Field(description="Observed bounded value used for claim review.")
    expected_posture: str = Field(description="Expected posture for this material field.")
    review_posture: Literal["PASS", "REVIEW_REQUIRED", "BLOCKED"] = Field(
        description="Review result for claim use."
    )
    claim_refs: list[str] = Field(
        default_factory=list,
        description="Supported-claim identifiers that depend on this field.",
    )


class BackendProofCaptureBundle(BaseModel):
    metadata: BackendProofCaptureMetadata
    scenario_contract: AdvisoryDemoScenarioContract
    supported_claim_register: AdvisorySupportedClaimRegister
    proof_pack: AdvisoryBankDemoProofPack
    document_proof_summary: AdvisoryDocumentProofSummary
    journey_integration_proof_summary: AdvisoryJourneyIntegrationProofSummary
    runtime_posture: BackendRuntimePosture
    sanitized_runtime_summary: dict[str, Any]
    material_field_reviews: list[MaterialFieldReview]


_MATERIAL_FIELD_SPECS: tuple[tuple[str, str, Any, str], ...] = (
    (
        "canonical_portfolio",
        "parity.complete_issuer_portfolio",
        RFC28_CANONICAL_PORTFOLIO_ID,
        "backend_proof_capture_repeatable",
    ),
    (
        "lifecycle_state",
        "parity.lifecycle_current_state",
        "EXECUTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "async_lifecycle_state",
        "parity.async_lifecycle_current_state",
        "EXECUTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "workspace_rationale_lineage",
        "parity.workspace_rationale_supportability_status",
        "HISTORICAL",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "execution_handoff",
        "parity.execution_handoff_status",
        "REQUESTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "execution_terminal",
        "parity.execution_terminal_status",
        "EXECUTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "report_status",
        "parity.report_status",
        "READY",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "narrative_review",
        "parity.proposal_narrative.review_state",
        "APPROVED_FOR_ADVISOR_USE",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "narrative_client_ready",
        "parity.proposal_narrative.client_ready_status",
        "NOT_REQUESTED",
        "client_ready_publication_blocked",
    ),
    (
        "memo_review",
        "parity.proposal_memo.review_action",
        "APPROVE_FOR_ADVISOR_USE",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "memo_client_ready",
        "parity.proposal_memo.review_client_ready_publication",
        "BLOCKED",
        "client_ready_publication_blocked",
    ),
    (
        "policy_evaluation",
        "parity.proposal_policy.evaluation_status",
        "PENDING_REVIEW",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "policy_client_ready",
        "parity.proposal_policy.workflow_client_ready_publication",
        "BLOCKED",
        "client_ready_publication_blocked",
    ),
    (
        "memo_document_render",
        "parity.proposal_memo.render_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "memo_document_archive",
        "parity.proposal_memo.archive_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "memo_archive_retention",
        "parity.proposal_memo.archive_retention_posture",
        "OWNED_BY_LOTUS_ARCHIVE",
        "advisor_use_document_proof_available",
    ),
    (
        "memo_archive_access_audit",
        "parity.proposal_memo.archive_access_audit_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_document_render",
        "parity.proposal_policy.render_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_document_archive",
        "parity.proposal_policy.archive_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_archive_retention",
        "parity.proposal_policy.archive_retention_posture",
        "OWNED_BY_LOTUS_ARCHIVE",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_archive_access_audit",
        "parity.proposal_policy.archive_access_audit_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "narrative_guardrail_reproduction",
        "parity.proposal_narrative.guardrail_failure_status",
        "LOCAL_POLICY_REPRODUCED",
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "memo_ai_non_authoritative",
        "parity.proposal_memo.ai_authoritative_for_memo_status",
        False,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "memo_ai_review_required",
        "parity.proposal_memo.ai_review_required",
        True,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_non_authoritative",
        "parity.proposal_policy.ai_authoritative_for_policy_status",
        False,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_human_review_required",
        "parity.proposal_policy.ai_human_review_required",
        True,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_raw_source_excluded",
        "parity.proposal_policy.ai_raw_source_evidence_included",
        False,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_forbidden_action_blocked",
        "parity.proposal_policy.forbidden_ai_action_block_status",
        "POLICY_AI_EVIDENCE_FORBIDDEN_ACTION",
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "degraded_risk",
        "degraded.risk_degraded_reason",
        "LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
        "degraded_runtime_boundary_evidence_available",
    ),
    (
        "degraded_core",
        "degraded.core_degraded_reason",
        "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
        "degraded_runtime_boundary_evidence_available",
    ),
    (
        "insufficient_evidence",
        "degraded.insufficient_evidence_decision.decision_status",
        "INSUFFICIENT_EVIDENCE",
        "degraded_runtime_boundary_evidence_available",
    ),
)


def build_default_scenario_contract() -> AdvisoryDemoScenarioContract:
    return AdvisoryDemoScenarioContract(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        governed_as_of_date=date(2026, 5, 28),
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        required_evidence_markers=[RFC28_CANONICAL_PROOF_MARKER],
        required_source_products=list(RFC28_SOURCE_PRODUCT_REFS),
        unsupported_boundaries=list(RFC28_UNSUPPORTED_BOUNDARIES),
        steps=[
            DemoScenarioStep(
                step_id="advisor_cockpit_operating_snapshot",
                title="Advisor reviews source-backed cockpit actions",
                owner_repository="lotus-advise",
                required_evidence_refs=["proof.assets.sanitized_runtime_summary"],
                required_workbench_panels=["advisory.advisor_cockpit"],
            ),
            DemoScenarioStep(
                step_id="proposal_lifecycle_and_decision_paths",
                title="Advisor validates proposal lifecycle, decisions, and alternatives",
                owner_repository="lotus-advise",
                required_evidence_refs=["proof.assets.material_field_review"],
            ),
            DemoScenarioStep(
                step_id="narrative_memo_policy_evidence",
                title="Advisor reviews narrative, memo, and policy evidence",
                owner_repository="lotus-advise",
                required_evidence_refs=[
                    "proof.assets.sanitized_runtime_summary",
                    "proof.assets.journey_integration_proof_summary",
                ],
                required_workbench_panels=[
                    "proposal.memo_evidence_pack",
                    "advisory.suitability_review",
                ],
            ),
            DemoScenarioStep(
                step_id="degraded_source_readiness",
                title="Advisor sees degraded-source boundaries without unsupported approval claims",
                owner_repository="lotus-advise",
                required_evidence_refs=["proof.assets.material_field_review"],
            ),
        ],
    )


def build_default_supported_claim_register() -> AdvisorySupportedClaimRegister:
    backend_summary_ref = "proof.assets.sanitized_runtime_summary"
    document_proof_ref = "proof.assets.document_proof_summary"
    integration_proof_ref = "proof.assets.journey_integration_proof_summary"
    field_review_ref = "proof.assets.material_field_review"
    runtime_posture_ref = "proof.assets.runtime_posture"
    return AdvisorySupportedClaimRegister(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        artifact_policy=ArtifactPolicy(
            commit_allowed_access_classes=[
                "COMMIT_SAFE_SUMMARY",
                "CUSTOMER_CONSUMABLE_SUMMARY",
            ],
            local_only_access_classes=[
                "LOCAL_ONLY_RUNTIME_EVIDENCE",
                "SECRET_MATERIAL",
            ],
            sensitive_material_rules=[
                "Secrets, tokens, prompts, raw provider payloads, and raw runtime logs stay local "
                "and must not be committed or used in client-facing proof material.",
            ],
        ),
        claims=[
            SupportedClaim(
                claim_id="backend_proof_capture_repeatable",
                title="Repeatable backend proof capture",
                classification="IMPLEMENTATION_BACKED",
                audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
                allowed_materials=["README", "WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "lotus-advise can generate a sanitized RFC-0028 backend proof pack from the "
                    "governed live runtime suite for the canonical private-banking scenario."
                ),
                evidence_refs=[backend_summary_ref, field_review_ref, runtime_posture_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-live-runtime-suite-result",
                        evidence_ref=backend_summary_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-material-field-review",
                        evidence_ref=field_review_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-runtime-posture",
                        evidence_ref=runtime_posture_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-document-proof-summary",
                        evidence_ref=document_proof_ref,
                    ),
                ],
                wording_rules=[
                    "State that this is backend proof until Gateway and Workbench slices pass.",
                    "Do not imply client-ready approval or external client communication.",
                ],
            ),
            SupportedClaim(
                claim_id="advisor_journey_backend_evidence_available",
                title="Advisor journey backend evidence available",
                classification="BACKEND_BACKED_UI_PENDING",
                audiences=["BUSINESS_USER", "SALES", "PRE_SALES", "CLIENT_DEMO"],
                allowed_materials=["WIKI", "DEMO_SCRIPT"],
                claim_text=(
                    "The advisory backend can prove the advisor journey evidence for proposal "
                    "lifecycle, narrative, memo, policy, report seam, and execution boundary "
                    "review before product-surface promotion."
                ),
                evidence_refs=[backend_summary_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-backend-advisor-journey-review",
                        evidence_ref=field_review_ref,
                    )
                ],
                wording_rules=[
                    "Use 'backend evidence available' until Gateway and Workbench proof is merged.",
                    "Do not use screenshots for this claim in Slice 5.",
                ],
            ),
            SupportedClaim(
                claim_id="advisor_use_document_proof_available",
                title="Advisor-use document proof is available",
                classification="BACKEND_BACKED_UI_PENDING",
                audiences=["BUSINESS_USER", "SALES", "PRE_SALES", "CLIENT_DEMO"],
                allowed_materials=["WIKI", "DEMO_SCRIPT"],
                claim_text=(
                    "The advisory backend records advisor-use memo and policy report packages "
                    "with render, archive, retention, legal-hold, and access-audit posture while "
                    "keeping client-ready documents blocked."
                ),
                evidence_refs=[document_proof_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-advisor-use-document-proof",
                        evidence_ref=document_proof_ref,
                    )
                ],
                wording_rules=[
                    "Use advisor-use document wording only until product-surface proof passes.",
                    "Do not imply client-ready publication or external client distribution.",
                ],
            ),
            SupportedClaim(
                claim_id="degraded_runtime_boundary_evidence_available",
                title="Degraded runtime boundaries are evidence-backed",
                classification="DEGRADED_SUPPORTED",
                audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
                allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "RFC-0028 backend proof records lotus-risk and lotus-core degraded paths and "
                    "keeps unsupported client-ready claims blocked when source evidence is absent."
                ),
                evidence_refs=[field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-degraded-source-review",
                        evidence_ref=field_review_ref,
                    )
                ],
                wording_rules=[
                    "Describe degraded support as controlled evidence posture, not as approval.",
                ],
            ),
            SupportedClaim(
                claim_id="ai_policy_cockpit_proof_integrated",
                title="AI, policy, and cockpit proof boundaries are integrated",
                classification="IMPLEMENTATION_BACKED",
                audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
                allowed_materials=["README", "WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "RFC-0028 backend proof includes a sanitized integration summary for "
                    "governed AI/model-risk controls, policy evidence, and advisor-cockpit "
                    "product-surface boundaries without promoting AI authority, policy approval, "
                    "or client-ready publication."
                ),
                evidence_refs=[integration_proof_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-ai-policy-cockpit-integration-proof",
                        evidence_ref=integration_proof_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-ai-policy-cockpit-material-review",
                        evidence_ref=field_review_ref,
                    ),
                ],
                wording_rules=[
                    "State that AI is review-gated and non-authoritative.",
                    (
                        "State that policy examples are source-owned reference controls, "
                        "not legal advice."
                    ),
                    "Do not imply advisor acknowledgement clears policy blockers.",
                ],
            ),
            SupportedClaim(
                claim_id="client_ready_publication_blocked",
                title="Client-ready publication is blocked",
                classification="UNSUPPORTED",
                audiences=["DEVELOPER", "OPERATIONS", "SALES", "PRE_SALES"],
                allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "Client-ready publication, sign-off approval, and external client "
                    "communication are not supported by this backend proof slice."
                ),
                wording_rules=[
                    "Use blocked/not supported language in all RFC-0028 Slice 5 material.",
                ],
            ),
            SupportedClaim(
                claim_id="rfp_security_package_pending",
                title="RFP and security pack publication pending",
                classification="PLANNED_RFC",
                audiences=["DEVELOPER", "OPERATIONS", "SALES", "PRE_SALES"],
                allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "RFP, security, one-pager, and architecture-pack publication remains pending "
                    "until the commercial artifact slice reviews claims against implementation "
                    "evidence."
                ),
                wording_rules=[
                    "Do not include this claim in RFP responses before Slice 10 completion.",
                ],
            ),
        ],
    )


def sanitize_live_runtime_summary(live_runtime_payload: dict[str, Any]) -> dict[str, Any]:
    parity = _dict_at(live_runtime_payload, "parity")
    degraded = _dict_at(live_runtime_payload, "degraded")
    return {
        "scenario_id": RFC28_CANONICAL_SCENARIO_ID,
        "primary_portfolio_id": _value_at(live_runtime_payload, "parity.complete_issuer_portfolio"),
        "proposal_lifecycle": {
            "sync_state": parity.get("lifecycle_current_state"),
            "sync_latest_version": parity.get("lifecycle_latest_version_no"),
            "async_state": parity.get("async_lifecycle_current_state"),
            "async_latest_version": parity.get("async_lifecycle_latest_version_no"),
            "execution_handoff_status": parity.get("execution_handoff_status"),
            "execution_terminal_status": parity.get("execution_terminal_status"),
            "report_status": parity.get("report_status"),
        },
        "workspace_rationale": {
            "initial_run_recorded": bool(parity.get("workspace_rationale_initial_run_id")),
            "replacement_run_recorded": bool(parity.get("workspace_rationale_replacement_run_id")),
            "review_state": parity.get("workspace_rationale_review_state"),
            "supportability_status": parity.get("workspace_rationale_supportability_status"),
        },
        "proposal_narrative": _select(
            _dict_at(parity, "proposal_narrative"),
            (
                "generation_mode",
                "policy_status",
                "read_posture_source",
                "regeneration_persistence_status",
                "review_state",
                "client_ready_status",
                "report_status",
                "report_package_status",
                "guardrail_failure_status",
                "ai_assisted_status",
            ),
        ),
        "proposal_memo": _select(
            _dict_at(parity, "proposal_memo"),
            (
                "memo_status",
                "lifecycle_status",
                "projection_client_ready_publication",
                "review_action",
                "review_client_ready_publication",
                "report_status",
                "report_package_status",
                "requested_output_formats",
                "render_ref_status",
                "archive_ref_status",
                "archive_retention_posture",
                "archive_legal_hold_posture",
                "archive_access_audit_ref_status",
                "ai_status",
                "ai_authoritative_for_memo_status",
                "ai_review_required",
                "lineage_complete",
                "replay_client_ready_publication",
                "stale_hash_block_status",
                "client_ready_release_block_status",
                "client_ready_document_block_status",
            ),
        ),
        "proposal_policy": _select(
            _dict_at(parity, "proposal_policy"),
            (
                "policy_pack_id",
                "policy_version",
                "evaluation_status",
                "material_rule_count",
                "pending_rule_count",
                "approval_dependency_count",
                "disclosure_requirement_count",
                "consent_requirement_count",
                "source_ref_count",
                "source_gap_count",
                "workflow_sign_off_status",
                "workflow_client_ready_publication",
                "workflow_open_requirement_count",
                "sign_off_decision_status",
                "report_status",
                "report_package_status",
                "requested_output_formats",
                "render_ref_status",
                "archive_ref_status",
                "archive_retention_posture",
                "archive_legal_hold_posture",
                "archive_access_audit_ref_status",
                "ai_status",
                "ai_authoritative_for_policy_status",
                "ai_human_review_required",
                "ai_raw_source_evidence_included",
                "lineage_complete",
                "replay_evaluation_hash_matches",
                "replay_source_evidence_hash_matches",
                "stale_hash_block_status",
                "client_ready_document_block_status",
                "forbidden_ai_action_block_status",
            ),
        ),
        "decision_paths": {
            path_name: _select(
                _dict_at(parity, path_name),
                (
                    "top_level_status",
                    "decision_status",
                    "primary_reason_code",
                    "recommended_next_action",
                    "approval_requirement_types",
                ),
            )
            for path_name in ("ready_decision", "review_decision", "blocked_decision")
        },
        "alternatives_paths": {
            path_name: _select(
                _dict_at(parity, path_name),
                (
                    "requested_objectives",
                    "feasible_count",
                    "feasible_with_review_count",
                    "rejected_count",
                    "selected_alternative_id",
                    "selected_rank",
                    "top_ranked_objective",
                    "top_ranked_reason_codes",
                    "rejected_reason_codes",
                ),
            )
            for path_name in (
                "noop_alternatives",
                "concentration_alternatives",
                "cash_raise_alternatives",
                "cross_currency_alternatives",
                "restricted_product_alternatives",
            )
        },
        "degraded_runtime": {
            "risk_drill_portfolio": degraded.get("risk_drill_portfolio"),
            "risk_degraded_reason": degraded.get("risk_degraded_reason"),
            "core_degraded_reason": degraded.get("core_degraded_reason"),
            "fallback_mode": degraded.get("fallback_mode"),
            "insufficient_evidence_decision": _select(
                _dict_at(degraded, "insufficient_evidence_decision"),
                (
                    "top_level_status",
                    "decision_status",
                    "primary_reason_code",
                    "recommended_next_action",
                ),
            ),
            "risk_unavailable_alternatives": _select(
                _dict_at(degraded, "risk_unavailable_alternatives"),
                ("requested_objectives", "rejected_count", "rejected_reason_codes"),
            ),
            "core_unavailable_alternatives": _select(
                _dict_at(degraded, "core_unavailable_alternatives"),
                ("requested_objectives", "rejected_count", "rejected_reason_codes"),
            ),
        },
    }


def review_material_fields(live_runtime_payload: dict[str, Any]) -> list[MaterialFieldReview]:
    reviews: list[MaterialFieldReview] = []
    for review_id, source_path, expected_value, claim_ref in _MATERIAL_FIELD_SPECS:
        observed_value = _value_at(live_runtime_payload, source_path)
        reviews.append(
            MaterialFieldReview(
                review_id=review_id,
                source_path=source_path,
                observed_value=observed_value,
                expected_posture=str(expected_value),
                review_posture="PASS" if observed_value == expected_value else "BLOCKED",
                claim_refs=[claim_ref],
            )
        )
    return reviews


def build_backend_proof_capture(
    live_runtime_payload: dict[str, Any],
    *,
    metadata: BackendProofCaptureMetadata,
    runtime_posture: BackendRuntimePosture,
    output_ref_prefix: str = RFC28_DEFAULT_OUTPUT_REF_PREFIX,
) -> BackendProofCaptureBundle:
    sanitized_summary = sanitize_live_runtime_summary(live_runtime_payload)
    document_proof_summary = build_document_proof_summary(live_runtime_payload)
    material_reviews = review_material_fields(live_runtime_payload)
    if any(review.review_posture == "BLOCKED" for review in material_reviews):
        blocked = ", ".join(
            f"{review.review_id}={review.observed_value!r}"
            for review in material_reviews
            if review.review_posture == "BLOCKED"
        )
        raise ValueError(f"RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED: {blocked}")
    journey_integration_proof_summary = build_journey_integration_proof_summary(
        live_runtime_payload
    )

    scenario_contract = build_default_scenario_contract()
    supported_claim_register = build_default_supported_claim_register()
    runtime_posture_payload = runtime_posture.model_dump(mode="json")
    document_proof_payload = document_proof_summary.model_dump(mode="json")
    integration_proof_payload = journey_integration_proof_summary.model_dump(mode="json")
    material_review_payload = [review.model_dump(mode="json") for review in material_reviews]
    proof_pack = AdvisoryBankDemoProofPack(
        proof_pack_id=f"rfc0028-backend-proof-{metadata.generated_at.strftime('%Y%m%dT%H%M%SZ')}",
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        generated_at=metadata.generated_at,
        correlation_id=metadata.correlation_id,
        client_ready_posture="CLIENT_READY_PUBLICATION_BLOCKED",
        repository_shas={"lotus-advise": metadata.repository_sha},
        evidence_markers=[
            RFC28_CANONICAL_PROOF_MARKER,
            "RFC0028_BACKEND_MATERIAL_FIELD_REVIEW_PASSED",
            "RFC0028_DOCUMENT_PROOF_SUMMARY_CREATED",
            "RFC0028_JOURNEY_INTEGRATION_PROOF_CREATED",
            "RFC0028_RUNTIME_POSTURE_CAPTURED",
        ],
        scenario_contract_ref=RFC28_SCENARIO_CONTRACT_REF,
        supported_claim_register_ref=RFC28_SUPPORTED_CLAIM_REGISTER_REF,
        source_product_refs=list(RFC28_SOURCE_PRODUCT_REFS),
        unsupported_boundaries=list(RFC28_UNSUPPORTED_BOUNDARIES),
        assets=[
            ProofAsset(
                asset_id="sanitized_runtime_summary",
                asset_type="LIVE_VALIDATION_SUMMARY",
                source_repository="lotus-advise",
                uri=f"{output_ref_prefix}/sanitized-runtime-summary.json",
                access_class="COMMIT_SAFE_SUMMARY",
                retention_class="LOCAL_EVIDENCE_BUNDLE",
                evidence_refs=[
                    "backend_proof_capture_repeatable",
                    "advisor_journey_backend_evidence_available",
                ],
                content_hash=hash_canonical_payload(sanitized_summary),
                commit_allowed=False,
            ),
            ProofAsset(
                asset_id="document_proof_summary",
                asset_type="REPORT_PACKAGE_SUMMARY",
                source_repository="lotus-advise",
                uri=f"{output_ref_prefix}/document-proof-summary.json",
                access_class="COMMIT_SAFE_SUMMARY",
                retention_class="LOCAL_EVIDENCE_BUNDLE",
                evidence_refs=[
                    "backend_proof_capture_repeatable",
                    "advisor_use_document_proof_available",
                ],
                content_hash=hash_canonical_payload(document_proof_payload),
                commit_allowed=False,
            ),
            ProofAsset(
                asset_id="journey_integration_proof_summary",
                asset_type="GOVERNANCE_INTEGRATION_SUMMARY",
                source_repository="lotus-advise",
                uri=f"{output_ref_prefix}/journey-integration-proof-summary.json",
                access_class="COMMIT_SAFE_SUMMARY",
                retention_class="LOCAL_EVIDENCE_BUNDLE",
                evidence_refs=[
                    "backend_proof_capture_repeatable",
                    "ai_policy_cockpit_proof_integrated",
                ],
                content_hash=hash_canonical_payload(integration_proof_payload),
                commit_allowed=False,
            ),
            ProofAsset(
                asset_id="material_field_review",
                asset_type="API_RESPONSE_SUMMARY",
                source_repository="lotus-advise",
                uri=f"{output_ref_prefix}/material-field-review.json",
                access_class="COMMIT_SAFE_SUMMARY",
                retention_class="LOCAL_EVIDENCE_BUNDLE",
                evidence_refs=[
                    "backend_proof_capture_repeatable",
                    "advisor_journey_backend_evidence_available",
                    "ai_policy_cockpit_proof_integrated",
                    "degraded_runtime_boundary_evidence_available",
                ],
                content_hash=hash_canonical_payload(material_review_payload),
                commit_allowed=False,
            ),
            ProofAsset(
                asset_id="runtime_posture",
                asset_type="SECURITY_CHECK_SUMMARY",
                source_repository="lotus-advise",
                uri=f"{output_ref_prefix}/runtime-posture.json",
                access_class="COMMIT_SAFE_SUMMARY",
                retention_class="LOCAL_EVIDENCE_BUNDLE",
                evidence_refs=["backend_proof_capture_repeatable"],
                content_hash=hash_canonical_payload(runtime_posture_payload),
                commit_allowed=False,
            ),
            ProofAsset(
                asset_id="source_live_runtime_bundle",
                asset_type="LOCAL_RUNTIME_BUNDLE",
                source_repository="lotus-advise",
                uri=metadata.live_suite_bundle_ref
                or metadata.live_suite_result_ref
                or f"{output_ref_prefix}/source-live-runtime-suite",
                access_class="LOCAL_ONLY_RUNTIME_EVIDENCE",
                retention_class="LOCAL_EVIDENCE_BUNDLE",
                evidence_refs=["backend_proof_capture_repeatable"],
                commit_allowed=False,
            ),
        ],
    )
    return BackendProofCaptureBundle(
        metadata=metadata,
        scenario_contract=scenario_contract,
        supported_claim_register=supported_claim_register,
        proof_pack=proof_pack,
        document_proof_summary=document_proof_summary,
        journey_integration_proof_summary=journey_integration_proof_summary,
        runtime_posture=runtime_posture,
        sanitized_runtime_summary=sanitized_summary,
        material_field_reviews=material_reviews,
    )


def default_capture_metadata(
    *,
    repository_sha: str,
    service_version: str,
    environment: str,
    correlation_id: str,
    generated_at: datetime | None = None,
    live_suite_result_ref: str | None = None,
    live_suite_bundle_ref: str | None = None,
) -> BackendProofCaptureMetadata:
    return BackendProofCaptureMetadata(
        generated_at=generated_at or datetime.now(UTC),
        repository_sha=repository_sha,
        service_version=service_version,
        environment=environment,
        correlation_id=correlation_id,
        live_suite_result_ref=live_suite_result_ref,
        live_suite_bundle_ref=live_suite_bundle_ref,
    )


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"RFC0028_BACKEND_PROOF_FIELD_MISSING: {key}")
    return value


def _value_at(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"RFC0028_BACKEND_PROOF_FIELD_MISSING: {dotted_path}")
        current = current[part]
    return current


def _select(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: payload.get(key) for key in keys}
