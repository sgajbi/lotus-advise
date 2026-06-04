from __future__ import annotations

from typing import Optional, cast

from src.core.proposals.async_operations import (
    AsyncCreateSubmissionStats,
    AsyncCreateSubmissionStatsTracker,
)
from src.core.proposals.models import (
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalVersionRequest,
)
from src.core.proposals.service_async_operations import (
    ASYNC_RECOVERY_BATCH_SIZE,
    ProposalWorkflowAsyncOperations,
)
from src.core.replay.models import AdvisoryReplayEvidenceResponse


class ProposalWorkflowAsyncFacadeMixin:
    def accept_create_proposal_async_submission(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
        return cast(
            "tuple[ProposalAsyncAcceptedResponse, bool]",
            self._proposal_async_operations().accept_create_proposal_submission(
                payload=payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            ),
        )

    def submit_create_proposal_async(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        accepted, _ = self.accept_create_proposal_async_submission(
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        return accepted

    def execute_create_proposal_async(
        self,
        *,
        operation_id: str,
        payload: Optional[ProposalCreateRequest] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        self._proposal_async_operations().execute_create_proposal(
            operation_id=operation_id,
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    def get_async_operation(self, *, operation_id: str) -> ProposalAsyncOperationStatusResponse:
        return self._proposal_async_operations().get_status(operation_id=operation_id)

    def get_async_operation_replay(self, *, operation_id: str) -> AdvisoryReplayEvidenceResponse:
        return self._proposal_async_operations().get_replay(operation_id=operation_id)

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> ProposalAsyncOperationStatusResponse:
        return self._proposal_async_operations().get_by_correlation(correlation_id=correlation_id)

    def submit_create_version_async(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        accepted, _ = self.accept_create_version_async_submission(
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
        )
        return accepted

    def accept_create_version_async_submission(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
        return cast(
            "tuple[ProposalAsyncAcceptedResponse, bool]",
            self._proposal_async_operations().accept_create_version_submission(
                proposal_id=proposal_id,
                payload=payload,
                correlation_id=correlation_id,
            ),
        )

    def execute_create_version_async(
        self,
        *,
        operation_id: str,
        proposal_id: Optional[str] = None,
        payload: Optional[ProposalVersionRequest] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        self._proposal_async_operations().execute_create_version(
            operation_id=operation_id,
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
        )

    def recover_async_operations(self, *, max_operations: int = ASYNC_RECOVERY_BATCH_SIZE) -> int:
        return cast(
            int,
            self._proposal_async_operations().recover_pending(max_operations=max_operations),
        )

    def get_async_create_submission_stats_for_tests(self) -> AsyncCreateSubmissionStats:
        return self._proposal_async_create_submission_stats().snapshot()

    def _proposal_async_operations(self) -> ProposalWorkflowAsyncOperations:
        return cast(ProposalWorkflowAsyncOperations, getattr(self, "_async_operations"))

    def _proposal_async_create_submission_stats(self) -> AsyncCreateSubmissionStatsTracker:
        return cast(
            AsyncCreateSubmissionStatsTracker,
            getattr(self, "_async_create_submission_stats"),
        )
