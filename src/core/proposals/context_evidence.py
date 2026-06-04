from __future__ import annotations

from typing import Any

from src.core.advisory.policy_context import build_advisory_policy_context
from src.core.proposals.context_resolution import (
    ResolvedProposalContext,
    ResolvedSimulationContext,
)


def build_context_resolution_evidence(
    resolved: ResolvedProposalContext | ResolvedSimulationContext,
) -> dict[str, Any]:
    return {
        "input_mode": resolved.input_mode,
        "resolution_source": resolved.resolution_source,
        "used_legacy_contract": resolved.used_legacy_contract,
        "resolved_context": resolved.resolved_context.model_dump(mode="json"),
        "advisory_policy_context": build_advisory_policy_context(
            input_mode=resolved.input_mode,
            resolution_source=resolved.resolution_source,
            selectors=resolved.policy_selectors,
        ),
    }


__all__ = ["build_context_resolution_evidence"]
