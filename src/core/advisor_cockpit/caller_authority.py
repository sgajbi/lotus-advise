from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast, get_args

from src.core.advisor_cockpit.api_models import AdvisorCockpitAcknowledgeRequest
from src.core.advisor_cockpit.reference_models import CockpitCallerContext
from src.core.advisor_cockpit.type_models import AdvisorCockpitCallerRole

ADVISOR_COCKPIT_READ_CAPABILITY = "advisory.advisor_cockpit.read"
ADVISOR_COCKPIT_ACKNOWLEDGE_CAPABILITY = "advisory.advisor_cockpit.acknowledge"
ADVISOR_COCKPIT_AUTHORIZED_ROLES = frozenset(get_args(AdvisorCockpitCallerRole))

ADVISOR_COCKPIT_ACTOR_MISMATCH = "ADVISOR_COCKPIT_ACTOR_MISMATCH"
ADVISOR_COCKPIT_SCOPE_REQUIRED = "ADVISOR_COCKPIT_SCOPE_REQUIRED"
ADVISOR_COCKPIT_SCOPE_FORBIDDEN = "ADVISOR_COCKPIT_SCOPE_FORBIDDEN"


@dataclass(frozen=True)
class AdvisorCockpitPrincipal:
    actor_id: str
    role: str
    tenant_id: str
    legal_entity_code: str
    correlation_id: str
    service_identity: str
    capabilities: frozenset[str]
    authorized_advisor_id: str | None = None
    authorized_portfolio_id: str | None = None

    def audit_metadata(self, *, capability: str) -> dict[str, str]:
        metadata = {
            "subject": self.actor_id,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "legal_entity_code": self.legal_entity_code,
            "correlation_id": self.correlation_id,
            "service_identity": self.service_identity,
            "capability": capability,
        }
        if self.authorized_advisor_id is not None:
            metadata["authorized_advisor_id"] = self.authorized_advisor_id
        if self.authorized_portfolio_id is not None:
            metadata["authorized_portfolio_id"] = self.authorized_portfolio_id
        return metadata


def cockpit_caller_context_from_principal(
    principal: AdvisorCockpitPrincipal,
) -> CockpitCallerContext:
    return CockpitCallerContext(
        advisor_id=_advisor_scope_for_context(principal),
        role=cast(AdvisorCockpitCallerRole, principal.role),
    )


def authorized_cockpit_portfolio_id(
    *,
    principal: AdvisorCockpitPrincipal,
    requested_portfolio_id: str | None,
) -> str | None:
    if requested_portfolio_id is None:
        return principal.authorized_portfolio_id
    if principal.authorized_portfolio_id is None:
        raise ValueError(ADVISOR_COCKPIT_SCOPE_REQUIRED)
    if requested_portfolio_id != principal.authorized_portfolio_id:
        raise ValueError(ADVISOR_COCKPIT_SCOPE_FORBIDDEN)
    return requested_portfolio_id


def bind_cockpit_acknowledgement_payload(
    *,
    payload: AdvisorCockpitAcknowledgeRequest,
    principal: AdvisorCockpitPrincipal,
) -> AdvisorCockpitAcknowledgeRequest:
    if payload.acknowledged_by != principal.actor_id:
        raise ValueError(ADVISOR_COCKPIT_ACTOR_MISMATCH)
    return payload.model_copy(update={"acknowledged_by": principal.actor_id})


def cockpit_acknowledgement_audit_reason(
    reason: dict[str, Any],
    *,
    principal: AdvisorCockpitPrincipal,
) -> dict[str, Any]:
    return {
        **reason,
        "trusted_principal": principal.audit_metadata(
            capability=ADVISOR_COCKPIT_ACKNOWLEDGE_CAPABILITY
        ),
        "acknowledgement_authorization": {
            "decision": "AUTHORIZED",
            "required_capability": ADVISOR_COCKPIT_ACKNOWLEDGE_CAPABILITY,
            "authorized_roles": sorted(ADVISOR_COCKPIT_AUTHORIZED_ROLES),
            "scope_decision": "AUTHORIZED",
        },
    }


def _advisor_scope_for_context(principal: AdvisorCockpitPrincipal) -> str | None:
    if principal.authorized_advisor_id is not None:
        return principal.authorized_advisor_id
    if principal.role == "ADVISOR":
        return principal.actor_id
    return None


__all__ = [
    "ADVISOR_COCKPIT_ACKNOWLEDGE_CAPABILITY",
    "ADVISOR_COCKPIT_ACTOR_MISMATCH",
    "ADVISOR_COCKPIT_AUTHORIZED_ROLES",
    "ADVISOR_COCKPIT_READ_CAPABILITY",
    "ADVISOR_COCKPIT_SCOPE_FORBIDDEN",
    "ADVISOR_COCKPIT_SCOPE_REQUIRED",
    "AdvisorCockpitPrincipal",
    "authorized_cockpit_portfolio_id",
    "bind_cockpit_acknowledgement_payload",
    "cockpit_acknowledgement_audit_reason",
    "cockpit_caller_context_from_principal",
]
