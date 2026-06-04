from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional, cast

from src.core.proposals.async_operation_execution import (
    execute_create_proposal_async_operation,
    execute_create_version_async_operation,
)
from src.core.proposals.async_operation_recovery import (
    ASYNC_RECOVERY_BATCH_SIZE,
    recover_async_operation_batch,
)
from src.core.proposals.async_operation_views import (
    build_async_operation_correlation_view,
    build_async_operation_replay_view,
    build_async_operation_status_view,
)
from src.core.proposals.async_operations import AsyncCreateSubmissionStatsTracker
from src.core.proposals.async_submission_commands import (
    accept_create_proposal_async_submission_command,
    accept_create_version_async_submission_command,
)
from src.core.proposals.models import (
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalVersionRequest,
)
from src.core.proposals.repository import ProposalRepository
from src.core.replay.models import AdvisoryReplayEvidenceResponse

ASYNC_DEFAULT_MAX_ATTEMPTS = 3


class ProposalWorkflowAsyncOperations:
    def __init__(
        self,
        *,
        repository: ProposalRepository,
        create_submission_stats: AsyncCreateSubmissionStatsTracker,
        utc_now: Callable[[], datetime],
        create_proposal: Callable[..., Any],
        create_version: Callable[..., Any],
    ) -> None:
        self._repository = repository
        self._create_submission_stats = create_submission_stats
        self._utc_now = utc_now
        self._create_proposal = create_proposal
        self._create_version = create_version

    def accept_create_proposal_submission(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
        return cast(
            "tuple[ProposalAsyncAcceptedResponse, bool]",
            accept_create_proposal_async_submission_command(
                repository=self._repository,
                payload=payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                max_attempts=ASYNC_DEFAULT_MAX_ATTEMPTS,
                utc_now=self._utc_now,
                submission_stats=self._create_submission_stats,
            ),
        )

    def execute_create_proposal(
        self,
        *,
        operation_id: str,
        payload: Optional[ProposalCreateRequest] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        execute_create_proposal_async_operation(
            repository=self._repository,
            operation_id=operation_id,
            fallback_payload=payload,
            fallback_idempotency_key=idempotency_key,
            fallback_correlation_id=correlation_id,
            utc_now=self._utc_now,
            create_proposal=self._create_proposal,
        )

    def accept_create_version_submission(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> tuple[ProposalAsyncAcceptedResponse, bool]:
        return cast(
            "tuple[ProposalAsyncAcceptedResponse, bool]",
            accept_create_version_async_submission_command(
                repository=self._repository,
                proposal_id=proposal_id,
                payload=payload,
                correlation_id=correlation_id,
                max_attempts=ASYNC_DEFAULT_MAX_ATTEMPTS,
                utc_now=self._utc_now,
            ),
        )

    def execute_create_version(
        self,
        *,
        operation_id: str,
        proposal_id: Optional[str] = None,
        payload: Optional[ProposalVersionRequest] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        execute_create_version_async_operation(
            repository=self._repository,
            operation_id=operation_id,
            fallback_proposal_id=proposal_id,
            fallback_payload=payload,
            fallback_correlation_id=correlation_id,
            utc_now=self._utc_now,
            create_version=self._create_version,
        )

    def recover_pending(self, *, max_operations: int = ASYNC_RECOVERY_BATCH_SIZE) -> int:
        return cast(
            "int",
            recover_async_operation_batch(
                repository=self._repository,
                max_operations=max_operations,
                utc_now=self._utc_now,
                execute_create_proposal_async=self.execute_create_proposal,
                execute_create_version_async=self.execute_create_version,
            ),
        )

    def get_status(self, *, operation_id: str) -> ProposalAsyncOperationStatusResponse:
        return build_async_operation_status_view(
            repository=self._repository,
            operation_id=operation_id,
        )

    def get_replay(self, *, operation_id: str) -> AdvisoryReplayEvidenceResponse:
        return build_async_operation_replay_view(
            repository=self._repository,
            operation_id=operation_id,
        )

    def get_by_correlation(self, *, correlation_id: str) -> ProposalAsyncOperationStatusResponse:
        return build_async_operation_correlation_view(
            repository=self._repository,
            correlation_id=correlation_id,
        )
