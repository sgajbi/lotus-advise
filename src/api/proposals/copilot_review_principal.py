from __future__ import annotations

from typing import Annotated, cast

from fastapi import Header

from src.api.proposals.principal import (
    ProposalPrincipalContext,
    ProposalPrincipalErrors,
    ProposalPrincipalHeaders,
    resolve_proposal_principal,
)
from src.core.advisory_copilot.review_authority import (
    COPILOT_ACTION_CAPABILITY,
    COPILOT_CALLER_AUTHORIZED_ROLES,
    COPILOT_PACKET_CAPABILITY,
    COPILOT_POLICY_READ_CAPABILITY,
    COPILOT_READ_AUTHORIZED_ROLES,
    COPILOT_READ_CAPABILITY,
    COPILOT_REVIEW_AUTHORIZED_ROLES,
    COPILOT_REVIEW_CAPABILITY,
    CopilotCallerPrincipal,
    CopilotReviewPrincipal,
)

COPILOT_REVIEW_PRINCIPAL_REQUIRED = "COPILOT_REVIEW_PRINCIPAL_REQUIRED"
COPILOT_REVIEW_PRINCIPAL_INVALID = "COPILOT_REVIEW_PRINCIPAL_INVALID"
COPILOT_REVIEW_ROLE_NOT_AUTHORIZED = "COPILOT_REVIEW_ROLE_NOT_AUTHORIZED"
COPILOT_REVIEW_CAPABILITY_REQUIRED = "COPILOT_REVIEW_CAPABILITY_REQUIRED"
COPILOT_CALLER_PRINCIPAL_REQUIRED = "COPILOT_CALLER_PRINCIPAL_REQUIRED"
COPILOT_CALLER_PRINCIPAL_INVALID = "COPILOT_CALLER_PRINCIPAL_INVALID"
COPILOT_CALLER_ROLE_NOT_AUTHORIZED = "COPILOT_CALLER_ROLE_NOT_AUTHORIZED"
COPILOT_CALLER_CAPABILITY_REQUIRED = "COPILOT_CALLER_CAPABILITY_REQUIRED"

_REVIEW_PRINCIPAL_ERRORS = ProposalPrincipalErrors(
    required=COPILOT_REVIEW_PRINCIPAL_REQUIRED,
    invalid=COPILOT_REVIEW_PRINCIPAL_INVALID,
    role_not_authorized=COPILOT_REVIEW_ROLE_NOT_AUTHORIZED,
    capability_required=COPILOT_REVIEW_CAPABILITY_REQUIRED,
)

_CALLER_PRINCIPAL_ERRORS = ProposalPrincipalErrors(
    required=COPILOT_CALLER_PRINCIPAL_REQUIRED,
    invalid=COPILOT_CALLER_PRINCIPAL_INVALID,
    role_not_authorized=COPILOT_CALLER_ROLE_NOT_AUTHORIZED,
    capability_required=COPILOT_CALLER_CAPABILITY_REQUIRED,
)


def require_advisory_copilot_review_principal(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    x_legal_entity_code: Annotated[str | None, Header(alias="X-Legal-Entity-Code")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    x_service_identity: Annotated[str | None, Header(alias="X-Service-Identity")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_capabilities: Annotated[str | None, Header(alias="X-Capabilities")] = None,
    x_principal_status: Annotated[str | None, Header(alias="X-Principal-Status")] = None,
    x_authorized_proposal_id: Annotated[
        str | None, Header(alias="X-Authorized-Proposal-Id")
    ] = None,
    x_authorized_portfolio_id: Annotated[
        str | None, Header(alias="X-Authorized-Portfolio-Id")
    ] = None,
) -> CopilotReviewPrincipal:
    return _resolve_copilot_principal(
        required_capability=COPILOT_REVIEW_CAPABILITY,
        authorized_roles=COPILOT_REVIEW_AUTHORIZED_ROLES,
        errors=_REVIEW_PRINCIPAL_ERRORS,
        headers=_copilot_principal_headers(
            x_actor_id=x_actor_id,
            x_role=x_role,
            x_tenant_id=x_tenant_id,
            x_legal_entity_code=x_legal_entity_code,
            x_correlation_id=x_correlation_id,
            x_service_identity=x_service_identity,
            authorization=authorization,
            x_capabilities=x_capabilities,
            x_principal_status=x_principal_status,
            x_authorized_proposal_id=x_authorized_proposal_id,
            x_authorized_portfolio_id=x_authorized_portfolio_id,
        ),
    )


def require_advisory_copilot_packet_principal(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    x_legal_entity_code: Annotated[str | None, Header(alias="X-Legal-Entity-Code")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    x_service_identity: Annotated[str | None, Header(alias="X-Service-Identity")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_capabilities: Annotated[str | None, Header(alias="X-Capabilities")] = None,
    x_principal_status: Annotated[str | None, Header(alias="X-Principal-Status")] = None,
    x_authorized_proposal_id: Annotated[
        str | None, Header(alias="X-Authorized-Proposal-Id")
    ] = None,
    x_authorized_portfolio_id: Annotated[
        str | None, Header(alias="X-Authorized-Portfolio-Id")
    ] = None,
) -> CopilotCallerPrincipal:
    return _resolve_copilot_principal(
        required_capability=COPILOT_PACKET_CAPABILITY,
        authorized_roles=COPILOT_CALLER_AUTHORIZED_ROLES,
        errors=_CALLER_PRINCIPAL_ERRORS,
        headers=_copilot_principal_headers(
            x_actor_id=x_actor_id,
            x_role=x_role,
            x_tenant_id=x_tenant_id,
            x_legal_entity_code=x_legal_entity_code,
            x_correlation_id=x_correlation_id,
            x_service_identity=x_service_identity,
            authorization=authorization,
            x_capabilities=x_capabilities,
            x_principal_status=x_principal_status,
            x_authorized_proposal_id=x_authorized_proposal_id,
            x_authorized_portfolio_id=x_authorized_portfolio_id,
        ),
    )


def require_advisory_copilot_action_principal(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    x_legal_entity_code: Annotated[str | None, Header(alias="X-Legal-Entity-Code")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    x_service_identity: Annotated[str | None, Header(alias="X-Service-Identity")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_capabilities: Annotated[str | None, Header(alias="X-Capabilities")] = None,
    x_principal_status: Annotated[str | None, Header(alias="X-Principal-Status")] = None,
    x_authorized_proposal_id: Annotated[
        str | None, Header(alias="X-Authorized-Proposal-Id")
    ] = None,
    x_authorized_portfolio_id: Annotated[
        str | None, Header(alias="X-Authorized-Portfolio-Id")
    ] = None,
) -> CopilotCallerPrincipal:
    return _resolve_copilot_principal(
        required_capability=COPILOT_ACTION_CAPABILITY,
        authorized_roles=COPILOT_CALLER_AUTHORIZED_ROLES,
        errors=_CALLER_PRINCIPAL_ERRORS,
        headers=_copilot_principal_headers(
            x_actor_id=x_actor_id,
            x_role=x_role,
            x_tenant_id=x_tenant_id,
            x_legal_entity_code=x_legal_entity_code,
            x_correlation_id=x_correlation_id,
            x_service_identity=x_service_identity,
            authorization=authorization,
            x_capabilities=x_capabilities,
            x_principal_status=x_principal_status,
            x_authorized_proposal_id=x_authorized_proposal_id,
            x_authorized_portfolio_id=x_authorized_portfolio_id,
        ),
    )


def require_advisory_copilot_read_principal(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    x_legal_entity_code: Annotated[str | None, Header(alias="X-Legal-Entity-Code")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    x_service_identity: Annotated[str | None, Header(alias="X-Service-Identity")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_capabilities: Annotated[str | None, Header(alias="X-Capabilities")] = None,
    x_principal_status: Annotated[str | None, Header(alias="X-Principal-Status")] = None,
    x_authorized_proposal_id: Annotated[
        str | None, Header(alias="X-Authorized-Proposal-Id")
    ] = None,
    x_authorized_portfolio_id: Annotated[
        str | None, Header(alias="X-Authorized-Portfolio-Id")
    ] = None,
) -> CopilotCallerPrincipal:
    return _resolve_copilot_principal(
        required_capability=COPILOT_READ_CAPABILITY,
        authorized_roles=COPILOT_READ_AUTHORIZED_ROLES,
        errors=_CALLER_PRINCIPAL_ERRORS,
        headers=_copilot_principal_headers(
            x_actor_id=x_actor_id,
            x_role=x_role,
            x_tenant_id=x_tenant_id,
            x_legal_entity_code=x_legal_entity_code,
            x_correlation_id=x_correlation_id,
            x_service_identity=x_service_identity,
            authorization=authorization,
            x_capabilities=x_capabilities,
            x_principal_status=x_principal_status,
            x_authorized_proposal_id=x_authorized_proposal_id,
            x_authorized_portfolio_id=x_authorized_portfolio_id,
        ),
    )


def require_advisory_copilot_policy_read_principal(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    x_legal_entity_code: Annotated[str | None, Header(alias="X-Legal-Entity-Code")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    x_service_identity: Annotated[str | None, Header(alias="X-Service-Identity")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_capabilities: Annotated[str | None, Header(alias="X-Capabilities")] = None,
    x_principal_status: Annotated[str | None, Header(alias="X-Principal-Status")] = None,
    x_authorized_proposal_id: Annotated[
        str | None, Header(alias="X-Authorized-Proposal-Id")
    ] = None,
    x_authorized_portfolio_id: Annotated[
        str | None, Header(alias="X-Authorized-Portfolio-Id")
    ] = None,
) -> CopilotCallerPrincipal:
    return _resolve_copilot_principal(
        required_capability=COPILOT_POLICY_READ_CAPABILITY,
        authorized_roles=COPILOT_CALLER_AUTHORIZED_ROLES,
        errors=_CALLER_PRINCIPAL_ERRORS,
        headers=_copilot_principal_headers(
            x_actor_id=x_actor_id,
            x_role=x_role,
            x_tenant_id=x_tenant_id,
            x_legal_entity_code=x_legal_entity_code,
            x_correlation_id=x_correlation_id,
            x_service_identity=x_service_identity,
            authorization=authorization,
            x_capabilities=x_capabilities,
            x_principal_status=x_principal_status,
            x_authorized_proposal_id=x_authorized_proposal_id,
            x_authorized_portfolio_id=x_authorized_portfolio_id,
        ),
    )


def _resolve_copilot_principal(
    *,
    required_capability: str,
    authorized_roles: frozenset[str],
    errors: ProposalPrincipalErrors,
    headers: ProposalPrincipalHeaders,
) -> CopilotCallerPrincipal:
    return cast(
        CopilotCallerPrincipal,
        resolve_proposal_principal(
            required_capability=required_capability,
            authorized_roles=authorized_roles,
            errors=errors,
            principal_factory=_build_copilot_review_principal,
            headers=headers,
        ),
    )


def _copilot_principal_headers(
    *,
    x_actor_id: str | None,
    x_role: str | None,
    x_tenant_id: str | None,
    x_legal_entity_code: str | None,
    x_correlation_id: str | None,
    x_service_identity: str | None,
    authorization: str | None,
    x_capabilities: str | None,
    x_principal_status: str | None,
    x_authorized_proposal_id: str | None,
    x_authorized_portfolio_id: str | None,
) -> ProposalPrincipalHeaders:
    return ProposalPrincipalHeaders(
        actor_id=x_actor_id,
        role=x_role,
        tenant_id=x_tenant_id,
        legal_entity_code=x_legal_entity_code,
        correlation_id=x_correlation_id,
        service_identity=x_service_identity,
        authorization=authorization,
        capabilities=x_capabilities,
        principal_status=x_principal_status,
        authorized_proposal_id=x_authorized_proposal_id,
        authorized_portfolio_id=x_authorized_portfolio_id,
    )


def _build_copilot_review_principal(
    context: ProposalPrincipalContext,
) -> CopilotCallerPrincipal:
    return CopilotCallerPrincipal(
        actor_id=context.actor_id,
        role=context.role,
        tenant_id=context.tenant_id,
        legal_entity_code=context.legal_entity_code,
        correlation_id=context.correlation_id,
        service_identity=context.service_identity,
        capabilities=context.capabilities,
        authorized_proposal_id=context.authorized_proposal_id,
        authorized_portfolio_id=context.authorized_portfolio_id,
    )


__all__ = [
    "COPILOT_CALLER_CAPABILITY_REQUIRED",
    "COPILOT_CALLER_PRINCIPAL_INVALID",
    "COPILOT_CALLER_PRINCIPAL_REQUIRED",
    "COPILOT_CALLER_ROLE_NOT_AUTHORIZED",
    "COPILOT_REVIEW_CAPABILITY_REQUIRED",
    "COPILOT_REVIEW_PRINCIPAL_INVALID",
    "COPILOT_REVIEW_PRINCIPAL_REQUIRED",
    "COPILOT_REVIEW_ROLE_NOT_AUTHORIZED",
    "require_advisory_copilot_action_principal",
    "require_advisory_copilot_packet_principal",
    "require_advisory_copilot_policy_read_principal",
    "require_advisory_copilot_read_principal",
    "require_advisory_copilot_review_principal",
]
