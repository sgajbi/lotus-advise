from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast

from src.core.common.canonical import hash_canonical_payload
from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.policy_packs.catalog import get_policy_pack_version
from src.core.policy_packs.evaluation import evaluate_policy_pack_version
from src.core.policy_packs.models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationEventType,
    PolicyEvaluationLineageResponse,
    PolicyEvaluationPersistenceResult,
    PolicyEvaluationRecord,
    PolicyEvaluationReplayResponse,
    PolicyEvaluationReviewQueueResponse,
    PolicyEvaluationSignOffPackageResponse,
    PolicyPackEvaluationResponse,
)
from src.core.policy_packs.supportability import (
    POLICY_EVALUATION_PERSISTENCE_CONTRACT_VERSION,
    policy_runtime_supportability,
    policy_sign_off_package_posture,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key

_PERSISTENCE_CONTRACT_VERSION = POLICY_EVALUATION_PERSISTENCE_CONTRACT_VERSION


def _required_idempotency_key(idempotency_key: str | None) -> str:
    return require_proposal_idempotency_key(idempotency_key)


def finalize_policy_evaluation_record(
    *,
    evidence_bundle: dict[str, Any],
    policy_pack_id: str,
    policy_version: str,
    proposal_id: str,
    proposal_version_id: str,
    created_by: str,
    idempotency_key: str,
    reason: dict[str, Any] | None = None,
) -> PolicyEvaluationPersistenceResult:
    idempotency_key = _required_idempotency_key(idempotency_key)
    return _STORE.finalize_policy_evaluation_record(
        evidence_bundle=evidence_bundle,
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        proposal_id=proposal_id,
        proposal_version_id=proposal_version_id,
        created_by=created_by,
        idempotency_key=idempotency_key,
        reason=reason or {},
    )


def get_policy_evaluation_record(*, evaluation_id: str) -> PolicyEvaluationRecord:
    return _STORE.get_policy_evaluation_record(evaluation_id=evaluation_id)


def list_policy_evaluation_records(
    *, evaluation_status: str | None = None, portfolio_id: str | None = None
) -> list[PolicyEvaluationRecord]:
    return _STORE.list_policy_evaluation_records(
        evaluation_status=evaluation_status,
        portfolio_id=portfolio_id,
    )


def list_policy_evaluation_events(*, evaluation_id: str) -> list[PolicyEvaluationAuditEvent]:
    return _STORE.list_policy_evaluation_events(evaluation_id=evaluation_id)


def get_policy_evaluation_lineage(*, evaluation_id: str) -> PolicyEvaluationLineageResponse:
    return _STORE.get_policy_evaluation_lineage(evaluation_id=evaluation_id)


def get_policy_evaluation_review_queue(
    *, evaluation_status: str | None = "PENDING_REVIEW", portfolio_id: str | None = None
) -> PolicyEvaluationReviewQueueResponse:
    return _STORE.get_policy_evaluation_review_queue(
        evaluation_status=evaluation_status,
        portfolio_id=portfolio_id,
    )


def get_policy_evaluation_sign_off_package(
    *, evaluation_id: str
) -> PolicyEvaluationSignOffPackageResponse:
    return _STORE.get_policy_evaluation_sign_off_package(evaluation_id=evaluation_id)


def append_policy_evaluation_event(
    *,
    evaluation_id: str,
    event_type: PolicyEvaluationEventType,
    actor_id: str,
    reason: dict[str, Any],
    idempotency_key: str | None = None,
) -> PolicyEvaluationAuditEvent:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    return _STORE.append_policy_evaluation_event(
        evaluation_id=evaluation_id,
        event_type=event_type,
        actor_id=actor_id,
        reason=reason,
        idempotency_key=idempotency_key,
    )


def replay_policy_evaluation_record(
    *, evaluation_id: str, evidence_bundle: dict[str, Any] | None = None
) -> PolicyEvaluationReplayResponse:
    return _STORE.replay_policy_evaluation_record(
        evaluation_id=evaluation_id,
        evidence_bundle=evidence_bundle,
    )


def reset_policy_evaluation_store_for_tests() -> None:
    _STORE.reset()


class PolicyEvaluationRecordStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._records: dict[str, PolicyEvaluationRecord] = {}
        self._events: dict[str, list[PolicyEvaluationAuditEvent]] = {}
        self._idempotency: dict[str, tuple[str, str, str]] = {}
        self._identity_index: dict[tuple[str, str, str, str, str], str] = {}

    def finalize_policy_evaluation_record(
        self,
        *,
        evidence_bundle: dict[str, Any],
        policy_pack_id: str,
        policy_version: str,
        proposal_id: str,
        proposal_version_id: str,
        created_by: str,
        idempotency_key: str,
        reason: dict[str, Any],
    ) -> PolicyEvaluationPersistenceResult:
        source_evidence_hash = hash_canonical_payload(evidence_bundle)
        request_hash = hash_canonical_payload(
            {
                "operation": "POLICY_EVALUATION_FINALIZED",
                "proposal_id": proposal_id,
                "proposal_version_id": proposal_version_id,
                "policy_pack_id": policy_pack_id,
                "policy_version": policy_version,
                "source_evidence_hash": source_evidence_hash,
                "reason": reason,
            }
        )
        replayed = self._find_replayed_event(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed is not None:
            _, record = replayed
            return PolicyEvaluationPersistenceResult(
                record=deepcopy(record),
                created=False,
                replayed=True,
                audit_event=deepcopy(replayed[0]),
            )

        identity = (
            proposal_id,
            proposal_version_id,
            policy_pack_id,
            policy_version,
            source_evidence_hash,
        )
        existing_id = self._identity_index.get(identity)
        if existing_id is not None:
            record = self._load_record(existing_id)
            event = self._events[existing_id][0]
            self._idempotency[idempotency_key] = (request_hash, existing_id, event.event_id)
            return PolicyEvaluationPersistenceResult(
                record=deepcopy(record),
                created=False,
                replayed=False,
                audit_event=deepcopy(event),
            )

        evaluation = evaluate_policy_pack_version(
            evidence_bundle=deepcopy(evidence_bundle),
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        detail = get_policy_pack_version(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        record = _build_record(
            evaluation=evaluation,
            evidence_bundle=evidence_bundle,
            proposal_id=proposal_id,
            proposal_version_id=proposal_version_id,
            created_by=created_by,
            source_evidence_hash=source_evidence_hash,
            policy_content_hash=detail.policy_pack.content_hash,
            idempotency_key=idempotency_key,
            reason=reason,
        )
        event = self._event(
            record=record,
            event_type="POLICY_EVALUATION_FINALIZED",
            actor_id=created_by,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            reason={
                "evaluation_status": record.evaluation_status,
                "policy_content_hash": record.policy_content_hash,
                "source_evidence_hash": record.source_evidence_hash,
                "evaluation_hash": record.evaluation_hash,
                "finalization_reason": reason,
            },
        )
        self._records[record.evaluation_id] = record
        self._events[record.evaluation_id] = [event]
        self._identity_index[identity] = record.evaluation_id
        self._idempotency[idempotency_key] = (
            request_hash,
            record.evaluation_id,
            event.event_id,
        )
        return PolicyEvaluationPersistenceResult(
            record=deepcopy(record),
            created=True,
            replayed=False,
            audit_event=deepcopy(event),
        )

    def get_policy_evaluation_record(self, *, evaluation_id: str) -> PolicyEvaluationRecord:
        return deepcopy(self._load_record(evaluation_id))

    def list_policy_evaluation_records(
        self, *, evaluation_status: str | None, portfolio_id: str | None
    ) -> list[PolicyEvaluationRecord]:
        records = list(self._records.values())
        if evaluation_status:
            records = [
                record for record in records if record.evaluation_status == evaluation_status
            ]
        if portfolio_id:
            records = [record for record in records if record.portfolio_id == portfolio_id]
        return [deepcopy(record) for record in sorted(records, key=lambda item: item.generated_at)]

    def list_policy_evaluation_events(
        self, *, evaluation_id: str
    ) -> list[PolicyEvaluationAuditEvent]:
        self._load_record(evaluation_id)
        return [deepcopy(event) for event in self._events[evaluation_id]]

    def get_policy_evaluation_lineage(
        self, *, evaluation_id: str
    ) -> PolicyEvaluationLineageResponse:
        record = self._load_record(evaluation_id)
        return _lineage_response(
            record=record,
            audit_events=self._events[evaluation_id],
        )

    def get_policy_evaluation_review_queue(
        self, *, evaluation_status: str | None, portfolio_id: str | None
    ) -> PolicyEvaluationReviewQueueResponse:
        return PolicyEvaluationReviewQueueResponse(
            items=self.list_policy_evaluation_records(
                evaluation_status=evaluation_status,
                portfolio_id=portfolio_id,
            ),
            queue_posture=_policy_api_posture(),
        )

    def get_policy_evaluation_sign_off_package(
        self, *, evaluation_id: str
    ) -> PolicyEvaluationSignOffPackageResponse:
        record = self._load_record(evaluation_id)
        lineage = _lineage_response(
            record=record,
            audit_events=self._events[evaluation_id],
        )
        return PolicyEvaluationSignOffPackageResponse(
            evaluation=deepcopy(record),
            lineage=lineage,
            package_posture=policy_sign_off_package_posture(),
        )

    def append_policy_evaluation_event(
        self,
        *,
        evaluation_id: str,
        event_type: PolicyEvaluationEventType,
        actor_id: str,
        reason: dict[str, Any],
        idempotency_key: str | None,
    ) -> PolicyEvaluationAuditEvent:
        record = self._load_record(evaluation_id)
        request_hash = hash_canonical_payload(
            {
                "operation": event_type,
                "evaluation_id": evaluation_id,
                "actor_id": actor_id,
                "reason": reason,
                "evaluation_hash": record.evaluation_hash,
            }
        )
        if idempotency_key:
            replayed = self._find_replayed_event(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if replayed is not None:
                return deepcopy(replayed[0])
        event = self._event(
            record=record,
            event_type=event_type,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            reason=deepcopy(reason),
        )
        self._events[evaluation_id].append(event)
        _attach_event(record=record, event=event)
        if idempotency_key:
            self._idempotency[idempotency_key] = (request_hash, evaluation_id, event.event_id)
        return deepcopy(event)

    def replay_policy_evaluation_record(
        self,
        *,
        evaluation_id: str,
        evidence_bundle: dict[str, Any] | None,
    ) -> PolicyEvaluationReplayResponse:
        record = self._load_record(evaluation_id)
        detail = get_policy_pack_version(
            policy_pack_id=record.policy_pack_id,
            policy_version=record.policy_version,
        )
        comparison: dict[str, Any] = {
            "stored_policy_version": record.policy_version,
            "current_policy_version": detail.policy_pack.policy_version,
            "policy_version_matches": detail.policy_pack.policy_version == record.policy_version,
            "stored_policy_content_hash": record.policy_content_hash,
            "current_policy_content_hash": detail.policy_pack.content_hash,
            "policy_content_hash_matches": detail.policy_pack.content_hash
            == record.policy_content_hash,
            "stored_source_evidence_hash": record.source_evidence_hash,
            "replayed_source_evidence_hash": record.source_evidence_hash,
            "source_evidence_hash_matches": True,
            "stored_evaluation_hash": record.evaluation_hash,
            "replayed_evaluation_hash": record.evaluation_hash,
            "evaluation_hash_matches": True,
        }
        if evidence_bundle is not None:
            replayed_evaluation = evaluate_policy_pack_version(
                evidence_bundle=deepcopy(evidence_bundle),
                policy_pack_id=record.policy_pack_id,
                policy_version=record.policy_version,
            )
            replayed_source_hash = hash_canonical_payload(evidence_bundle)
            replayed_hash = _evaluation_hash(
                evaluation=replayed_evaluation,
                source_evidence_hash=replayed_source_hash,
                policy_content_hash=detail.policy_pack.content_hash,
            )
            comparison.update(
                {
                    "replayed_source_evidence_hash": replayed_source_hash,
                    "source_evidence_hash_matches": replayed_source_hash
                    == record.source_evidence_hash,
                    "replayed_evaluation_hash": replayed_hash,
                    "evaluation_hash_matches": replayed_hash == record.evaluation_hash,
                }
            )
        return PolicyEvaluationReplayResponse(
            evaluation_id=record.evaluation_id,
            replay_contract_version=_PERSISTENCE_CONTRACT_VERSION,
            policy_pack_id=record.policy_pack_id,
            policy_version=record.policy_version,
            source_refs=list(record.source_refs),
            source_gaps=list(record.source_gaps),
            hash_comparison=comparison,
            replay_metadata=deepcopy(record.replay_metadata_json),
        )

    def _load_record(self, evaluation_id: str) -> PolicyEvaluationRecord:
        record = self._records.get(evaluation_id)
        if record is None:
            raise ProposalNotFoundError("POLICY_EVALUATION_RECORD_NOT_FOUND")
        return record

    def _event(
        self,
        *,
        record: PolicyEvaluationRecord,
        event_type: PolicyEvaluationEventType,
        actor_id: str,
        idempotency_key: str | None,
        request_hash: str,
        reason: dict[str, Any],
    ) -> PolicyEvaluationAuditEvent:
        events = self._events.get(record.evaluation_id, [])
        return PolicyEvaluationAuditEvent(
            event_id=f"peev_{len(events) + 1:06d}",
            evaluation_id=record.evaluation_id,
            proposal_id=record.proposal_id,
            proposal_version_id=record.proposal_version_id,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=datetime.now(UTC).isoformat(),
            content_hash=record.evaluation_hash,
            idempotency_key=idempotency_key,
            reason_json={
                **reason,
                "idempotency_request_hash": request_hash,
                "persistence_contract_version": _PERSISTENCE_CONTRACT_VERSION,
            },
        )

    def _find_replayed_event(
        self, *, idempotency_key: str, request_hash: str
    ) -> tuple[PolicyEvaluationAuditEvent, PolicyEvaluationRecord] | None:
        stored = self._idempotency.get(idempotency_key)
        if stored is None:
            return None
        stored_hash, evaluation_id, event_id = stored
        if stored_hash != request_hash:
            raise ProposalIdempotencyConflictError("POLICY_EVALUATION_IDEMPOTENCY_KEY_CONFLICT")
        record = self._load_record(evaluation_id)
        event = next(event for event in self._events[evaluation_id] if event.event_id == event_id)
        return event, record


def _build_record(
    *,
    evaluation: PolicyPackEvaluationResponse,
    evidence_bundle: dict[str, Any],
    proposal_id: str,
    proposal_version_id: str,
    created_by: str,
    source_evidence_hash: str,
    policy_content_hash: str,
    idempotency_key: str,
    reason: dict[str, Any],
) -> PolicyEvaluationRecord:
    evaluation_hash = _evaluation_hash(
        evaluation=evaluation,
        source_evidence_hash=source_evidence_hash,
        policy_content_hash=policy_content_hash,
    )
    source_refs = _source_refs(evaluation)
    source_gaps = _source_gaps(evaluation)
    record_identity_hash = hash_canonical_payload(
        {
            "proposal_id": proposal_id,
            "proposal_version_id": proposal_version_id,
            "policy_pack_id": evaluation.policy_pack.policy_pack_id,
            "policy_version": evaluation.policy_pack.policy_version,
            "source_evidence_hash": source_evidence_hash,
        }
    )
    evaluation_id = f"pev_{record_identity_hash.removeprefix('sha256:')[:20]}"
    return PolicyEvaluationRecord(
        evaluation_id=evaluation_id,
        proposal_id=proposal_id,
        proposal_version_id=proposal_version_id,
        portfolio_id=_portfolio_id(evidence_bundle),
        policy_pack_id=evaluation.policy_pack.policy_pack_id,
        policy_version=evaluation.policy_pack.policy_version,
        generated_at=datetime.now(UTC).isoformat(),
        created_by=created_by,
        evaluation_status=evaluation.evaluation_status,
        policy_content_hash=policy_content_hash,
        source_evidence_hash=source_evidence_hash,
        evaluation_hash=evaluation_hash,
        rule_result_hashes={
            result.rule_id: hash_canonical_payload(result.model_dump(mode="json"))
            for result in evaluation.rule_results
        },
        evaluation_json=evaluation.model_dump(mode="json"),
        source_refs=source_refs,
        source_gaps=source_gaps,
        approval_dependencies=_approval_dependencies(evaluation),
        disclosure_requirements=_disclosure_requirements(evaluation),
        consent_requirements=_consent_requirements(evaluation),
        replay_metadata_json={
            "persistence_contract_version": _PERSISTENCE_CONTRACT_VERSION,
            "policy_evaluation_contract_version": evaluation.contract_version,
            "policy_pack_id": evaluation.policy_pack.policy_pack_id,
            "policy_version": evaluation.policy_pack.policy_version,
            "policy_content_hash": policy_content_hash,
            "source_evidence_hash": source_evidence_hash,
            "evaluation_hash": evaluation_hash,
            "source_refs": source_refs,
            "source_gaps": source_gaps,
            "idempotency_key": idempotency_key,
            "creation_reason": reason,
            "replay_policy": "PIN_POLICY_VERSION_AND_COMPARE_SOURCE_HASHES",
        },
    )


def _evaluation_hash(
    *,
    evaluation: PolicyPackEvaluationResponse,
    source_evidence_hash: str,
    policy_content_hash: str,
) -> str:
    return cast(
        str,
        hash_canonical_payload(
            {
                "contract_version": _PERSISTENCE_CONTRACT_VERSION,
                "policy_evaluation": evaluation.model_dump(mode="json"),
                "policy_content_hash": policy_content_hash,
                "source_evidence_hash": source_evidence_hash,
            }
        ),
    )


def _portfolio_id(evidence_bundle: dict[str, Any]) -> str:
    portfolio = evidence_bundle.get("inputs", {}).get("portfolio_snapshot", {})
    if isinstance(portfolio, dict):
        value = portfolio.get("portfolio_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ProposalValidationError("POLICY_EVALUATION_PORTFOLIO_ID_REQUIRED")


def _source_refs(evaluation: PolicyPackEvaluationResponse) -> list[str]:
    refs: list[str] = []
    for result in evaluation.rule_results:
        refs.extend(result.source_authority_refs)
        refs.extend(result.evidence_refs)
    return _unique(refs)


def _source_gaps(evaluation: PolicyPackEvaluationResponse) -> list[str]:
    gaps = list(evaluation.applicability.missing_evidence)
    for result in evaluation.rule_results:
        gaps.extend(result.missing_evidence)
    return _unique(gaps)


def _approval_dependencies(evaluation: PolicyPackEvaluationResponse) -> list[str]:
    actions = _required_actions(evaluation)
    return _unique(
        [
            action
            for action in actions
            if action.startswith(("REVIEW_", "SUPERVISORY_", "POLICY_STEWARD_"))
        ]
    )


def _disclosure_requirements(evaluation: PolicyPackEvaluationResponse) -> list[str]:
    values: list[str] = []
    for result in evaluation.rule_results:
        values.extend(
            item
            for item in result.missing_evidence
            if item.startswith("advisor_reviewed_disclosure")
        )
    values.extend(action for action in _required_actions(evaluation) if "DISCLOSURE" in action)
    return _unique(values)


def _consent_requirements(evaluation: PolicyPackEvaluationResponse) -> list[str]:
    values: list[str] = []
    for result in evaluation.rule_results:
        values.extend(item for item in result.missing_evidence if item.startswith("client_consent"))
    values.extend(action for action in _required_actions(evaluation) if "CONSENT" in action)
    return _unique(values)


def _required_actions(evaluation: PolicyPackEvaluationResponse) -> list[str]:
    actions: list[str] = []
    for result in evaluation.rule_results:
        actions.extend(result.required_actions)
    return _unique(actions)


def _attach_event(*, record: PolicyEvaluationRecord, event: PolicyEvaluationAuditEvent) -> None:
    payload = event.model_dump(mode="json")
    if event.event_type == "POLICY_EVALUATION_REVIEW_RECORDED":
        record.review_events_json.append(payload)
    elif event.event_type == "POLICY_EVALUATION_SIGN_OFF_RECORDED":
        record.sign_off_events_json.append(payload)
    elif event.event_type == "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED":
        record.report_archive_refs_json.append(payload)


def _lineage_response(
    *,
    record: PolicyEvaluationRecord,
    audit_events: list[PolicyEvaluationAuditEvent],
) -> PolicyEvaluationLineageResponse:
    return PolicyEvaluationLineageResponse(
        evaluation_id=record.evaluation_id,
        proposal_id=record.proposal_id,
        proposal_version_id=record.proposal_version_id,
        policy_pack_id=record.policy_pack_id,
        policy_version=record.policy_version,
        policy_content_hash=record.policy_content_hash,
        source_evidence_hash=record.source_evidence_hash,
        evaluation_hash=record.evaluation_hash,
        rule_result_hashes=dict(record.rule_result_hashes),
        source_refs=list(record.source_refs),
        source_gaps=list(record.source_gaps),
        audit_events=[deepcopy(event) for event in audit_events],
        lineage_posture=_policy_api_posture(),
    )


def _policy_api_posture() -> dict[str, Any]:
    return policy_runtime_supportability()


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


_STORE = PolicyEvaluationRecordStore()
