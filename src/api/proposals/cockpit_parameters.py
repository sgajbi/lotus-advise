from __future__ import annotations

from typing import Annotated

from fastapi import Header, Path, Query

from src.core.advisor_cockpit import AdvisorCockpitCallerRole
from src.core.advisor_cockpit.pagination import COCKPIT_ACTION_MAX_PAGE_SIZE
from src.core.advisor_cockpit.projection_bounds import COCKPIT_IDENTIFIER_MAX_LENGTH
from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH

AdvisorCockpitPortfolioIdQuery = Annotated[
    str | None,
    Query(
        description="Optional portfolio scope.",
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        examples=["PB_SG_GLOBAL_BAL_001"],
    ),
]

AdvisorCockpitAdvisorIdQuery = Annotated[
    str | None,
    Query(
        description="Optional advisor actor scope.",
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        examples=["advisor_sg_001"],
    ),
]

AdvisorCockpitCallerRoleQuery = Annotated[
    AdvisorCockpitCallerRole,
    Query(
        description=(
            "Caller role for server-side projection. `DPM_OWNER` is accepted only as a legacy "
            "caller alias and is projected to `PORTFOLIO_MANAGER` owned actions."
        ),
        examples=["ADVISOR"],
    ),
]

AdvisorCockpitCorrelationIdHeader = Annotated[
    str | None,
    Header(
        alias="X-Correlation-ID",
        description="Optional correlation id propagated into returned cockpit evidence.",
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisorCockpitActionLimitQuery = Annotated[
    int,
    Query(
        description="Bounded page size. Default is 25; maximum is 100.",
        ge=1,
        le=COCKPIT_ACTION_MAX_PAGE_SIZE,
    ),
]

AdvisorCockpitActionCursorQuery = Annotated[
    str | None,
    Query(
        description="Opaque action cursor from a previous page.",
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisorCockpitPreparationPacketCursorQuery = Annotated[
    str | None,
    Query(
        description="Opaque preparation-packet cursor from a previous page.",
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisorCockpitActionItemIdPath = Annotated[
    str,
    Path(
        description="Advisor cockpit action item identifier.",
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
    ),
]

AdvisorCockpitAcknowledgementIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        description="Required replay-safe acknowledgement idempotency key.",
        max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
        examples=["ack-cockpit-action-001"],
    ),
]
