from fastapi import APIRouter

from src.api.capabilities import (
    IntegrationCapabilitiesResponse,
    build_integration_capabilities,
)
from src.api.routers.integration_capabilities_parameters import (
    IntegrationConsumerSystemQuery,
)
from src.api.routers.integration_capabilities_responses import INTEGRATION_CAPABILITIES_RESPONSES

router = APIRouter(tags=["Integration"])


@router.get(
    "/platform/capabilities",
    response_model=IntegrationCapabilitiesResponse,
    summary="Get Integration Capabilities",
    description=(
        "Returns deployment-scoped integration capability flags and workflow readiness metadata "
        "for a bounded consumer-system view. Tenant-specific entitlement decisions are not "
        "published by this discovery endpoint."
    ),
    responses=INTEGRATION_CAPABILITIES_RESPONSES,
)
async def get_integration_capabilities(
    consumer_system: IntegrationConsumerSystemQuery = "lotus-gateway",
) -> IntegrationCapabilitiesResponse:
    return build_integration_capabilities(
        consumer_system=consumer_system,
    )
