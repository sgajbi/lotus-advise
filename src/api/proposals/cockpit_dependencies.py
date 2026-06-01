from __future__ import annotations

from typing import cast

from src.api.proposals import router as shared
from src.core.advisor_cockpit import (
    AdvisorCockpitRepository,
    AdvisorCockpitService,
)


def get_advisor_cockpit_service() -> AdvisorCockpitService:
    return AdvisorCockpitService(
        repository=cast(AdvisorCockpitRepository, shared.get_proposal_repository())
    )
