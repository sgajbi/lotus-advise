from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord

COPILOT_REVIEW_CAPABILITY = "advisory.copilot.review"
COPILOT_REVIEW_AUTHORIZED_ROLES = frozenset(
    {"ADVISORY_SUPERVISOR", "COMPLIANCE_REVIEWER", "POLICY_CHECKER"}
)
COPILOT_REVIEW_ACTOR_MISMATCH = "COPILOT_REVIEW_ACTOR_MISMATCH"
COPILOT_REVIEW_SCOPE_REQUIRED = "COPILOT_REVIEW_SCOPE_REQUIRED"
COPILOT_REVIEW_SCOPE_FORBIDDEN = "COPILOT_REVIEW_SCOPE_FORBIDDEN"
COPILOT_REVIEW_MAKER_CHECKER_VIOLATION = "COPILOT_REVIEW_MAKER_CHECKER_VIOLATION"


@dataclass(frozen=True)
class CopilotReviewPrincipal:
    actor_id: str
    role: str
    tenant_id: str
    legal_entity_code: str
    correlation_id: str
    service_identity: str
    capabilities: frozenset[str]
    authorized_proposal_id: str | None = None
    authorized_portfolio_id: str | None = None

    def audit_metadata(self) -> dict[str, str]:
        metadata = {
            "subject": self.actor_id,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "legal_entity_code": self.legal_entity_code,
            "correlation_id": self.correlation_id,
            "service_identity": self.service_identity,
            "capability": COPILOT_REVIEW_CAPABILITY,
        }
        if self.authorized_proposal_id is not None:
            metadata["authorized_proposal_id"] = self.authorized_proposal_id
        if self.authorized_portfolio_id is not None:
            metadata["authorized_portfolio_id"] = self.authorized_portfolio_id
        return metadata


def validate_copilot_review_authority(
    *,
    principal: CopilotReviewPrincipal,
    run: AdvisoryCopilotRunRecord,
    submitted_actor_id: str | None,
) -> None:
    if submitted_actor_id is not None and submitted_actor_id != principal.actor_id:
        raise ValueError(COPILOT_REVIEW_ACTOR_MISMATCH)
    _require_scope(principal.authorized_portfolio_id)
    if principal.authorized_portfolio_id != run.portfolio_id:
        raise ValueError(COPILOT_REVIEW_SCOPE_FORBIDDEN)
    if run.proposal_id is not None:
        _require_scope(principal.authorized_proposal_id)
        if principal.authorized_proposal_id != run.proposal_id:
            raise ValueError(COPILOT_REVIEW_SCOPE_FORBIDDEN)
    if principal.tenant_id != run.tenant_id:
        raise ValueError(COPILOT_REVIEW_SCOPE_FORBIDDEN)
    if principal.actor_id == run.created_by:
        raise ValueError(COPILOT_REVIEW_MAKER_CHECKER_VIOLATION)


def copilot_review_audit_reason(
    reason: dict[str, Any],
    *,
    principal: CopilotReviewPrincipal,
    action: CopilotReviewAction,
) -> dict[str, Any]:
    return {
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


def _require_scope(value: str | None) -> None:
    if value is None:
        raise ValueError(COPILOT_REVIEW_SCOPE_REQUIRED)


__all__ = [
    "COPILOT_REVIEW_ACTOR_MISMATCH",
    "COPILOT_REVIEW_AUTHORIZED_ROLES",
    "COPILOT_REVIEW_CAPABILITY",
    "COPILOT_REVIEW_MAKER_CHECKER_VIOLATION",
    "COPILOT_REVIEW_SCOPE_FORBIDDEN",
    "COPILOT_REVIEW_SCOPE_REQUIRED",
    "CopilotReviewPrincipal",
    "copilot_review_audit_reason",
    "validate_copilot_review_authority",
]
