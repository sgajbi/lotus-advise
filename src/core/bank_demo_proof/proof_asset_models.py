from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.artifact_refs import normalize_local_artifact_ref
from src.core.bank_demo_proof.model_common import (
    RFC28_ARTIFACT_URI_MAX_LENGTH,
    RFC28_COMMIT_ALLOWED_ACCESS_CLASSES,
    RFC28_CONTENT_HASH_MAX_LENGTH,
    RFC28_IDENTIFIER_MAX_LENGTH,
    RFC28_MAX_REF_LIST_ITEMS,
    RFC28_SHA256_HASH_PATTERN,
    ProofAssetAccessClass,
    ProofAssetType,
    ProofRetentionClass,
    normalize_ref_list,
    normalize_required_text,
)


class ProofAsset(BaseModel):
    asset_id: str = Field(
        description="Stable proof asset identifier.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    asset_type: ProofAssetType = Field(description="Proof asset family.")
    source_repository: str = Field(
        description="Repository that produced the asset.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    uri: str = Field(
        description="Relative committed or local output path for the asset.",
        max_length=RFC28_ARTIFACT_URI_MAX_LENGTH,
    )
    access_class: ProofAssetAccessClass = Field(description="Access and sharing classification.")
    retention_class: ProofRetentionClass = Field(description="Retention posture for the asset.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Claims or proof requirements this asset supports.",
    )
    content_hash: str | None = Field(
        default=None,
        max_length=RFC28_CONTENT_HASH_MAX_LENGTH,
        description="Optional stable hash for immutable or sanitized assets.",
    )
    commit_allowed: bool = Field(
        description="Whether this asset may be committed to the repository.",
    )

    @field_validator("asset_id", "source_repository")
    @classmethod
    def _asset_identifier_must_be_bounded(cls, value: str) -> str:
        return normalize_required_text(value, error_code="proof asset identifier is required")

    @field_validator("uri")
    @classmethod
    def _asset_uri_must_be_safe_local_ref(cls, value: str) -> str:
        normalized: str = normalize_local_artifact_ref(value, field_name="proof asset uri")
        return normalized

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return normalize_ref_list(value, field_name="proof asset evidence_refs")

    @field_validator("content_hash")
    @classmethod
    def _content_hash_must_be_canonical_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not RFC28_SHA256_HASH_PATTERN.fullmatch(normalized):
            raise ValueError("proof asset content_hash must be a canonical sha256 digest")
        return normalized

    @model_validator(mode="after")
    def _sensitive_assets_cannot_be_committed(self) -> ProofAsset:
        local_only_classes = {"LOCAL_ONLY_RUNTIME_EVIDENCE", "SECRET_MATERIAL"}
        if self.access_class in local_only_classes and self.commit_allowed:
            raise ValueError("local-only or secret proof assets cannot be commit_allowed")
        if self.access_class == "SECRET_MATERIAL" and self.retention_class != "DO_NOT_RETAIN":
            raise ValueError("secret proof assets must use DO_NOT_RETAIN")
        if self.commit_allowed:
            if self.access_class not in RFC28_COMMIT_ALLOWED_ACCESS_CLASSES:
                raise ValueError("commit_allowed proof assets must use a commit-safe access class")
            if self.retention_class != "COMMIT_SOURCE":
                raise ValueError("commit_allowed proof assets must use COMMIT_SOURCE retention")
            if self.content_hash is None:
                raise ValueError("commit_allowed proof assets require a content_hash")
        return self
