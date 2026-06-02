from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord


class AdvisoryCopilotRunPersistenceResult(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(
        description="Persisted or replayed advisory copilot run record."
    )
    replayed: bool = Field(description="Whether the request replayed an existing idempotent run.")


class AdvisoryCopilotReviewResult(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(description="Run after review processing.")
    review: AdvisoryCopilotReviewRecord = Field(
        description="Persisted or replayed advisory copilot review event."
    )
    replayed: bool = Field(
        description="Whether the request replayed an existing idempotent review."
    )
