from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE

LIFECYCLE_RUNTIME_UNAVAILABLE_RESPONSE = {
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Proposal runtime persistence is unavailable or misconfigured."
    },
}

LIFECYCLE_PROPOSAL_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {"description": "Proposal was not found."},
}

LIFECYCLE_VERSION_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "description": "Proposal or immutable proposal version was not found."
    },
}

PROPOSAL_CREATE_RESPONSES = {
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused with a different proposal-create payload."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": (
            "Proposal input failed validation or required stateful context could not be resolved."
        )
    },
    **LIFECYCLE_RUNTIME_UNAVAILABLE_RESPONSE,
}

PROPOSAL_VERSION_CREATE_RESPONSES = {
    **LIFECYCLE_PROPOSAL_NOT_FOUND_RESPONSE,
    status.HTTP_409_CONFLICT: {"description": "Expected current version check failed."},
    HTTP_422_UNPROCESSABLE: {"description": "Proposal version input failed validation."},
    **LIFECYCLE_RUNTIME_UNAVAILABLE_RESPONSE,
}

PROPOSAL_NARRATIVE_REGENERATE_RESPONSES = {
    **LIFECYCLE_VERSION_NOT_FOUND_RESPONSE,
    HTTP_422_UNPROCESSABLE: {
        "description": "The proposal version has no persisted `proposal_narrative`."
    },
    **LIFECYCLE_RUNTIME_UNAVAILABLE_RESPONSE,
}

PROPOSAL_NARRATIVE_READ_RESPONSES = {
    **LIFECYCLE_VERSION_NOT_FOUND_RESPONSE,
    HTTP_422_UNPROCESSABLE: {
        "description": "The proposal version has no persisted `proposal_narrative`."
    },
    **LIFECYCLE_RUNTIME_UNAVAILABLE_RESPONSE,
}

PROPOSAL_NARRATIVE_REVIEW_RESPONSES = {
    **LIFECYCLE_VERSION_NOT_FOUND_RESPONSE,
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused with a different narrative review payload."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": (
            "The proposal version has no reviewable `proposal_narrative`, or the review request "
            "is invalid."
        )
    },
    **LIFECYCLE_RUNTIME_UNAVAILABLE_RESPONSE,
}
