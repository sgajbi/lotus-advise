from datetime import datetime, timezone
from typing import Any, Optional

from src.core.advisory.narrative_review_models import ProposalNarrativeReviewRequest
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalLifecycleError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)
from src.core.proposals.models import (
    ProposalApprovalRequest,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalDeliveryHistoryResponse,
    ProposalDeliverySummaryResponse,
    ProposalExecutionHandoffRequest,
    ProposalExecutionHandoffResponse,
    ProposalExecutionStatusResponse,
    ProposalExecutionUpdateRequest,
    ProposalLifecycleOrigin,
    ProposalNarrativeReadResponse,
    ProposalNarrativeRegenerationRequest,
    ProposalNarrativeRegenerationResponse,
    ProposalNarrativeReviewResponse,
    ProposalReportResponse,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalVersionRequest,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.service_async_facade import ProposalWorkflowAsyncFacadeMixin
from src.core.proposals.service_operation_registry import (
    build_proposal_workflow_operation_registry,
)
from src.core.proposals.service_read_facade import ProposalWorkflowReadFacadeMixin

__all__ = [
    "ProposalIdempotencyConflictError",
    "ProposalLifecycleError",
    "ProposalNotFoundError",
    "ProposalStateConflictError",
    "ProposalTransitionError",
    "ProposalValidationError",
    "ProposalWorkflowService",
]


class ProposalWorkflowService(ProposalWorkflowAsyncFacadeMixin, ProposalWorkflowReadFacadeMixin):
    def __init__(
        self,
        *,
        repository: ProposalRepository,
        store_evidence_bundle: bool = True,
        require_expected_state: bool = True,
        allow_portfolio_id_change_on_new_version: bool = False,
        require_proposal_simulation_flag: bool = True,
    ) -> None:
        self._repository = repository
        self._store_evidence_bundle = store_evidence_bundle
        self._require_expected_state = require_expected_state
        self._allow_portfolio_id_change_on_new_version = allow_portfolio_id_change_on_new_version
        self._require_proposal_simulation_flag = require_proposal_simulation_flag
        operation_registry = build_proposal_workflow_operation_registry(
            repository=self._repository,
            store_evidence_bundle=store_evidence_bundle,
            require_expected_state=require_expected_state,
            allow_portfolio_id_change_on_new_version=allow_portfolio_id_change_on_new_version,
            require_proposal_simulation_flag=require_proposal_simulation_flag,
            utc_now=_utc_now,
            create_proposal=lambda **kwargs: self.create_proposal(**kwargs),
            create_version=lambda **kwargs: self.create_version(**kwargs),
        )
        self._async_create_submission_stats = operation_registry.create_submission_stats
        self._command_operations = operation_registry.command_operations
        self._async_operations = operation_registry.async_operations
        self._delivery_operations = operation_registry.delivery_operations
        self._narrative_operations = operation_registry.narrative_operations
        self._read_operations = operation_registry.read_operations

    def create_proposal(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
        lifecycle_origin: ProposalLifecycleOrigin = "DIRECT_CREATE",
        source_workspace_id: Optional[str] = None,
        replay_lineage: Optional[dict[str, Any]] = None,
        context_resolution_override: Optional[dict[str, Any]] = None,
    ) -> ProposalCreateResponse:
        return self._command_operations.create_proposal(
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            lifecycle_origin=lifecycle_origin,
            source_workspace_id=source_workspace_id,
            replay_lineage=replay_lineage,
            context_resolution_override=context_resolution_override,
        )

    def request_execution_handoff(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionHandoffRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalExecutionHandoffResponse:
        return self._delivery_operations.request_execution_handoff(
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    def get_execution_status(self, *, proposal_id: str) -> ProposalExecutionStatusResponse:
        return self._delivery_operations.get_execution_status(proposal_id=proposal_id)

    def get_delivery_summary(self, *, proposal_id: str) -> ProposalDeliverySummaryResponse:
        return self._delivery_operations.get_delivery_summary(proposal_id=proposal_id)

    def get_delivery_history(self, *, proposal_id: str) -> ProposalDeliveryHistoryResponse:
        return self._delivery_operations.get_delivery_history(proposal_id=proposal_id)

    def record_execution_update(
        self,
        *,
        proposal_id: str,
        payload: ProposalExecutionUpdateRequest,
    ) -> ProposalExecutionStatusResponse:
        return self._delivery_operations.record_execution_update(
            proposal_id=proposal_id,
            payload=payload,
        )

    def create_version(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
        replay_lineage: Optional[dict[str, Any]] = None,
        context_resolution_override: Optional[dict[str, Any]] = None,
    ) -> ProposalCreateResponse:
        return self._command_operations.create_version(
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
            replay_lineage=replay_lineage,
            context_resolution_override=context_resolution_override,
        )

    def transition_state(
        self,
        *,
        proposal_id: str,
        payload: ProposalStateTransitionRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        return self._command_operations.transition_state(
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    def record_approval(
        self,
        *,
        proposal_id: str,
        payload: ProposalApprovalRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        return self._command_operations.record_approval(
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    def get_narrative(
        self,
        *,
        proposal_id: str,
        version_no: int,
    ) -> ProposalNarrativeReadResponse:
        return self._narrative_operations.get_narrative(
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
        return self._narrative_operations.regenerate_narrative(
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
        return self._narrative_operations.record_narrative_review(
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
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
        return self._narrative_operations.record_report_request(
            proposal_id=proposal_id,
            report_response=report_response,
            requested_by=requested_by,
            related_version_no=related_version_no,
            include_execution_summary=include_execution_summary,
            include_reviewed_narrative=include_reviewed_narrative,
            proposal_narrative_package=proposal_narrative_package,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
