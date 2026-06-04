from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from src.core.advisor_cockpit.action_models import (
    AdvisoryActionItem,
    AdvisoryActionItemPage,
)
from src.core.advisor_cockpit.api_models import (
    AdvisorCockpitAcknowledgeRequest,
    AdvisorCockpitAcknowledgeResponse,
    AdvisorCockpitPreparationPacketPage,
    AdvisorCockpitSnapshotResponse,
    AdvisorCockpitSupportabilityResponse,
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
    bounded_reference,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitAcknowledgementState,
    CockpitCallerContext,
)
from src.core.advisor_cockpit.repository import AdvisorCockpitRepository
from src.core.advisor_cockpit.rules import (
    apply_cockpit_acknowledgement_state,
    with_cockpit_sla_age_band,
)
from src.core.advisor_cockpit.service_projection import (
    action_counts,
    preparation_packets,
    project_actions_for_caller,
    supportability,
)
from src.core.advisor_cockpit.service_source_loader import (
    load_advisor_cockpit_source_read_model,
)
from src.core.advisor_cockpit.snapshot_models import AdvisorCockpitOperatingSnapshot
from src.core.advisor_cockpit.source_read_model import (
    COCKPIT_SOURCE_BATCH_MAX_ITEMS,
    AdvisorCockpitSourceReadModel,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key

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
        actions = project_actions_for_caller(actions=actions, caller_context=caller_context)
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
        for action in project_actions_for_caller(
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
        actions = project_actions_for_caller(
            actions=read_model.action_items,
            caller_context=caller_context,
        )
        counts = action_counts(actions)
        cockpit_supportability = supportability(
            actions=actions,
            source_limit=COCKPIT_SOURCE_LIMIT,
            contract_version=COCKPIT_CONTRACT_VERSION,
        )
        snapshot = AdvisorCockpitOperatingSnapshot(
            snapshot_id=bounded_reference(
                f"cockpit_snapshot_{portfolio_id or caller_context.advisor_id or 'all'}"
            ),
            caller_context=caller_context,
            as_of=self._now_fn().isoformat(),
            action_counts=counts,
            top_priority_actions=actions[:10],
            preparation_packets=preparation_packets(read_model),
            unsupported_capabilities=sorted(
                {capability for action in actions for capability in action.unsupported_capabilities}
            ),
            supportability=cockpit_supportability,
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
        packets = preparation_packets(read_model)
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
            supportability=supportability(
                actions=read_model.action_items,
                source_limit=COCKPIT_SOURCE_LIMIT,
                contract_version=COCKPIT_CONTRACT_VERSION,
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
        actions = project_actions_for_caller(actions=actions, caller_context=caller_context)
        return AdvisorCockpitSupportabilityResponse(
            posture="ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED",
            supportability=supportability(
                actions=actions,
                source_limit=COCKPIT_SOURCE_LIMIT,
                contract_version=COCKPIT_CONTRACT_VERSION,
            ),
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
        idempotency_key = require_proposal_idempotency_key(idempotency_key)
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
        read_model = load_advisor_cockpit_source_read_model(
            repository=self._repository,
            caller_context=caller_context,
            portfolio_id=portfolio_id,
            correlation_id=correlation_id,
            source_limit=COCKPIT_SOURCE_LIMIT,
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
