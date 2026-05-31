from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.api.observability_contracts import ADVISORY_SUPPORTABILITY_METRIC_LABELS
from src.integrations.lotus_core import CONTROLLED_LOCAL_SIMULATION_FALLBACK

ConsumerSystem = Literal["lotus-gateway", "lotus-performance", "UI", "UNKNOWN"]
ReadinessBasis = Literal[
    "not_configured",
    "invalid_configuration",
    "configuration_only",
    "probe_succeeded",
    "probe_failed",
]


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


class DependencyReadiness(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "dependency_key": "lotus_core",
                "service_name": "lotus-core",
                "description": "Canonical portfolio state and portfolio simulation authority.",
                "base_url_env": "LOTUS_CORE_BASE_URL",
                "configured": True,
                "operational_ready": True,
                "runtime_probe_enabled": True,
                "readiness_basis": "probe_succeeded",
                "degraded_reason": None,
                "fallback_mode": "NONE",
            }
        }
    }

    dependency_key: str = Field(
        description="Canonical dependency key for the Lotus platform integration boundary.",
        examples=["lotus_core"],
    )
    service_name: str = Field(
        description="Lotus service name for the dependency.",
        examples=["lotus-core"],
    )
    description: str = Field(
        description="Lotus-branded summary of what this dependency provides.",
        examples=["Canonical portfolio state and portfolio simulation authority."],
    )
    base_url_env: str = Field(
        description="Environment variable used to configure the dependency base URL.",
        examples=["LOTUS_CORE_BASE_URL"],
    )
    configured: bool = Field(
        description="Whether the dependency base URL is configured for this lotus-advise runtime.",
        examples=[True],
    )
    operational_ready: bool = Field(
        description="Whether the dependency boundary is currently ready for use by lotus-advise.",
        examples=[True],
    )
    runtime_probe_enabled: bool = Field(
        description=(
            "Whether this readiness decision used runtime health probing instead of "
            "configuration-only posture."
        ),
        examples=[True],
    )
    readiness_basis: ReadinessBasis = Field(
        description=(
            "Bounded evidence basis for the readiness decision: missing configuration, "
            "configuration-only non-production posture, successful runtime probe, or failed "
            "runtime probe. Invalid configuration is reported separately when a dependency URL "
            "is present but unusable."
        ),
        examples=["probe_succeeded"],
    )
    degraded_reason: str | None = Field(
        default=None,
        description=(
            "Bounded dependency-level degraded reason when this integration boundary is not "
            "operationally ready."
        ),
        examples=["LOTUS_CORE_DEPENDENCY_UNAVAILABLE"],
    )
    fallback_mode: str = Field(
        description="Fallback posture used when the dependency is unavailable.",
        examples=[CONTROLLED_LOCAL_SIMULATION_FALLBACK],
    )


class OperationalReadiness(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "operational_ready": False,
                "degraded": True,
                "degraded_reasons": ["LOTUS_CORE_DEPENDENCY_UNAVAILABLE"],
                "dependencies": [
                    {
                        "dependency_key": "lotus_core",
                        "service_name": "lotus-core",
                        "description": (
                            "Canonical portfolio state and portfolio simulation authority."
                        ),
                        "base_url_env": "LOTUS_CORE_BASE_URL",
                        "configured": False,
                        "operational_ready": False,
                        "runtime_probe_enabled": False,
                        "readiness_basis": "not_configured",
                        "degraded_reason": "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
                        "fallback_mode": "CONTROLLED_LOCAL_SIMULATION_FALLBACK",
                    }
                ],
            }
        }
    }

    operational_ready: bool = Field(
        description=(
            "Whether the current lotus-advise runtime has all configured integration boundaries "
            "ready."
        ),
        examples=[False],
    )
    degraded: bool = Field(
        description="Whether lotus-advise is running in a degraded integration posture.",
        examples=[True],
    )
    degraded_reasons: list[str] = Field(
        default_factory=list,
        description="Structured reasons describing why the runtime is degraded.",
        examples=[["LOTUS_CORE_DEPENDENCY_UNAVAILABLE"]],
    )
    dependencies: list[DependencyReadiness] = Field(
        default_factory=list,
        description=(
            "Lotus platform dependency readiness details for advisory integration boundaries."
        ),
    )


SupportabilityState = Literal["ready", "degraded", "stale", "empty", "unsupported"]
SupportabilityReason = Literal[
    "advisory_ready",
    "dependency_degraded",
    "lifecycle_disabled",
    "supportability_unsupported",
]
FreshnessBucket = Literal["current", "stale", "unknown"]


class AdvisorySupportability(BaseModel):
    state: SupportabilityState = Field(
        description="Source-backed advisory supportability state for UI-facing advisory workflows.",
        examples=["ready"],
    )
    reason: SupportabilityReason = Field(
        description="Bounded reason code explaining the advisory supportability state.",
        examples=["advisory_ready"],
    )
    freshness_bucket: FreshnessBucket = Field(
        description="Bounded freshness bucket for advisory dependency and lifecycle posture.",
        examples=["current"],
    )
    metric_labels: tuple[str, ...] = Field(
        default=ADVISORY_SUPPORTABILITY_METRIC_LABELS,
        description=(
            "Prometheus labels emitted by lotus_advise_advisory_supportability_total. "
            "The tuple is intentionally bounded and excludes portfolio, client, request, "
            "response, correlation, trace, transaction, security, proposal, workspace, and "
            "payload identifiers."
        ),
        examples=[list(ADVISORY_SUPPORTABILITY_METRIC_LABELS)],
    )
    dependency_count: int = Field(
        ge=0,
        description="Number of advisory dependency boundaries evaluated for supportability.",
        examples=[5],
    )
    ready_dependency_count: int = Field(
        ge=0,
        description="Number of advisory dependency boundaries currently operationally ready.",
        examples=[5],
    )
    degraded_dependency_count: int = Field(
        ge=0,
        description="Number of advisory dependency boundaries currently degraded.",
        examples=[0],
    )
    enabled_feature_count: int = Field(
        ge=0,
        description="Number of advisory features enabled in the current runtime policy.",
        examples=[8],
    )
    ready_feature_count: int = Field(
        ge=0,
        description="Number of enabled advisory features currently operationally ready.",
        examples=[8],
    )


class IntegrationCapabilitiesResponse(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "contract_version": "v1",
                "source_service": "lotus-advise",
                "consumer_system": "lotus-gateway",
                "tenant_id": "default",
                "generated_at": "2026-03-25T00:00:00Z",
                "as_of_date": "2026-03-25",
                "policy_version": "advisory.v1",
                "supported_input_modes": ["stateless", "stateful"],
                "features": [
                    {
                        "key": "advisory.proposals.lifecycle",
                        "enabled": True,
                        "operational_ready": True,
                        "owner_service": "ADVISORY",
                        "description": "Advisory proposal lifecycle APIs.",
                        "fallback_mode": "NONE",
                        "degraded_reason": None,
                    }
                ],
                "workflows": [
                    {
                        "workflow_key": "advisory_proposal_lifecycle",
                        "enabled": True,
                        "operational_ready": True,
                        "required_features": ["advisory.proposals.lifecycle"],
                        "dependency_keys": [],
                        "degraded_reason": None,
                    }
                ],
                "readiness": {
                    "operational_ready": False,
                    "degraded": True,
                    "degraded_reasons": ["LOTUS_CORE_DEPENDENCY_UNAVAILABLE"],
                    "dependencies": [
                        {
                            "dependency_key": "lotus_core",
                            "service_name": "lotus-core",
                            "description": (
                                "Canonical portfolio state and portfolio simulation authority."
                            ),
                            "base_url_env": "LOTUS_CORE_BASE_URL",
                            "configured": False,
                            "operational_ready": False,
                            "runtime_probe_enabled": False,
                            "readiness_basis": "not_configured",
                            "degraded_reason": "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
                            "fallback_mode": "CONTROLLED_LOCAL_SIMULATION_FALLBACK",
                        }
                    ],
                },
                "supportability": {
                    "state": "degraded",
                    "reason": "dependency_degraded",
                    "freshness_bucket": "unknown",
                    "dependency_count": 5,
                    "ready_dependency_count": 1,
                    "degraded_dependency_count": 4,
                    "enabled_feature_count": 8,
                    "ready_feature_count": 4,
                },
            }
        }
    }

    contract_version: str = Field(description="Integration contract version.", examples=["v1"])
    source_service: str = Field(
        description="Source service generating this capability contract.",
        examples=["lotus-advise"],
    )
    consumer_system: ConsumerSystem = Field(
        description="Consumer system requesting capabilities.",
        examples=["lotus-gateway"],
    )
    tenant_id: str = Field(
        description="Tenant identifier used for feature policy resolution.",
        examples=["default"],
    )
    generated_at: datetime = Field(
        description="UTC timestamp when capability payload is generated.",
        examples=["2026-03-02T00:00:00Z"],
    )
    as_of_date: date = Field(
        description="Business date that the capability contract applies to.",
        examples=["2026-03-02"],
    )
    policy_version: str = Field(
        description="Capability policy pack version.",
        examples=["advisory.v1"],
    )
    supported_input_modes: list[str] = Field(
        description="Supported request input modes for integrations.",
        examples=[["stateless", "stateful"]],
    )
    features: list[FeatureCapability] = Field(
        description="Feature-level capability flags and ownership."
    )
    workflows: list[WorkflowCapability] = Field(
        description="Workflow-level capability flags and feature dependencies."
    )
    readiness: OperationalReadiness = Field(
        description="Operational readiness metadata for Lotus platform dependency boundaries."
    )
    supportability: AdvisorySupportability = Field(
        description=(
            "Source-backed advisory supportability summary for Gateway and Workbench consumers."
        )
    )
