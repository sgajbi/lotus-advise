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
        self, *, tenant_id: str, evidence_packet_id: str
    ) -> AdvisoryCopilotEvidencePacketRecord | None: ...

    def get_evidence_packet_for_authorized_scope(
        self,
        *,
        tenant_id: str,
        evidence_packet_id: str,
        authorized_portfolio_id: str | None,
        authorized_proposal_id: str | None,
    ) -> AdvisoryCopilotEvidencePacketRecord | None: ...

    def get_run(self, *, tenant_id: str, run_id: str) -> AdvisoryCopilotRunRecord | None: ...

    def get_run_for_authorized_scope(
        self,
        *,
        tenant_id: str,
        run_id: str,
        authorized_portfolio_id: str | None,
        authorized_proposal_id: str | None,
    ) -> AdvisoryCopilotRunRecord | None: ...

    def get_run_idempotency(
        self, *, tenant_id: str, idempotency_key: str
    ) -> AdvisoryCopilotRunIdempotencyRecord | None: ...

    def save_run_with_idempotency(
        self,
        *,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord: ...

    def transition_review(
        self,
        *,
        expected_run: AdvisoryCopilotRunRecord,
        updated_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> tuple[AdvisoryCopilotRunRecord, AdvisoryCopilotReviewRecord, bool]: ...

    def update_run(self, run: AdvisoryCopilotRunRecord) -> None: ...

    def list_reviews(self, *, tenant_id: str, run_id: str) -> list[AdvisoryCopilotReviewRecord]: ...

    def list_runs_for_proposal_version(
        self,
        *,
        tenant_id: str,
        proposal_id: str,
        proposal_version_id: str | None,
        proposal_version_no: int | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[AdvisoryCopilotRunRecord], str | None]: ...
