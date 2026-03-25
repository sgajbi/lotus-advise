import os
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.api.capabilities import build_operational_readiness

ConsumerSystem = Literal["lotus-gateway", "lotus-performance", "UI", "UNKNOWN"]


class FeatureCapability(BaseModel):
    key: str = Field(
        description="Canonical feature key.", examples=["advisory.proposals.lifecycle"]
    )
    enabled: bool = Field(description="Whether this feature is enabled.", examples=[True])
    owner_service: str = Field(
        description="Owning service for this feature.", examples=["ADVISORY"]
    )
    description: str = Field(
        description="Human-readable capability summary.",
        examples=["Advisory proposal lifecycle APIs."],
    )


class WorkflowCapability(BaseModel):
    workflow_key: str = Field(
        description="Workflow key for feature orchestration.",
        examples=["advisory_proposal_lifecycle"],
    )
    enabled: bool = Field(description="Whether workflow is enabled.", examples=[True])
    required_features: list[str] = Field(
        default_factory=list,
        description="Feature keys required by this workflow.",
        examples=[["advisory.proposals.lifecycle"]],
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


class OperationalReadiness(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "operational_ready": False,
                "degraded": True,
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
    dependencies: list[DependencyReadiness] = Field(
        default_factory=list,
        description="Lotus platform dependency readiness details for advisory integration seams.",
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
                "supported_input_modes": ["advisor_input"],
                "features": [
                    {
                        "key": "advisory.proposals.lifecycle",
                        "enabled": True,
                        "owner_service": "ADVISORY",
                        "description": "Advisory proposal lifecycle APIs.",
                    }
                ],
                "workflows": [
                    {
                        "workflow_key": "advisory_proposal_lifecycle",
                        "enabled": True,
                        "required_features": ["advisory.proposals.lifecycle"],
                    }
                ],
                "readiness": {
                    "operational_ready": False,
                    "degraded": True,
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
                        }
                    ],
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
        examples=[["advisor_input"]],
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


router = APIRouter(tags=["Integration"])


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    readiness = build_operational_readiness()

    return IntegrationCapabilitiesResponse(
        contract_version="v1",
        source_service="lotus-advise",
        consumer_system=consumer_system,
        tenant_id=tenant_id,
        generated_at=datetime.now(UTC),
        as_of_date=date.today(),
        policy_version="advisory.v1",
        supported_input_modes=["advisor_input"],
        features=[
            FeatureCapability(
                key="advisory.proposals.lifecycle",
                enabled=lifecycle_enabled,
                owner_service="ADVISORY",
                description="Advisory proposal lifecycle APIs.",
            ),
            FeatureCapability(
                key="advisory.proposals.async_operations",
                enabled=async_enabled,
                owner_service="ADVISORY",
                description="Async advisory proposal operations.",
            ),
        ],
        workflows=[
            WorkflowCapability(
                workflow_key="advisory_proposal_lifecycle",
                enabled=lifecycle_enabled,
                required_features=["advisory.proposals.lifecycle"],
            ),
        ],
        readiness=OperationalReadiness.model_validate(readiness),
    )
