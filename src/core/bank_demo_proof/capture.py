from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.artifact_refs import (
    normalize_optional_local_artifact_ref,
    normalize_output_ref_prefix,
)
from src.core.bank_demo_proof.commercial_materials import (
    CommercialMaterialPack,
    build_commercial_material_pack,
)
from src.core.bank_demo_proof.document_proof import (
    AdvisoryDocumentProofSummary,
    build_document_proof_summary,
)
from src.core.bank_demo_proof.integration_proof import (
    AdvisoryJourneyIntegrationProofSummary,
    build_journey_integration_proof_summary,
)
from src.core.bank_demo_proof.material_review import MaterialFieldReview, review_material_fields
from src.core.bank_demo_proof.models import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    AdvisoryBankDemoProofPack,
    AdvisoryDemoScenarioContract,
    AdvisorySupportedClaimRegister,
    ArtifactPolicy,
    DemoScenarioStep,
    SupportedClaim,
    SupportedClaimProofRequirement,
)
from src.core.bank_demo_proof.proof_assets import build_backend_proof_assets
from src.core.bank_demo_proof.runtime_posture import BackendRuntimePosture
from src.core.bank_demo_proof.runtime_summary import sanitize_live_runtime_summary
from src.core.bank_demo_proof.validation import (
    RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
    RFC28_CAPTURE_METADATA_LABEL_MAX_LENGTH,
    normalize_capture_text,
)

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
_RFC28_CAPTURE_TOP_LEVEL_JSON_MAX_KEYS = 64
_RFC28_CAPTURE_MATERIAL_REVIEWS_MAX_ITEMS = 64


class BackendProofCaptureMetadata(BaseModel):
    generated_at: datetime = Field(description="UTC backend proof generation timestamp.")
    repository_sha: str = Field(
        description="lotus-advise commit SHA used for proof generation.",
        min_length=1,
        max_length=RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
    )
    service_version: str = Field(
        description="lotus-advise service version.",
        min_length=1,
        max_length=RFC28_CAPTURE_METADATA_LABEL_MAX_LENGTH,
    )
    environment: str = Field(
        description="Runtime environment label for the proof capture.",
        min_length=1,
        max_length=RFC28_CAPTURE_METADATA_LABEL_MAX_LENGTH,
    )
    correlation_id: str = Field(
        description="Correlation id for the proof-capture run.",
        min_length=1,
        max_length=RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
    )
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
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() != UTC.utcoffset(None):
            raise ValueError("generated_at must be timezone-aware UTC")
        self.live_suite_result_ref = normalize_optional_local_artifact_ref(
            self.live_suite_result_ref,
            field_name="live_suite_result_ref",
        )
        self.live_suite_bundle_ref = normalize_optional_local_artifact_ref(
            self.live_suite_bundle_ref,
            field_name="live_suite_bundle_ref",
        )
        return self

    @field_validator("repository_sha", "correlation_id")
    @classmethod
    def _metadata_identifiers_must_be_bounded(cls, value: str) -> str:
        return normalize_capture_text(value, field_name="proof metadata identifier")

    @field_validator("service_version", "environment")
    @classmethod
    def _metadata_labels_must_be_bounded(cls, value: str) -> str:
        return normalize_capture_text(
            value,
            field_name="proof metadata label",
            max_length=RFC28_CAPTURE_METADATA_LABEL_MAX_LENGTH,
        )


class BackendProofCaptureBundle(BaseModel):
    metadata: BackendProofCaptureMetadata
    scenario_contract: AdvisoryDemoScenarioContract
    supported_claim_register: AdvisorySupportedClaimRegister
    proof_pack: AdvisoryBankDemoProofPack
    document_proof_summary: AdvisoryDocumentProofSummary
    journey_integration_proof_summary: AdvisoryJourneyIntegrationProofSummary
    commercial_material_pack: CommercialMaterialPack
    runtime_posture: BackendRuntimePosture
    sanitized_runtime_summary: dict[str, Any] = Field(
        max_length=_RFC28_CAPTURE_TOP_LEVEL_JSON_MAX_KEYS,
        description="Sanitized runtime evidence summary used by proof-pack assets.",
    )
    material_field_reviews: list[MaterialFieldReview] = Field(
        max_length=_RFC28_CAPTURE_MATERIAL_REVIEWS_MAX_ITEMS,
        description="Material field review rows used for supported-claim gating.",
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
    commercial_material_ref = "proof.assets.commercial_material_pack"
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
                claim_id="commercial_rfp_security_material_available",
                title="Commercial, RFP, security, architecture, ROI, and demo material available",
                classification="IMPLEMENTATION_BACKED",
                audiences=[
                    "DEVELOPER",
                    "OPERATIONS",
                    "SALES",
                    "PRE_SALES",
                    "CLIENT_DEMO",
                    "RFP_SECURITY",
                ],
                allowed_materials=[
                    "README",
                    "WIKI",
                    "SUPPORTED_FEATURES",
                    "DEMO_SCRIPT",
                    "PRODUCT_ONE_PAGER",
                    "RFP_RESPONSE",
                    "SECURITY_PACK",
                    "ARCHITECTURE_DECK",
                    "ROI_STORY",
                    "OPERATOR_RUNBOOK",
                ],
                claim_text=(
                    "RFC-0028 has claim-controlled product one-pager, RFP response, security "
                    "posture, architecture, demo-script, proof-guide, ROI, feature-matrix, "
                    "client-demo boundary, and operator-checklist material grounded in the "
                    "supported-claim register and sanitized proof pack."
                ),
                evidence_refs=[commercial_material_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-commercial-material-pack",
                        evidence_ref=commercial_material_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-commercial-material-field-review",
                        evidence_ref=field_review_ref,
                    ),
                ],
                wording_rules=[
                    "Map every asset to the supported-claim register before use.",
                    "Do not claim bank-specific certifications or external attestations.",
                    (
                        "Do not claim client-ready publication, policy approval, "
                        "or execution authority."
                    ),
                ],
            ),
            SupportedClaim(
                claim_id="rfp_security_package_pending",
                title="Legacy RFP and security pack pending claim is retired",
                classification="UNSUPPORTED",
                audiences=["DEVELOPER", "OPERATIONS"],
                allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "The old pending RFP/security wording is retired. Use "
                    "commercial_rfp_security_material_available for the implemented, "
                    "claim-controlled material pack and preserve the blocked boundaries."
                ),
                wording_rules=[
                    "Do not use this retired claim in product, RFP, security, or demo material.",
                ],
            ),
        ],
    )


def build_backend_proof_capture(
    live_runtime_payload: dict[str, Any],
    *,
    metadata: BackendProofCaptureMetadata,
    runtime_posture: BackendRuntimePosture,
    output_ref_prefix: str = RFC28_DEFAULT_OUTPUT_REF_PREFIX,
) -> BackendProofCaptureBundle:
    output_ref_prefix = normalize_output_ref_prefix(output_ref_prefix)
    sanitized_summary = sanitize_live_runtime_summary(live_runtime_payload)
    document_proof_summary = build_document_proof_summary(live_runtime_payload)
    commercial_material_pack = build_commercial_material_pack()
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
    commercial_material_payload = commercial_material_pack.model_dump(mode="json")
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
            "RFC0028_COMMERCIAL_MATERIAL_PACK_CREATED",
            "RFC0028_RUNTIME_POSTURE_CAPTURED",
            "RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED",
        ],
        scenario_contract_ref=RFC28_SCENARIO_CONTRACT_REF,
        supported_claim_register_ref=RFC28_SUPPORTED_CLAIM_REGISTER_REF,
        source_product_refs=list(RFC28_SOURCE_PRODUCT_REFS),
        unsupported_boundaries=list(RFC28_UNSUPPORTED_BOUNDARIES),
        assets=build_backend_proof_assets(
            output_ref_prefix=output_ref_prefix,
            sanitized_summary=sanitized_summary,
            document_proof_payload=document_proof_payload,
            integration_proof_payload=integration_proof_payload,
            commercial_material_payload=commercial_material_payload,
            material_review_payload=material_review_payload,
            runtime_posture_payload=runtime_posture_payload,
            live_suite_bundle_ref=metadata.live_suite_bundle_ref,
            live_suite_result_ref=metadata.live_suite_result_ref,
        ),
    )
    return BackendProofCaptureBundle(
        metadata=metadata,
        scenario_contract=scenario_contract,
        supported_claim_register=supported_claim_register,
        proof_pack=proof_pack,
        document_proof_summary=document_proof_summary,
        journey_integration_proof_summary=journey_integration_proof_summary,
        commercial_material_pack=commercial_material_pack,
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
