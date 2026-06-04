from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.core.proposals.async_operations import AsyncCreateSubmissionStatsTracker
from src.core.proposals.models import ProposalCreateResponse
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.service_async_operations import ProposalWorkflowAsyncOperations
from src.core.proposals.service_command_operations import ProposalWorkflowCommandOperations
from src.core.proposals.service_delivery_operations import ProposalWorkflowDeliveryOperations
from src.core.proposals.service_narrative_operations import (
    ProposalWorkflowNarrativeOperations,
)
from src.core.proposals.service_read_operations import ProposalWorkflowReadOperations


@dataclass(frozen=True)
class ProposalWorkflowOperationRegistry:
    create_submission_stats: AsyncCreateSubmissionStatsTracker
    command_operations: ProposalWorkflowCommandOperations
    async_operations: ProposalWorkflowAsyncOperations
    delivery_operations: ProposalWorkflowDeliveryOperations
    narrative_operations: ProposalWorkflowNarrativeOperations
    read_operations: ProposalWorkflowReadOperations


def build_proposal_workflow_operation_registry(
    *,
    repository: ProposalRepository,
    store_evidence_bundle: bool,
    require_expected_state: bool,
    allow_portfolio_id_change_on_new_version: bool,
    require_proposal_simulation_flag: bool,
    utc_now: Callable[[], datetime],
    create_proposal: Callable[..., ProposalCreateResponse],
    create_version: Callable[..., ProposalCreateResponse],
) -> ProposalWorkflowOperationRegistry:
    create_submission_stats = AsyncCreateSubmissionStatsTracker()
    command_operations = ProposalWorkflowCommandOperations(
        repository=repository,
        store_evidence_bundle=store_evidence_bundle,
        require_expected_state=require_expected_state,
        allow_portfolio_id_change_on_new_version=allow_portfolio_id_change_on_new_version,
        require_proposal_simulation_flag=require_proposal_simulation_flag,
        utc_now=utc_now,
    )
    async_operations = ProposalWorkflowAsyncOperations(
        repository=repository,
        create_submission_stats=create_submission_stats,
        utc_now=utc_now,
        create_proposal=create_proposal,
        create_version=create_version,
    )
    return ProposalWorkflowOperationRegistry(
        create_submission_stats=create_submission_stats,
        command_operations=command_operations,
        async_operations=async_operations,
        delivery_operations=ProposalWorkflowDeliveryOperations(
            repository=repository,
            require_expected_state=require_expected_state,
            utc_now=utc_now,
        ),
        narrative_operations=ProposalWorkflowNarrativeOperations(
            repository=repository,
            utc_now=utc_now,
        ),
        read_operations=ProposalWorkflowReadOperations(repository=repository),
    )
