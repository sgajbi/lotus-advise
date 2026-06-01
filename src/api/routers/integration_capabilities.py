from fastapi import APIRouter, Query

from src.api.capabilities import (
    ConsumerSystem,
    IntegrationCapabilitiesResponse,
    build_integration_capabilities,
)
from src.api.routers.integration_capabilities_responses import INTEGRATION_CAPABILITIES_RESPONSES

router = APIRouter(tags=["Integration"])


@router.get(
    "/platform/capabilities",
    response_model=IntegrationCapabilitiesResponse,
    summary="Get Integration Capabilities",
    description=(
        "Returns integration capability flags and workflow readiness metadata for "
        "the specified consumer system and tenant."
    ),
    responses=INTEGRATION_CAPABILITIES_RESPONSES,
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
    return build_integration_capabilities(
        consumer_system=consumer_system,
        tenant_id=tenant_id,
    )
