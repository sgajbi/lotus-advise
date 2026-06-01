from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE

POLICY_EVALUATION_CREATE_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {"description": "Policy-pack version was not found."},
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused for a different evaluation request."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Policy pack is inactive, not applicable, or source evidence is invalid."
    },
}

POLICY_REVIEW_QUEUE_RESPONSES = {
    status.HTTP_200_OK: {"description": "Policy review queue returned."}
}

POLICY_EVALUATION_READ_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {"description": "Policy evaluation was not found."}
}

POLICY_EVALUATION_EVENT_RESPONSES = {
    **POLICY_EVALUATION_READ_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused for a different event request."
    },
}

POLICY_SIGN_OFF_DECISION_RESPONSES = {
    **POLICY_EVALUATION_READ_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused for a different sign-off decision."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": (
            "Sign-off is blocked by stale hash, maker-checker, unresolved requirement, "
            "blocked evaluation, or unresolved conflict posture."
        )
    },
}

POLICY_REPORT_PACKAGE_RESPONSES = {
    **POLICY_EVALUATION_READ_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused with a different report-package request."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": (
            "Report package is blocked by stale hash, missing sign-off, unresolved "
            "requirements, unsupported output formats, or client-ready document request."
        )
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "lotus-report report/render/archive materialization is unavailable."
    },
}

POLICY_AI_EVIDENCE_RESPONSES = {
    **POLICY_EVALUATION_READ_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was reused with a different AI evidence request."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": (
            "AI evidence request is blocked by stale hash, missing action, forbidden action, "
            "or unsupported claim request."
        )
    },
}
