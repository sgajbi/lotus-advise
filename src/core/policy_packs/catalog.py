from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from src.core.policy_packs.catalog_commands import (
    activate_policy_pack_catalog_definition,
    validate_policy_pack_catalog_definition,
)
from src.core.policy_packs.catalog_definitions import (
    catalog_posture,
    definition_key,
    prepare_definition,
    summary_from_definition,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackActivationResponse,
    PolicyPackAuditEvent,
    PolicyPackDetailResponse,
    PolicyPackListResponse,
    PolicyPackValidationResponse,
)
from src.core.policy_packs.catalog_projection import build_policy_pack_detail_response
from src.core.policy_packs.catalog_reference_packs import reference_policy_packs
from src.core.policy_packs.repositories import PolicyPackCatalogRepository
from src.core.proposals.exceptions import ProposalNotFoundError, ProposalValidationError
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key


def list_policy_pack_versions() -> PolicyPackListResponse:
    return _repository().list_policy_pack_versions()


def get_policy_pack_version(
    *, policy_pack_id: str, policy_version: str
) -> PolicyPackDetailResponse:
    return _repository().get_policy_pack_version(
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
    return _repository().validate_policy_pack_version(
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
    return _repository().activate_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        activated_by=activated_by,
        source_content_hash=source_content_hash,
        idempotency_key=idempotency_key,
        reason=reason,
    )


def list_policy_pack_events(
    *, policy_pack_id: str, policy_version: str
) -> list[PolicyPackAuditEvent]:
    return _repository().list_policy_pack_events(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )


def configure_policy_pack_catalog_repository(repository: PolicyPackCatalogRepository) -> None:
    global _REPOSITORY
    _REPOSITORY = repository


def get_policy_pack_catalog_repository() -> PolicyPackCatalogRepository:
    return _repository()


def reset_policy_pack_catalog_for_tests() -> None:
    configure_policy_pack_catalog_repository(PolicyPackCatalogStore(reference_policy_packs()))


def _repository() -> PolicyPackCatalogRepository:
    return _REPOSITORY


class PolicyPackCatalogStore:
    def __init__(self, definitions: list[dict[str, Any]]) -> None:
        self._source_definitions = deepcopy(definitions)
        self.reset()

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> PolicyPackCatalogStore:
        definitions = deepcopy(snapshot.get("definitions", [])) or reference_policy_packs()
        store = cls(definitions)
        store._events = {key: [] for key in store._definitions}
        for item in snapshot.get("events", []):
            event = PolicyPackAuditEvent.model_validate(item)
            store._events.setdefault((event.policy_pack_id, event.policy_version), []).append(event)
        event_index = {
            (
                event.policy_pack_id,
                event.policy_version,
                event.event_id,
            ): event
            for events in store._events.values()
            for event in events
        }
        store._idempotency = {
            str(item["idempotency_key"]): (
                str(item["request_hash"]),
                event_index[
                    (
                        str(item["policy_pack_id"]),
                        str(item["policy_version"]),
                        str(item["event_id"]),
                    )
                ],
            )
            for item in snapshot.get("idempotency", [])
        }
        return store

    def reset(self) -> None:
        self._definitions = {
            definition_key(definition): prepare_definition(definition)
            for definition in deepcopy(self._source_definitions)
        }
        self._events: dict[tuple[str, str], list[PolicyPackAuditEvent]] = {
            key: [] for key in self._definitions
        }
        self._idempotency: dict[str, tuple[str, PolicyPackAuditEvent]] = {}

    def snapshot(self) -> dict[str, Any]:
        return {
            "definitions": [deepcopy(definition) for definition in self._definitions.values()],
            "events": [
                event.model_dump(mode="json")
                for events in self._events.values()
                for event in events
            ],
            "idempotency": [
                {
                    "idempotency_key": idempotency_key,
                    "request_hash": request_hash,
                    "policy_pack_id": event.policy_pack_id,
                    "policy_version": event.policy_version,
                    "event_id": event.event_id,
                }
                for idempotency_key, (request_hash, event) in self._idempotency.items()
            ],
        }

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
        return validate_policy_pack_catalog_definition(
            definition=definition,
            events=self._events,
            idempotency=self._idempotency,
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            requested_by=requested_by,
            idempotency_key=idempotency_key,
            reason=reason,
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
        active_definition = self._single_active_definition(policy_pack_id=policy_pack_id)
        previous_active_policy_version = (
            str(active_definition["policy_version"])
            if active_definition is not None and active_definition is not definition
            else None
        )
        response = activate_policy_pack_catalog_definition(
            definition=definition,
            events=self._events,
            idempotency=self._idempotency,
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            activated_by=activated_by,
            source_content_hash=source_content_hash,
            idempotency_key=idempotency_key,
            reason=reason,
            previous_active_policy_version=previous_active_policy_version,
        )
        if (
            not response.replayed
            and active_definition is not None
            and active_definition is not definition
        ):
            active_definition["activation_state"] = "SUPERSEDED"
        return response

    def list_policy_pack_events(
        self, *, policy_pack_id: str, policy_version: str
    ) -> list[PolicyPackAuditEvent]:
        self._load_definition(policy_pack_id=policy_pack_id, policy_version=policy_version)
        return [deepcopy(event) for event in self._events.get((policy_pack_id, policy_version), [])]

    def _load_definition(self, *, policy_pack_id: str, policy_version: str) -> dict[str, Any]:
        definition = self._definitions.get((policy_pack_id, policy_version))
        if definition is None:
            raise ProposalNotFoundError("POLICY_PACK_VERSION_NOT_FOUND")
        return cast(dict[str, Any], definition)

    def _single_active_definition(self, *, policy_pack_id: str) -> dict[str, Any] | None:
        active_definitions = [
            definition
            for (candidate_pack_id, _policy_version), definition in self._definitions.items()
            if candidate_pack_id == policy_pack_id and definition["activation_state"] == "ACTIVE"
        ]
        if len(active_definitions) > 1:
            raise ProposalValidationError("POLICY_PACK_ACTIVE_VERSION_CONFLICT")
        return cast(dict[str, Any] | None, active_definitions[0] if active_definitions else None)

    def _detail_from_definition(self, definition: dict[str, Any]) -> PolicyPackDetailResponse:
        return build_policy_pack_detail_response(definition=definition, events=self._events)


_REPOSITORY: PolicyPackCatalogRepository = PolicyPackCatalogStore(reference_policy_packs())
