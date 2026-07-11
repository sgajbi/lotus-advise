"""Support-safe build and image metadata exposed to operators."""

import os
from dataclasses import asdict, dataclass

SERVICE_NAME = "lotus-advise"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class ReleaseMetadata:
    service_name: str
    service_version: str
    git_commit_sha: str
    git_branch: str
    repository_url: str
    build_timestamp_utc: str
    ci_pipeline_run_id: str
    image_digest: str

    def as_response(self) -> dict[str, str]:
        return asdict(self)


def build_release_metadata() -> ReleaseMetadata:
    return ReleaseMetadata(
        service_name=SERVICE_NAME,
        service_version=_env("LOTUS_BUILD_VERSION", "0.1.0"),
        git_commit_sha=_env("LOTUS_BUILD_COMMIT_SHA"),
        git_branch=_env("LOTUS_BUILD_GIT_BRANCH"),
        repository_url=_env("LOTUS_BUILD_REPO_URL", "https://github.com/sgajbi/lotus-advise"),
        build_timestamp_utc=_env("LOTUS_BUILD_TIMESTAMP"),
        ci_pipeline_run_id=_env("LOTUS_CI_PIPELINE_ID"),
        image_digest=_env("LOTUS_IMAGE_DIGEST"),
    )


def _env(name: str, default: str = UNKNOWN) -> str:
    value = os.getenv(name, "").strip()
    return value or default
