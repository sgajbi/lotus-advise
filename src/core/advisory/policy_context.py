from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

POLICY_CONTEXT_AVAILABLE = "AVAILABLE"
POLICY_CONTEXT_MISSING = "MISSING"

CLIENT_CONTEXT_STATUS = "client_context_status"
MANDATE_CONTEXT_STATUS = "mandate_context_status"
JURISDICTION_CONTEXT_STATUS = "jurisdiction_context_status"


@dataclass(frozen=True)
class ProposalPolicySelectors:
    household_id: str | None = None
    mandate_id: str | None = None
    jurisdiction: str | None = None
    legal_entity_code: str | None = None
    benchmark_id: str | None = None


def build_advisory_policy_context(
    *,
    input_mode: str,
    resolution_source: str,
    selectors: ProposalPolicySelectors,
) -> dict[str, Any]:
    client_context_status = _status_from_selector(selectors.household_id)
    mandate_context_status = _status_from_selector(selectors.mandate_id)
    jurisdiction_context_status = _status_from_selector(selectors.jurisdiction)

    missing_context: list[str] = []
    if client_context_status == POLICY_CONTEXT_MISSING:
        missing_context.append("CLIENT_CONTEXT")
    if mandate_context_status == POLICY_CONTEXT_MISSING:
        missing_context.append("MANDATE_CONTEXT")
    if jurisdiction_context_status == POLICY_CONTEXT_MISSING:
        missing_context.append("JURISDICTION")

    return {
        "input_mode": input_mode,
        "context_source": resolution_source,
        CLIENT_CONTEXT_STATUS: client_context_status,
        MANDATE_CONTEXT_STATUS: mandate_context_status,
        JURISDICTION_CONTEXT_STATUS: jurisdiction_context_status,
        "household_id": selectors.household_id,
        "mandate_id": selectors.mandate_id,
        "jurisdiction": selectors.jurisdiction,
        "legal_entity_code": selectors.legal_entity_code,
        "benchmark_id": selectors.benchmark_id,
        "missing_context": missing_context,
    }


def client_context_available(policy_context: Mapping[str, Any] | None) -> bool:
    return _context_status_available(policy_context, CLIENT_CONTEXT_STATUS)


def mandate_context_available(policy_context: Mapping[str, Any] | None) -> bool:
    return _context_status_available(policy_context, MANDATE_CONTEXT_STATUS)


def jurisdiction_context_available(policy_context: Mapping[str, Any] | None) -> bool:
    return _context_status_available(policy_context, JURISDICTION_CONTEXT_STATUS)


def _context_status_available(
    policy_context: Mapping[str, Any] | None,
    status_key: str,
) -> bool:
    if policy_context is None:
        return False
    return policy_context.get(status_key) == POLICY_CONTEXT_AVAILABLE


def _status_from_selector(value: str | None) -> str:
    return POLICY_CONTEXT_AVAILABLE if value else POLICY_CONTEXT_MISSING
