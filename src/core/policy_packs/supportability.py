from __future__ import annotations

from typing import Any

POLICY_CATALOG_CONTRACT_VERSION = "rfc0025.policy-pack-catalog.v1"
POLICY_EVALUATION_ENGINE_CONTRACT_VERSION = "rfc0025.policy-evaluation-engine.v1"
POLICY_EVALUATION_PERSISTENCE_CONTRACT_VERSION = "rfc0025.policy-evaluation-persistence.v1"
POLICY_WORKFLOW_CONTRACT_VERSION = "rfc0025.policy-sign-off-workflow.v1"
POLICY_REPORTING_CONTRACT_VERSION = "rfc0025.policy-report-package-realization.v1"

REFERENCE_POLICY_PACK_POSTURE = "REFERENCE_EXAMPLE_NOT_LEGAL_ADVICE"
CLIENT_READY_PUBLICATION_POSTURE = "BLOCKED"


def policy_runtime_supportability() -> dict[str, Any]:
    return {
        "catalog_contract_version": POLICY_CATALOG_CONTRACT_VERSION,
        "reference_posture": REFERENCE_POLICY_PACK_POSTURE,
        "policy_catalog": "SUPPORTED_BY_RFC0025_SLICE5",
        "policy_activation": "SUPPORTED_BY_RFC0025_SLICE5",
        "policy_evaluation": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API",
        "policy_evaluation_engine": "SUPPORTED_BY_RFC0025_SLICE6",
        "policy_evaluation_persistence": "SUPPORTED_BY_RFC0025_SLICE7_INTERNAL",
        "policy_evaluation_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API",
        "review_queue_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API",
        "sign_off_package_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API",
        "sign_off_decision_recording": "SUPPORTED_BY_RFC0025_SLICE9_ADVISE_API",
        "report_package_realization": "SUPPORTED_BY_RFC0025_SLICE10_SIGNED_OFF_PACKAGE",
        "ai_policy_evidence": "SUPPORTED_BY_RFC0025_SLICE11_BOUNDED_NON_AUTHORITATIVE",
        "gateway_supported": True,
        "gateway_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF",
        "workbench_supported": True,
        "workbench_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI",
        "live_runtime_proof": "SUPPORTED_BY_RFC0025_SLICE14_LIVE_SUITE",
        "active_data_product_promotion": "BLOCKED_UNTIL_FINAL_CLOSURE",
        "completed_compliance_authority": "BLOCKED",
        "client_ready_publication": CLIENT_READY_PUBLICATION_POSTURE,
    }


def policy_sign_off_package_posture() -> dict[str, Any]:
    return {
        **policy_runtime_supportability(),
        "sign_off_source_package": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API",
        "report_render_archive_realization": (
            "SUPPORTED_BY_RFC0025_SLICE10_SIGNED_OFF_PACKAGE_HANDOFF"
        ),
    }
