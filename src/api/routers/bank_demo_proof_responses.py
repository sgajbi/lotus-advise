from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE

RFC28_MATERIAL_REVIEW_BLOCKED_PREFIX = "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED"
RFC28_PROOF_VALIDATION_FAILED = "RFC0028_PROOF_PACK_VALIDATION_FAILED"

BANK_DEMO_PROOF_PACK_RESPONSES = {
    status.HTTP_409_CONFLICT: {
        "description": (
            "Material proof evidence is missing or does not match the canonical scenario."
        ),
        "content": {
            "application/json": {
                "example": {
                    "detail": (
                        "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED: "
                        "policy_evaluation expected PENDING_REVIEW"
                    )
                }
            }
        },
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Request shape, proof metadata, or source evidence validation failed.",
        "content": {
            "application/json": {
                "example": {"detail": "RFC0028_INTEGRATION_PROOF_FIELD_MISSING: policy_pack_id"}
            }
        },
    },
}

BANK_DEMO_READ_RESPONSES = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Bank-demo contract metadata could not be assembled."
    },
}
