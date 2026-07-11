from __future__ import annotations

from typing import Annotated

from fastapi import Query

from src.api.capabilities import ConsumerSystem

IntegrationConsumerSystemQuery = Annotated[
    ConsumerSystem,
    Query(
        description=(
            "Bounded consumer-system view for deployment-scoped capability discovery. This value "
            "is not an authenticated caller identity or tenant entitlement decision."
        ),
        examples=["lotus-gateway"],
    ),
]
