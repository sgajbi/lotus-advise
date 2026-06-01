from fastapi import HTTPException, status

from src.api.runtime_flags import env_flag


def assert_feature_enabled(*, name: str, default: bool, detail: str) -> None:
    if not env_flag(name, default):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


def normalize_backend_init_error(*, detail: str, required_detail: str, fallback_detail: str) -> str:
    if detail == required_detail:
        return detail
    return fallback_detail
