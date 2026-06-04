from datetime import datetime
from typing import Callable, Optional, cast

from src.core.proposals.activity_views import (
    build_delivery_history_view,
    build_delivery_summary_view,
    build_execution_status_view,
)
from src.core.proposals.execution_handoff_command import request_proposal_execution_handoff
from src.core.proposals.execution_update_command import record_proposal_execution_update
from src.core.proposals.models import (
    ProposalDeliveryHistoryResponse,
    ProposalDeliverySummaryResponse,
    ProposalExecutionHandoffRequest,
    ProposalExecutionHandoffResponse,
    ProposalExecutionStatusResponse,
    ProposalExecutionUpdateRequest,
)
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.workflow_rules import TERMINAL_STATES


class ProposalWorkflowDeliveryOperations:
    def __init__(
        self,
        *,
        repository: ProposalRepository,
        require_expected_state: bool,
        utc_now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._require_expected_state = require_expected_state
        self._utc_now = utc_now

    def request_execution_handoff(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionHandoffRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalExecutionHandoffResponse:
        return cast(
            ProposalExecutionHandoffResponse,
            request_proposal_execution_handoff(
                repository=self._repository,
                proposal_id=proposal_id,
                payload=payload,
                idempotency_key=idempotency_key,
                require_expected_state=self._require_expected_state,
                occurred_at=self._utc_now(),
            ),
        )

    def get_execution_status(self, *, proposal_id: str) -> ProposalExecutionStatusResponse:
        return cast(
            ProposalExecutionStatusResponse,
            build_execution_status_view(repository=self._repository, proposal_id=proposal_id),
        )

    def get_delivery_summary(self, *, proposal_id: str) -> ProposalDeliverySummaryResponse:
        return cast(
            ProposalDeliverySummaryResponse,
            build_delivery_summary_view(repository=self._repository, proposal_id=proposal_id),
        )

    def get_delivery_history(self, *, proposal_id: str) -> ProposalDeliveryHistoryResponse:
        return cast(
            ProposalDeliveryHistoryResponse,
            build_delivery_history_view(repository=self._repository, proposal_id=proposal_id),
        )

    def record_execution_update(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionUpdateRequest,
    ) -> ProposalExecutionStatusResponse:
        replay_response = record_proposal_execution_update(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            terminal_states=TERMINAL_STATES,
            default_occurred_at=self._utc_now(),
        )
        if replay_response is not None:
            return cast(ProposalExecutionStatusResponse, replay_response)
        return self.get_execution_status(proposal_id=proposal_id)
