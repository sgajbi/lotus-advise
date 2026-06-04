from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from src.core.proposals.create_command import create_proposal_command
from src.core.proposals.lifecycle_command import (
    record_proposal_approval,
    transition_proposal_state,
)
from src.core.proposals.models import (
    ProposalApprovalRequest,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalLifecycleOrigin,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalVersionRequest,
)
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.version_command import create_proposal_version


class ProposalWorkflowCommandOperations:
    def __init__(
        self,
        *,
        repository: ProposalRepository,
        store_evidence_bundle: bool,
        require_expected_state: bool,
        allow_portfolio_id_change_on_new_version: bool,
        require_proposal_simulation_flag: bool,
        utc_now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._store_evidence_bundle = store_evidence_bundle
        self._require_expected_state = require_expected_state
        self._allow_portfolio_id_change_on_new_version = allow_portfolio_id_change_on_new_version
        self._require_proposal_simulation_flag = require_proposal_simulation_flag
        self._utc_now = utc_now

    def create_proposal(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
        lifecycle_origin: ProposalLifecycleOrigin,
        source_workspace_id: Optional[str],
        replay_lineage: Optional[dict[str, Any]],
        context_resolution_override: Optional[dict[str, Any]],
    ) -> ProposalCreateResponse:
        return create_proposal_command(
            repository=self._repository,
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            lifecycle_origin=lifecycle_origin,
            source_workspace_id=source_workspace_id,
            replay_lineage=replay_lineage,
            context_resolution_override=context_resolution_override,
            store_evidence_bundle=self._store_evidence_bundle,
            require_proposal_simulation_flag=self._require_proposal_simulation_flag,
            utc_now=self._utc_now,
        )

    def create_version(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
        replay_lineage: Optional[dict[str, Any]],
        context_resolution_override: Optional[dict[str, Any]],
    ) -> ProposalCreateResponse:
        return create_proposal_version(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
            replay_lineage=replay_lineage,
            context_resolution_override=context_resolution_override,
            store_evidence_bundle=self._store_evidence_bundle,
            require_proposal_simulation_flag=self._require_proposal_simulation_flag,
            allow_portfolio_id_change_on_new_version=(
                self._allow_portfolio_id_change_on_new_version
            ),
            utc_now=self._utc_now,
        )

    def transition_state(
        self,
        *,
        proposal_id: str,
        payload: ProposalStateTransitionRequest,
        idempotency_key: Optional[str],
    ) -> ProposalStateTransitionResponse:
        return transition_proposal_state(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
            require_expected_state=self._require_expected_state,
            occurred_at=self._utc_now(),
        )

    def record_approval(
        self,
        *,
        proposal_id: str,
        payload: ProposalApprovalRequest,
        idempotency_key: Optional[str],
    ) -> ProposalStateTransitionResponse:
        return record_proposal_approval(
            repository=self._repository,
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
            require_expected_state=self._require_expected_state,
            occurred_at=self._utc_now(),
        )
