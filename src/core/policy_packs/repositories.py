from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.core.policy_packs.catalog_models import (
    PolicyPackActivationResponse,
    PolicyPackAuditEvent,
    PolicyPackDetailResponse,
    PolicyPackListResponse,
    PolicyPackValidationResponse,
)
from src.core.policy_packs.event_authority import PolicyEvaluationEventAuthority
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationEventType,
    PolicyEvaluationPersistenceResult,
    PolicyEvaluationRecord,
    PolicyEvaluationReplayResponse,
)
from src.core.policy_packs.projection_models import (
    PolicyEvaluationLineageResponse,
    PolicyEvaluationReviewQueueResponse,
    PolicyEvaluationSignOffPackageResponse,
)


@dataclass(frozen=True)
class PolicyEvaluationFinalizationRequest:
    """Everything needed to finalize one policy evaluation record.

    One object rather than eleven keyword parameters repeated at every
    implementation of the protocol below. The repeated signature was duplication
    the code-health gate reported once the tenant made it twelve parameters -- and
    the gate was right that the parameter list, not the delegation, was the smell.

    Frozen because a finalization request is a description of one submission: a
    frame that could edit it in flight could change what gets recorded from what
    was admitted.
    """

    evidence_bundle: dict[str, Any]
    policy_pack_id: str
    policy_version: str
    proposal_id: str
    proposal_version_id: str
    created_by: str
    tenant_id: str
    idempotency_key: str
    reason: dict[str, Any]
    observed_trace_id: str | None = None


class PolicyEvaluationRepository(Protocol):
    def finalize_policy_evaluation_record(
        self, request: PolicyEvaluationFinalizationRequest
    ) -> PolicyEvaluationPersistenceResult: ...

    def get_policy_evaluation_record(self, *, evaluation_id: str) -> PolicyEvaluationRecord: ...

    def list_policy_evaluation_records(
        self, *, evaluation_status: str | None, portfolio_id: str | None
    ) -> list[PolicyEvaluationRecord]: ...

    def list_policy_evaluation_events(
        self, *, evaluation_id: str
    ) -> list[PolicyEvaluationAuditEvent]: ...

    def get_policy_evaluation_lineage(
        self, *, evaluation_id: str
    ) -> PolicyEvaluationLineageResponse: ...

    def get_policy_evaluation_review_queue(
        self, *, evaluation_status: str | None, portfolio_id: str | None
    ) -> PolicyEvaluationReviewQueueResponse: ...

    def get_policy_evaluation_sign_off_package(
        self, *, evaluation_id: str
    ) -> PolicyEvaluationSignOffPackageResponse: ...

    def append_policy_evaluation_event(
        self,
        *,
        evaluation_id: str,
        event_type: PolicyEvaluationEventType,
        actor_id: str,
        reason: dict[str, Any],
        idempotency_key: str | None,
        authority: PolicyEvaluationEventAuthority | None = None,
    ) -> PolicyEvaluationAuditEvent: ...

    def replay_policy_evaluation_record(
        self,
        *,
        evaluation_id: str,
        evidence_bundle: dict[str, Any] | None,
    ) -> PolicyEvaluationReplayResponse: ...


class PolicyPackCatalogRepository(Protocol):
    def list_policy_pack_versions(self) -> PolicyPackListResponse: ...

    def get_policy_pack_version(
        self, *, policy_pack_id: str, policy_version: str
    ) -> PolicyPackDetailResponse: ...

    def validate_policy_pack_version(
        self,
        *,
        policy_pack_id: str,
        policy_version: str,
        requested_by: str,
        idempotency_key: str,
        reason: dict[str, Any],
    ) -> PolicyPackValidationResponse: ...

    def activate_policy_pack_version(
        self,
        *,
        policy_pack_id: str,
        policy_version: str,
        activated_by: str,
        source_content_hash: str,
        idempotency_key: str,
        reason: dict[str, Any],
    ) -> PolicyPackActivationResponse: ...

    def list_policy_pack_events(
        self, *, policy_pack_id: str, policy_version: str
    ) -> list[PolicyPackAuditEvent]: ...


__all__ = [
    "PolicyEvaluationRepository",
    "PolicyPackCatalogRepository",
]
