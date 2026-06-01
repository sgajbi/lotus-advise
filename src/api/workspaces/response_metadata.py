from __future__ import annotations

from fastapi import status

from src.api.http_status import HTTP_422_UNPROCESSABLE

WORKSPACE_CREATE_EXAMPLE = {
    "summary": "Create a stateful advisory workspace",
    "value": {
        "workspace_name": "Q2 2026 growth reallocation draft",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "household_id": "hh_001",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_growth_01",
        },
    },
}

WORKSPACE_ADD_TRADE_EXAMPLE = {
    "summary": "Add a draft trade and re-evaluate the workspace",
    "value": {
        "actor_id": "advisor_123",
        "action_type": "ADD_TRADE",
        "trade": {
            "intent_type": "SECURITY_TRADE",
            "side": "BUY",
            "instrument_id": "EQ_GROWTH",
            "quantity": "25",
        },
    },
}

WORKSPACE_SAVE_EXAMPLE = {
    "summary": "Save the current advisory workspace draft",
    "value": {
        "saved_by": "advisor_123",
        "version_label": "Initial sandbox draft",
    },
}

WORKSPACE_RESUME_EXAMPLE = {
    "summary": "Resume a previously saved workspace version",
    "value": {
        "actor_id": "advisor_123",
        "workspace_version_id": "awv_001",
    },
}

WORKSPACE_COMPARE_EXAMPLE = {
    "summary": "Compare the current draft to a saved baseline",
    "value": {
        "workspace_version_id": "awv_001",
    },
}

WORKSPACE_HANDOFF_EXAMPLE = {
    "summary": "Persist the current workspace into proposal lifecycle",
    "value": {
        "handoff_by": "advisor_123",
        "metadata": {
            "title": "Q2 2026 growth reallocation proposal",
            "advisor_notes": "Prepared after client review call with growth tilt preference.",
            "jurisdiction": "SG",
            "mandate_id": "mandate_growth_01",
        },
    },
}

WORKSPACE_AI_RATIONALE_EXAMPLE = {
    "summary": "Generate an evidence-grounded workspace rationale",
    "value": {
        "requested_by": "advisor_123",
        "instruction": "Summarize the proposal rationale for an advisor review note.",
    },
}

WORKSPACE_AI_REVIEW_ACTION_EXAMPLE = {
    "summary": "Supersede a historical workspace rationale run with replacement lineage",
    "value": {
        "run_id": "packrun_workspace_rationale_req_001",
        "action_type": "SUPERSEDE",
        "reviewed_by": "advisor_123",
        "reason": "A refreshed rationale run supersedes the earlier workspace draft.",
        "replacement_run_id": "packrun_workspace_rationale_req_002",
    },
}

WORKSPACE_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {"description": "Workspace session not found."},
}

WORKSPACE_SAVED_VERSION_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "description": "Workspace session or saved workspace version not found."
    },
}

WORKSPACE_CREATE_RESPONSES = {
    status.HTTP_201_CREATED: {
        "description": "Advisory workspace session created successfully.",
        "content": {
            "application/json": {"examples": {"stateful_workspace": WORKSPACE_CREATE_EXAMPLE}}
        },
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Validation error for invalid workspace contract payloads."
    },
}

WORKSPACE_DRAFT_ACTION_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Workspace draft action applied successfully.",
        "content": {"application/json": {"examples": {"add_trade": WORKSPACE_ADD_TRADE_EXAMPLE}}},
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Workspace session or targeted draft item not found."
    },
    status.HTTP_409_CONFLICT: {
        "description": "Workspace evaluation is not available for the current workspace mode."
    },
    HTTP_422_UNPROCESSABLE: {"description": "Validation error for invalid draft action payloads."},
}

WORKSPACE_EVALUATE_RESPONSES = {
    status.HTTP_200_OK: {"description": "Workspace re-evaluated successfully."},
    **WORKSPACE_NOT_FOUND_RESPONSE,
    status.HTTP_409_CONFLICT: {
        "description": "Workspace evaluation is not available for the current workspace mode."
    },
}

WORKSPACE_SAVE_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Workspace version saved successfully.",
        "content": {"application/json": {"examples": {"save_version": WORKSPACE_SAVE_EXAMPLE}}},
    },
    **WORKSPACE_NOT_FOUND_RESPONSE,
}

WORKSPACE_RESUME_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Workspace version resumed successfully.",
        "content": {"application/json": {"examples": {"resume_version": WORKSPACE_RESUME_EXAMPLE}}},
    },
    **WORKSPACE_SAVED_VERSION_NOT_FOUND_RESPONSE,
}

WORKSPACE_COMPARE_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Workspace comparison created successfully.",
        "content": {
            "application/json": {"examples": {"compare_version": WORKSPACE_COMPARE_EXAMPLE}}
        },
    },
    **WORKSPACE_SAVED_VERSION_NOT_FOUND_RESPONSE,
}

WORKSPACE_RATIONALE_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Workspace rationale generated successfully.",
        "content": {
            "application/json": {
                "examples": {"workspace_rationale": WORKSPACE_AI_RATIONALE_EXAMPLE}
            }
        },
    },
    **WORKSPACE_NOT_FOUND_RESPONSE,
    status.HTTP_409_CONFLICT: {"description": "Workspace is not yet ready for AI assistance."},
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Lotus AI assistance is unavailable for this runtime."
    },
}

WORKSPACE_RATIONALE_REVIEW_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Workspace rationale review action applied successfully.",
        "content": {
            "application/json": {
                "examples": {
                    "workspace_rationale_review": WORKSPACE_AI_REVIEW_ACTION_EXAMPLE,
                }
            }
        },
    },
    **WORKSPACE_NOT_FOUND_RESPONSE,
    status.HTTP_409_CONFLICT: {
        "description": "Review action conflicted with the Lotus AI run ledger state."
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Lotus AI assistance is unavailable for this runtime."
    },
}

WORKSPACE_HANDOFF_RESPONSES = {
    status.HTTP_200_OK: {
        "description": "Workspace handed off to proposal lifecycle successfully.",
        "content": {"application/json": {"examples": {"handoff": WORKSPACE_HANDOFF_EXAMPLE}}},
    },
    status.HTTP_404_NOT_FOUND: {"description": "Workspace session or linked proposal not found."},
    status.HTTP_409_CONFLICT: {
        "description": "Workspace handoff is unavailable for the current workspace state."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Lifecycle validation failed for the current workspace draft."
    },
}
