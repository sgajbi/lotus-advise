from typing import Annotated

from fastapi import Header, Path, status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.policy_pack_responses import (
    POLICY_PACK_ACTIVATE_RESPONSES,
    POLICY_PACK_LIST_RESPONSES,
    POLICY_PACK_NOT_FOUND_RESPONSE,
    POLICY_PACK_VALIDATE_RESPONSES,
)
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


@shared.router.get(
    "/advisory/policy-packs",
    response_model=PolicyPackListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Packs"],
    summary="List Policy Packs",
    description=(
        "Lists RFC-0025 policy-pack versions and activation posture. Policy evaluation, "
        "Gateway-routed Workbench consumption, signed-off report-package handoff, and bounded AI "
        "evidence are supported by the current RFC-0025 implementation; client-ready publication "
        "remains gated."
    ),
    responses=POLICY_PACK_LIST_RESPONSES,
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
    responses=POLICY_PACK_NOT_FOUND_RESPONSE,
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
    return run_proposal_operation(
        lambda: get_policy_pack_version(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
    )


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
    responses=POLICY_PACK_VALIDATE_RESPONSES,
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
    return run_proposal_operation(
        lambda: validate_policy_pack_version(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            requested_by=payload.requested_by,
            idempotency_key=idempotency_key,
            reason=payload.reason,
        )
    )


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
    responses=POLICY_PACK_ACTIVATE_RESPONSES,
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
    return run_proposal_operation(
        lambda: activate_policy_pack_version(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            activated_by=payload.activated_by,
            source_content_hash=payload.source_content_hash,
            idempotency_key=idempotency_key,
            reason=payload.reason,
        )
    )
