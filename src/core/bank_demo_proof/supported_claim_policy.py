from __future__ import annotations

from src.core.bank_demo_proof.supported_claim_models import ArtifactPolicy


def build_supported_claim_artifact_policy() -> ArtifactPolicy:
    return ArtifactPolicy(
        commit_allowed_access_classes=[
            "COMMIT_SAFE_SUMMARY",
            "CUSTOMER_CONSUMABLE_SUMMARY",
        ],
        local_only_access_classes=[
            "LOCAL_ONLY_RUNTIME_EVIDENCE",
            "SECRET_MATERIAL",
        ],
        sensitive_material_rules=[
            "Secrets, tokens, prompts, raw provider payloads, and raw runtime logs stay local "
            "and must not be committed or used in client-facing proof material.",
        ],
    )
