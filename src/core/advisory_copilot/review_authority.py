from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.structured_payload import (
    MAX_SAFE_STRUCTURED_PAYLOAD_ITEMS,
    assert_safe_structured_payload,
)

COPILOT_REVIEW_CAPABILITY = "advisory.copilot.review"
COPILOT_PACKET_CAPABILITY = "advisory.copilot.packet"
COPILOT_ACTION_CAPABILITY = "advisory.copilot.action"
COPILOT_READ_CAPABILITY = "advisory.copilot.read"
COPILOT_POLICY_READ_CAPABILITY = "advisory.policy_evaluation.read"
COPILOT_CALLER_AUTHORIZED_ROLES = frozenset({"ADVISOR", "COMPLIANCE_REVIEWER", "POLICY_CHECKER"})
COPILOT_READ_AUTHORIZED_ROLES = COPILOT_CALLER_AUTHORIZED_ROLES | frozenset({"ADVISORY_SUPERVISOR"})
COPILOT_REVIEW_AUTHORIZED_ROLES = frozenset(
    {"ADVISORY_SUPERVISOR", "COMPLIANCE_REVIEWER", "POLICY_CHECKER"}
)
COPILOT_REVIEW_ACTOR_MISMATCH = "COPILOT_REVIEW_ACTOR_MISMATCH"
COPILOT_REVIEW_SCOPE_REQUIRED = "COPILOT_REVIEW_SCOPE_REQUIRED"
COPILOT_REVIEW_SCOPE_FORBIDDEN = "COPILOT_REVIEW_SCOPE_FORBIDDEN"
COPILOT_REVIEW_MAKER_CHECKER_VIOLATION = "COPILOT_REVIEW_MAKER_CHECKER_VIOLATION"
COPILOT_RESOURCE_SCOPE_REQUIRED = "COPILOT_RESOURCE_SCOPE_REQUIRED"
COPILOT_RESOURCE_SCOPE_FORBIDDEN = "COPILOT_RESOURCE_SCOPE_FORBIDDEN"


@dataclass(frozen=True)
class CopilotCallerPrincipal:
    actor_id: str
    role: str
    tenant_id: str
    legal_entity_code: str
    correlation_id: str
    service_identity: str
    capabilities: frozenset[str]
    authorized_proposal_id: str | None = None
    authorized_portfolio_id: str | None = None

    def audit_metadata(self) -> dict[str, Any]:
        if len(self.capabilities) > MAX_SAFE_STRUCTURED_PAYLOAD_ITEMS:
            raise ValueError("COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE")
        metadata = {
            "subject": self.actor_id,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "legal_entity_code": self.legal_entity_code,
            "correlation_id": self.correlation_id,
            "service_identity": self.service_identity,
            "capabilities": sorted(self.capabilities),
        }
        if self.authorized_proposal_id is not None:
            metadata["authorized_proposal_id"] = self.authorized_proposal_id
        if self.authorized_portfolio_id is not None:
            metadata["authorized_portfolio_id"] = self.authorized_portfolio_id
        return metadata


CopilotReviewPrincipal = CopilotCallerPrincipal


def validate_copilot_resource_authority(
    *,
    principal: CopilotCallerPrincipal,
    tenant_id: str,
    portfolio_id: str,
    proposal_id: str | None,
) -> None:
    _require_resource_scope(principal.authorized_portfolio_id)
    if principal.tenant_id != tenant_id or principal.authorized_portfolio_id != portfolio_id:
        raise ValueError(COPILOT_RESOURCE_SCOPE_FORBIDDEN)
    if proposal_id is not None:
        _require_resource_scope(principal.authorized_proposal_id)
        if principal.authorized_proposal_id != proposal_id:
            raise ValueError(COPILOT_RESOURCE_SCOPE_FORBIDDEN)


def validate_copilot_proposal_scope(*, principal: CopilotCallerPrincipal, proposal_id: str) -> None:
    _require_resource_scope(principal.authorized_proposal_id)
    if principal.authorized_proposal_id != proposal_id:
        raise ValueError(COPILOT_RESOURCE_SCOPE_FORBIDDEN)


def validate_copilot_review_authority(
    *,
    principal: CopilotCallerPrincipal,
    run: AdvisoryCopilotRunRecord,
    submitted_actor_id: str | None,
) -> None:
    if submitted_actor_id is not None and submitted_actor_id != principal.actor_id:
        raise ValueError(COPILOT_REVIEW_ACTOR_MISMATCH)
    try:
        validate_copilot_resource_authority(
            principal=principal,
            tenant_id=run.tenant_id,
            portfolio_id=run.portfolio_id,
            proposal_id=run.proposal_id,
        )
    except ValueError as exc:
        if str(exc) == COPILOT_RESOURCE_SCOPE_REQUIRED:
            raise ValueError(COPILOT_REVIEW_SCOPE_REQUIRED) from exc
        raise ValueError(COPILOT_REVIEW_SCOPE_FORBIDDEN)
    if principal.actor_id == run.created_by:
        raise ValueError(COPILOT_REVIEW_MAKER_CHECKER_VIOLATION)


def copilot_review_audit_reason(
    reason: dict[str, Any],
    *,
    principal: CopilotCallerPrincipal,
    action: CopilotReviewAction,
) -> dict[str, Any]:
    if len(reason) > MAX_SAFE_STRUCTURED_PAYLOAD_ITEMS - 2:
        raise ValueError("COPILOT_STRUCTURED_PAYLOAD_TOO_LARGE")
    audit_reason = {
        **reason,
        "trusted_principal": principal.audit_metadata(),
        "review_authorization": {
            "decision": "AUTHORIZED",
            "review_action": action,
            "required_capability": COPILOT_REVIEW_CAPABILITY,
            "authorized_roles": sorted(COPILOT_REVIEW_AUTHORIZED_ROLES),
            "maker_checker_required": True,
            "maker_checker_satisfied": True,
            "scope_decision": "AUTHORIZED",
        },
    }
    assert_safe_structured_payload(audit_reason)
    return audit_reason


def _require_resource_scope(value: str | None) -> None:
    if value is None:
        raise ValueError(COPILOT_RESOURCE_SCOPE_REQUIRED)


__all__ = [
    "COPILOT_REVIEW_ACTOR_MISMATCH",
    "COPILOT_REVIEW_AUTHORIZED_ROLES",
    "COPILOT_REVIEW_CAPABILITY",
    "COPILOT_REVIEW_MAKER_CHECKER_VIOLATION",
    "COPILOT_REVIEW_SCOPE_FORBIDDEN",
    "COPILOT_REVIEW_SCOPE_REQUIRED",
    "COPILOT_ACTION_CAPABILITY",
    "COPILOT_CALLER_AUTHORIZED_ROLES",
    "COPILOT_PACKET_CAPABILITY",
    "COPILOT_POLICY_READ_CAPABILITY",
    "COPILOT_READ_CAPABILITY",
    "COPILOT_READ_AUTHORIZED_ROLES",
    "COPILOT_RESOURCE_SCOPE_FORBIDDEN",
    "COPILOT_RESOURCE_SCOPE_REQUIRED",
    "CopilotCallerPrincipal",
    "CopilotReviewPrincipal",
    "copilot_review_audit_reason",
    "validate_copilot_proposal_scope",
    "validate_copilot_resource_authority",
    "validate_copilot_review_authority",
]
