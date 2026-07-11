from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import Header, status

from src.api.proposals.errors import raise_proposal_api_http_exception
from src.core.advisory_copilot.review_authority import (
    COPILOT_REVIEW_AUTHORIZED_ROLES,
    COPILOT_REVIEW_CAPABILITY,
    CopilotReviewPrincipal,
)

COPILOT_REVIEW_PRINCIPAL_REQUIRED = "COPILOT_REVIEW_PRINCIPAL_REQUIRED"
COPILOT_REVIEW_PRINCIPAL_INVALID = "COPILOT_REVIEW_PRINCIPAL_INVALID"
COPILOT_REVIEW_ROLE_NOT_AUTHORIZED = "COPILOT_REVIEW_ROLE_NOT_AUTHORIZED"
COPILOT_REVIEW_CAPABILITY_REQUIRED = "COPILOT_REVIEW_CAPABILITY_REQUIRED"


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
    actor_id = _required_header(x_actor_id)
    role = _required_header(x_role).upper()
    tenant_id = _required_header(x_tenant_id)
    legal_entity_code = _required_header(x_legal_entity_code).upper()
    correlation_id = _required_header(x_correlation_id)
    service_identity = _service_identity(x_service_identity, authorization)
    capabilities = _capability_set(x_capabilities)

    if (x_principal_status or "ACTIVE").strip().upper() != "ACTIVE":
        _raise_authn(COPILOT_REVIEW_PRINCIPAL_INVALID)
    if role not in COPILOT_REVIEW_AUTHORIZED_ROLES:
        _raise_authz(COPILOT_REVIEW_ROLE_NOT_AUTHORIZED)
    if COPILOT_REVIEW_CAPABILITY not in capabilities:
        _raise_authz(COPILOT_REVIEW_CAPABILITY_REQUIRED)

    return CopilotReviewPrincipal(
        actor_id=actor_id,
        role=role,
        tenant_id=tenant_id,
        legal_entity_code=legal_entity_code,
        correlation_id=correlation_id,
        service_identity=service_identity,
        capabilities=frozenset(capabilities),
        authorized_proposal_id=_optional_header(x_authorized_proposal_id),
        authorized_portfolio_id=_optional_header(x_authorized_portfolio_id),
    )


def _required_header(value: str | None) -> str:
    normalized = _optional_header(value)
    if normalized is None:
        _raise_authn(COPILOT_REVIEW_PRINCIPAL_REQUIRED)
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
    _raise_authn(COPILOT_REVIEW_PRINCIPAL_REQUIRED)


def _capability_set(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def _raise_authn(detail: str) -> NoReturn:
    raise_proposal_api_http_exception(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def _raise_authz(detail: str) -> NoReturn:
    raise_proposal_api_http_exception(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


__all__ = [
    "COPILOT_REVIEW_CAPABILITY_REQUIRED",
    "COPILOT_REVIEW_PRINCIPAL_INVALID",
    "COPILOT_REVIEW_PRINCIPAL_REQUIRED",
    "COPILOT_REVIEW_ROLE_NOT_AUTHORIZED",
    "require_advisory_copilot_review_principal",
]
