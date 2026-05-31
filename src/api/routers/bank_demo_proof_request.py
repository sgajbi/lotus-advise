from __future__ import annotations

import os
from typing import Any, cast

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from src.api.observability import correlation_id_var
from src.core.bank_demo_proof import BackendRuntimePosture
from src.core.bank_demo_proof.artifact_refs import (
    normalize_optional_local_artifact_ref,
    normalize_output_ref_prefix,
)
from src.core.bank_demo_proof.capture import RFC28_DEFAULT_OUTPUT_REF_PREFIX

SERVICE_VERSION_DEFAULT = "0.1.0"
ENVIRONMENT_DEFAULT = "local"
RFC28_CORRELATION_ID_MAX_LENGTH = 128
RFC28_ENVIRONMENT_MAX_LENGTH = 64
RFC28_LIVE_PAYLOAD_TOP_LEVEL_MAX_KEYS = 16
RFC28_REPOSITORY_SHA_MAX_LENGTH = 160
RFC28_SERVICE_VERSION_MAX_LENGTH = 64
SENSITIVE_METADATA_FRAGMENTS = (
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
        max_length=RFC28_LIVE_PAYLOAD_TOP_LEVEL_MAX_KEYS,
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
        max_length=RFC28_REPOSITORY_SHA_MAX_LENGTH,
    )
    service_version: str | None = Field(
        default=None,
        description="Optional service version recorded in proof metadata.",
        examples=["0.1.0"],
        max_length=RFC28_SERVICE_VERSION_MAX_LENGTH,
    )
    environment: str | None = Field(
        default=None,
        description="Runtime environment label recorded in proof metadata.",
        examples=["local"],
        max_length=RFC28_ENVIRONMENT_MAX_LENGTH,
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
        return normalize_optional_metadata(value, field_name=info.field_name)


def runtime_repository_sha(request_value: str | None) -> str:
    return normalize_runtime_metadata(
        (request_value or "").strip()
        or os.getenv("LOTUS_ADVISE_COMMIT_SHA", "").strip()
        or os.getenv("GITHUB_SHA", "").strip()
        or "runtime-unknown",
        field_name="repository_sha",
        max_length=RFC28_REPOSITORY_SHA_MAX_LENGTH,
    )


def runtime_service_version(request_value: str | None) -> str:
    return normalize_runtime_metadata(
        (request_value or "").strip() or os.getenv("SERVICE_VERSION", SERVICE_VERSION_DEFAULT),
        field_name="service_version",
        max_length=RFC28_SERVICE_VERSION_MAX_LENGTH,
    )


def runtime_environment(request_value: str | None) -> str:
    return normalize_runtime_metadata(
        (request_value or "").strip() or os.getenv("ENVIRONMENT", ENVIRONMENT_DEFAULT),
        field_name="environment",
        max_length=RFC28_ENVIRONMENT_MAX_LENGTH,
    )


def runtime_correlation_id(request_value: str | None) -> str:
    return normalize_runtime_metadata(
        (request_value or "").strip() or correlation_id_var.get() or "rfc0028-bank-demo-proof-api",
        field_name="correlation_id",
        max_length=RFC28_CORRELATION_ID_MAX_LENGTH,
    )


def normalize_optional_metadata(value: str | None, *, field_name: str | None) -> str | None:
    if value is None:
        return None
    if not value.strip():
        return None
    return normalize_runtime_metadata(
        value,
        field_name=field_name or "metadata",
        max_length=metadata_max_length(field_name),
    )


def normalize_runtime_metadata(value: str, *, field_name: str, max_length: int) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} is too long")
    lowered = normalized.lower().replace("-", "_")
    if any(fragment in lowered for fragment in SENSITIVE_METADATA_FRAGMENTS):
        raise ValueError(f"{field_name} cannot contain sensitive material")
    return normalized


def metadata_max_length(field_name: str | None) -> int:
    if field_name == "service_version":
        return RFC28_SERVICE_VERSION_MAX_LENGTH
    if field_name == "environment":
        return RFC28_ENVIRONMENT_MAX_LENGTH
    return RFC28_REPOSITORY_SHA_MAX_LENGTH
