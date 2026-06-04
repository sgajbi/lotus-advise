from __future__ import annotations

from datetime import datetime
from typing import Optional, cast

from src.core.proposals.models import (
    ProposalApprovalsResponse,
    ProposalDetailResponse,
    ProposalIdempotencyLookupResponse,
    ProposalLineageResponse,
    ProposalListResponse,
    ProposalVersionDetail,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.service_read_operations import ProposalWorkflowReadOperations
from src.core.replay.models import AdvisoryReplayEvidenceResponse


class ProposalWorkflowReadFacadeMixin:
    def get_proposal(
        self, *, proposal_id: str, include_evidence: bool = True
    ) -> ProposalDetailResponse:
        return self._proposal_read_operations().get_proposal(
            proposal_id=proposal_id,
            include_evidence=include_evidence,
        )

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
    ) -> ProposalListResponse:
        return self._proposal_read_operations().list_proposals(
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            cursor=cursor,
        )

    def get_workflow_timeline(self, *, proposal_id: str) -> ProposalWorkflowTimelineResponse:
        return self._proposal_read_operations().get_workflow_timeline(proposal_id=proposal_id)

    def get_approvals(self, *, proposal_id: str) -> ProposalApprovalsResponse:
        return self._proposal_read_operations().get_approvals(proposal_id=proposal_id)

    def get_lineage(self, *, proposal_id: str) -> ProposalLineageResponse:
        return self._proposal_read_operations().get_lineage(proposal_id=proposal_id)

    def get_idempotency_lookup(self, *, idempotency_key: str) -> ProposalIdempotencyLookupResponse:
        return self._proposal_read_operations().get_idempotency_lookup(
            idempotency_key=idempotency_key
        )

    def get_version(
        self,
        *,
        proposal_id: str,
        version_no: int,
        include_evidence: bool = True,
    ) -> ProposalVersionDetail:
        return self._proposal_read_operations().get_version(
            proposal_id=proposal_id,
            version_no=version_no,
            include_evidence=include_evidence,
        )

    def get_version_replay(
        self,
        *,
        proposal_id: str,
        version_no: int,
    ) -> AdvisoryReplayEvidenceResponse:
        return self._proposal_read_operations().get_version_replay(
            proposal_id=proposal_id,
            version_no=version_no,
        )

    def _proposal_read_operations(self) -> ProposalWorkflowReadOperations:
        return cast(ProposalWorkflowReadOperations, getattr(self, "_read_operations"))
