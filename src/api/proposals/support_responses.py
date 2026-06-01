from __future__ import annotations

from fastapi import status

SUPPORT_RUNTIME_UNAVAILABLE_RESPONSE = {
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Proposal runtime persistence is unavailable or misconfigured."
    },
}

SUPPORT_PROPOSAL_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {"description": "Proposal was not found."},
}

SUPPORT_VERSION_REPLAY_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "description": "Proposal or immutable proposal version was not found."
    },
}

SUPPORT_ASYNC_REPLAY_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {"description": "Async proposal operation was not found."},
}

SUPPORT_LINEAGE_RESPONSES = {
    **SUPPORT_PROPOSAL_NOT_FOUND_RESPONSE,
    **SUPPORT_RUNTIME_UNAVAILABLE_RESPONSE,
}

SUPPORT_VERSION_REPLAY_RESPONSES = {
    **SUPPORT_VERSION_REPLAY_NOT_FOUND_RESPONSE,
    **SUPPORT_RUNTIME_UNAVAILABLE_RESPONSE,
}

SUPPORT_ASYNC_REPLAY_RESPONSES = {
    **SUPPORT_ASYNC_REPLAY_NOT_FOUND_RESPONSE,
    **SUPPORT_RUNTIME_UNAVAILABLE_RESPONSE,
}
