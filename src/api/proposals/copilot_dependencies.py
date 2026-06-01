from __future__ import annotations

from typing import cast

from fastapi import Depends, HTTPException, status

from src.api.proposals.copilot_errors import safe_copilot_repository_error_detail
from src.api.proposals.router import get_proposal_repository
from src.api.proposals.runtime import proposal_postgres_dsn
from src.core.advisory_copilot.application import (
    AdvisoryCopilotApplicationService,
    AdvisoryCopilotDraftGenerator,
)
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.policy_packs.persistence import list_policy_evaluation_records
from src.core.proposals.repository import ProposalRepository
from src.infrastructure.advisory_copilot import PostgresAdvisoryCopilotRepository
from src.integrations.lotus_ai import generate_advisory_copilot_draft_with_lotus_ai

_COPILOT_REPOSITORY: AdvisoryCopilotRepository | None = None


def get_advisory_copilot_repository() -> AdvisoryCopilotRepository:
    global _COPILOT_REPOSITORY
    if _COPILOT_REPOSITORY is None:
        dsn = _advisory_copilot_postgres_dsn()
        try:
            _COPILOT_REPOSITORY = PostgresAdvisoryCopilotRepository(dsn=dsn)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=safe_copilot_repository_error_detail(str(exc)),
            ) from exc
    return _COPILOT_REPOSITORY


def reset_advisory_copilot_repository_for_tests() -> None:
    global _COPILOT_REPOSITORY
    _COPILOT_REPOSITORY = None


def get_advisory_copilot_application_service(
    repository: AdvisoryCopilotRepository = Depends(get_advisory_copilot_repository),
) -> AdvisoryCopilotApplicationService:
    return AdvisoryCopilotApplicationService(
        repository=repository,
        draft_generator=cast(
            AdvisoryCopilotDraftGenerator,
            generate_advisory_copilot_draft_with_lotus_ai,
        ),
        policy_evaluation_loader=list_policy_evaluation_records,
    )


def get_advisory_proposal_repository(
    repository: ProposalRepository = Depends(get_proposal_repository),
) -> ProposalRepository:
    return repository


def _advisory_copilot_postgres_dsn() -> str:
    import os

    return os.getenv("ADVISORY_COPILOT_POSTGRES_DSN", "").strip() or proposal_postgres_dsn()
