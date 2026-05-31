from __future__ import annotations

import os
from typing import Annotated, Any, cast

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
_RFC28_CORRELATION_ID_MAX_LENGTH = 128
_RFC28_ENVIRONMENT_MAX_LENGTH = 64
_RFC28_LIVE_PAYLOAD_TOP_LEVEL_MAX_KEYS = 16
_RFC28_REPOSITORY_SHA_MAX_LENGTH = 160
_RFC28_SERVICE_VERSION_MAX_LENGTH = 64
_SENSITIVE_METADATA_FRAGMENTS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "prompt",
)


class BankDemoProofCaptureRequest(BaseModel):
    live_runtime_payload: dict[str, Any] = Field(
        description=(
            "Governed live runtime suite result used as source evidence for RFC-0028 proof "
            "capture. The API returns sanitized proof output and does not persist raw payloads."
        ),
        max_length=_RFC28_LIVE_PAYLOAD_TOP_LEVEL_MAX_KEYS,
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
        max_length=_RFC28_REPOSITORY_SHA_MAX_LENGTH,
    )
    service_version: str | None = Field(
        default=None,
        description="Optional service version recorded in proof metadata.",
        examples=["0.1.0"],
        max_length=_RFC28_SERVICE_VERSION_MAX_LENGTH,
    )
    environment: str | None = Field(
        default=None,
        description="Runtime environment label recorded in proof metadata.",
        examples=["local"],
        max_length=_RFC28_ENVIRONMENT_MAX_LENGTH,
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
        return cast(
            str | None,
            normalize_optional_local_artifact_ref(value, field_name=info.field_name),
        )

    @field_validator("output_ref_prefix")
    @classmethod
    def _output_ref_prefix_must_be_local(cls, value: str) -> str:
        return cast(str, normalize_output_ref_prefix(value))

    @field_validator("repository_sha", "service_version", "environment")
    @classmethod
    def _metadata_must_be_bounded_and_non_sensitive(
        cls,
        value: str | None,
        info: ValidationInfo,
    ) -> str | None:
        return _normalize_optional_metadata(value, field_name=info.field_name)


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
            max_length=_RFC28_CORRELATION_ID_MAX_LENGTH,
        ),
    ] = None,
) -> BackendProofCaptureBundle:
    correlation_id = _runtime_correlation_id(x_correlation_id)
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
    return _normalize_runtime_metadata(
        (request_value or "").strip()
        or os.getenv("LOTUS_ADVISE_COMMIT_SHA", "").strip()
        or os.getenv("GITHUB_SHA", "").strip()
        or "runtime-unknown",
        field_name="repository_sha",
        max_length=_RFC28_REPOSITORY_SHA_MAX_LENGTH,
    )


def _runtime_service_version(request_value: str | None) -> str:
    return _normalize_runtime_metadata(
        (request_value or "").strip() or os.getenv("SERVICE_VERSION", _SERVICE_VERSION),
        field_name="service_version",
        max_length=_RFC28_SERVICE_VERSION_MAX_LENGTH,
    )


def _runtime_environment(request_value: str | None) -> str:
    return _normalize_runtime_metadata(
        (request_value or "").strip() or os.getenv("ENVIRONMENT", _DEFAULT_ENVIRONMENT),
        field_name="environment",
        max_length=_RFC28_ENVIRONMENT_MAX_LENGTH,
    )


def _runtime_correlation_id(request_value: str | None) -> str:
    return _normalize_runtime_metadata(
        (request_value or "").strip() or correlation_id_var.get() or "rfc0028-bank-demo-proof-api",
        field_name="correlation_id",
        max_length=_RFC28_CORRELATION_ID_MAX_LENGTH,
    )


def _normalize_optional_metadata(value: str | None, *, field_name: str | None) -> str | None:
    if value is None:
        return None
    if not value.strip():
        return None
    return _normalize_runtime_metadata(
        value,
        field_name=field_name or "metadata",
        max_length=_metadata_max_length(field_name),
    )


def _normalize_runtime_metadata(value: str, *, field_name: str, max_length: int) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} is too long")
    lowered = normalized.lower().replace("-", "_")
    if any(fragment in lowered for fragment in _SENSITIVE_METADATA_FRAGMENTS):
        raise ValueError(f"{field_name} cannot contain sensitive material")
    return normalized


def _metadata_max_length(field_name: str | None) -> int:
    if field_name == "service_version":
        return _RFC28_SERVICE_VERSION_MAX_LENGTH
    if field_name == "environment":
        return _RFC28_ENVIRONMENT_MAX_LENGTH
    return _RFC28_REPOSITORY_SHA_MAX_LENGTH
