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
from src.core.bank_demo_proof import (
    AdvisoryDemoScenarioContract,
    AdvisorySupportedClaimRegister,
    BackendProofCaptureBundle,
    build_backend_proof_capture,
    build_default_scenario_contract,
    build_default_supported_claim_register,
    default_capture_metadata,
)

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
        "incomplete proof state. Raw live runtime payloads are not persisted by this endpoint."
    ),
    responses={
        status.HTTP_409_CONFLICT: {
            "description": (
                "Material proof evidence is missing or does not match the canonical scenario."
            )
        },
        422: {"description": "Request shape or proof metadata validation failed."},
    },
)
def build_bank_demo_proof_pack(
    request: BankDemoProofCaptureRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-Id",
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
