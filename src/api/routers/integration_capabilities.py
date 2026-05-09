import os
from datetime import UTC, date, datetime
from typing import Literal, cast

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.capabilities import build_operational_readiness
from src.api.observability import record_advisory_supportability
from src.api.observability_contracts import ADVISORY_SUPPORTABILITY_METRIC_LABELS
from src.integrations.lotus_core import (
    CONTROLLED_LOCAL_SIMULATION_FALLBACK,
    lotus_core_fallback_mode,
)

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


class DependencyReadiness(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "dependency_key": "lotus_core",
                "service_name": "lotus-core",
                "description": ("Canonical portfolio state and portfolio simulation authority."),
                "base_url_env": "LOTUS_CORE_BASE_URL",
                "configured": True,
                "operational_ready": True,
            }
        }
    }

    dependency_key: str = Field(
        description="Canonical dependency key for the Lotus platform integration seam.",
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
        description="Whether the dependency seam is currently ready for use by lotus-advise.",
        examples=[True],
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
                        "fallback_mode": "CONTROLLED_LOCAL_SIMULATION_FALLBACK",
                    }
                ],
            }
        }
    }

    operational_ready: bool = Field(
        description=(
            "Whether the current lotus-advise runtime has all configured integration seams ready."
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
        description="Lotus platform dependency readiness details for advisory integration seams.",
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
        description="Number of advisory dependency seams evaluated for supportability.",
        examples=[5],
    )
    ready_dependency_count: int = Field(
        ge=0,
        description="Number of advisory dependency seams currently operationally ready.",
        examples=[5],
    )
    degraded_dependency_count: int = Field(
        ge=0,
        description="Number of advisory dependency seams currently degraded.",
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
        description="Operational readiness metadata for Lotus platform dependency seams."
    )
    supportability: AdvisorySupportability = Field(
        description=(
            "Source-backed advisory supportability summary for Gateway and Workbench consumers."
        )
    )


router = APIRouter(tags=["Integration"])


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_advisory_supportability(
    *,
    readiness: dict[str, object],
    lifecycle_enabled: bool,
    features: list[FeatureCapability],
) -> AdvisorySupportability:
    dependency_rows = cast(list[dict[str, object]], readiness["dependencies"])
    dependency_count = len(dependency_rows)
    ready_dependency_count = sum(
        1 for dependency in dependency_rows if bool(dependency["operational_ready"])
    )
    degraded_dependency_count = dependency_count - ready_dependency_count
    enabled_features = [feature for feature in features if feature.enabled]
    ready_feature_count = sum(1 for feature in enabled_features if feature.operational_ready)

    if not lifecycle_enabled:
        state: SupportabilityState = "unsupported"
        reason: SupportabilityReason = "lifecycle_disabled"
        freshness_bucket: FreshnessBucket = "unknown"
    elif degraded_dependency_count > 0 or ready_feature_count < len(enabled_features):
        state = "degraded"
        reason = "dependency_degraded"
        freshness_bucket = "unknown"
    else:
        state = "ready"
        reason = "advisory_ready"
        freshness_bucket = "current"

    supportability = AdvisorySupportability(
        state=state,
        reason=reason,
        freshness_bucket=freshness_bucket,
        dependency_count=dependency_count,
        ready_dependency_count=ready_dependency_count,
        degraded_dependency_count=degraded_dependency_count,
        enabled_feature_count=len(enabled_features),
        ready_feature_count=ready_feature_count,
    )
    record_advisory_supportability(
        state=supportability.state,
        reason=supportability.reason,
        freshness_bucket=supportability.freshness_bucket,
    )
    return supportability


@router.get(
    "/platform/capabilities",
    response_model=IntegrationCapabilitiesResponse,
    summary="Get Integration Capabilities",
    description=(
        "Returns integration capability flags and workflow readiness metadata for "
        "the specified consumer system and tenant."
    ),
    responses={
        200: {
            "description": (
                "Lotus-branded advisory capability contract returned with readiness metadata."
            )
        },
        500: {"description": "Unexpected service error while building capabilities."},
    },
)
async def get_integration_capabilities(
    consumer_system: ConsumerSystem = Query(
        "lotus-gateway",
        description="Consumer system requesting capabilities.",
        examples=["lotus-gateway"],
    ),
    tenant_id: str = Query(
        "default",
        description="Tenant identifier used for policy resolution.",
        examples=["default"],
    ),
) -> IntegrationCapabilitiesResponse:
    lifecycle_enabled = _env_bool("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", True)
    async_enabled = _env_bool("PROPOSAL_ASYNC_OPERATIONS_ENABLED", True)
    ai_rationale_enabled = _env_bool("LOTUS_AI_WORKSPACE_RATIONALE_ENABLED", True)
    readiness = build_operational_readiness()
    dependency_rows = cast(list[dict[str, object]], readiness["dependencies"])
    dependencies = {item["dependency_key"]: item for item in dependency_rows}
    lotus_core_ready = bool(dependencies["lotus_core"]["operational_ready"])
    lotus_risk_ready = bool(dependencies["lotus_risk"]["operational_ready"])
    lotus_ai_ready = bool(dependencies["lotus_ai"]["operational_ready"])
    lotus_report_ready = bool(dependencies["lotus_report"]["operational_ready"])

    features = [
        FeatureCapability(
            key="advisory.proposals.simulation",
            enabled=True,
            operational_ready=lotus_core_ready,
            owner_service="LOTUS_CORE",
            description=(
                "Canonical advisory proposal simulation through lotus-core; "
                "lotus-advise remains the workflow and API owner."
            ),
            fallback_mode=lotus_core_fallback_mode(),
            degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
        ),
        FeatureCapability(
            key="advisory.proposals.lifecycle",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description="Advisory proposal lifecycle APIs.",
            fallback_mode="NONE",
            degraded_reason=None,
        ),
        FeatureCapability(
            key="advisory.proposals.async_operations",
            enabled=async_enabled,
            operational_ready=async_enabled,
            owner_service="ADVISORY",
            description="Async advisory proposal operations.",
            fallback_mode="NONE",
            degraded_reason=None,
        ),
        FeatureCapability(
            key="advisory.workspaces.stateful",
            enabled=True,
            operational_ready=lotus_core_ready,
            owner_service="ADVISORY",
            description=(
                "Stateful advisory workspace evaluation through Lotus Core context resolution."
            ),
            fallback_mode=lotus_core_fallback_mode(),
            degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
        ),
        FeatureCapability(
            key="advisory.workspaces.ai_rationale",
            enabled=ai_rationale_enabled,
            operational_ready=ai_rationale_enabled and lotus_ai_ready,
            owner_service="ADVISORY",
            description="Evidence-grounded advisory workspace rationale through Lotus AI.",
            fallback_mode="NONE",
            degraded_reason=(
                None
                if not ai_rationale_enabled or lotus_ai_ready
                else "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        FeatureCapability(
            key="advisory.proposals.risk_lens",
            enabled=True,
            operational_ready=lotus_risk_ready,
            owner_service="LOTUS_RISK",
            description="Proposal before/after concentration risk lens through lotus-risk.",
            fallback_mode="LOCAL_RISK_FALLBACK",
            degraded_reason=(None if lotus_risk_ready else "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"),
        ),
        FeatureCapability(
            key="advisory.proposals.reporting",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_report_ready,
            owner_service="LOTUS_REPORT",
            description="Advisory proposal report-request seam through lotus-report.",
            fallback_mode="NONE",
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_report_ready
                else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        FeatureCapability(
            key="advisory.proposals.execution_handoff",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description="Advisory execution handoff and execution-state correlation APIs.",
            fallback_mode="NONE",
            degraded_reason=None,
        ),
        FeatureCapability(
            key="advise.observability.advisory_supportability",
            enabled=True,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description=(
                "Source-backed advisory supportability posture for Gateway and Workbench consumers."
            ),
            fallback_mode="NONE",
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
    ]

    return IntegrationCapabilitiesResponse(
        contract_version="v1",
        source_service="lotus-advise",
        consumer_system=consumer_system,
        tenant_id=tenant_id,
        generated_at=datetime.now(UTC),
        as_of_date=date.today(),
        policy_version="advisory.v1",
        supported_input_modes=["stateless", "stateful"],
        features=features,
        workflows=[
            WorkflowCapability(
                workflow_key="advisory_proposal_simulation",
                enabled=True,
                operational_ready=lotus_core_ready,
                required_features=["advisory.proposals.simulation"],
                dependency_keys=["lotus_core"],
                degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
            ),
            WorkflowCapability(
                workflow_key="advisory_proposal_lifecycle",
                enabled=lifecycle_enabled,
                operational_ready=lifecycle_enabled,
                required_features=["advisory.proposals.lifecycle"],
                dependency_keys=[],
                degraded_reason=None,
            ),
            WorkflowCapability(
                workflow_key="advisory_workspace_stateful",
                enabled=True,
                operational_ready=lotus_core_ready,
                required_features=["advisory.workspaces.stateful"],
                dependency_keys=["lotus_core"],
                degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
            ),
            WorkflowCapability(
                workflow_key="advisory_workspace_ai_rationale",
                enabled=ai_rationale_enabled,
                operational_ready=ai_rationale_enabled and lotus_ai_ready,
                required_features=["advisory.workspaces.ai_rationale"],
                dependency_keys=["lotus_ai"],
                degraded_reason=(
                    None
                    if not ai_rationale_enabled or lotus_ai_ready
                    else "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
                ),
            ),
            WorkflowCapability(
                workflow_key="advisory_proposal_risk_lens",
                enabled=True,
                operational_ready=lotus_risk_ready,
                required_features=["advisory.proposals.risk_lens"],
                dependency_keys=["lotus_risk"],
                degraded_reason=(None if lotus_risk_ready else "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"),
            ),
            WorkflowCapability(
                workflow_key="advisory_proposal_reporting",
                enabled=lifecycle_enabled,
                operational_ready=lifecycle_enabled and lotus_report_ready,
                required_features=["advisory.proposals.reporting"],
                dependency_keys=["lotus_report"],
                degraded_reason=(
                    None
                    if not lifecycle_enabled or lotus_report_ready
                    else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
                ),
            ),
            WorkflowCapability(
                workflow_key="advisory_proposal_execution_handoff",
                enabled=lifecycle_enabled,
                operational_ready=lifecycle_enabled,
                required_features=["advisory.proposals.execution_handoff"],
                dependency_keys=[],
                degraded_reason=None,
            ),
        ],
        readiness=OperationalReadiness.model_validate(readiness),
        supportability=_build_advisory_supportability(
            readiness=readiness,
            lifecycle_enabled=lifecycle_enabled,
            features=features,
        ),
    )
