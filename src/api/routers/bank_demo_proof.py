from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from src.api.observability import correlation_id_var
from src.core.bank_demo_proof import (
    AdvisoryDemoScenarioContract,
    AdvisorySupportedClaimRegister,
    BackendProofCaptureBundle,
    BackendRuntimePosture,
    build_backend_proof_capture,
    build_default_scenario_contract,
    build_default_supported_claim_register,
    default_capture_metadata,
)
from src.core.bank_demo_proof.artifact_refs import (
    normalize_optional_local_artifact_ref,
    normalize_output_ref_prefix,
)
from src.core.bank_demo_proof.capture import RFC28_DEFAULT_OUTPUT_REF_PREFIX

router = APIRouter(prefix="/advisory/bank-demo-proof", tags=["Bank Demo Proof"])

_SERVICE_VERSION = "0.1.0"
_DEFAULT_ENVIRONMENT = "local"


class BankDemoProofCaptureRequest(BaseModel):
    live_runtime_payload: dict[str, Any] = Field(
        description=(
            "Governed live runtime suite result used as source evidence for RFC-0028 proof "
            "capture. The API returns sanitized proof output and does not persist raw payloads."
        )
    )
    runtime_posture: BackendRuntimePosture = Field(
        description="Sanitized health, readiness, and capability posture observed for lotus-advise."
    )
    repository_sha: str | None = Field(
        default=None,
        description=(
            "Optional lotus-advise commit SHA. When omitted, the service uses configured runtime "
            "metadata and falls back to runtime-unknown."
        ),
        examples=["8e7409d51975d4c72a8bc822d9551104e410476a"],
    )
    service_version: str | None = Field(
        default=None,
        description="Optional service version recorded in proof metadata.",
        examples=["0.1.0"],
    )
    environment: str | None = Field(
        default=None,
        description="Runtime environment label recorded in proof metadata.",
        examples=["local"],
    )
    live_suite_result_ref: str | None = Field(
        default=None,
        description=(
            "Optional local-only relative reference to the source live runtime result. URL "
            "schemes, credentials, query strings, fragments, traversal, and sensitive tokens are "
            "rejected."
        ),
        examples=["output/live-runtime-suite/result.json"],
    )
    live_suite_bundle_ref: str | None = Field(
        default=None,
        description=(
            "Optional local-only relative reference to the source live runtime evidence bundle. "
            "URL schemes, credentials, query strings, fragments, traversal, and sensitive tokens "
            "are rejected."
        ),
        examples=["output/live-runtime-suite"],
    )
    output_ref_prefix: str = Field(
        default=RFC28_DEFAULT_OUTPUT_REF_PREFIX,
        description=(
            "Sanitized relative proof artifact reference prefix used inside the returned proof "
            "pack. It must not contain URL schemes, credentials, query strings, fragments, "
            "traversal, or sensitive tokens."
        ),
        examples=[RFC28_DEFAULT_OUTPUT_REF_PREFIX],
    )

    @field_validator("live_suite_result_ref", "live_suite_bundle_ref")
    @classmethod
    def _live_suite_refs_must_be_local(
        cls,
        value: str | None,
        info: ValidationInfo,
    ) -> str | None:
        return normalize_optional_local_artifact_ref(value, field_name=info.field_name)

    @field_validator("output_ref_prefix")
    @classmethod
    def _output_ref_prefix_must_be_local(cls, value: str) -> str:
        return normalize_output_ref_prefix(value)


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
        ),
    ] = None,
) -> BackendProofCaptureBundle:
    correlation_id = x_correlation_id or correlation_id_var.get() or "rfc0028-bank-demo-proof-api"
    metadata = default_capture_metadata(
        repository_sha=_runtime_repository_sha(request.repository_sha),
        service_version=_runtime_service_version(request.service_version),
        environment=_runtime_environment(request.environment),
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


def _runtime_repository_sha(request_value: str | None) -> str:
    return (
        (request_value or "").strip()
        or os.getenv("LOTUS_ADVISE_COMMIT_SHA", "").strip()
        or os.getenv("GITHUB_SHA", "").strip()
        or "runtime-unknown"
    )


def _runtime_service_version(request_value: str | None) -> str:
    return (request_value or "").strip() or os.getenv("SERVICE_VERSION", _SERVICE_VERSION)


def _runtime_environment(request_value: str | None) -> str:
    return (request_value or "").strip() or os.getenv("ENVIRONMENT", _DEFAULT_ENVIRONMENT)
