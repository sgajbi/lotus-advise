from dataclasses import dataclass

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.context import (
    canonicalize_create_request_payload,
    canonicalize_version_request_payload,
    resolve_create_request,
    resolve_version_request,
)
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateRequest,
    ProposalVersionRequest,
)


@dataclass(frozen=True)
class AsyncPayloadResolutionFailure:
    message: str
    code: str = "ProposalLifecycleError"


@dataclass(frozen=True)
class AsyncCreatePayloadResolution:
    payload: ProposalCreateRequest
    idempotency_key: str


@dataclass(frozen=True)
class AsyncVersionPayloadResolution:
    proposal_id: str
    payload: ProposalVersionRequest


def extract_async_submission_hash(operation: ProposalAsyncOperationRecord) -> str | None:
    submission_hash = operation.payload_json.get("submission_hash")
    if isinstance(submission_hash, str) and submission_hash:
        return submission_hash
    payload_json = operation.payload_json.get("payload")
    if not isinstance(payload_json, dict):
        return None
    return str(hash_canonical_payload(payload_json))


def hash_async_create_submission(payload: ProposalCreateRequest) -> str:
    if payload.input_mode == "stateful":
        return str(hash_canonical_payload(payload.model_dump(mode="json", exclude_none=True)))
    resolved_request = resolve_create_request(payload)
    return str(
        hash_canonical_payload(
            canonicalize_create_request_payload(
                payload=payload,
                resolved=resolved_request,
            )
        )
    )


def hash_async_version_submission(
    *,
    proposal_id: str,
    payload: ProposalVersionRequest,
) -> str:
    if payload.input_mode == "stateful":
        return str(
            hash_canonical_payload(
                {
                    "proposal_id": proposal_id,
                    **payload.model_dump(mode="json", exclude_none=True),
                }
            )
        )
    resolved_request = resolve_version_request(payload)
    return str(
        hash_canonical_payload(
            {
                "proposal_id": proposal_id,
                **canonicalize_version_request_payload(
                    payload=payload,
                    resolved=resolved_request,
                ),
            }
        )
    )


def resolve_async_create_payload(
    *,
    operation: ProposalAsyncOperationRecord,
    fallback_payload: ProposalCreateRequest | None,
    fallback_idempotency_key: str | None,
) -> AsyncCreatePayloadResolution | AsyncPayloadResolutionFailure:
    payload_json = operation.payload_json.get("payload")
    if not isinstance(payload_json, dict):
        if fallback_payload is None:
            return AsyncPayloadResolutionFailure(message="PROPOSAL_ASYNC_PAYLOAD_INVALID")
        payload = fallback_payload
    else:
        try:
            payload = ProposalCreateRequest.model_validate(payload_json)
        except Exception:
            return AsyncPayloadResolutionFailure(message="PROPOSAL_ASYNC_PAYLOAD_INVALID")

    resolved_idempotency_key = (
        operation.payload_json.get("idempotency_key")
        or operation.idempotency_key
        or fallback_idempotency_key
    )
    if not isinstance(resolved_idempotency_key, str) or not resolved_idempotency_key:
        return AsyncPayloadResolutionFailure(message="PROPOSAL_ASYNC_IDEMPOTENCY_KEY_REQUIRED")
    return AsyncCreatePayloadResolution(
        payload=payload,
        idempotency_key=resolved_idempotency_key,
    )


def resolve_async_version_payload(
    *,
    operation: ProposalAsyncOperationRecord,
    fallback_proposal_id: str | None,
    fallback_payload: ProposalVersionRequest | None,
) -> AsyncVersionPayloadResolution | AsyncPayloadResolutionFailure:
    payload_json = operation.payload_json.get("payload")
    if not isinstance(payload_json, dict):
        if fallback_payload is None:
            return AsyncPayloadResolutionFailure(message="PROPOSAL_ASYNC_PAYLOAD_INVALID")
        payload = fallback_payload
    else:
        try:
            payload = ProposalVersionRequest.model_validate(payload_json)
        except Exception:
            return AsyncPayloadResolutionFailure(message="PROPOSAL_ASYNC_PAYLOAD_INVALID")

    resolved_proposal_id = operation.payload_json.get("proposal_id") or operation.proposal_id
    if not isinstance(resolved_proposal_id, str) or not resolved_proposal_id:
        resolved_proposal_id = fallback_proposal_id or ""
    if not resolved_proposal_id:
        return AsyncPayloadResolutionFailure(message="PROPOSAL_ASYNC_PROPOSAL_ID_REQUIRED")
    return AsyncVersionPayloadResolution(
        proposal_id=resolved_proposal_id,
        payload=payload,
    )
