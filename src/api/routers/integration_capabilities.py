import os
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

ConsumerSystem = Literal["BFF", "PA", "DPM", "UI", "UNKNOWN"]


class FeatureCapability(BaseModel):
    key: str = Field(description="Canonical feature key.")
    enabled: bool = Field(description="Whether this feature is enabled.")
    owner_service: str = Field(description="Owning service for this feature.")
    description: str = Field(description="Human-readable capability summary.")


class WorkflowCapability(BaseModel):
    workflow_key: str = Field(description="Workflow key for feature orchestration.")
    enabled: bool = Field(description="Whether workflow is enabled.")
    required_features: list[str] = Field(
        default_factory=list,
        description="Feature keys required for this workflow.",
    )


class IntegrationCapabilitiesResponse(BaseModel):
    contract_version: str = Field(alias="contractVersion")
    source_service: str = Field(alias="sourceService")
    consumer_system: ConsumerSystem = Field(alias="consumerSystem")
    tenant_id: str = Field(alias="tenantId")
    generated_at: datetime = Field(alias="generatedAt")
    as_of_date: date = Field(alias="asOfDate")
    policy_version: str = Field(alias="policyVersion")
    supported_input_modes: list[str] = Field(alias="supportedInputModes")
    features: list[FeatureCapability]
    workflows: list[WorkflowCapability]

    model_config = {"populate_by_name": True}


router = APIRouter(tags=["Integration"])


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@router.get(
    "/integration/capabilities",
    response_model=IntegrationCapabilitiesResponse,
    summary="Get DPM Integration Capabilities",
    description=(
        "Returns backend-driven DPM capability/workflow controls for BFF, PAS, and UI integration."
    ),
)
async def get_integration_capabilities(
    consumer_system: ConsumerSystem = Query("BFF", alias="consumerSystem"),
    tenant_id: str = Query("default", alias="tenantId"),
) -> IntegrationCapabilitiesResponse:
    proposal_lifecycle_enabled = _env_bool("DPM_CAP_PROPOSAL_LIFECYCLE_ENABLED", True)
    run_support_enabled = _env_bool("DPM_CAP_RUN_SUPPORT_ENABLED", True)
    workflow_enabled = _env_bool(
        "DPM_CAP_WORKFLOW_ENABLED", _env_bool("DPM_WORKFLOW_ENABLED", False)
    )
    async_analysis_enabled = _env_bool("DPM_CAP_ASYNC_ANALYSIS_ENABLED", True)
    pas_ref_mode_enabled = _env_bool("DPM_CAP_INPUT_MODE_PAS_REF_ENABLED", True)
    inline_bundle_mode_enabled = _env_bool("DPM_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED", True)

    features = [
        FeatureCapability(
            key="dpm.proposals.lifecycle",
            enabled=proposal_lifecycle_enabled,
            owner_service="DPM",
            description="Advisory proposal lifecycle APIs.",
        ),
        FeatureCapability(
            key="dpm.support.run_apis",
            enabled=run_support_enabled,
            owner_service="DPM",
            description="DPM supportability and lineage APIs.",
        ),
        FeatureCapability(
            key="dpm.workflow.approval_gates",
            enabled=workflow_enabled,
            owner_service="DPM",
            description="Approval workflow gates for rebalance/proposal lifecycle.",
        ),
        FeatureCapability(
            key="dpm.analysis.async",
            enabled=async_analysis_enabled,
            owner_service="DPM",
            description="Asynchronous scenario analysis execution APIs.",
        ),
        FeatureCapability(
            key="dpm.execution.stateful_pas_ref",
            enabled=pas_ref_mode_enabled,
            owner_service="DPM",
            description="DPM resolves core inputs from PAS API contracts.",
        ),
        FeatureCapability(
            key="dpm.execution.stateless_inline_bundle",
            enabled=inline_bundle_mode_enabled,
            owner_service="DPM",
            description="DPM executes simulation from request-supplied inline input bundle.",
        ),
    ]

    workflows = [
        WorkflowCapability(
            workflow_key="proposal_lifecycle",
            enabled=proposal_lifecycle_enabled,
            required_features=["dpm.proposals.lifecycle"],
        ),
        WorkflowCapability(
            workflow_key="proposal_approval_flow",
            enabled=proposal_lifecycle_enabled and workflow_enabled,
            required_features=["dpm.proposals.lifecycle", "dpm.workflow.approval_gates"],
        ),
        WorkflowCapability(
            workflow_key="rebalance_async_analysis",
            enabled=async_analysis_enabled,
            required_features=["dpm.analysis.async"],
        ),
        WorkflowCapability(
            workflow_key="execution_stateful_pas_ref",
            enabled=pas_ref_mode_enabled,
            required_features=["dpm.execution.stateful_pas_ref"],
        ),
        WorkflowCapability(
            workflow_key="execution_stateless_inline_bundle",
            enabled=inline_bundle_mode_enabled,
            required_features=["dpm.execution.stateless_inline_bundle"],
        ),
    ]

    supported_input_modes: list[str] = []
    if pas_ref_mode_enabled:
        supported_input_modes.append("pas_ref")
    if inline_bundle_mode_enabled:
        supported_input_modes.append("inline_bundle")

    return IntegrationCapabilitiesResponse(
        contractVersion="v1",
        sourceService="lotus-advise",
        consumerSystem=consumer_system,
        tenantId=tenant_id,
        generatedAt=datetime.now(UTC),
        asOfDate=date.today(),
        policyVersion=os.getenv("DPM_POLICY_VERSION", "tenant-default-v1"),
        supportedInputModes=supported_input_modes,
        features=features,
        workflows=workflows,
    )

