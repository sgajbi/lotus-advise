from __future__ import annotations

from dataclasses import dataclass

from src.api.runtime_flags import env_flag


@dataclass(frozen=True)
class CapabilityRuntimeFlags:
    lifecycle_enabled: bool
    async_enabled: bool
    ai_rationale_enabled: bool


def resolve_capability_runtime_flags() -> CapabilityRuntimeFlags:
    return CapabilityRuntimeFlags(
        lifecycle_enabled=env_flag("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", True),
        async_enabled=env_flag("PROPOSAL_ASYNC_OPERATIONS_ENABLED", True),
        ai_rationale_enabled=env_flag("LOTUS_AI_WORKSPACE_RATIONALE_ENABLED", True),
    )


__all__ = ["CapabilityRuntimeFlags", "resolve_capability_runtime_flags"]
