from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE

POLICY_PACK_LIST_RESPONSES = {
    status.HTTP_200_OK: {"description": "Policy-pack catalog metadata returned."},
}

POLICY_PACK_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {"description": "Policy-pack version was not found."},
}

POLICY_PACK_VALIDATE_RESPONSES = {
    **POLICY_PACK_NOT_FOUND_RESPONSE,
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused for a different validation request."
    },
    HTTP_422_UNPROCESSABLE: {"description": "Policy-pack validation failed with diagnostics."},
}

POLICY_PACK_ACTIVATE_RESPONSES = {
    **POLICY_PACK_NOT_FOUND_RESPONSE,
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused for a different activation request."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": (
            "Activation failed because validation is missing, hash mismatched, maker-checker "
            "control failed, or the version is already active and immutable."
        )
    },
}
