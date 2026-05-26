from typing import Annotated

from fastapi import Header, Path, status

import src.api.proposals.router as shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.core.policy_packs import (
    PolicyPackActivationRequest,
    PolicyPackActivationResponse,
    PolicyPackDetailResponse,
    PolicyPackListResponse,
    PolicyPackValidationRequest,
    PolicyPackValidationResponse,
    activate_policy_pack_version,
    get_policy_pack_version,
    list_policy_pack_versions,
    validate_policy_pack_version,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)


@shared.router.get(
    "/advisory/policy-packs",
    response_model=PolicyPackListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Packs"],
    summary="List Policy Packs",
    description=(
        "Lists RFC-0025 policy-pack versions and activation posture. Policy evaluation, "
        "Gateway-routed Workbench consumption, signed-off report-package handoff, and bounded AI "
        "evidence are supported by later RFC-0025 slices; client-ready publication remains gated."
    ),
    responses={200: {"description": "Policy-pack catalog metadata returned."}},
)
def list_advisory_policy_packs() -> PolicyPackListResponse:
    return list_policy_pack_versions()


@shared.router.get(
    "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}",
    response_model=PolicyPackDetailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Packs"],
    summary="Read Policy Pack Version",
    description=(
        "Returns immutable policy-pack version metadata, applicability, source requirements, "
        "rule summaries, disclosure/consent template summaries, approval routes, sample fixtures, "
        "content hash, and append-only Slice 5 catalog audit events."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "Policy-pack version was not found."}},
)
def get_advisory_policy_pack_version(
    policy_pack_id: Annotated[
        str,
        Path(description="Policy pack identifier.", examples=["SG_PRIVATE_BANKING_REFERENCE"]),
    ],
    policy_version: Annotated[
        str,
        Path(description="Policy pack version.", examples=["2026.05"]),
    ],
) -> PolicyPackDetailResponse:
    try:
        return get_policy_pack_version(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)
    raise AssertionError("unreachable")


@shared.router.post(
    "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/validate",
    response_model=PolicyPackValidationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Packs"],
    summary="Validate Policy Pack Version",
    description=(
        "Validates a policy-pack version before activation and records an idempotent validation "
        "audit event. Invalid source-controlled policy definitions fail with diagnostics rather "
        "than activating partially supported policy behavior."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Policy-pack version was not found."},
        status.HTTP_409_CONFLICT: {
            "description": "Idempotency key was reused for a different validation request."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Policy-pack validation failed with diagnostics."
        },
    },
)
def validate_advisory_policy_pack_version(
    policy_pack_id: Annotated[
        str,
        Path(description="Policy pack identifier.", examples=["SG_PRIVATE_BANKING_REFERENCE"]),
    ],
    policy_version: Annotated[
        str,
        Path(description="Policy pack version.", examples=["2026.05"]),
    ],
    payload: PolicyPackValidationRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key for replay-safe policy-pack validation.",
            examples=["validate-sg-policy-pack-001"],
        ),
    ],
) -> PolicyPackValidationResponse:
    try:
        return validate_policy_pack_version(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            requested_by=payload.requested_by,
            idempotency_key=idempotency_key,
            reason=payload.reason,
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)
    raise AssertionError("unreachable")


@shared.router.post(
    "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/activate",
    response_model=PolicyPackActivationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Packs"],
    summary="Activate Policy Pack Version",
    description=(
        "Activates a validated draft policy-pack version using the caller-supplied source content "
        "hash and maker-checker control where configured. Activated versions are immutable. This "
        "does not evaluate proposals or approve client-ready publication."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Policy-pack version was not found."},
        status.HTTP_409_CONFLICT: {
            "description": "Idempotency key was reused for a different activation request."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": (
                "Activation failed because validation is missing, hash mismatched, maker-checker "
                "control failed, or the version is already active and immutable."
            )
        },
    },
)
def activate_advisory_policy_pack_version(
    policy_pack_id: Annotated[
        str,
        Path(description="Policy pack identifier.", examples=["SG_PRIVATE_BANKING_REFERENCE"]),
    ],
    policy_version: Annotated[
        str,
        Path(description="Policy pack version.", examples=["2026.05"]),
    ],
    payload: PolicyPackActivationRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key for replay-safe policy-pack activation.",
            examples=["activate-sg-policy-pack-001"],
        ),
    ],
) -> PolicyPackActivationResponse:
    try:
        return activate_policy_pack_version(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            activated_by=payload.activated_by,
            source_content_hash=payload.source_content_hash,
            idempotency_key=idempotency_key,
            reason=payload.reason,
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)
    raise AssertionError("unreachable")
