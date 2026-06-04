from datetime import datetime
from typing import Optional

from src.core.proposals.activity_views import build_workflow_timeline_view
from src.core.proposals.models import (
    ProposalApprovalsResponse,
    ProposalDetailResponse,
    ProposalIdempotencyLookupResponse,
    ProposalLineageResponse,
    ProposalListResponse,
    ProposalVersionDetail,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.read_views import (
    build_idempotency_lookup_view,
    build_proposal_approvals_view,
    build_proposal_detail_view,
    build_proposal_lineage_view,
    build_proposal_list_view,
    build_proposal_version_view,
)
from src.core.proposals.replay_views import build_proposal_version_replay_view
from src.core.proposals.repository import ProposalRepository
from src.core.replay.models import AdvisoryReplayEvidenceResponse


class ProposalWorkflowReadOperations:
    def __init__(self, *, repository: ProposalRepository) -> None:
        self._repository = repository

    def get_proposal(
        self, *, proposal_id: str, include_evidence: bool = True
    ) -> ProposalDetailResponse:
        return build_proposal_detail_view(
            repository=self._repository,
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
        return build_proposal_list_view(
            repository=self._repository,
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            cursor=cursor,
        )

    def get_workflow_timeline(self, *, proposal_id: str) -> ProposalWorkflowTimelineResponse:
        return build_workflow_timeline_view(repository=self._repository, proposal_id=proposal_id)

    def get_approvals(self, *, proposal_id: str) -> ProposalApprovalsResponse:
        return build_proposal_approvals_view(repository=self._repository, proposal_id=proposal_id)

    def get_lineage(self, *, proposal_id: str) -> ProposalLineageResponse:
        return build_proposal_lineage_view(repository=self._repository, proposal_id=proposal_id)

    def get_idempotency_lookup(self, *, idempotency_key: str) -> ProposalIdempotencyLookupResponse:
        return build_idempotency_lookup_view(
            repository=self._repository,
            idempotency_key=idempotency_key,
        )

    def get_version(
        self,
        *,
        proposal_id: str,
        version_no: int,
        include_evidence: bool = True,
    ) -> ProposalVersionDetail:
        return build_proposal_version_view(
            repository=self._repository,
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
        return build_proposal_version_replay_view(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
