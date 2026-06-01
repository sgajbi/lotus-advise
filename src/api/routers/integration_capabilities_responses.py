from __future__ import annotations

from fastapi import status

INTEGRATION_CAPABILITIES_RESPONSES = {
    status.HTTP_200_OK: {
        "description": (
            "Lotus-branded advisory capability contract returned with readiness metadata."
        )
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Unexpected service error while building capabilities."
    },
}
