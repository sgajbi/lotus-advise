from __future__ import annotations

from fastapi.responses import JSONResponse


def build_problem_detail_response(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    correlation_id: str,
    problem_type: str = "about:blank",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": problem_type,
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
            "correlation_id": correlation_id,
        },
    )


__all__ = ["build_problem_detail_response"]
