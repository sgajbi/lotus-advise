import importlib
from typing import Callable, cast

from src.core.advisory_copilot.repository import AdvisoryCopilotRepository

AdvisoryCopilotRepositoryFactory = Callable[..., AdvisoryCopilotRepository]

PostgresAdvisoryCopilotRepository: AdvisoryCopilotRepositoryFactory | None = None


def _postgres_repository_factory() -> AdvisoryCopilotRepositoryFactory:
    if PostgresAdvisoryCopilotRepository is not None:
        return PostgresAdvisoryCopilotRepository
    module = importlib.import_module("src.infrastructure.advisory_copilot")
    return cast(
        AdvisoryCopilotRepositoryFactory,
        module.PostgresAdvisoryCopilotRepository,
    )


def build_advisory_copilot_repository(*, dsn: str) -> AdvisoryCopilotRepository:
    return _postgres_repository_factory()(dsn=dsn)
