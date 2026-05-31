from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, Path, Query, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.proposals import router as shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.core.advisor_cockpit import (
    AdvisorCockpitAcknowledgeRequest,
    AdvisorCockpitAcknowledgeResponse,
    AdvisorCockpitCallerRole,
    AdvisorCockpitPreparationPacketPage,
    AdvisorCockpitRepository,
    AdvisorCockpitService,
    AdvisorCockpitSnapshotResponse,
    AdvisorCockpitSupportabilityResponse,
    AdvisoryActionItem,
    AdvisoryActionItemPage,
    CockpitCallerContext,
)
from src.core.advisor_cockpit.pagination import COCKPIT_ACTION_MAX_PAGE_SIZE
from src.core.advisor_cockpit.projection_bounds import COCKPIT_IDENTIFIER_MAX_LENGTH
from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)

ADVISOR_COCKPIT_READ_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {
        "description": "Advisor cockpit action item was not found for the supplied scope."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Advisor cockpit request failed validation, including invalid cursors."
    },
}

ADVISOR_COCKPIT_ACKNOWLEDGEMENT_RESPONSES = {
    **ADVISOR_COCKPIT_READ_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": ("Idempotency key was reused with a different acknowledgement request.")
    },
}


def get_advisor_cockpit_service() -> AdvisorCockpitService:
    return AdvisorCockpitService(
        repository=cast(AdvisorCockpitRepository, shared.get_proposal_repository())
    )


@shared.router.get(
    "/advisory/cockpit/actions",
    response_model=AdvisoryActionItemPage,
    status_code=status.HTTP_200_OK,
    tags=["Advisor Cockpit"],
    summary="List Advisor Cockpit Actions",
    description=(
        "Lists Advise-owned cockpit action items derived from source-backed proposal, policy, "
        "memo, supportability, and unsupported-capability evidence. Gateway and Workbench must "
        "render these semantics rather than reconstructing advisory policy or memo meaning."
    ),
    responses=ADVISOR_COCKPIT_READ_RESPONSES,
)
def list_advisor_cockpit_actions(
    portfolio_id: Annotated[
        str | None,
        Query(
            description="Optional portfolio scope for cockpit actions.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ] = None,
    advisor_id: Annotated[
        str | None,
        Query(
            description="Optional advisor actor scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["advisor_sg_001"],
        ),
    ] = None,
    role: Annotated[
        AdvisorCockpitCallerRole,
        Query(
            description=(
                "Caller role for server-side projection. `DPM_OWNER` is accepted only as a "
                "legacy caller alias and is projected to `PORTFOLIO_MANAGER` owned actions."
            ),
            examples=["ADVISOR"],
        ),
    ] = "ADVISOR",
    limit: Annotated[
        int,
        Query(
            description="Bounded page size. Default is 25; maximum is 100.",
            ge=1,
            le=COCKPIT_ACTION_MAX_PAGE_SIZE,
        ),
    ] = 25,
    cursor: Annotated[
        str | None,
        Query(
            description="Opaque action cursor from a previous page.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Optional correlation id propagated into returned action items.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisoryActionItemPage:
    try:
        return service.list_actions(
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
            limit=limit,
            cursor=cursor,
            correlation_id=correlation_id,
        )
    except (ProposalValidationError, ProposalNotFoundError) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/cockpit/actions/{action_item_id}",
    response_model=AdvisoryActionItem,
    status_code=status.HTTP_200_OK,
    tags=["Advisor Cockpit"],
    summary="Get Advisor Cockpit Action",
    description=(
        "Returns one source-backed Advise-owned cockpit action item with reason codes, owner "
        "role, evidence refs, lineage refs, dependency posture, and unsupported capability "
        "boundaries."
    ),
    responses=ADVISOR_COCKPIT_READ_RESPONSES,
)
def get_advisor_cockpit_action(
    action_item_id: Annotated[
        str,
        Path(
            description="Advisor cockpit action item identifier.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ],
    portfolio_id: Annotated[
        str | None,
        Query(
            description="Optional portfolio scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ] = None,
    advisor_id: Annotated[
        str | None,
        Query(
            description="Optional advisor actor scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["advisor_sg_001"],
        ),
    ] = None,
    role: Annotated[
        AdvisorCockpitCallerRole,
        Query(
            description=(
                "Caller role. `DPM_OWNER` is accepted only as a legacy caller alias and is "
                "projected to `PORTFOLIO_MANAGER` owned actions."
            ),
            examples=["ADVISOR"],
        ),
    ] = "ADVISOR",
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Optional correlation id.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisoryActionItem:
    try:
        return service.get_action(
            action_item_id=action_item_id,
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
    except (ProposalValidationError, ProposalNotFoundError) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/cockpit/snapshot",
    response_model=AdvisorCockpitSnapshotResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisor Cockpit"],
    summary="Get Advisor Cockpit Snapshot",
    description=(
        "Returns a bounded Advise-owned cockpit operating snapshot with action counts, top "
        "priority actions, unsupported capability boundaries, and supportability posture."
    ),
    responses=ADVISOR_COCKPIT_READ_RESPONSES,
)
def get_advisor_cockpit_snapshot(
    portfolio_id: Annotated[
        str | None,
        Query(
            description="Optional portfolio scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ] = None,
    advisor_id: Annotated[
        str | None,
        Query(
            description="Optional advisor actor scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["advisor_sg_001"],
        ),
    ] = None,
    role: Annotated[
        AdvisorCockpitCallerRole,
        Query(
            description=(
                "Caller role. `DPM_OWNER` is accepted only as a legacy caller alias and is "
                "projected to `PORTFOLIO_MANAGER` owned actions."
            ),
            examples=["ADVISOR"],
        ),
    ] = "ADVISOR",
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Optional correlation id.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitSnapshotResponse:
    return service.get_snapshot(
        caller_context=_caller_context(advisor_id=advisor_id, role=role),
        portfolio_id=portfolio_id,
        correlation_id=correlation_id,
    )


@shared.router.get(
    "/advisory/cockpit/preparation-packets",
    response_model=AdvisorCockpitPreparationPacketPage,
    status_code=status.HTTP_200_OK,
    tags=["Advisor Cockpit"],
    summary="List Advisor Cockpit Preparation Packets",
    description=(
        "Lists source-backed meeting-preparation packets projected by Lotus Advise from "
        "proposal lifecycle evidence. The endpoint exposes support-safe advisor preparation "
        "context only; Gateway and Workbench must render these packets without reconstructing "
        "advisory suitability, memo, narrative, policy, CRM, calendar, or client communication "
        "semantics locally."
    ),
    responses=ADVISOR_COCKPIT_READ_RESPONSES,
)
def list_advisor_cockpit_preparation_packets(
    portfolio_id: Annotated[
        str | None,
        Query(
            description="Optional portfolio scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ] = None,
    advisor_id: Annotated[
        str | None,
        Query(
            description="Optional advisor actor scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["advisor_sg_001"],
        ),
    ] = None,
    role: Annotated[
        AdvisorCockpitCallerRole,
        Query(
            description=(
                "Caller role. `DPM_OWNER` is accepted only as a legacy caller alias and is "
                "projected to `PORTFOLIO_MANAGER` owned actions."
            ),
            examples=["ADVISOR"],
        ),
    ] = "ADVISOR",
    limit: Annotated[
        int,
        Query(
            description="Bounded page size. Default is 25; maximum is 100.",
            ge=1,
            le=COCKPIT_ACTION_MAX_PAGE_SIZE,
        ),
    ] = 25,
    cursor: Annotated[
        str | None,
        Query(
            description="Opaque preparation-packet cursor from a previous page.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Optional correlation id.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitPreparationPacketPage:
    try:
        return service.list_preparation_packets(
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
            limit=limit,
            cursor=cursor,
            correlation_id=correlation_id,
        )
    except (ProposalValidationError, ProposalNotFoundError) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/cockpit/supportability",
    response_model=AdvisorCockpitSupportabilityResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisor Cockpit"],
    summary="Get Advisor Cockpit Supportability",
    description=(
        "Returns support-safe Advise cockpit runtime posture, including Advise API support, "
        "Gateway publication, Workbench canonical proof, active data-product posture, and the "
        "client-ready, external communication, CRM, OMS, and completed approval boundaries."
    ),
    responses=ADVISOR_COCKPIT_READ_RESPONSES,
)
def get_advisor_cockpit_supportability(
    portfolio_id: Annotated[
        str | None,
        Query(
            description="Optional portfolio scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ] = None,
    advisor_id: Annotated[
        str | None,
        Query(
            description="Optional advisor actor scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["advisor_sg_001"],
        ),
    ] = None,
    role: Annotated[
        AdvisorCockpitCallerRole,
        Query(
            description=(
                "Caller role. `DPM_OWNER` is accepted only as a legacy caller alias and is "
                "projected to `PORTFOLIO_MANAGER` owned actions."
            ),
            examples=["ADVISOR"],
        ),
    ] = "ADVISOR",
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Optional correlation id.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitSupportabilityResponse:
    return service.get_supportability(
        caller_context=_caller_context(advisor_id=advisor_id, role=role),
        portfolio_id=portfolio_id,
        correlation_id=correlation_id,
    )


@shared.router.post(
    "/advisory/cockpit/actions/{action_item_id}/acknowledgements",
    response_model=AdvisorCockpitAcknowledgeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisor Cockpit"],
    summary="Acknowledge Advisor Cockpit Action",
    description=(
        "Records an idempotent acknowledgement for an Advise-owned cockpit action item. "
        "Acknowledgement does not clear blocking policy, memo, supportability, or owner-role "
        "posture; it only records that the actor has seen the action."
    ),
    responses=ADVISOR_COCKPIT_ACKNOWLEDGEMENT_RESPONSES,
)
def acknowledge_advisor_cockpit_action(
    action_item_id: Annotated[
        str,
        Path(
            description="Advisor cockpit action item identifier.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ],
    payload: AdvisorCockpitAcknowledgeRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required replay-safe acknowledgement idempotency key.",
            max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
            examples=["ack-cockpit-action-001"],
        ),
    ],
    portfolio_id: Annotated[
        str | None,
        Query(
            description="Optional portfolio scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["PB_SG_GLOBAL_BAL_001"],
        ),
    ] = None,
    advisor_id: Annotated[
        str | None,
        Query(
            description="Optional advisor actor scope.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
            examples=["advisor_sg_001"],
        ),
    ] = None,
    role: Annotated[
        AdvisorCockpitCallerRole,
        Query(
            description=(
                "Caller role. `DPM_OWNER` is accepted only as a legacy caller alias and is "
                "projected to `PORTFOLIO_MANAGER` owned actions."
            ),
            examples=["ADVISOR"],
        ),
    ] = "ADVISOR",
    correlation_id: Annotated[
        str | None,
        Header(
            alias="X-Correlation-ID",
            description="Optional correlation id.",
            max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        ),
    ] = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitAcknowledgeResponse:
    try:
        return service.acknowledge_action(
            action_item_id=action_item_id,
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)


def _caller_context(
    *, advisor_id: str | None, role: AdvisorCockpitCallerRole
) -> CockpitCallerContext:
    return CockpitCallerContext(
        advisor_id=advisor_id,
        role=role,
    )
