from __future__ import annotations

import os
from urllib.parse import SplitResult, urlsplit, urlunsplit

DEFAULT_LOTUS_CORE_QUERY_BASE_URL = "http://core-query.dev.lotus"
DEFAULT_LOTUS_CORE_CONTROL_PLANE_BASE_URL = "http://core-control.dev.lotus"
PORTFOLIO_PATH = "/portfolios/{portfolio_id}"
POSITIONS_PATH = "/portfolios/{portfolio_id}/positions"
CASH_BALANCES_PATH = "/portfolios/{portfolio_id}/cash-balances"
INSTRUMENTS_PATH = "/instruments/?security_id={instrument_id}"
INSTRUMENT_ENRICHMENT_BULK_PATH = "/integration/instruments/enrichment-bulk"
PRICES_PATH = "/prices/?security_id={instrument_id}"
FX_RATES_PATH = "/fx-rates/?from_currency={from_currency}&to_currency={to_currency}"
CLASSIFICATION_TAXONOMY_PATH = "/integration/reference/classification-taxonomy"


def _sanitized_base_url(value: str) -> str:
    split = urlsplit(value)
    host = split.hostname
    if host is None:
        raise ValueError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")
    return urlunsplit(
        (
            split.scheme or "http",
            _netloc_without_credentials(split, port=split.port),
            split.path.rstrip("/"),
            "",
            "",
        )
    )


def _netloc_without_credentials(split: SplitResult, *, port: int | None) -> str:
    return _netloc_from_host(host=split.hostname, port=port)


def _netloc_from_host(*, host: str | None, port: int | None) -> str:
    if host is None:
        raise ValueError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")
    netloc = host
    if port is not None:
        netloc = f"{netloc}:{port}"
    return netloc


def resolve_query_base_url() -> str:
    explicit = os.getenv("LOTUS_CORE_QUERY_BASE_URL")
    if explicit:
        return _sanitized_base_url(explicit)

    configured = os.getenv("LOTUS_CORE_BASE_URL")
    if configured:
        split = urlsplit(configured)
        host = split.hostname
        if host is None:
            raise ValueError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")
        configured_port = split.port
        port = configured_port
        if port is not None:
            query_port = 8201 if port == 8202 else port
            port = query_port
        return urlunsplit(
            (
                split.scheme or "http",
                _netloc_without_credentials(split, port=port),
                split.path.rstrip("/"),
                "",
                "",
            )
        )
    return DEFAULT_LOTUS_CORE_QUERY_BASE_URL


def positions_path(*, portfolio_id: str, as_of: str) -> str:
    return f"{POSITIONS_PATH.format(portfolio_id=portfolio_id)}?as_of_date={as_of}"


def cash_balances_path(*, portfolio_id: str, as_of: str) -> str:
    return f"{CASH_BALANCES_PATH.format(portfolio_id=portfolio_id)}?as_of_date={as_of}"


def resolve_control_plane_base_url() -> str:
    explicit = os.getenv("LOTUS_CORE_BASE_URL")
    if explicit:
        return _sanitized_base_url(explicit)

    query_base_url = os.getenv("LOTUS_CORE_QUERY_BASE_URL")
    if not query_base_url:
        return DEFAULT_LOTUS_CORE_CONTROL_PLANE_BASE_URL

    split = urlsplit(query_base_url)
    host = split.hostname
    if host is None:
        raise ValueError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")
    if host == "core-query.dev.lotus":
        host = "core-control.dev.lotus"
    elif host == "lotus-core-query":
        host = "lotus-core-control"
    port = split.port
    if port is not None:
        port = 8202 if port == 8201 else port
    return urlunsplit(
        (
            split.scheme or "http",
            _netloc_from_host(host=host, port=port),
            split.path.rstrip("/"),
            "",
            "",
        )
    )
