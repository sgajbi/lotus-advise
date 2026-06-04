from typing import Literal

from pydantic import BaseModel, Field

from src.integrations.lotus_core import CONTROLLED_LOCAL_SIMULATION_FALLBACK

ConsumerSystem = Literal["lotus-gateway", "lotus-performance", "UI", "UNKNOWN"]


class FeatureCapability(BaseModel):
    key: str = Field(
        description="Canonical feature key.", examples=["advisory.proposals.lifecycle"]
    )
    enabled: bool = Field(description="Whether this feature is enabled.", examples=[True])
    operational_ready: bool = Field(
        description="Whether the feature is operationally ready in the current runtime posture.",
        examples=[True],
    )
    owner_service: str = Field(
        description="Owning service for this feature.", examples=["ADVISORY"]
    )
    description: str = Field(
        description="Human-readable capability summary.",
        examples=["Advisory proposal lifecycle APIs."],
    )
    fallback_mode: str = Field(
        description="Fallback posture when a required upstream dependency is unavailable.",
        examples=[CONTROLLED_LOCAL_SIMULATION_FALLBACK],
    )
    degraded_reason: str | None = Field(
        default=None,
        description=(
            "Optional degraded-mode reason when the feature is enabled but not fully ready."
        ),
        examples=["LOTUS_AI_DEPENDENCY_UNAVAILABLE"],
    )


class WorkflowCapability(BaseModel):
    workflow_key: str = Field(
        description="Workflow key for feature orchestration.",
        examples=["advisory_proposal_lifecycle"],
    )
    enabled: bool = Field(description="Whether workflow is enabled.", examples=[True])
    operational_ready: bool = Field(
        description="Whether the workflow is operationally ready in the current runtime posture.",
        examples=[False],
    )
    required_features: list[str] = Field(
        default_factory=list,
        description="Feature keys required by this workflow.",
        examples=[["advisory.proposals.lifecycle"]],
    )
    dependency_keys: list[str] = Field(
        default_factory=list,
        description="Dependency keys that materially affect workflow readiness.",
        examples=[["lotus_core"]],
    )
    degraded_reason: str | None = Field(
        default=None,
        description=(
            "Optional degraded-mode reason when the workflow is enabled but not fully ready."
        ),
        examples=["LOTUS_CORE_DEPENDENCY_UNAVAILABLE"],
    )


__all__ = ["ConsumerSystem", "FeatureCapability", "WorkflowCapability"]
