from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import Header, status

from src.api.proposals.errors import raise_proposal_api_http_exception
from src.core.advisor_cockpit.caller_authority import (
    ADVISOR_COCKPIT_ACKNOWLEDGE_CAPABILITY,
    ADVISOR_COCKPIT_AUTHORIZED_ROLES,
    ADVISOR_COCKPIT_READ_CAPABILITY,
    AdvisorCockpitPrincipal,
)

ADVISOR_COCKPIT_PRINCIPAL_REQUIRED = "ADVISOR_COCKPIT_PRINCIPAL_REQUIRED"
ADVISOR_COCKPIT_PRINCIPAL_INVALID = "ADVISOR_COCKPIT_PRINCIPAL_INVALID"
ADVISOR_COCKPIT_ROLE_NOT_AUTHORIZED = "ADVISOR_COCKPIT_ROLE_NOT_AUTHORIZED"
ADVISOR_COCKPIT_CAPABILITY_REQUIRED = "ADVISOR_COCKPIT_CAPABILITY_REQUIRED"


def require_advisor_cockpit_read_principal(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    x_legal_entity_code: Annotated[str | None, Header(alias="X-Legal-Entity-Code")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    x_service_identity: Annotated[str | None, Header(alias="X-Service-Identity")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_capabilities: Annotated[str | None, Header(alias="X-Capabilities")] = None,
    x_principal_status: Annotated[str | None, Header(alias="X-Principal-Status")] = None,
    x_authorized_advisor_id: Annotated[str | None, Header(alias="X-Authorized-Advisor-Id")] = None,
    x_authorized_portfolio_id: Annotated[
        str | None, Header(alias="X-Authorized-Portfolio-Id")
    ] = None,
) -> AdvisorCockpitPrincipal:
    return resolve_advisor_cockpit_principal(
        required_capability=ADVISOR_COCKPIT_READ_CAPABILITY,
        x_actor_id=x_actor_id,
        x_role=x_role,
        x_tenant_id=x_tenant_id,
        x_legal_entity_code=x_legal_entity_code,
        x_correlation_id=x_correlation_id,
        x_service_identity=x_service_identity,
        authorization=authorization,
        x_capabilities=x_capabilities,
        x_principal_status=x_principal_status,
        x_authorized_advisor_id=x_authorized_advisor_id,
        x_authorized_portfolio_id=x_authorized_portfolio_id,
    )


def require_advisor_cockpit_acknowledgement_principal(
    x_actor_id: Annotated[str | None, Header(alias="X-Actor-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    x_legal_entity_code: Annotated[str | None, Header(alias="X-Legal-Entity-Code")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    x_service_identity: Annotated[str | None, Header(alias="X-Service-Identity")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_capabilities: Annotated[str | None, Header(alias="X-Capabilities")] = None,
    x_principal_status: Annotated[str | None, Header(alias="X-Principal-Status")] = None,
    x_authorized_advisor_id: Annotated[str | None, Header(alias="X-Authorized-Advisor-Id")] = None,
    x_authorized_portfolio_id: Annotated[
        str | None, Header(alias="X-Authorized-Portfolio-Id")
    ] = None,
) -> AdvisorCockpitPrincipal:
    return resolve_advisor_cockpit_principal(
        required_capability=ADVISOR_COCKPIT_ACKNOWLEDGE_CAPABILITY,
        x_actor_id=x_actor_id,
        x_role=x_role,
        x_tenant_id=x_tenant_id,
        x_legal_entity_code=x_legal_entity_code,
        x_correlation_id=x_correlation_id,
        x_service_identity=x_service_identity,
        authorization=authorization,
        x_capabilities=x_capabilities,
        x_principal_status=x_principal_status,
        x_authorized_advisor_id=x_authorized_advisor_id,
        x_authorized_portfolio_id=x_authorized_portfolio_id,
    )


def resolve_advisor_cockpit_principal(
    *,
    required_capability: str,
    x_actor_id: str | None,
    x_role: str | None,
    x_tenant_id: str | None,
    x_legal_entity_code: str | None,
    x_correlation_id: str | None,
    x_service_identity: str | None,
    authorization: str | None,
    x_capabilities: str | None,
    x_principal_status: str | None,
    x_authorized_advisor_id: str | None,
    x_authorized_portfolio_id: str | None,
) -> AdvisorCockpitPrincipal:
    actor_id = _required_header(x_actor_id)
    role = _required_header(x_role).upper()
    tenant_id = _required_header(x_tenant_id)
    legal_entity_code = _required_header(x_legal_entity_code).upper()
    correlation_id = _required_header(x_correlation_id)
    service_identity = _service_identity(x_service_identity, authorization)
    capabilities = _capability_set(x_capabilities)

    if (x_principal_status or "ACTIVE").strip().upper() != "ACTIVE":
        _raise_authn(ADVISOR_COCKPIT_PRINCIPAL_INVALID)
    if role not in ADVISOR_COCKPIT_AUTHORIZED_ROLES:
        _raise_authz(ADVISOR_COCKPIT_ROLE_NOT_AUTHORIZED)
    if required_capability not in capabilities:
        _raise_authz(ADVISOR_COCKPIT_CAPABILITY_REQUIRED)

    return AdvisorCockpitPrincipal(
        actor_id=actor_id,
        role=role,
        tenant_id=tenant_id,
        legal_entity_code=legal_entity_code,
        correlation_id=correlation_id,
        service_identity=service_identity,
        capabilities=frozenset(capabilities),
        authorized_advisor_id=_optional_header(x_authorized_advisor_id),
        authorized_portfolio_id=_optional_header(x_authorized_portfolio_id),
    )


def _required_header(value: str | None) -> str:
    normalized = _optional_header(value)
    if normalized is None:
        _raise_authn(ADVISOR_COCKPIT_PRINCIPAL_REQUIRED)
    return normalized


def _optional_header(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _service_identity(x_service_identity: str | None, authorization: str | None) -> str:
    service_identity = _optional_header(x_service_identity)
    if service_identity is not None:
        return service_identity
    if _optional_header(authorization) is not None:
        return "authorization"
    _raise_authn(ADVISOR_COCKPIT_PRINCIPAL_REQUIRED)


def _capability_set(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def _raise_authn(detail: str) -> NoReturn:
    raise_proposal_api_http_exception(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )
    raise AssertionError("unreachable")


def _raise_authz(detail: str) -> NoReturn:
    raise_proposal_api_http_exception(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )
    raise AssertionError("unreachable")


__all__ = [
    "ADVISOR_COCKPIT_CAPABILITY_REQUIRED",
    "ADVISOR_COCKPIT_PRINCIPAL_INVALID",
    "ADVISOR_COCKPIT_PRINCIPAL_REQUIRED",
    "ADVISOR_COCKPIT_ROLE_NOT_AUTHORIZED",
    "require_advisor_cockpit_acknowledgement_principal",
    "require_advisor_cockpit_read_principal",
]
