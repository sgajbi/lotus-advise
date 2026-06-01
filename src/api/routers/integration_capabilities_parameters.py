from __future__ import annotations

from typing import Annotated

from fastapi import Query

from src.api.capabilities import ConsumerSystem

IntegrationConsumerSystemQuery = Annotated[
    ConsumerSystem,
    Query(
        description="Consumer system requesting capabilities.",
        examples=["lotus-gateway"],
    ),
]

IntegrationTenantIdQuery = Annotated[
    str,
    Query(
        description="Tenant identifier used for policy resolution.",
        examples=["default"],
    ),
]
