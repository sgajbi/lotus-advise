from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProposalPolicySelectors:
    household_id: str | None = None
    mandate_id: str | None = None
    jurisdiction: str | None = None
    benchmark_id: str | None = None


def build_advisory_policy_context(
    *,
    input_mode: str,
    resolution_source: str,
    selectors: ProposalPolicySelectors,
) -> dict[str, Any]:
    client_context_status = "AVAILABLE" if selectors.household_id else "MISSING"
    mandate_context_status = "AVAILABLE" if selectors.mandate_id else "MISSING"
    jurisdiction_context_status = "AVAILABLE" if selectors.jurisdiction else "MISSING"

    missing_context: list[str] = []
    if client_context_status == "MISSING":
        missing_context.append("CLIENT_CONTEXT")
    if mandate_context_status == "MISSING":
        missing_context.append("MANDATE_CONTEXT")
    if jurisdiction_context_status == "MISSING":
        missing_context.append("JURISDICTION")

    return {
        "input_mode": input_mode,
        "context_source": resolution_source,
        "client_context_status": client_context_status,
        "mandate_context_status": mandate_context_status,
        "jurisdiction_context_status": jurisdiction_context_status,
        "household_id": selectors.household_id,
        "mandate_id": selectors.mandate_id,
        "jurisdiction": selectors.jurisdiction,
        "benchmark_id": selectors.benchmark_id,
        "missing_context": missing_context,
    }
