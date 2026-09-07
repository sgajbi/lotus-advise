"""Admitted-tenant handling for the live cross-service parity harness.

Extracted from `validate_cross_service_parity_live`, which the oversized-code gate
already flagged before this work and which these additions made worse. The tenant
rules are a coherent unit with one job, and they are easier to reason about — and
to test — away from two thousand lines of scenario assertions.

Core's enterprise middleware requires a nonblank `X-Tenant-Id` on the routes this
journey reads and answers 401 `TENANT_CONTEXT_REQUIRED` without one.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

import httpx

#: The tenant that owns the canonical seeded portfolio at source, published by
#: lotus-platform `context/contracts/canonical-front-office-demo-data-contract.json`
#: (contract 1.2.0) as `portfolio.source_tenant_id`, whose `source_tenant_authority`
#: names lotus-core's own seed constant.
#:
#: Deliberately NOT `dpm_command_center.tenant_id`, which an earlier revision of this
#: harness used. That field is the DPM command-centre query scope, and the contract
#: states the rule directly: read `portfolio.source_tenant_id` for the tenant that owns
#: the seeded portfolio, and never read caller admission as provenance "even while the
#: two values are equal". Picking the wrong field happened to work only because the
#: route it was tested against applies no tenant predicate at all (lotus-core#1102).
#:
#: Overridable so a different governed dataset can be certified without editing this
#: harness. Nothing mints a tenant: a blank override is refused.
CORE_TENANT_HEADER = "X-Tenant-Id"
DEFAULT_CORE_TENANT_ID = "tenant-sg"

DEFAULT_CORE_QUERY_BASE_URL = "http://core-query.dev.lotus"
DEFAULT_CORE_CONTROL_BASE_URL = "http://core-control.dev.lotus"


class LiveParityValidationError(RuntimeError):
    """A live parity expectation was not met."""


class LiveParityHttpError(LiveParityValidationError):
    """A non-expected HTTP status, carrying the status itself.

    The status has to travel with the error. Classifying a failure by searching its
    message for a phrase means a 401 whose body says a tenant was not found reads as
    a missing portfolio — which would skip the candidate and continue past the exact
    admission boundary this harness exists to surface.
    """

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


#: The Core base URLs this run actually resolved. Populated once at entry from the
#: same values the requests are built with, because a caller may supply them
#: explicitly rather than through the environment — re-reading the environment here
#: would match a different URL than the one being requested, and silently attach no
#: tenant. The environment defaults remain the fallback for direct callers.
_RESOLVED_CORE_BASE_URLS: tuple[str, ...] = ()


def set_resolved_core_base_urls(*, core_query_base_url: str, core_control_base_url: str) -> None:
    global _RESOLVED_CORE_BASE_URLS
    _RESOLVED_CORE_BASE_URLS = (
        core_query_base_url.rstrip("/"),
        core_control_base_url.rstrip("/"),
    )


def resolved_core_base_urls() -> tuple[str, ...]:
    if _RESOLVED_CORE_BASE_URLS:
        return _RESOLVED_CORE_BASE_URLS
    return (
        os.environ.get("LOTUS_CORE_QUERY_BASE_URL", DEFAULT_CORE_QUERY_BASE_URL).rstrip("/"),
        os.environ.get("LOTUS_CORE_BASE_URL", DEFAULT_CORE_CONTROL_BASE_URL).rstrip("/"),
    )


def core_tenant_id() -> str:
    """The admitted tenant for Core reads, refused rather than defaulted when blank.

    An empty override is a configuration mistake, and sending a blank tenant would
    reach Core as an absent claim and fail there with a less specific message. Fail
    here, where the cause is visible.
    """

    tenant_id = os.environ.get("LOTUS_PARITY_CORE_TENANT_ID", DEFAULT_CORE_TENANT_ID).strip()
    if not tenant_id:
        raise LiveParityValidationError(
            "LOTUS_PARITY_CORE_TENANT_ID is set but blank. Core requires a nonblank "
            "X-Tenant-Id; this harness does not mint or default one when the override "
            "is present and empty."
        )
    return tenant_id


def _is_same_service(url: str, base_url: str) -> bool:
    """Whether `url` belongs to the service rooted at `base_url`.

    A plain prefix test is wrong here: with Core at `http://gateway/core`, the
    string `http://gateway/core-risk/...` starts with it, so Risk would be handed a
    tenant and its response would look scoped in certification evidence. Compare the
    origin, then require the path to end at a segment boundary.
    """

    target, base = urlsplit(url), urlsplit(base_url)
    if (target.scheme, target.netloc) != (base.scheme, base.netloc):
        return False
    base_path = base.path.rstrip("/")
    if not base_path:
        return True
    return target.path == base_path or target.path.startswith(f"{base_path}/")


def with_core_tenant(url: str, headers: dict[str, str] | None) -> dict[str, str] | None:
    """Attach the admitted tenant to Core requests, and to nothing else.

    Deliberately not a default header on the shared client: the same client talks to
    Advise and Risk, and sending a tenant to a service that cannot honour it makes the
    response look scoped when it is not. That is the defect this repository has asked
    lotus-gateway not to introduce (#624), and a harness should not model the thing it
    certifies incorrectly.
    """

    if not any(_is_same_service(url, base) for base in resolved_core_base_urls()):
        return headers
    merged = dict(headers or {})
    merged.setdefault(CORE_TENANT_HEADER, core_tenant_id())
    return merged


def assert_status(response: Any, *, expected_status: int, message: str) -> None:
    if response.status_code != expected_status:
        raise LiveParityHttpError(message, status_code=response.status_code)


def request_json(
    client: httpx.Client,
    *,
    method: str,
    url: str,
    expected_status: int,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One JSON request helper for the live validators.

    Both scripts carried a near-identical copy. Sharing it means the admitted tenant
    reaches Core from either, rather than only from whichever copy was updated last --
    which is the defect this module exists to prevent, one level up.
    """

    response = client.request(method, url, json=json_body, headers=with_core_tenant(url, headers))
    assert_status(
        response,
        expected_status=expected_status,
        message=(
            f"{method} {url}: expected HTTP {expected_status}, "
            f"got {response.status_code}, body={response.text}"
        ),
    )
    payload = response.json()
    if not isinstance(payload, dict):
        raise LiveParityValidationError(f"{method} {url}: expected JSON object payload")
    return payload
