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
