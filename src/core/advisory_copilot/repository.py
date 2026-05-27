from __future__ import annotations

from typing import Protocol

from src.core.advisory_copilot.records import (
    AdvisoryCopilotReviewRecord,
    AdvisoryCopilotRunIdempotencyRecord,
    AdvisoryCopilotRunRecord,
)


class AdvisoryCopilotRepository(Protocol):
    def get_run(self, *, run_id: str) -> AdvisoryCopilotRunRecord | None: ...

    def get_run_idempotency(
        self, *, idempotency_key: str
    ) -> AdvisoryCopilotRunIdempotencyRecord | None: ...

    def save_run_with_idempotency(
        self,
        *,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord: ...

    def update_run(self, run: AdvisoryCopilotRunRecord) -> None: ...

    def append_review(self, review: AdvisoryCopilotReviewRecord) -> None: ...

    def get_review_by_idempotency(
        self, *, run_id: str, idempotency_key: str
    ) -> AdvisoryCopilotReviewRecord | None: ...

    def list_reviews(self, *, run_id: str) -> list[AdvisoryCopilotReviewRecord]: ...

    def list_runs_for_proposal_version(
        self,
        *,
        proposal_id: str,
        proposal_version_id: str | None,
        proposal_version_no: int | None,
    ) -> list[AdvisoryCopilotRunRecord]: ...
