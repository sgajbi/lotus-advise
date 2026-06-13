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

LOCAL_ONLY_PROOF_ASSET_ACCESS_CLASSES = frozenset(
    {"LOCAL_ONLY_RUNTIME_EVIDENCE", "SECRET_MATERIAL"}
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
        normalized: str = normalize_required_text(
            value,
            error_code="proof asset identifier is required",
        )
        return normalized

    @field_validator("uri")
    @classmethod
    def _asset_uri_must_be_safe_local_ref(cls, value: str) -> str:
        normalized: str = normalize_local_artifact_ref(value, field_name="proof asset uri")
        return normalized

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        normalized: list[str] = normalize_ref_list(value, field_name="proof asset evidence_refs")
        return normalized

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
        _ensure_local_only_assets_are_not_committed(
            access_class=self.access_class,
            commit_allowed=self.commit_allowed,
        )
        _ensure_secret_asset_retention(
            access_class=self.access_class,
            retention_class=self.retention_class,
        )
        _ensure_commit_allowed_asset_is_safe(
            access_class=self.access_class,
            retention_class=self.retention_class,
            content_hash=self.content_hash,
            commit_allowed=self.commit_allowed,
        )
        return self


def _ensure_local_only_assets_are_not_committed(
    *,
    access_class: ProofAssetAccessClass,
    commit_allowed: bool,
) -> None:
    if access_class in LOCAL_ONLY_PROOF_ASSET_ACCESS_CLASSES and commit_allowed:
        raise ValueError("local-only or secret proof assets cannot be commit_allowed")


def _ensure_secret_asset_retention(
    *,
    access_class: ProofAssetAccessClass,
    retention_class: ProofRetentionClass,
) -> None:
    if access_class == "SECRET_MATERIAL" and retention_class != "DO_NOT_RETAIN":
        raise ValueError("secret proof assets must use DO_NOT_RETAIN")


def _ensure_commit_allowed_asset_is_safe(
    *,
    access_class: ProofAssetAccessClass,
    retention_class: ProofRetentionClass,
    content_hash: str | None,
    commit_allowed: bool,
) -> None:
    if not commit_allowed:
        return
    _ensure_commit_allowed_access_class(access_class)
    _ensure_commit_allowed_retention(retention_class)
    _ensure_commit_allowed_content_hash(content_hash)


def _ensure_commit_allowed_access_class(access_class: ProofAssetAccessClass) -> None:
    if access_class not in RFC28_COMMIT_ALLOWED_ACCESS_CLASSES:
        raise ValueError("commit_allowed proof assets must use a commit-safe access class")


def _ensure_commit_allowed_retention(retention_class: ProofRetentionClass) -> None:
    if retention_class != "COMMIT_SOURCE":
        raise ValueError("commit_allowed proof assets must use COMMIT_SOURCE retention")


def _ensure_commit_allowed_content_hash(content_hash: str | None) -> None:
    if content_hash is None:
        raise ValueError("commit_allowed proof assets require a content_hash")
