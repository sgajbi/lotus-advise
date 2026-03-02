import os
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

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


class IntegrationCapabilitiesResponse(BaseModel):
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
        200: {"description": "Integration capabilities returned."},
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
    )
