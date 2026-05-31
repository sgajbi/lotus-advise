from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from src.core.advisor_cockpit.action_sources import HouseViewImpactActionSource
from src.core.advisor_cockpit.api_models import (
    AdvisorCockpitAcknowledgeRequest,
    AdvisorCockpitAcknowledgeResponse,
    AdvisorCockpitPreparationPacketPage,
    AdvisorCockpitSnapshotResponse,
    AdvisorCockpitSupportabilityResponse,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitOperatingSnapshot,
    AdvisoryActionItem,
    AdvisoryActionItemPage,
    CockpitAcknowledgementState,
    CockpitCallerContext,
    CockpitEvidenceRef,
    MeetingPreparationPacket,
)
from src.core.advisor_cockpit.pagination import (
    cockpit_cursor_start,
    normalize_cockpit_page_size,
)
from src.core.advisor_cockpit.persistence import (
    CockpitAcknowledgementIdempotencyRecord,
    CockpitAcknowledgementRecord,
)
from src.core.advisor_cockpit.projection_bounds import (
    bounded_optional_reference,
    bounded_reference,
    bounded_summary,
)
from src.core.advisor_cockpit.repository import AdvisorCockpitRepository
from src.core.advisor_cockpit.rules import (
    apply_cockpit_acknowledgement_state,
    with_cockpit_sla_age_band,
)
from src.core.advisor_cockpit.source_read_model import (
    COCKPIT_SOURCE_BATCH_MAX_ITEMS,
    AdvisorCockpitSourceBatch,
    AdvisorCockpitSourceReadModel,
    build_advisor_cockpit_source_read_model,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.common.idempotency import normalize_required_idempotency_key
from src.core.policy_packs.persistence import list_policy_evaluation_records
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.tactical_house_view import (
    TacticalHouseViewAffectedCohort,
    list_tactical_house_view_affected_cohorts,
)

COCKPIT_SOURCE_LIMIT = COCKPIT_SOURCE_BATCH_MAX_ITEMS
COCKPIT_CONTRACT_VERSION = "rfc0026.advisor-cockpit-api.v1"


class AdvisorCockpitService:
    def __init__(
        self,
        *,
        repository: AdvisorCockpitRepository,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now_fn = now_fn or (lambda: datetime.now(UTC))

    def list_actions(
        self,
        *,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
        limit: int | None,
        cursor: str | None,
        correlation_id: str | None,
    ) -> AdvisoryActionItemPage:
        actions = self._build_actions(
            caller_context=caller_context,
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
        actions = _project_actions_for_caller(actions=actions, caller_context=caller_context)
        page_size = normalize_cockpit_page_size(limit)
        start = cockpit_cursor_start(
            items=actions,
            cursor=cursor,
            identity=lambda action: action.action_item_id,
            invalid_code="ADVISOR_COCKPIT_CURSOR_INVALID",
        )
        page_items = actions[start : start + page_size]
        next_cursor = None
        if start + page_size < len(actions):
            next_cursor = (
                page_items[-1].action_item_id if page_items else actions[start].action_item_id
            )
        return AdvisoryActionItemPage(
            items=page_items,
            next_cursor=next_cursor,
            page_size=page_size,
            total_count=len(actions),
        )

    def get_action(
        self,
        *,
        action_item_id: str,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
        correlation_id: str | None,
    ) -> AdvisoryActionItem:
        for action in _project_actions_for_caller(
            actions=self._build_actions(
                caller_context=caller_context,
                portfolio_id=portfolio_id,
                correlation_id=correlation_id,
            ),
            caller_context=caller_context,
        ):
            if action.action_item_id == action_item_id:
                return action
        raise ProposalNotFoundError("ADVISOR_COCKPIT_ACTION_NOT_FOUND")

    def get_snapshot(
        self,
        *,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
        correlation_id: str | None,
    ) -> AdvisorCockpitSnapshotResponse:
        read_model = self._build_read_model(
            caller_context=caller_context,
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
        actions = _project_actions_for_caller(
            actions=read_model.action_items,
            caller_context=caller_context,
        )
        counts = _action_counts(actions)
        supportability = _supportability(actions=actions, source_limit=COCKPIT_SOURCE_LIMIT)
        snapshot = AdvisorCockpitOperatingSnapshot(
            snapshot_id=bounded_reference(
                f"cockpit_snapshot_{portfolio_id or caller_context.advisor_id or 'all'}"
            ),
            caller_context=caller_context,
            as_of=self._now_fn().isoformat(),
            action_counts=counts,
            top_priority_actions=actions[:10],
            preparation_packets=_preparation_packets(read_model),
            unsupported_capabilities=sorted(
                {capability for action in actions for capability in action.unsupported_capabilities}
            ),
            supportability=supportability,
        )
        return cast(
            AdvisorCockpitSnapshotResponse,
            AdvisorCockpitSnapshotResponse.model_validate(snapshot.model_dump(mode="json")),
        )

    def list_preparation_packets(
        self,
        *,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
        limit: int | None,
        cursor: str | None,
        correlation_id: str | None,
    ) -> AdvisorCockpitPreparationPacketPage:
        read_model = self._build_read_model(
            caller_context=caller_context,
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
        packets = _preparation_packets(read_model)
        page_size = normalize_cockpit_page_size(limit)
        start = cockpit_cursor_start(
            items=packets,
            cursor=cursor,
            identity=lambda packet: packet.packet_id,
            invalid_code="ADVISOR_COCKPIT_PREPARATION_CURSOR_INVALID",
        )
        page_items = packets[start : start + page_size]
        next_cursor = None
        if start + page_size < len(packets):
            next_cursor = page_items[-1].packet_id if page_items else packets[start].packet_id
        return AdvisorCockpitPreparationPacketPage(
            items=page_items,
            next_cursor=next_cursor,
            page_size=page_size,
            total_count=len(packets),
            supportability=_supportability(
                actions=read_model.action_items,
                source_limit=COCKPIT_SOURCE_LIMIT,
            ),
        )

    def get_supportability(
        self,
        *,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
        correlation_id: str | None,
    ) -> AdvisorCockpitSupportabilityResponse:
        actions = self._build_actions(
            caller_context=caller_context,
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
        actions = _project_actions_for_caller(actions=actions, caller_context=caller_context)
        return AdvisorCockpitSupportabilityResponse(
            posture="ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED",
            supportability=_supportability(actions=actions, source_limit=COCKPIT_SOURCE_LIMIT),
            unsupported_capabilities=sorted(
                {capability for action in actions for capability in action.unsupported_capabilities}
            ),
        )

    def acknowledge_action(
        self,
        *,
        action_item_id: str,
        payload: AdvisorCockpitAcknowledgeRequest,
        idempotency_key: str,
        correlation_id: str | None,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
    ) -> AdvisorCockpitAcknowledgeResponse:
        try:
            idempotency_key = normalize_required_idempotency_key(idempotency_key)
        except ValueError as exc:
            raise ProposalValidationError(str(exc)) from exc
        action = self.get_action(
            action_item_id=action_item_id,
            caller_context=caller_context,
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
        if payload.action_item_version != action.action_item_version:
            raise ProposalValidationError("ADVISOR_COCKPIT_ACTION_VERSION_STALE")

        request_hash = hash_canonical_payload(
            {
                "contract_version": COCKPIT_CONTRACT_VERSION,
                "operation": "ACKNOWLEDGE_COCKPIT_ACTION",
                "action_item_id": action_item_id,
                "action_item_version": payload.action_item_version,
                "acknowledged_by": payload.acknowledged_by,
                "acknowledgement_note": payload.acknowledgement_note,
            }
        )
        replayed = self._repository.get_cockpit_acknowledgement_idempotency(
            idempotency_key=idempotency_key
        )
        if replayed is not None:
            if replayed.request_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "ADVISOR_COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_CONFLICT"
                )
            record = self._repository.get_cockpit_acknowledgement(
                action_item_id=replayed.action_item_id
            )
            if record is None:
                raise ProposalNotFoundError("ADVISOR_COCKPIT_ACKNOWLEDGEMENT_NOT_FOUND")
            return _acknowledgement_response(action=action, record=record, replayed=True)

        acknowledged_at = self._now_fn()
        record = CockpitAcknowledgementRecord(
            acknowledgement_id=bounded_reference(f"ack_{action_item_id}"),
            action_item_id=action_item_id,
            action_item_version=payload.action_item_version,
            acknowledged_by=payload.acknowledged_by,
            acknowledged_at=acknowledged_at,
            acknowledgement_note=payload.acknowledgement_note,
            correlation_id=correlation_id,
            reason_json={
                "contract_version": COCKPIT_CONTRACT_VERSION,
                "idempotency_key": idempotency_key,
                "request_hash": request_hash,
                "owner_role": action.owner_role,
                "status_after_acknowledgement": action.status,
            },
        )
        try:
            self._repository.save_cockpit_acknowledgement_with_idempotency(
                acknowledgement=record,
                idempotency=CockpitAcknowledgementIdempotencyRecord(
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    acknowledgement_id=record.acknowledgement_id,
                    action_item_id=action_item_id,
                    created_at=acknowledged_at,
                ),
            )
        except ValueError as exc:
            raise ProposalIdempotencyConflictError(
                "ADVISOR_COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_CONFLICT"
            ) from exc
        return _acknowledgement_response(action=action, record=record, replayed=False)

    def _build_actions(
        self,
        *,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
        correlation_id: str | None,
    ) -> list[AdvisoryActionItem]:
        read_model = self._build_read_model(
            caller_context=caller_context,
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
        )
        return cast(list[AdvisoryActionItem], read_model.action_items)

    def _build_read_model(
        self,
        *,
        caller_context: CockpitCallerContext,
        portfolio_id: str | None,
        correlation_id: str | None,
    ) -> AdvisorCockpitSourceReadModel:
        proposals, _next_cursor = self._repository.list_proposals(
            portfolio_id=portfolio_id,
            state=None,
            created_by=None if portfolio_id is not None else caller_context.advisor_id,
            created_from=None,
            created_to=None,
            limit=COCKPIT_SOURCE_LIMIT,
            cursor=None,
        )
        memos = self._repository.list_memos_for_proposals(
            proposal_ids=[proposal.proposal_id for proposal in proposals]
        )
        approvals = self._repository.list_approvals_for_proposals(
            proposal_ids=[proposal.proposal_id for proposal in proposals]
        )
        workflow_events = self._repository.list_events_for_proposals(
            proposal_ids=[proposal.proposal_id for proposal in proposals]
        )
        read_model = build_advisor_cockpit_source_read_model(
            AdvisorCockpitSourceBatch(
                proposals=proposals,
                policy_evaluations=list_policy_evaluation_records(
                    evaluation_status=None,
                    portfolio_id=portfolio_id,
                )[:COCKPIT_SOURCE_LIMIT],
                memos=memos[:COCKPIT_SOURCE_LIMIT],
                approvals=approvals[:COCKPIT_SOURCE_LIMIT],
                workflow_events=workflow_events[:COCKPIT_SOURCE_LIMIT],
                house_view_impacts=_house_view_impacts(
                    list_tactical_house_view_affected_cohorts(
                        portfolio_id=portfolio_id,
                        limit=COCKPIT_SOURCE_LIMIT,
                    ),
                    portfolio_id=portfolio_id,
                    correlation_id=correlation_id,
                ),
            )
        )
        action_items = [
            self._attach_runtime_state(action=action, correlation_id=correlation_id)
            for action in read_model.action_items
        ]
        return cast(
            AdvisorCockpitSourceReadModel,
            read_model.model_copy(update={"action_items": action_items}),
        )

    def _attach_runtime_state(
        self,
        *,
        action: AdvisoryActionItem,
        correlation_id: str | None,
    ) -> AdvisoryActionItem:
        action = with_cockpit_sla_age_band(action, now=self._now_fn())
        acknowledgement = self._repository.get_cockpit_acknowledgement(
            action_item_id=action.action_item_id
        )
        if acknowledgement is not None:
            action = apply_cockpit_acknowledgement_state(
                action,
                _acknowledgement_state(acknowledgement),
            )
        if correlation_id and action.correlation_id is None:
            action = action.model_copy(update={"correlation_id": correlation_id})
        return action


def _project_actions_for_caller(
    *,
    actions: list[AdvisoryActionItem],
    caller_context: CockpitCallerContext,
) -> list[AdvisoryActionItem]:
    visible_owner_roles = _visible_owner_roles(caller_context.role)
    if visible_owner_roles is None:
        return actions
    return [
        action
        for action in actions
        if action.owner_role in visible_owner_roles or action.owner_role == "SYSTEM"
    ]


def _visible_owner_roles(role: str) -> set[str] | None:
    if role in {"ADVISOR", "DESK_HEAD"}:
        return None
    if role == "COMPLIANCE_REVIEWER":
        return {"COMPLIANCE_REVIEWER"}
    if role == "INVESTMENT_DESK":
        return {"INVESTMENT_DESK"}
    if role == "OPERATIONS":
        return {"REPORTING_OWNER", "ARCHIVE_OWNER", "EXECUTION_OWNER", "OPERATIONS"}
    if role in {"PORTFOLIO_MANAGER", "DPM_OWNER"}:
        return {"PORTFOLIO_MANAGER", "DPM_OWNER"}
    if role == "CRM_OWNER":
        return {"CRM_OWNER", "ADVISOR"}
    return {role}


def _house_view_impacts(
    cohorts: list[TacticalHouseViewAffectedCohort],
    *,
    portfolio_id: str | None,
    correlation_id: str | None,
) -> list[HouseViewImpactActionSource]:
    impacts: list[HouseViewImpactActionSource] = []
    for cohort in cohorts:
        for affected in cohort.affected_portfolios:
            if portfolio_id is not None and affected.portfolio_id != portfolio_id:
                continue
            inclusion_reason_codes = affected.inclusion_reason_codes or [
                "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED"
            ]
            impact_code = (
                "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED"
                if "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED" in inclusion_reason_codes
                else inclusion_reason_codes[0]
            )
            impacts.append(
                HouseViewImpactActionSource(
                    cohort_id=cohort.cohort_id,
                    tactical_view_id=cohort.tactical_view_id,
                    tactical_view_version=cohort.tactical_view_version,
                    portfolio_id=affected.portfolio_id,
                    impact_code=impact_code,
                    summary=(
                        "Portfolio is included in a source-backed tactical house-view affected "
                        "cohort for discretionary portfolio-management review."
                    ),
                    lineage_id=f"tactical_house_view_cohort:{cohort.cohort_id}",
                    content_hash=cohort.content_hash,
                    source_timestamp=cohort.generated_at,
                    materiality_rank=52,
                    correlation_id=correlation_id or cohort.correlation_id,
                )
            )
    return impacts


def _action_counts(actions: list[AdvisoryActionItem]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for action in actions:
        counts[f"family.{action.action_family}"] += 1
        counts[f"status.{action.status}"] += 1
        counts[f"priority.{action.priority}"] += 1
        counts[f"owner.{action.owner_role}"] += 1
        counts[f"sla.{action.sla_age_band}"] += 1
    return dict(sorted(counts.items()))


def _supportability(*, actions: list[AdvisoryActionItem], source_limit: int) -> dict[str, Any]:
    return {
        "contract_version": COCKPIT_CONTRACT_VERSION,
        "source_limit": source_limit,
        "action_count": len(actions),
        "api_posture": "SUPPORTED_BY_LOTUS_ADVISE_RFC0026",
        "gateway_posture": "SUPPORTED_BY_LOTUS_GATEWAY_RFC0026",
        "workbench_posture": "CANONICAL_WORKBENCH_PROOF_PASSED_RFC0026",
        "data_product_posture": "ACTIVE_ADVISOR_COCKPIT_PRODUCTS_RFC0026",
        "canonical_proof": "PB_SG_GLOBAL_BAL_001_ADVISOR_COCKPIT_VALIDATED",
        "client_ready_publication": "BLOCKED",
        "external_client_communication": "BLOCKED",
    }


def _preparation_packets(
    read_model: AdvisorCockpitSourceReadModel,
) -> list[MeetingPreparationPacket]:
    packets: list[MeetingPreparationPacket] = []
    for source in read_model.meeting_preparations:
        packet_id = bounded_reference(source.preparation_id)
        summary = bounded_summary(source.summary)
        source_ref = bounded_optional_reference(
            source.proposal_id or source.portfolio_id or source.context_ref
        )
        packets.append(
            MeetingPreparationPacket(
                packet_id=packet_id,
                context_type=source.context_type,
                context_ref=bounded_reference(source.context_ref),
                status="READY",
                evidence_refs=source.evidence_refs
                or [
                    CockpitEvidenceRef(
                        evidence_id=packet_id,
                        evidence_type="MEETING_PREPARATION_PACKET",
                        source_system="lotus-advise",
                        access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                        summary=summary,
                    )
                ],
                sections=[
                    {
                        "section_id": "advisor_meeting_context",
                        "title": "Advisor meeting context",
                        "summary": summary,
                        "source_ref": source_ref,
                    }
                ],
            )
        )
    return packets


def _acknowledgement_response(
    *,
    action: AdvisoryActionItem,
    record: CockpitAcknowledgementRecord,
    replayed: bool,
) -> AdvisorCockpitAcknowledgeResponse:
    acknowledgement = _acknowledgement_state(record)
    return AdvisorCockpitAcknowledgeResponse(
        action_item=apply_cockpit_acknowledgement_state(action, acknowledgement),
        acknowledgement=acknowledgement,
        replayed=replayed,
        audit={
            "acknowledgement_id": record.acknowledgement_id,
            "correlation_id": record.correlation_id,
            "contract_version": COCKPIT_CONTRACT_VERSION,
            "idempotency_key": record.reason_json.get("idempotency_key"),
        },
    )


def _acknowledgement_state(
    record: CockpitAcknowledgementRecord,
) -> CockpitAcknowledgementState:
    return CockpitAcknowledgementState(
        acknowledged=True,
        acknowledgement_id=record.acknowledgement_id,
        acknowledged_by=record.acknowledged_by,
        acknowledged_at=record.acknowledged_at.isoformat(),
        acknowledgement_note=record.acknowledgement_note,
    )
