from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE

ADVISOR_COCKPIT_READ_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {
        "description": "Advisor cockpit action item was not found for the supplied scope."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Advisor cockpit request failed validation, including invalid cursors."
    },
}

ADVISOR_COCKPIT_ACKNOWLEDGEMENT_RESPONSES = {
    **ADVISOR_COCKPIT_READ_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": ("Idempotency key was reused with a different acknowledgement request.")
    },
}
