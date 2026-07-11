from typing import cast

from fastapi import Depends, status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.policy_control_principal import (
    POLICY_PACK_ACTIVATE_CAPABILITY,
    POLICY_PACK_VALIDATE_CAPABILITY,
    PolicyControlPrincipal,
    assert_policy_pack_scope,
    bind_policy_control_actor,
    policy_control_audit_reason,
    require_policy_pack_activation_principal,
    require_policy_pack_validation_principal,
)
from src.api.proposals.policy_pack_parameters import (
    PolicyPackActivationIdempotencyKeyHeader,
    PolicyPackIdPath,
    PolicyPackValidationIdempotencyKeyHeader,
    PolicyPackVersionPath,
)
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
    return shared.get_policy_evidence_application_service().list_policy_pack_versions()


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
    policy_pack_id: PolicyPackIdPath,
    policy_version: PolicyPackVersionPath,
) -> PolicyPackDetailResponse:
    return cast(
        PolicyPackDetailResponse,
        run_proposal_operation(
            lambda: shared.get_policy_evidence_application_service().get_policy_pack_version(
                policy_pack_id=policy_pack_id,
                policy_version=policy_version,
            )
        ),
    )


@shared.router.post(
    "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/validate",
    response_model=PolicyPackValidationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Policy Packs"],
    summary="Validate Policy Pack Version",
    description=(
        "Validates a policy-pack version before activation and records an idempotent validation "
        "audit event. The `requested_by` field must match the trusted `X-Actor-Id` policy "
        "steward principal; authorization is derived from policy-control headers, not the "
        "request body. Invalid source-controlled policy definitions fail with diagnostics rather "
        "than activating partially supported policy behavior."
    ),
    responses=POLICY_PACK_VALIDATE_RESPONSES,
)
def validate_advisory_policy_pack_version(
    policy_pack_id: PolicyPackIdPath,
    policy_version: PolicyPackVersionPath,
    payload: PolicyPackValidationRequest,
    idempotency_key: PolicyPackValidationIdempotencyKeyHeader,
    principal: PolicyControlPrincipal = Depends(require_policy_pack_validation_principal),
) -> PolicyPackValidationResponse:
    return cast(
        PolicyPackValidationResponse,
        run_proposal_operation(
            lambda: _validate_policy_pack_version(
                policy_pack_id=policy_pack_id,
                policy_version=policy_version,
                payload=payload,
                idempotency_key=idempotency_key,
                principal=principal,
            )
        ),
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
        "does not evaluate proposals or approve client-ready publication. The `activated_by` "
        "field must match the trusted `X-Actor-Id` policy checker principal."
    ),
    responses=POLICY_PACK_ACTIVATE_RESPONSES,
)
def activate_advisory_policy_pack_version(
    policy_pack_id: PolicyPackIdPath,
    policy_version: PolicyPackVersionPath,
    payload: PolicyPackActivationRequest,
    idempotency_key: PolicyPackActivationIdempotencyKeyHeader,
    principal: PolicyControlPrincipal = Depends(require_policy_pack_activation_principal),
) -> PolicyPackActivationResponse:
    return cast(
        PolicyPackActivationResponse,
        run_proposal_operation(
            lambda: _activate_policy_pack_version(
                policy_pack_id=policy_pack_id,
                policy_version=policy_version,
                payload=payload,
                idempotency_key=idempotency_key,
                principal=principal,
            )
        ),
    )


def _validate_policy_pack_version(
    *,
    policy_pack_id: str,
    policy_version: str,
    payload: PolicyPackValidationRequest,
    idempotency_key: str,
    principal: PolicyControlPrincipal,
) -> PolicyPackValidationResponse:
    service = shared.get_policy_evidence_application_service()
    policy_pack = service.get_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )
    assert_policy_pack_scope(principal=principal, policy_pack=policy_pack)
    return service.validate_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        requested_by=bind_policy_control_actor(payload.requested_by, principal),
        idempotency_key=idempotency_key,
        reason=policy_control_audit_reason(
            payload.reason,
            principal=principal,
            capability=POLICY_PACK_VALIDATE_CAPABILITY,
        ),
    )


def _activate_policy_pack_version(
    *,
    policy_pack_id: str,
    policy_version: str,
    payload: PolicyPackActivationRequest,
    idempotency_key: str,
    principal: PolicyControlPrincipal,
) -> PolicyPackActivationResponse:
    service = shared.get_policy_evidence_application_service()
    policy_pack = service.get_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )
    assert_policy_pack_scope(principal=principal, policy_pack=policy_pack)
    return service.activate_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        activated_by=bind_policy_control_actor(payload.activated_by, principal),
        source_content_hash=payload.source_content_hash,
        idempotency_key=idempotency_key,
        reason=policy_control_audit_reason(
            payload.reason,
            principal=principal,
            capability=POLICY_PACK_ACTIVATE_CAPABILITY,
        ),
    )
