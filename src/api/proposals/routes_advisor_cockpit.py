from __future__ import annotations

from fastapi import Depends, Request, status

from src.api.proposals import router as shared
from src.api.proposals.advisor_cockpit_principal import (
    require_advisor_cockpit_acknowledgement_principal,
    require_advisor_cockpit_read_principal,
)
from src.api.proposals.cockpit_dependencies import get_advisor_cockpit_service
from src.api.proposals.cockpit_parameters import (
    AdvisorCockpitAcknowledgementIdempotencyKeyHeader,
    AdvisorCockpitActionCursorQuery,
    AdvisorCockpitActionItemIdPath,
    AdvisorCockpitActionLimitQuery,
    AdvisorCockpitCorrelationIdHeader,
    AdvisorCockpitPortfolioIdQuery,
    AdvisorCockpitPreparationPacketCursorQuery,
)
from src.api.proposals.cockpit_responses import (
    ADVISOR_COCKPIT_ACKNOWLEDGEMENT_RESPONSES,
    ADVISOR_COCKPIT_READ_RESPONSES,
)
from src.api.proposals.errors import (
    raise_proposal_api_http_exception,
    reject_unexpected_query_params,
    run_proposal_operation,
)
from src.core.advisor_cockpit import (
    AdvisorCockpitAcknowledgeRequest,
    AdvisorCockpitAcknowledgeResponse,
    AdvisorCockpitPreparationPacketPage,
    AdvisorCockpitService,
    AdvisorCockpitSnapshotResponse,
    AdvisorCockpitSupportabilityResponse,
    AdvisoryActionItem,
    AdvisoryActionItemPage,
)
from src.core.advisor_cockpit.caller_authority import (
    ADVISOR_COCKPIT_ACTOR_MISMATCH,
    ADVISOR_COCKPIT_SCOPE_REQUIRED,
    AdvisorCockpitPrincipal,
    authorized_cockpit_portfolio_id,
    bind_cockpit_acknowledgement_payload,
    cockpit_caller_context_from_principal,
)

_READ_QUERY_PARAMS = {"portfolio_id", "limit", "cursor"}
_SCOPED_READ_QUERY_PARAMS = {"portfolio_id"}
_ACKNOWLEDGEMENT_QUERY_PARAMS = {"portfolio_id"}


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
    request: Request,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    limit: AdvisorCockpitActionLimitQuery = 25,
    cursor: AdvisorCockpitActionCursorQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    principal: AdvisorCockpitPrincipal = Depends(require_advisor_cockpit_read_principal),
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisoryActionItemPage:
    reject_unexpected_query_params(request, allowed_params=_READ_QUERY_PARAMS)
    return run_proposal_operation(
        lambda: service.list_actions(
            caller_context=cockpit_caller_context_from_principal(principal),
            portfolio_id=_authorized_portfolio_id(
                principal=principal,
                requested_portfolio_id=portfolio_id,
            ),
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
    request: Request,
    action_item_id: AdvisorCockpitActionItemIdPath,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    principal: AdvisorCockpitPrincipal = Depends(require_advisor_cockpit_read_principal),
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisoryActionItem:
    reject_unexpected_query_params(request, allowed_params=_SCOPED_READ_QUERY_PARAMS)
    return run_proposal_operation(
        lambda: service.get_action(
            action_item_id=action_item_id,
            caller_context=cockpit_caller_context_from_principal(principal),
            portfolio_id=_authorized_portfolio_id(
                principal=principal,
                requested_portfolio_id=portfolio_id,
            ),
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
    request: Request,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    principal: AdvisorCockpitPrincipal = Depends(require_advisor_cockpit_read_principal),
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitSnapshotResponse:
    reject_unexpected_query_params(request, allowed_params=_SCOPED_READ_QUERY_PARAMS)
    return service.get_snapshot(
        caller_context=cockpit_caller_context_from_principal(principal),
        portfolio_id=_authorized_portfolio_id(
            principal=principal,
            requested_portfolio_id=portfolio_id,
        ),
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
    request: Request,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    limit: AdvisorCockpitActionLimitQuery = 25,
    cursor: AdvisorCockpitPreparationPacketCursorQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    principal: AdvisorCockpitPrincipal = Depends(require_advisor_cockpit_read_principal),
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitPreparationPacketPage:
    reject_unexpected_query_params(request, allowed_params=_READ_QUERY_PARAMS)
    return run_proposal_operation(
        lambda: service.list_preparation_packets(
            caller_context=cockpit_caller_context_from_principal(principal),
            portfolio_id=_authorized_portfolio_id(
                principal=principal,
                requested_portfolio_id=portfolio_id,
            ),
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
    request: Request,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    principal: AdvisorCockpitPrincipal = Depends(require_advisor_cockpit_read_principal),
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitSupportabilityResponse:
    reject_unexpected_query_params(request, allowed_params=_SCOPED_READ_QUERY_PARAMS)
    return service.get_supportability(
        caller_context=cockpit_caller_context_from_principal(principal),
        portfolio_id=_authorized_portfolio_id(
            principal=principal,
            requested_portfolio_id=portfolio_id,
        ),
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
    request: Request,
    action_item_id: AdvisorCockpitActionItemIdPath,
    payload: AdvisorCockpitAcknowledgeRequest,
    idempotency_key: AdvisorCockpitAcknowledgementIdempotencyKeyHeader,
    portfolio_id: AdvisorCockpitPortfolioIdQuery = None,
    correlation_id: AdvisorCockpitCorrelationIdHeader = None,
    principal: AdvisorCockpitPrincipal = Depends(require_advisor_cockpit_acknowledgement_principal),
    service: AdvisorCockpitService = Depends(get_advisor_cockpit_service),
) -> AdvisorCockpitAcknowledgeResponse:
    reject_unexpected_query_params(request, allowed_params=_ACKNOWLEDGEMENT_QUERY_PARAMS)
    return run_proposal_operation(
        lambda: service.acknowledge_action(
            action_item_id=action_item_id,
            payload=_trusted_acknowledgement_payload(payload=payload, principal=principal),
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            caller_context=cockpit_caller_context_from_principal(principal),
            portfolio_id=_authorized_portfolio_id(
                principal=principal,
                requested_portfolio_id=portfolio_id,
            ),
            principal=principal,
        )
    )


def _authorized_portfolio_id(
    *,
    principal: AdvisorCockpitPrincipal,
    requested_portfolio_id: str | None,
) -> str | None:
    try:
        return authorized_cockpit_portfolio_id(
            principal=principal,
            requested_portfolio_id=requested_portfolio_id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_401_UNAUTHORIZED
            if detail == ADVISOR_COCKPIT_SCOPE_REQUIRED
            else status.HTTP_403_FORBIDDEN
        )
        raise_proposal_api_http_exception(status_code=status_code, detail=detail)
        raise AssertionError("unreachable")


def _trusted_acknowledgement_payload(
    *,
    payload: AdvisorCockpitAcknowledgeRequest,
    principal: AdvisorCockpitPrincipal,
) -> AdvisorCockpitAcknowledgeRequest:
    try:
        return bind_cockpit_acknowledgement_payload(payload=payload, principal=principal)
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_403_FORBIDDEN
            if detail == ADVISOR_COCKPIT_ACTOR_MISMATCH
            else status.HTTP_401_UNAUTHORIZED
        )
        raise_proposal_api_http_exception(status_code=status_code, detail=detail)
        raise AssertionError("unreachable")
