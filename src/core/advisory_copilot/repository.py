from __future__ import annotations

from typing import Protocol

from src.core.advisory_copilot.idempotency_records import AdvisoryCopilotRunIdempotencyRecord
from src.core.advisory_copilot.packet_records import AdvisoryCopilotEvidencePacketRecord
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord


class AdvisoryCopilotRepository(Protocol):
    def save_evidence_packet(
        self, record: AdvisoryCopilotEvidencePacketRecord
    ) -> AdvisoryCopilotEvidencePacketRecord: ...

    def get_evidence_packet(
        self, *, evidence_packet_id: str
    ) -> AdvisoryCopilotEvidencePacketRecord | None: ...

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
        limit: int,
        cursor: str | None,
    ) -> tuple[list[AdvisoryCopilotRunRecord], str | None]: ...
