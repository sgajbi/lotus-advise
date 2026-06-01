from __future__ import annotations

from fastapi import Depends, status

from src.api.proposals import router as shared
from src.api.proposals.cockpit_dependencies import get_advisor_cockpit_service
from src.api.proposals.cockpit_parameters import (
    AdvisorCockpitAcknowledgementIdempotencyKeyHeader,
    AdvisorCockpitActionCursorQuery,
    AdvisorCockpitActionItemIdPath,
    AdvisorCockpitActionLimitQuery,
    AdvisorCockpitAdvisorIdQuery,
    AdvisorCockpitCallerRoleQuery,
    AdvisorCockpitCorrelationIdHeader,
    AdvisorCockpitPortfolioIdQuery,
    AdvisorCockpitPreparationPacketCursorQuery,
)
from src.api.proposals.cockpit_responses import (
    ADVISOR_COCKPIT_ACKNOWLEDGEMENT_RESPONSES,
    ADVISOR_COCKPIT_READ_RESPONSES,
)
from src.api.proposals.errors import run_proposal_operation
from src.core.advisor_cockpit import (
    AdvisorCockpitAcknowledgeRequest,
    AdvisorCockpitAcknowledgeResponse,
    AdvisorCockpitCallerRole,
    AdvisorCockpitPreparationPacketPage,
    AdvisorCockpitService,
    AdvisorCockpitSnapshotResponse,
    AdvisorCockpitSupportabilityResponse,
    AdvisoryActionItem,
    AdvisoryActionItemPage,
    CockpitCallerContext,
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
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    advisor_id: AdvisorCockpitAdvisorIdQuery = None,
    role: AdvisorCockpitCallerRoleQuery = "ADVISOR",
    limit: AdvisorCockpitActionLimitQuery = 25,
    cursor: AdvisorCockpitActionCursorQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisoryActionItemPage:
    return run_proposal_operation(
        lambda: service.list_actions(
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
            limit=limit,
            cursor=cursor,
            correlation_id=correlation_id,
        )
    )


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
    action_item_id: AdvisorCockpitActionItemIdPath,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    advisor_id: AdvisorCockpitAdvisorIdQuery = None,
    role: AdvisorCockpitCallerRoleQuery = "ADVISOR",
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisoryActionItem:
    return run_proposal_operation(
        lambda: service.get_action(
            action_item_id=action_item_id,
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
    )


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
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    advisor_id: AdvisorCockpitAdvisorIdQuery = None,
    role: AdvisorCockpitCallerRoleQuery = "ADVISOR",
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
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
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    advisor_id: AdvisorCockpitAdvisorIdQuery = None,
    role: AdvisorCockpitCallerRoleQuery = "ADVISOR",
    limit: AdvisorCockpitActionLimitQuery = 25,
    cursor: AdvisorCockpitPreparationPacketCursorQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitPreparationPacketPage:
    return run_proposal_operation(
        lambda: service.list_preparation_packets(
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
            limit=limit,
            cursor=cursor,
            correlation_id=correlation_id,
        )
    )


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
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    advisor_id: AdvisorCockpitAdvisorIdQuery = None,
    role: AdvisorCockpitCallerRoleQuery = "ADVISOR",
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
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
    action_item_id: AdvisorCockpitActionItemIdPath,
    payload: AdvisorCockpitAcknowledgeRequest,
    idempotency_key: AdvisorCockpitAcknowledgementIdempotencyKeyHeader,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    advisor_id: AdvisorCockpitAdvisorIdQuery = None,
    role: AdvisorCockpitCallerRoleQuery = "ADVISOR",
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitAcknowledgeResponse:
    return run_proposal_operation(
        lambda: service.acknowledge_action(
            action_item_id=action_item_id,
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            caller_context=_caller_context(advisor_id=advisor_id, role=role),
            portfolio_id=portfolio_id,
        )
    )


def _caller_context(
    *, advisor_id: str | None, role: AdvisorCockpitCallerRole
) -> CockpitCallerContext:
    return CockpitCallerContext(
        advisor_id=advisor_id,
        role=role,
    )
