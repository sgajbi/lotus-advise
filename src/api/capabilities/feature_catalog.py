from __future__ import annotations

from src.api.capabilities.dependencies import (
    DependencyMap,
    resolve_capability_dependency_status,
)
from src.api.capabilities.feature_catalog_evidence_products import (
    build_evidence_product_feature_capabilities,
)
from src.api.capabilities.feature_catalog_foundation import (
    build_foundational_feature_capabilities,
)
from src.api.capabilities.feature_catalog_operations import (
    build_operational_feature_capabilities,
)
from src.api.capabilities.models import FeatureCapability


def build_feature_capabilities(
    *,
    lifecycle_enabled: bool,
    async_enabled: bool,
    ai_rationale_enabled: bool,
    dependencies: DependencyMap,
) -> list[FeatureCapability]:
    dependency_status = resolve_capability_dependency_status(
        lifecycle_enabled=lifecycle_enabled,
        dependencies=dependencies,
    )

    return [
        *build_foundational_feature_capabilities(
            lifecycle_enabled=lifecycle_enabled,
            async_enabled=async_enabled,
            ai_rationale_enabled=ai_rationale_enabled,
            dependency_status=dependency_status,
        ),
        *build_evidence_product_feature_capabilities(
            lifecycle_enabled=lifecycle_enabled,
            dependency_status=dependency_status,
        ),
        *build_operational_feature_capabilities(
            lifecycle_enabled=lifecycle_enabled,
        ),
    ]


__all__ = ["build_feature_capabilities"]
