from __future__ import annotations

from typing import Any


class FakeHttpxResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("boom")

    def json(self) -> Any:
        return self._payload


class CountingLotusCoreQueryClient:
    def __init__(self, responses: dict[tuple[str, str], FakeHttpxResponse]) -> None:
        self._responses = responses
        self.request_count = 0
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def __enter__(self) -> CountingLotusCoreQueryClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def request(
        self,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,
    ) -> FakeHttpxResponse:
        self.request_count += 1
        self.requests.append((method.upper(), url, json))
        key = (method.upper(), url)
        if key not in self._responses and "?" in url:
            key = (method.upper(), url.split("?", 1)[0])
        if key not in self._responses:
            raise AssertionError(f"unexpected request: {key} body={json}")
        return self._responses[key]


def build_basic_stateful_query_responses(
    *,
    base_url: str,
    portfolio_id: str,
    as_of: str,
    base_currency: str = "USD",
) -> dict[tuple[str, str], FakeHttpxResponse]:
    return {
        ("GET", f"{base_url}/portfolios/{portfolio_id}"): FakeHttpxResponse(
            {"portfolio_id": portfolio_id, "base_currency": base_currency}
        ),
        ("GET", f"{base_url}/portfolios/{portfolio_id}/positions"): FakeHttpxResponse(
            {"portfolio_id": portfolio_id, "positions": []}
        ),
        ("POST", f"{base_url}/reporting/cash-balances/query"): FakeHttpxResponse(
            {
                "portfolio_id": portfolio_id,
                "resolved_as_of_date": as_of,
                "cash_accounts": [],
            }
        ),
    }
