from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from src.core.advisor_cockpit.persistence import (
    CockpitAcknowledgementIdempotencyRecord,
    CockpitAcknowledgementRecord,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)


class AdvisorCockpitRepository(Protocol):
    def list_proposals(
        self,
        *,
        portfolio_id: Optional[str],
        state: Optional[str],
        created_by: Optional[str],
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[ProposalRecord], Optional[str]]: ...

    def list_memos_for_proposals(self, *, proposal_ids: list[str]) -> list[ProposalMemoRecord]: ...

    def list_approvals_for_proposals(
        self, *, proposal_ids: list[str]
    ) -> list[ProposalApprovalRecordData]: ...

    def list_events_for_proposals(
        self, *, proposal_ids: list[str]
    ) -> list[ProposalWorkflowEventRecord]: ...

    def get_cockpit_acknowledgement(
        self, *, action_item_id: str
    ) -> Optional[CockpitAcknowledgementRecord]: ...

    def save_cockpit_acknowledgement_with_idempotency(
        self,
        *,
        acknowledgement: CockpitAcknowledgementRecord,
        idempotency: CockpitAcknowledgementIdempotencyRecord,
    ) -> None: ...

    def get_cockpit_acknowledgement_idempotency(
        self, *, idempotency_key: str
    ) -> Optional[CockpitAcknowledgementIdempotencyRecord]: ...
