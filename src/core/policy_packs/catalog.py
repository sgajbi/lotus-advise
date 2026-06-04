from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.policy_packs.catalog_definitions import (
    CATALOG_CONTRACT_VERSION,
    REFERENCE_POSTURE,
    catalog_posture,
    definition_key,
    prepare_definition,
    summary_from_definition,
    validate_definition,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackActivationResponse,
    PolicyPackAuditEvent,
    PolicyPackDetailResponse,
    PolicyPackListResponse,
    PolicyPackValidationResponse,
)
from src.core.policy_packs.catalog_reference_packs import reference_policy_packs
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key

_CATALOG_CONTRACT_VERSION = CATALOG_CONTRACT_VERSION
_REFERENCE_POSTURE = REFERENCE_POSTURE


def list_policy_pack_versions() -> PolicyPackListResponse:
    return _STORE.list_policy_pack_versions()


def get_policy_pack_version(
    *, policy_pack_id: str, policy_version: str
) -> PolicyPackDetailResponse:
    return _STORE.get_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )


def validate_policy_pack_version(
    *,
    policy_pack_id: str,
    policy_version: str,
    requested_by: str,
    idempotency_key: str,
    reason: dict[str, Any],
) -> PolicyPackValidationResponse:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    return _STORE.validate_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        requested_by=requested_by,
        idempotency_key=idempotency_key,
        reason=reason,
    )


def activate_policy_pack_version(
    *,
    policy_pack_id: str,
    policy_version: str,
    activated_by: str,
    source_content_hash: str,
    idempotency_key: str,
    reason: dict[str, Any],
) -> PolicyPackActivationResponse:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    return _STORE.activate_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        activated_by=activated_by,
        source_content_hash=source_content_hash,
        idempotency_key=idempotency_key,
        reason=reason,
    )


def reset_policy_pack_catalog_for_tests() -> None:
    _STORE.reset()


class PolicyPackCatalogStore:
    def __init__(self, definitions: list[dict[str, Any]]) -> None:
        self._source_definitions = deepcopy(definitions)
        self.reset()

    def reset(self) -> None:
        self._definitions = {
            definition_key(definition): prepare_definition(definition)
            for definition in deepcopy(self._source_definitions)
        }
        self._events: dict[tuple[str, str], list[PolicyPackAuditEvent]] = {
            key: [] for key in self._definitions
        }
        self._idempotency: dict[str, tuple[str, PolicyPackAuditEvent]] = {}

    def list_policy_pack_versions(self) -> PolicyPackListResponse:
        return PolicyPackListResponse(
            items=[
                summary_from_definition(definition)
                for definition in sorted(
                    self._definitions.values(),
                    key=lambda item: (item["policy_pack_id"], item["policy_version"]),
                )
            ],
            catalog_posture=catalog_posture(),
        )

    def get_policy_pack_version(
        self, *, policy_pack_id: str, policy_version: str
    ) -> PolicyPackDetailResponse:
        definition = self._load_definition(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        return self._detail_from_definition(definition)

    def validate_policy_pack_version(
        self,
        *,
        policy_pack_id: str,
        policy_version: str,
        requested_by: str,
        idempotency_key: str,
        reason: dict[str, Any],
    ) -> PolicyPackValidationResponse:
        definition = self._load_definition(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        request_hash = hash_canonical_payload(
            {
                "operation": "POLICY_PACK_VALIDATED",
                "policy_pack_id": policy_pack_id,
                "policy_version": policy_version,
                "requested_by": requested_by,
                "content_hash": definition["content_hash"],
                "reason": reason,
            }
        )
        replayed = self._find_replayed_event(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed is not None:
            return PolicyPackValidationResponse(
                policy_pack=summary_from_definition(definition),
                validation_status="READY",
                diagnostics=list(replayed.reason.get("diagnostics", [])),
                validation_event=replayed,
                replayed=True,
            )

        diagnostics = validate_definition(definition)
        if diagnostics:
            raise ProposalValidationError(";".join(diagnostics))
        event = self._append_event(
            event_type="POLICY_PACK_VALIDATED",
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            actor_id=requested_by,
            content_hash=str(definition["content_hash"]),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            reason={
                "validation_status": "READY",
                "diagnostics": [],
                "dry_run_status": "REFERENCE_FIXTURES_VALIDATED",
                "sample_fixture_refs": list(definition["sample_fixture_refs"]),
                "reason": deepcopy(reason),
                "reference_posture": _REFERENCE_POSTURE,
            },
        )
        return PolicyPackValidationResponse(
            policy_pack=summary_from_definition(definition),
            validation_status="READY",
            diagnostics=[],
            validation_event=event,
            replayed=False,
        )

    def activate_policy_pack_version(
        self,
        *,
        policy_pack_id: str,
        policy_version: str,
        activated_by: str,
        source_content_hash: str,
        idempotency_key: str,
        reason: dict[str, Any],
    ) -> PolicyPackActivationResponse:
        definition = self._load_definition(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        request_hash = hash_canonical_payload(
            {
                "operation": "POLICY_PACK_ACTIVATED",
                "policy_pack_id": policy_pack_id,
                "policy_version": policy_version,
                "activated_by": activated_by,
                "source_content_hash": source_content_hash,
                "reason": reason,
            }
        )
        replayed = self._find_replayed_event(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed is not None:
            return PolicyPackActivationResponse(
                policy_pack=summary_from_definition(definition),
                activation_event=replayed,
                replayed=True,
            )

        if source_content_hash != definition["content_hash"]:
            raise ProposalValidationError("POLICY_PACK_CONTENT_HASH_MISMATCH")
        if definition["activation_state"] == "ACTIVE":
            raise ProposalValidationError("POLICY_PACK_VERSION_ALREADY_ACTIVE_IMMUTABLE")
        diagnostics = validate_definition(definition)
        if diagnostics:
            raise ProposalValidationError(";".join(diagnostics))
        validation_event = self._latest_validation_event(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        if validation_event is None:
            raise ProposalValidationError("POLICY_PACK_VALIDATION_REQUIRED_BEFORE_ACTIVATION")
        if definition["maker_checker_required"] and validation_event.actor_id == activated_by:
            raise ProposalValidationError("POLICY_PACK_MAKER_CHECKER_REQUIRES_DIFFERENT_ACTOR")

        definition["activation_state"] = "ACTIVE"
        event = self._append_event(
            event_type="POLICY_PACK_ACTIVATED",
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            actor_id=activated_by,
            content_hash=str(definition["content_hash"]),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            reason={
                "activation_state": "ACTIVE",
                "maker_checker_required": definition["maker_checker_required"],
                "validated_by": validation_event.actor_id,
                "validation_event_id": validation_event.event_id,
                "reason": deepcopy(reason),
                "reference_posture": _REFERENCE_POSTURE,
            },
        )
        return PolicyPackActivationResponse(
            policy_pack=summary_from_definition(definition),
            activation_event=event,
            replayed=False,
        )

    def _load_definition(self, *, policy_pack_id: str, policy_version: str) -> dict[str, Any]:
        definition = self._definitions.get((policy_pack_id, policy_version))
        if definition is None:
            raise ProposalNotFoundError("POLICY_PACK_VERSION_NOT_FOUND")
        return definition

    def _detail_from_definition(self, definition: dict[str, Any]) -> PolicyPackDetailResponse:
        key = definition_key(definition)
        return PolicyPackDetailResponse(
            policy_pack=summary_from_definition(definition),
            applicability=deepcopy(definition["applicability"]),
            source_requirements=list(definition["source_requirements"]),
            rules=deepcopy(definition["rules"]),
            disclosure_templates=deepcopy(definition["disclosure_templates"]),
            consent_templates=deepcopy(definition["consent_templates"]),
            approval_routes=deepcopy(definition["approval_routes"]),
            sample_fixture_refs=list(definition["sample_fixture_refs"]),
            supportability={
                **catalog_posture(),
                "activation_lifecycle": "SUPPORTED_BY_RFC0025_SLICE5",
            },
            audit_events=list(self._events[key]),
        )

    def _append_event(
        self,
        *,
        event_type: str,
        policy_pack_id: str,
        policy_version: str,
        actor_id: str,
        content_hash: str,
        idempotency_key: str,
        request_hash: str,
        reason: dict[str, Any],
    ) -> PolicyPackAuditEvent:
        key = (policy_pack_id, policy_version)
        event = PolicyPackAuditEvent(
            event_id=f"ppev_{len(self._events[key]) + 1:06d}",
            event_type=event_type,
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            actor_id=actor_id,
            occurred_at=datetime.now(UTC).isoformat(),
            content_hash=content_hash,
            idempotency_key=idempotency_key,
            reason={
                **reason,
                "idempotency_request_hash": request_hash,
                "catalog_contract_version": _CATALOG_CONTRACT_VERSION,
            },
        )
        self._events[key].append(event)
        self._idempotency[idempotency_key] = (request_hash, event)
        return event

    def _find_replayed_event(
        self, *, idempotency_key: str, request_hash: str
    ) -> PolicyPackAuditEvent | None:
        stored = self._idempotency.get(idempotency_key)
        if stored is None:
            return None
        stored_hash, event = stored
        if stored_hash != request_hash:
            raise ProposalIdempotencyConflictError("POLICY_PACK_IDEMPOTENCY_KEY_CONFLICT")
        return event

    def _latest_validation_event(
        self, *, policy_pack_id: str, policy_version: str
    ) -> PolicyPackAuditEvent | None:
        for event in reversed(self._events[(policy_pack_id, policy_version)]):
            if event.event_type == "POLICY_PACK_VALIDATED":
                return event
        return None


_STORE = PolicyPackCatalogStore(reference_policy_packs())
