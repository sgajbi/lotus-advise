from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.simulation_examples import (
    PROPOSAL_409_EXAMPLE,
    PROPOSAL_BLOCKED_EXAMPLE,
    PROPOSAL_PENDING_EXAMPLE,
    PROPOSAL_READY_EXAMPLE,
)

PROPOSAL_SIMULATION_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Proposal simulation completed with domain status in payload.",
        "content": {
            "application/json": {
                "examples": {
                    "ready": PROPOSAL_READY_EXAMPLE,
                    "pending_review": PROPOSAL_PENDING_EXAMPLE,
                    "blocked": PROPOSAL_BLOCKED_EXAMPLE,
                }
            }
        },
    },
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key reused with different canonical request hash.",
        "content": {"application/json": {"examples": {"conflict": PROPOSAL_409_EXAMPLE}}},
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Validation error (invalid payload or missing required headers)."
    },
}

PROPOSAL_ARTIFACT_RESPONSES = {
    status.HTTP_200_OK: {"description": "Proposal artifact generated successfully."},
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key reused with different canonical request hash.",
        "content": {"application/json": {"examples": {"conflict": PROPOSAL_409_EXAMPLE}}},
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Validation error (invalid payload or missing required headers)."
    },
}
