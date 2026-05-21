from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

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


def resolve_query_base_url() -> str:
    explicit = os.getenv("LOTUS_CORE_QUERY_BASE_URL")
    if explicit:
        return explicit.rstrip("/")

    configured = os.getenv("LOTUS_CORE_BASE_URL")
    if configured:
        split = urlsplit(configured)
        host = split.hostname
        if host is None:
            raise ValueError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")
        port = split.port
        netloc = host
        if split.username or split.password:
            auth = split.username or ""
            if split.password:
                auth = f"{auth}:{split.password}"
            netloc = f"{auth}@{host}"
        if port is not None:
            query_port = 8201 if port == 8202 else port
            netloc = f"{netloc}:{query_port}"
        return urlunsplit((split.scheme or "http", netloc, split.path.rstrip("/"), "", ""))
    return DEFAULT_LOTUS_CORE_QUERY_BASE_URL


def positions_path(*, portfolio_id: str, as_of: str) -> str:
    return f"{POSITIONS_PATH.format(portfolio_id=portfolio_id)}?as_of_date={as_of}"


def cash_balances_path(*, portfolio_id: str, as_of: str) -> str:
    return f"{CASH_BALANCES_PATH.format(portfolio_id=portfolio_id)}?as_of_date={as_of}"


def resolve_control_plane_base_url() -> str:
    explicit = os.getenv("LOTUS_CORE_BASE_URL")
    if explicit:
        return explicit.rstrip("/")

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
    netloc = host
    if split.username or split.password:
        auth = split.username or ""
        if split.password:
            auth = f"{auth}:{split.password}"
        netloc = f"{auth}@{host}"
    if split.port is not None:
        control_plane_port = 8202 if split.port == 8201 else split.port
        netloc = f"{netloc}:{control_plane_port}"
    return urlunsplit((split.scheme or "http", netloc, split.path.rstrip("/"), "", ""))
