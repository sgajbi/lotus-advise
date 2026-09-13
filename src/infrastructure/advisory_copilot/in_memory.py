from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from threading import Lock

from src.core.advisory_copilot.idempotency_records import AdvisoryCopilotRunIdempotencyRecord
from src.core.advisory_copilot.packet_records import AdvisoryCopilotEvidencePacketRecord
from src.core.advisory_copilot.pagination import (
    AdvisoryCopilotRunCursor,
    decode_copilot_run_cursor,
    encode_copilot_run_cursor,
    run_is_after_cursor,
)
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.review import is_terminal_review_posture
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.source_projection_packets import (
    can_refresh_source_projection_packet,
)


class InMemoryAdvisoryCopilotRepository(AdvisoryCopilotRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._evidence_packets: dict[str, AdvisoryCopilotEvidencePacketRecord] = {}
        self._runs: dict[str, AdvisoryCopilotRunRecord] = {}
        self._run_idempotency: dict[tuple[str, str], AdvisoryCopilotRunIdempotencyRecord] = {}
        self._reviews: dict[str, list[AdvisoryCopilotReviewRecord]] = {}
        self._review_idempotency: dict[tuple[str, str, str], str] = {}

    def save_evidence_packet(
        self, record: AdvisoryCopilotEvidencePacketRecord
    ) -> AdvisoryCopilotEvidencePacketRecord:
        with self._lock:
            existing = self._evidence_packets.get(record.evidence_packet_id)
            if existing is not None:
                if existing.tenant_id != record.tenant_id:
                    raise ValueError("COPILOT_EVIDENCE_PACKET_NOT_FOUND")
                if existing.evidence_packet_hash != record.evidence_packet_hash:
                    if not can_refresh_source_projection_packet(
                        existing=existing,
                        incoming=record,
                    ):
                        raise ValueError("COPILOT_EVIDENCE_PACKET_HASH_CONFLICT")
                    self._evidence_packets[record.evidence_packet_id] = deepcopy(record)
                    return deepcopy(record)
                return deepcopy(existing)
            self._evidence_packets[record.evidence_packet_id] = deepcopy(record)
            return deepcopy(record)

    def get_evidence_packet(
        self, *, tenant_id: str, evidence_packet_id: str
    ) -> AdvisoryCopilotEvidencePacketRecord | None:
        with self._lock:
            record = self._evidence_packets.get(evidence_packet_id)
            return (
                deepcopy(record) if record is not None and record.tenant_id == tenant_id else None
            )

    def get_evidence_packet_for_authorized_scope(
        self,
        *,
        tenant_id: str,
        evidence_packet_id: str,
        authorized_portfolio_id: str | None,
        authorized_proposal_id: str | None,
    ) -> AdvisoryCopilotEvidencePacketRecord | None:
        with self._lock:
            record = self._evidence_packets.get(evidence_packet_id)
            if record is None or record.tenant_id != tenant_id:
                return None
            if record.portfolio_id != authorized_portfolio_id:
                return None
            if record.proposal_id is not None and record.proposal_id != authorized_proposal_id:
                return None
            return deepcopy(record)

    def get_run(self, *, tenant_id: str, run_id: str) -> AdvisoryCopilotRunRecord | None:
        with self._lock:
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None and run.tenant_id == tenant_id else None

    def get_run_for_authorized_scope(
        self,
        *,
        tenant_id: str,
        run_id: str,
        authorized_portfolio_id: str | None,
        authorized_proposal_id: str | None,
    ) -> AdvisoryCopilotRunRecord | None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.tenant_id != tenant_id:
                return None
            if run.portfolio_id != authorized_portfolio_id:
                return None
            if run.proposal_id is not None and run.proposal_id != authorized_proposal_id:
                return None
            return deepcopy(run)

    def get_run_idempotency(
        self, *, tenant_id: str, idempotency_key: str
    ) -> AdvisoryCopilotRunIdempotencyRecord | None:
        with self._lock:
            record = self._run_idempotency.get((tenant_id, idempotency_key))
            return deepcopy(record) if record is not None else None

    def save_run_with_idempotency(
        self,
        *,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord:
        with self._lock:
            if idempotency is not None:
                replay = self._run_replay_for_idempotency(run=run, idempotency=idempotency)
                if replay is not None:
                    return replay
            replay = self._run_replay_for_run_id(run)
            if replay is not None:
                return replay
            return self._store_new_run(run=run, idempotency=idempotency)

    def _run_replay_for_idempotency(
        self,
        *,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord,
    ) -> AdvisoryCopilotRunRecord | None:
        existing_idempotency = self._run_idempotency.get(
            (idempotency.tenant_id, idempotency.idempotency_key)
        )
        if existing_idempotency is None:
            return None
        if _run_idempotency_conflicts(
            existing=existing_idempotency,
            incoming=idempotency,
            incoming_run_id=run.run_id,
        ):
            raise ValueError("COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT")
        existing_run = self._runs.get(existing_idempotency.run_id)
        if existing_run is None:
            raise ValueError("COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED")
        return deepcopy(existing_run)

    def _run_replay_for_run_id(
        self, run: AdvisoryCopilotRunRecord
    ) -> AdvisoryCopilotRunRecord | None:
        existing_run = self._runs.get(run.run_id)
        if existing_run is None:
            return None
        if existing_run.tenant_id != run.tenant_id:
            raise ValueError("COPILOT_RUN_NOT_FOUND")
        if existing_run.request_hash != run.request_hash:
            raise ValueError("COPILOT_RUN_HASH_CONFLICT")
        return deepcopy(existing_run)

    def _store_new_run(
        self,
        *,
        run: AdvisoryCopilotRunRecord,
        idempotency: AdvisoryCopilotRunIdempotencyRecord | None,
    ) -> AdvisoryCopilotRunRecord:
        self._runs[run.run_id] = deepcopy(run)
        if idempotency is not None:
            self._run_idempotency[(idempotency.tenant_id, idempotency.idempotency_key)] = deepcopy(
                idempotency
            )
        return deepcopy(run)

    def update_run(self, run: AdvisoryCopilotRunRecord) -> None:
        with self._lock:
            existing = self._runs.get(run.run_id)
            if existing is None or existing.tenant_id != run.tenant_id:
                raise ValueError("COPILOT_RUN_NOT_FOUND")
            self._runs[run.run_id] = deepcopy(run)

    def transition_review(
        self,
        *,
        expected_run: AdvisoryCopilotRunRecord,
        updated_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> tuple[AdvisoryCopilotRunRecord, AdvisoryCopilotReviewRecord, bool]:
        with self._lock:
            current = self._runs.get(review.run_id)
            if current is None or current.tenant_id != review.tenant_id:
                raise ValueError("COPILOT_RUN_NOT_FOUND")
            existing = self._review_for_idempotency_locked(review)
            if existing is not None:
                if existing.request_hash != review.request_hash:
                    raise ValueError("COPILOT_REVIEW_IDEMPOTENCY_KEY_CONFLICT")
                reconciled = self._reconcile_existing_review_locked(
                    current=current,
                    expected_run=expected_run,
                    updated_run=updated_run,
                    review=existing,
                )
                return deepcopy(reconciled), deepcopy(existing), True
            self._assert_review_transition_preconditions_locked(
                current=current,
                expected_run=expected_run,
                review=review,
            )
            self._append_review_locked(review)
            self._runs[review.run_id] = deepcopy(updated_run)
            return deepcopy(updated_run), deepcopy(review), False

    def _review_for_idempotency_locked(
        self, review: AdvisoryCopilotReviewRecord
    ) -> AdvisoryCopilotReviewRecord | None:
        if review.idempotency_key is None:
            return None
        review_id = self._review_idempotency.get(
            (review.tenant_id, review.run_id, review.idempotency_key)
        )
        return next(
            (item for item in self._reviews.get(review.run_id, []) if item.review_id == review_id),
            None,
        )

    def _reconcile_existing_review_locked(
        self,
        *,
        current: AdvisoryCopilotRunRecord,
        expected_run: AdvisoryCopilotRunRecord,
        updated_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> AdvisoryCopilotRunRecord:
        if current.review_posture == review.new_posture:
            return current
        if (
            current.review_posture == review.previous_posture
            and current.updated_at == expected_run.updated_at
        ):
            self._runs[review.run_id] = deepcopy(updated_run)
            return updated_run
        raise ValueError("COPILOT_REVIEW_TRANSITION_INCONSISTENT")

    @staticmethod
    def _assert_review_transition_preconditions_locked(
        *,
        current: AdvisoryCopilotRunRecord,
        expected_run: AdvisoryCopilotRunRecord,
        review: AdvisoryCopilotReviewRecord,
    ) -> None:
        if is_terminal_review_posture(current.review_posture):
            raise ValueError("COPILOT_RUN_REVIEW_POSTURE_TERMINAL")
        if (
            current.review_posture != expected_run.review_posture
            or current.updated_at != expected_run.updated_at
            or current.review_posture != review.previous_posture
        ):
            raise ValueError("COPILOT_REVIEW_TRANSITION_STALE")

    def _append_review_locked(self, review: AdvisoryCopilotReviewRecord) -> None:
        reviews = self._reviews.setdefault(review.run_id, [])
        if review.idempotency_key is not None:
            self._review_idempotency[(review.tenant_id, review.run_id, review.idempotency_key)] = (
                review.review_id
            )
        reviews.append(deepcopy(review))

    def list_reviews(self, *, tenant_id: str, run_id: str) -> list[AdvisoryCopilotReviewRecord]:
        with self._lock:
            reviews = [
                review for review in self._reviews.get(run_id, []) if review.tenant_id == tenant_id
            ]
        reviews.sort(key=lambda review: (review.occurred_at, review.review_id))
        return [deepcopy(review) for review in reviews]

    def list_runs_for_proposal_version(
        self,
        *,
        tenant_id: str,
        proposal_id: str,
        proposal_version_id: str | None,
        proposal_version_no: int | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[AdvisoryCopilotRunRecord], str | None]:
        decoded_cursor = decode_copilot_run_cursor(cursor)
        with self._lock:
            runs = _runs_for_proposal_version(
                runs=self._runs.values(),
                tenant_id=tenant_id,
                proposal_id=proposal_id,
                proposal_version_id=proposal_version_id,
                proposal_version_no=proposal_version_no,
                cursor=decoded_cursor,
            )
        return _copilot_run_page(runs=runs, limit=limit)


def _runs_for_proposal_version(
    *,
    runs: Iterable[AdvisoryCopilotRunRecord],
    tenant_id: str,
    proposal_id: str,
    proposal_version_id: str | None,
    proposal_version_no: int | None,
    cursor: AdvisoryCopilotRunCursor | None,
) -> list[AdvisoryCopilotRunRecord]:
    matched_runs = [
        run
        for run in runs
        if _matches_run_filter(
            run=run,
            tenant_id=tenant_id,
            proposal_id=proposal_id,
            proposal_version_id=proposal_version_id,
            proposal_version_no=proposal_version_no,
            cursor=cursor,
        )
    ]
    matched_runs.sort(key=lambda run: (run.created_at, run.run_id), reverse=True)
    return matched_runs


def _matches_run_filter(
    *,
    run: AdvisoryCopilotRunRecord,
    tenant_id: str,
    proposal_id: str,
    proposal_version_id: str | None,
    proposal_version_no: int | None,
    cursor: AdvisoryCopilotRunCursor | None,
) -> bool:
    return bool(
        run.tenant_id == tenant_id
        and run.proposal_id == proposal_id
        and _matches_proposal_version(
            run=run,
            proposal_version_id=proposal_version_id,
            proposal_version_no=proposal_version_no,
        )
        and run_is_after_cursor(run, cursor)
    )


def _copilot_run_page(
    *,
    runs: list[AdvisoryCopilotRunRecord],
    limit: int,
) -> tuple[list[AdvisoryCopilotRunRecord], str | None]:
    page = runs[:limit]
    next_cursor = encode_copilot_run_cursor(page[-1]) if len(runs) > limit and page else None
    return [deepcopy(run) for run in page], next_cursor


def _matches_proposal_version(
    *,
    run: AdvisoryCopilotRunRecord,
    proposal_version_id: str | None,
    proposal_version_no: int | None,
) -> bool:
    lineage = run.lineage_json
    if proposal_version_id is not None:
        return bool(lineage.get("proposal_version_id") == proposal_version_id)
    if proposal_version_no is not None:
        return bool(lineage.get("proposal_version_no") == proposal_version_no)
    return True


def _run_idempotency_conflicts(
    *,
    existing: AdvisoryCopilotRunIdempotencyRecord,
    incoming: AdvisoryCopilotRunIdempotencyRecord,
    incoming_run_id: str,
) -> bool:
    return bool(
        existing.request_hash != incoming.request_hash or existing.run_id != incoming_run_id
    )
