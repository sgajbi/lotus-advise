from __future__ import annotations

from copy import deepcopy
from threading import Lock

from src.core.advisory_copilot.records import (
    AdvisoryCopilotEvidencePacketRecord,
    AdvisoryCopilotReviewRecord,
    AdvisoryCopilotRunIdempotencyRecord,
    AdvisoryCopilotRunRecord,
)
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository


class InMemoryAdvisoryCopilotRepository(AdvisoryCopilotRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._evidence_packets: dict[str, AdvisoryCopilotEvidencePacketRecord] = {}
        self._runs: dict[str, AdvisoryCopilotRunRecord] = {}
        self._run_idempotency: dict[str, AdvisoryCopilotRunIdempotencyRecord] = {}
        self._reviews: dict[str, list[AdvisoryCopilotReviewRecord]] = {}
        self._review_idempotency: dict[tuple[str, str], str] = {}

    def save_evidence_packet(
        self, record: AdvisoryCopilotEvidencePacketRecord
    ) -> AdvisoryCopilotEvidencePacketRecord:
        with self._lock:
            existing = self._evidence_packets.get(record.evidence_packet_id)
            if existing is not None:
                if existing.evidence_packet_hash != record.evidence_packet_hash:
                    raise ValueError("COPILOT_EVIDENCE_PACKET_HASH_CONFLICT")
                return deepcopy(existing)
            self._evidence_packets[record.evidence_packet_id] = deepcopy(record)
            return deepcopy(record)

    def get_evidence_packet(
        self, *, evidence_packet_id: str
    ) -> AdvisoryCopilotEvidencePacketRecord | None:
        with self._lock:
            record = self._evidence_packets.get(evidence_packet_id)
            return deepcopy(record) if record is not None else None

    def get_run(self, *, run_id: str) -> AdvisoryCopilotRunRecord | None:
        with self._lock:
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None else None

    def get_run_idempotency(
        self, *, idempotency_key: str
    ) -> AdvisoryCopilotRunIdempotencyRecord | None:
        with self._lock:
            record = self._run_idempotency.get(idempotency_key)
            return deepcopy(record) if record is not None else None

    def save_run_with_idempotency(
        self,
        *,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord:
        with self._lock:
            if idempotency is not None:
                existing_idempotency = self._run_idempotency.get(idempotency.idempotency_key)
                if existing_idempotency is not None:
                    if (
                        existing_idempotency.request_hash != idempotency.request_hash
                        or existing_idempotency.run_id != run.run_id
                    ):
                        raise ValueError("COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT")
                    existing_run = self._runs.get(existing_idempotency.run_id)
                    if existing_run is None:
                        raise ValueError("COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED")
                    return deepcopy(existing_run)
            existing_run = self._runs.get(run.run_id)
            if existing_run is not None:
                if existing_run.request_hash != run.request_hash:
                    raise ValueError("COPILOT_RUN_HASH_CONFLICT")
                return deepcopy(existing_run)
            self._runs[run.run_id] = deepcopy(run)
            if idempotency is not None:
                self._run_idempotency[idempotency.idempotency_key] = deepcopy(idempotency)
            return deepcopy(run)

    def update_run(self, run: AdvisoryCopilotRunRecord) -> None:
        with self._lock:
            if run.run_id not in self._runs:
                raise ValueError("COPILOT_RUN_NOT_FOUND")
            self._runs[run.run_id] = deepcopy(run)

    def append_review(self, review: AdvisoryCopilotReviewRecord) -> None:
        with self._lock:
            reviews = self._reviews.setdefault(review.run_id, [])
            if any(existing.review_id == review.review_id for existing in reviews):
                return
            if review.idempotency_key is not None:
                idem_key = (review.run_id, review.idempotency_key)
                existing_review_id = self._review_idempotency.get(idem_key)
                if existing_review_id is not None and existing_review_id != review.review_id:
                    raise ValueError("COPILOT_REVIEW_IDEMPOTENCY_KEY_CONFLICT")
                self._review_idempotency[idem_key] = review.review_id
            reviews.append(deepcopy(review))

    def get_review_by_idempotency(
        self, *, run_id: str, idempotency_key: str
    ) -> AdvisoryCopilotReviewRecord | None:
        with self._lock:
            review_id = self._review_idempotency.get((run_id, idempotency_key))
            if review_id is None:
                return None
            for review in self._reviews.get(run_id, []):
                if review.review_id == review_id:
                    return deepcopy(review)
            return None

    def list_reviews(self, *, run_id: str) -> list[AdvisoryCopilotReviewRecord]:
        with self._lock:
            reviews = list(self._reviews.get(run_id, []))
        reviews.sort(key=lambda review: (review.occurred_at, review.review_id))
        return [deepcopy(review) for review in reviews]

    def list_runs_for_proposal_version(
        self,
        *,
        proposal_id: str,
        proposal_version_id: str | None,
        proposal_version_no: int | None,
    ) -> list[AdvisoryCopilotRunRecord]:
        with self._lock:
            runs = [
                run
                for run in self._runs.values()
                if run.proposal_id == proposal_id
                and _matches_proposal_version(
                    run=run,
                    proposal_version_id=proposal_version_id,
                    proposal_version_no=proposal_version_no,
                )
            ]
        runs.sort(key=lambda run: (run.created_at, run.run_id), reverse=True)
        return [deepcopy(run) for run in runs]


def _matches_proposal_version(
    *,
    run: AdvisoryCopilotRunRecord,
    proposal_version_id: str | None,
    proposal_version_no: int | None,
) -> bool:
    lineage = run.lineage_json
    if proposal_version_id is not None:
        return lineage.get("proposal_version_id") == proposal_version_id
    if proposal_version_no is not None:
        return lineage.get("proposal_version_no") == proposal_version_no
    return True
