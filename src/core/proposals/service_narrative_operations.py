from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from src.core.advisory.narrative_models import ProposalNarrativeReviewRequest
from src.core.proposals.identifiers import new_workflow_event_id
from src.core.proposals.models import (
    ProposalNarrativeReadResponse,
    ProposalNarrativeRegenerationRequest,
    ProposalNarrativeRegenerationResponse,
    ProposalNarrativeReviewResponse,
    ProposalReportResponse,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.narrative_views import (
    build_narrative_view,
    record_narrative_review,
    regenerate_narrative_view,
)
from src.core.proposals.report_request_command import record_proposal_report_request
from src.core.proposals.repository import ProposalRepository


class ProposalWorkflowNarrativeOperations:
    def __init__(
        self,
        *,
        repository: ProposalRepository,
        utc_now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._utc_now = utc_now

    def get_narrative(
        self,
        *,
        proposal_id: str,
        version_no: int,
    ) -> ProposalNarrativeReadResponse:
        return build_narrative_view(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )

    def regenerate_narrative(
        self,
        *,
        proposal_id: str,
        version_no: int,
        payload: ProposalNarrativeRegenerationRequest,
    ) -> ProposalNarrativeRegenerationResponse:
        return regenerate_narrative_view(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
        )

    def record_narrative_review(
        self,
        *,
        proposal_id: str,
        version_no: int,
        payload: ProposalNarrativeReviewRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalNarrativeReviewResponse:
        return record_narrative_review(
            repository=self._repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_workflow_event_id(),
            occurred_at=self._utc_now,
        )

    def record_report_request(
        self,
        *,
        proposal_id: str,
        report_response: ProposalReportResponse,
        requested_by: str,
        related_version_no: int,
        include_execution_summary: bool,
        include_reviewed_narrative: bool = False,
        proposal_narrative_package: dict[str, Any] | None = None,
    ) -> ProposalWorkflowEventRecord:
        return record_proposal_report_request(
            repository=self._repository,
            proposal_id=proposal_id,
            event_id=new_workflow_event_id(),
            report_response=report_response,
            requested_by=requested_by,
            related_version_no=related_version_no,
            include_execution_summary=include_execution_summary,
            include_reviewed_narrative=include_reviewed_narrative,
            proposal_narrative_package=proposal_narrative_package,
        )
