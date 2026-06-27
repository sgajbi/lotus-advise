from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.core.proposals.idea_proposal_intake import (
    IDEA_PROPOSAL_INTAKE_ERROR_EXAMPLE,
    IDEA_PROPOSAL_INTAKE_RESPONSE_EXAMPLE,
)

IDEA_PROPOSAL_INTAKE_RESPONSES = {
    status.HTTP_202_ACCEPTED: {
        "description": (
            "Source-safe route-foundation acknowledgement. This is not proposal creation, "
            "suitability approval, or client-publication proof."
        ),
        "content": {"application/json": {"example": IDEA_PROPOSAL_INTAKE_RESPONSE_EXAMPLE}},
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Invalid payload or unsupported query parameters were supplied.",
        "content": {"application/json": {"example": IDEA_PROPOSAL_INTAKE_ERROR_EXAMPLE}},
    },
}
