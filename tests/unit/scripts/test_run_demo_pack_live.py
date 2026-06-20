import pytest

from scripts.run_demo_pack_live import (
    REQUIRED_FEATURE_KEYS,
    REQUIRED_WORKFLOW_KEYS,
    DemoRunError,
    _assert_capability_truth,
    _openapi_operations,
    _sample_path,
)


def test_openapi_operations_inventory_counts_declared_http_methods() -> None:
    schema = {
        "paths": {
            "/health": {"get": {"operationId": "health", "tags": ["Health"]}},
            "/advisory/proposals": {
                "post": {
                    "operationId": "createProposal",
                    "tags": ["Advisory Proposal Lifecycle"],
                    "requestBody": {"required": True},
                }
            },
        }
    }

    assert _openapi_operations(schema) == [
        {
            "method": "POST",
            "path": "/advisory/proposals",
            "operationId": "createProposal",
            "tags": ["Advisory Proposal Lifecycle"],
            "requiresRequestBody": True,
        },
        {
            "method": "GET",
            "path": "/health",
            "operationId": "health",
            "tags": ["Health"],
            "requiresRequestBody": False,
        },
    ]


def test_sample_path_uses_deterministic_demo_parameters() -> None:
    assert (
        _sample_path("/advisory/proposals/{proposal_id}/versions/{version_no}/memo")
        == "/advisory/proposals/demo-proposal-id/versions/1/memo"
    )


def test_capability_truth_accepts_required_ready_features_and_workflows() -> None:
    capabilities = {
        "features": [
            {"key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_FEATURE_KEYS)
        ],
        "workflows": [
            {"workflow_key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_WORKFLOW_KEYS)
        ],
        "supportability": {"state": "ready"},
        "readiness": {"operational_ready": True},
    }

    evidence = _assert_capability_truth(capabilities)

    assert evidence["requiredFeatureCount"] > 0
    assert evidence["requiredWorkflowCount"] > 0
    assert evidence["supportability"]["state"] == "ready"


def test_capability_truth_rejects_missing_required_feature() -> None:
    capabilities = {
        "features": [],
        "workflows": [],
    }

    with pytest.raises(DemoRunError, match="Missing required capability features"):
        _assert_capability_truth(capabilities)
