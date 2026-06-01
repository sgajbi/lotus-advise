from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from src.api.routers.bank_demo_proof_request import (
    RFC28_CORRELATION_ID_MAX_LENGTH,
    BankDemoProofCaptureRequest,
    runtime_correlation_id,
    runtime_environment,
    runtime_repository_sha,
    runtime_service_version,
)
from src.api.sensitive_error_details import contains_sensitive_error_detail
from src.core.bank_demo_proof import (
    AdvisoryDemoScenarioContract,
    AdvisorySupportedClaimRegister,
    BackendProofCaptureBundle,
    build_backend_proof_capture,
    build_default_scenario_contract,
    build_default_supported_claim_register,
    default_capture_metadata,
)

RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX = "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED"
RFC28_PROOF_VALIDATION_FAILED = "RFC0028_PROOF_PACK_VALIDATION_FAILED"

router = APIRouter(prefix="/advisory/bank-demo-proof", tags=["Bank Demo Proof"])


@router.get(
    "/scenario-contract",
    response_model=AdvisoryDemoScenarioContract,
    status_code=status.HTTP_200_OK,
    summary="Get RFC-0028 Demo Scenario Contract",
    description=(
        "Returns the governed RFC-0028 bank-demo scenario contract used by Gateway, Workbench, "
        "and proof automation. The contract is source-owned by lotus-advise and does not imply "
        "client-ready publication or external client communication."
    ),
)
def get_bank_demo_scenario_contract() -> AdvisoryDemoScenarioContract:
    return build_default_scenario_contract()


@router.get(
    "/supported-claim-register",
    response_model=AdvisorySupportedClaimRegister,
    status_code=status.HTTP_200_OK,
    summary="Get RFC-0028 Supported-Claim Register",
    description=(
        "Returns the source-owned RFC-0028 supported-claim register. Claim classifications and "
        "wording rules govern demo, wiki, screenshot, RFP, security, and one-pager usage."
    ),
)
def get_bank_demo_supported_claim_register() -> AdvisorySupportedClaimRegister:
    return build_default_supported_claim_register()


@router.post(
    "/proof-packs",
    response_model=BackendProofCaptureBundle,
    status_code=status.HTTP_200_OK,
    summary="Build RFC-0028 Backend Proof Pack",
    description=(
        "Builds a sanitized RFC-0028 backend proof pack from governed live runtime evidence. "
        "Material-field drift returns HTTP 409 so Gateway and Workbench cannot promote stale or "
        "incomplete proof state. Ready /platform/capabilities runtime evidence must include "
        "feature advisory.bank_demo_proof and workflow advisory_bank_demo_proof before proof "
        "artifacts can be reused. Unredacted live runtime payloads are not persisted by this "
        "endpoint."
    ),
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Material proof evidence is missing or does not match the canonical scenario."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED: "
                            "policy_evaluation expected PENDING_REVIEW"
                        )
                    }
                }
            },
        },
        422: {
            "description": ("Request shape, proof metadata, or source evidence validation failed."),
            "content": {
                "application/json": {
                    "example": {
                        "detail": ("RFC0028_INTEGRATION_PROOF_FIELD_MISSING: policy_pack_id")
                    }
                }
            },
        },
    },
)
def build_bank_demo_proof_pack(
    request: BankDemoProofCaptureRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            title="X-Correlation-ID",
            description="Optional caller correlation id propagated into proof metadata.",
            max_length=RFC28_CORRELATION_ID_MAX_LENGTH,
        ),
    ] = None,
) -> BackendProofCaptureBundle:
    correlation_id = runtime_correlation_id(x_correlation_id)
    metadata = default_capture_metadata(
        repository_sha=runtime_repository_sha(request.repository_sha),
        service_version=runtime_service_version(request.service_version),
        environment=runtime_environment(request.environment),
        correlation_id=correlation_id,
        live_suite_result_ref=request.live_suite_result_ref,
        live_suite_bundle_ref=request.live_suite_bundle_ref,
    )
    try:
        return build_backend_proof_capture(
            request.live_runtime_payload,
            metadata=metadata,
            runtime_posture=request.runtime_posture,
            output_ref_prefix=request.output_ref_prefix,
        )
    except ValueError as exc:
        raw_detail = str(exc)
        raise HTTPException(
            status_code=_proof_pack_error_status(raw_detail),
            detail=_safe_proof_pack_error_detail(raw_detail),
        ) from exc


def _proof_pack_error_status(error_detail: str) -> int:
    if error_detail.startswith(RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX):
        return 409
    return 422


def _safe_proof_pack_error_detail(error_detail: str) -> str:
    if not _contains_sensitive_error_detail(error_detail):
        return error_detail
    if error_detail.startswith(RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX):
        return (
            f"{RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX}: "
            "material field review failed with sensitive detail redacted"
        )
    return f"{RFC28_PROOF_VALIDATION_FAILED}: source evidence failed validation"


def _contains_sensitive_error_detail(error_detail: str) -> bool:
    return contains_sensitive_error_detail(error_detail)
