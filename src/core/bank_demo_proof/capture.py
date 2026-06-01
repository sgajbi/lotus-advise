from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.artifact_refs import (
    normalize_optional_local_artifact_ref,
    normalize_output_ref_prefix,
)
from src.core.bank_demo_proof.commercial_materials import (
    CommercialMaterialPack,
    build_commercial_material_pack,
    validate_commercial_material_pack_against_register,
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
from src.core.bank_demo_proof.proof_assets import build_backend_proof_assets
from src.core.bank_demo_proof.proof_pack import build_backend_proof_pack
from src.core.bank_demo_proof.proof_pack_models import AdvisoryBankDemoProofPack
from src.core.bank_demo_proof.runtime_posture import BackendRuntimePosture
from src.core.bank_demo_proof.runtime_summary import sanitize_live_runtime_summary
from src.core.bank_demo_proof.scenario_contract import build_default_scenario_contract
from src.core.bank_demo_proof.scenario_models import AdvisoryDemoScenarioContract
from src.core.bank_demo_proof.supported_claim_models import AdvisorySupportedClaimRegister
from src.core.bank_demo_proof.supported_claim_register import (
    build_default_supported_claim_register,
)
from src.core.bank_demo_proof.validation import (
    RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
    RFC28_CAPTURE_METADATA_LABEL_MAX_LENGTH,
    normalize_capture_text,
)

RFC28_DEFAULT_OUTPUT_REF_PREFIX = "output/rfc0028/backend-proof"
_RFC28_REQUIRED_RUNTIME_FEATURE_KEYS = frozenset({"advisory.bank_demo_proof"})
_RFC28_REQUIRED_RUNTIME_WORKFLOW_KEYS = frozenset({"advisory_bank_demo_proof"})
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
        return cast(str, normalize_capture_text(value, field_name="proof metadata identifier"))

    @field_validator("service_version", "environment")
    @classmethod
    def _metadata_labels_must_be_bounded(cls, value: str) -> str:
        return cast(
            str,
            normalize_capture_text(
                value,
                field_name="proof metadata label",
                max_length=RFC28_CAPTURE_METADATA_LABEL_MAX_LENGTH,
            ),
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
    material_reviews = review_material_fields(live_runtime_payload)
    if any(review.review_posture == "BLOCKED" for review in material_reviews):
        blocked = ", ".join(
            f"{review.review_id}={review.observed_value!r}"
            for review in material_reviews
            if review.review_posture == "BLOCKED"
        )
        raise ValueError(f"RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED: {blocked}")
    _validate_runtime_capability_posture(runtime_posture)
    journey_integration_proof_summary = build_journey_integration_proof_summary(
        live_runtime_payload
    )

    scenario_contract = build_default_scenario_contract()
    supported_claim_register = build_default_supported_claim_register()
    commercial_material_pack = validate_commercial_material_pack_against_register(
        build_commercial_material_pack(),
        supported_claim_register,
    )
    runtime_posture_payload = runtime_posture.model_dump(mode="json")
    document_proof_payload = document_proof_summary.model_dump(mode="json")
    integration_proof_payload = journey_integration_proof_summary.model_dump(mode="json")
    commercial_material_payload = commercial_material_pack.model_dump(mode="json")
    material_review_payload = [review.model_dump(mode="json") for review in material_reviews]
    proof_assets = build_backend_proof_assets(
        output_ref_prefix=output_ref_prefix,
        sanitized_summary=sanitized_summary,
        document_proof_payload=document_proof_payload,
        integration_proof_payload=integration_proof_payload,
        commercial_material_payload=commercial_material_payload,
        material_review_payload=material_review_payload,
        runtime_posture_payload=runtime_posture_payload,
        live_suite_bundle_ref=metadata.live_suite_bundle_ref,
        live_suite_result_ref=metadata.live_suite_result_ref,
    )
    proof_pack = build_backend_proof_pack(
        generated_at=metadata.generated_at,
        correlation_id=metadata.correlation_id,
        repository_sha=metadata.repository_sha,
        assets=proof_assets,
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


def _validate_runtime_capability_posture(runtime_posture: BackendRuntimePosture) -> None:
    capability_endpoint = next(
        (
            endpoint
            for endpoint in runtime_posture.endpoints
            if endpoint.endpoint == "/platform/capabilities"
        ),
        None,
    )
    if capability_endpoint is None:
        raise ValueError(
            "RFC0028_RUNTIME_CAPABILITY_PROOF_MISSING: /platform/capabilities was not captured"
        )
    if capability_endpoint.posture == "NOT_PROBED":
        return
    if capability_endpoint.posture != "READY":
        raise ValueError(
            "RFC0028_RUNTIME_CAPABILITY_PROOF_UNREADY: /platform/capabilities was not ready"
        )

    feature_keys = _summary_string_set(capability_endpoint.summary, "feature_keys")
    missing_features = sorted(_RFC28_REQUIRED_RUNTIME_FEATURE_KEYS.difference(feature_keys))
    if missing_features:
        raise ValueError(
            "RFC0028_RUNTIME_CAPABILITY_PROOF_MISSING: missing feature "
            + ", ".join(missing_features)
        )

    workflow_keys = _summary_string_set(capability_endpoint.summary, "workflow_keys")
    missing_workflows = sorted(_RFC28_REQUIRED_RUNTIME_WORKFLOW_KEYS.difference(workflow_keys))
    if missing_workflows:
        raise ValueError(
            "RFC0028_RUNTIME_CAPABILITY_PROOF_MISSING: missing workflow "
            + ", ".join(missing_workflows)
        )


def _summary_string_set(summary: dict[str, Any], key: str) -> set[str]:
    values = summary.get(key)
    if not isinstance(values, list):
        return set()
    return {item for item in values if isinstance(item, str)}


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
