from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from src.core.source_completeness_models import (
    SourceCollectionCompleteness,
    SourceCompletenessReport,
    SourceCompletenessStatus,
)
from src.integrations.lotus_core.classification import ClassificationTaxonomy
from src.integrations.lotus_core.stateful_context_payload_values import (
    decimal_or_none,
    is_cash_asset_class,
    normalized_text,
)

_MAX_AFFECTED_REFS = 20


@dataclass(frozen=True)
class _PositionRowCompleteness:
    instrument_id: str | None = None
    rejection_reason: str | None = None
    affected_ref: str | None = None


@dataclass(frozen=True)
class _PriceRejection:
    reason: str
    affected_ref: str


def build_lotus_core_source_completeness(
    *,
    portfolio_id: str,
    resolved_as_of: str,
    portfolio_base_currency: str,
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
    enrichment_by_instrument_id: dict[str, dict[str, Any]],
    classification_taxonomy: ClassificationTaxonomy | None,
    classification_taxonomy_unavailable: bool,
    enrichment_malformed_record_count: int = 0,
) -> SourceCompletenessReport:
    requested_instrument_ids = sorted(_held_security_ids(positions_payload))
    collections = [
        _positions_completeness(positions_payload, portfolio_base_currency=portfolio_base_currency),
        _cash_completeness(cash_payload),
        _prices_completeness(positions_payload),
        _fx_completeness(
            positions_payload=positions_payload,
            cash_payload=cash_payload,
            portfolio_base_currency=portfolio_base_currency,
        ),
        _instrument_enrichment_completeness(
            requested_instrument_ids=requested_instrument_ids,
            enrichment_by_instrument_id=enrichment_by_instrument_id,
            malformed_record_count=enrichment_malformed_record_count,
        ),
        _classification_taxonomy_completeness(
            classification_taxonomy=classification_taxonomy,
            classification_taxonomy_unavailable=classification_taxonomy_unavailable,
        ),
    ]
    return SourceCompletenessReport(
        source_system="LOTUS_CORE",
        portfolio_id=portfolio_id,
        as_of=resolved_as_of,
        status=_overall_status(collections),
        collections=collections,
    )


def _positions_completeness(
    positions_payload: dict[str, Any],
    *,
    portfolio_base_currency: str,
) -> SourceCollectionCompleteness:
    tracker = _CollectionTracker("POSITIONS", required=True)
    rows = _source_rows(positions_payload, "positions", tracker)
    accepted_instrument_ids: list[str] = []
    for index, row in enumerate(rows):
        if not _require_mapping_row(tracker, row, index):
            continue
        result = _position_row_completeness(
            row,
            index=index,
            portfolio_base_currency=portfolio_base_currency,
        )
        if result.rejection_reason is not None:
            tracker.reject(result.rejection_reason, ref=result.affected_ref, index=index)
            continue
        if result.instrument_id is not None:
            accepted_instrument_ids.append(result.instrument_id)
        tracker.accepted_count += 1
    tracker.duplicate_count = _duplicate_count(accepted_instrument_ids)
    if tracker.duplicate_count:
        tracker.add_refs("DUPLICATE_INSTRUMENT", _duplicates(accepted_instrument_ids))
    return tracker.to_summary()


def _position_row_completeness(
    row: dict[str, Any],
    *,
    index: int,
    portfolio_base_currency: str,
) -> _PositionRowCompleteness:
    if is_cash_asset_class(row.get("asset_class")):
        return _PositionRowCompleteness()
    instrument_id = normalized_text(row.get("security_id"))
    if not instrument_id:
        return _PositionRowCompleteness(
            rejection_reason="MISSING_SECURITY_ID",
            affected_ref=f"row:{index}",
        )
    rejection_reason = _position_rejection_reason(
        row,
        portfolio_base_currency=portfolio_base_currency,
    )
    return _PositionRowCompleteness(
        instrument_id=instrument_id,
        rejection_reason=rejection_reason,
        affected_ref=instrument_id if rejection_reason is not None else None,
    )


def _position_rejection_reason(
    row: dict[str, Any],
    *,
    portfolio_base_currency: str,
) -> str | None:
    if not _valid_required_decimal(row.get("quantity")):
        return "INVALID_QUANTITY"
    if not normalized_text(row.get("currency")):
        return "MISSING_CURRENCY"
    valuation = row.get("valuation")
    if not isinstance(valuation, dict):
        return "MISSING_VALUATION"
    if not _valid_required_decimal(valuation.get("market_value")):
        return "INVALID_MARKET_VALUE"
    if not _valid_positive_decimal(valuation.get("market_price")):
        return "INVALID_MARKET_PRICE"
    if not _has_valid_position_fx_inputs(
        row,
        valuation=valuation,
        portfolio_base_currency=portfolio_base_currency,
    ):
        return "INVALID_FX_SOURCE_VALUE"
    return None


def _cash_completeness(cash_payload: dict[str, Any]) -> SourceCollectionCompleteness:
    tracker = _CollectionTracker("CASH_BALANCES", required=True)
    rows = _source_rows(cash_payload, "cash_accounts", tracker)
    accepted_currencies: list[str] = []
    for index, row in enumerate(rows):
        if not _require_mapping_row(tracker, row, index):
            continue
        currency = normalized_text(row.get("account_currency"))
        if not currency:
            tracker.reject("MISSING_CURRENCY", index=index)
            continue
        accepted_currencies.append(currency)
        if not _valid_required_decimal(row.get("balance_account_currency")):
            tracker.reject("INVALID_CASH_AMOUNT", ref=currency)
            continue
        tracker.accepted_count += 1
    tracker.duplicate_count = _duplicate_count(accepted_currencies)
    if tracker.duplicate_count:
        tracker.add_refs("DUPLICATE_CURRENCY", _duplicates(accepted_currencies))
    return tracker.to_summary()


def _prices_completeness(positions_payload: dict[str, Any]) -> SourceCollectionCompleteness:
    tracker = _CollectionTracker("PRICES", required=True)
    rows = _source_rows(positions_payload, "positions", tracker, track_received=False)
    price_rows = [(index, row) for index, row in enumerate(rows) if _requires_price(row)]
    tracker.received_count = len(price_rows)
    for index, row in price_rows:
        price_rejection = _price_rejection(row, index=index)
        if price_rejection is None:
            tracker.accepted_count += 1
            continue
        tracker.reject(price_rejection.reason, ref=price_rejection.affected_ref)
    return tracker.to_summary()


def _requires_price(row: Any) -> bool:
    return isinstance(row, dict) and not is_cash_asset_class(row.get("asset_class"))


def _price_rejection(row: Any, *, index: int) -> _PriceRejection | None:
    if not _requires_price(row):
        return None
    instrument_id = normalized_text(row.get("security_id")) or f"row:{index}"
    valuation = row.get("valuation")
    if not isinstance(valuation, dict):
        return _PriceRejection("MISSING_PRICE_VALUATION", instrument_id)
    if not _valid_positive_decimal(valuation.get("market_price")):
        return _PriceRejection("INVALID_MARKET_PRICE", instrument_id)
    if not normalized_text(row.get("currency")):
        return _PriceRejection("MISSING_PRICE_CURRENCY", instrument_id)
    return None


def _fx_completeness(
    *,
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
    portfolio_base_currency: str,
) -> SourceCollectionCompleteness:
    tracker = _CollectionTracker("FX_RATES", required=True)
    accepted_pairs: list[str] = []
    _record_position_fx_completeness(
        tracker,
        accepted_pairs=accepted_pairs,
        positions_payload=positions_payload,
        portfolio_base_currency=portfolio_base_currency,
    )
    _record_cash_fx_completeness(
        tracker,
        accepted_pairs=accepted_pairs,
        cash_payload=cash_payload,
        portfolio_base_currency=portfolio_base_currency,
    )
    tracker.duplicate_count = _duplicate_count(accepted_pairs)
    if tracker.duplicate_count:
        tracker.add_refs("DUPLICATE_FX_PAIR", _duplicates(accepted_pairs))
    return tracker.to_summary()


def _record_position_fx_completeness(
    tracker: "_CollectionTracker",
    *,
    accepted_pairs: list[str],
    positions_payload: dict[str, Any],
    portfolio_base_currency: str,
) -> None:
    for index, row in enumerate(
        _source_rows(positions_payload, "positions", tracker, track_received=False)
    ):
        if not isinstance(row, dict) or is_cash_asset_class(row.get("asset_class")):
            continue
        instrument_currency = normalized_text(row.get("currency"))
        if not instrument_currency or instrument_currency == portfolio_base_currency:
            continue
        tracker.received_count += 1
        instrument_id = normalized_text(row.get("security_id")) or f"row:{index}"
        valuation = row.get("valuation")
        if not isinstance(valuation, dict) or not _valid_required_decimal(
            valuation.get("market_value")
        ):
            tracker.reject("INVALID_FX_SOURCE_VALUE", ref=instrument_id)
            continue
        if not _valid_non_zero_decimal(valuation.get("market_value_local")):
            tracker.reject("INVALID_FX_SOURCE_VALUE", ref=instrument_id)
            continue
        accepted_pairs.append(f"{instrument_currency}/{portfolio_base_currency}")
        tracker.accepted_count += 1


def _record_cash_fx_completeness(
    tracker: "_CollectionTracker",
    *,
    accepted_pairs: list[str],
    cash_payload: dict[str, Any],
    portfolio_base_currency: str,
) -> None:
    for index, row in enumerate(
        _source_rows(cash_payload, "cash_accounts", tracker, track_received=False)
    ):
        if not isinstance(row, dict):
            continue
        account_currency = normalized_text(row.get("account_currency"))
        if not account_currency or account_currency == portfolio_base_currency:
            continue
        tracker.received_count += 1
        if not _valid_required_decimal(row.get("balance_portfolio_currency")):
            tracker.reject("INVALID_FX_SOURCE_VALUE", ref=account_currency or f"row:{index}")
            continue
        if not _valid_non_zero_decimal(row.get("balance_account_currency")):
            tracker.reject("INVALID_FX_SOURCE_VALUE", ref=account_currency or f"row:{index}")
            continue
        accepted_pairs.append(f"{account_currency}/{portfolio_base_currency}")
        tracker.accepted_count += 1


def _instrument_enrichment_completeness(
    *,
    requested_instrument_ids: list[str],
    enrichment_by_instrument_id: dict[str, dict[str, Any]],
    malformed_record_count: int,
) -> SourceCollectionCompleteness:
    tracker = _CollectionTracker("INSTRUMENT_ENRICHMENT", required=False)
    tracker.received_count = len(requested_instrument_ids)
    if malformed_record_count:
        tracker.rejected_count += malformed_record_count
        tracker.rejection_reasons["MALFORMED_ENRICHMENT"] = malformed_record_count
        tracker.add_refs(
            "MALFORMED_ENRICHMENT",
            [f"record:{index}" for index in range(malformed_record_count)],
        )
    for instrument_id in requested_instrument_ids:
        if instrument_id in enrichment_by_instrument_id:
            tracker.accepted_count += 1
        else:
            tracker.reject("MISSING_ENRICHMENT", ref=instrument_id)
    return tracker.to_summary()


def _classification_taxonomy_completeness(
    *,
    classification_taxonomy: ClassificationTaxonomy | None,
    classification_taxonomy_unavailable: bool,
) -> SourceCollectionCompleteness:
    tracker = _CollectionTracker("CLASSIFICATION_TAXONOMY", required=False)
    tracker.received_count = 1
    if classification_taxonomy_unavailable:
        tracker.reject("CLASSIFICATION_TAXONOMY_UNAVAILABLE", ref="taxonomy")
    elif classification_taxonomy is None or not classification_taxonomy.labels_by_dimension:
        tracker.reject("EMPTY_CLASSIFICATION_TAXONOMY", ref="taxonomy")
    else:
        tracker.accepted_count = 1
    return tracker.to_summary()


def _source_rows(
    payload: dict[str, Any],
    key: str,
    tracker: "_CollectionTracker",
    *,
    track_received: bool = True,
) -> list[Any]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        if track_received:
            tracker.received_count = 0
        tracker.reject("COLLECTION_NOT_LIST", ref=key)
        return []
    if track_received:
        tracker.received_count = len(rows)
    return rows


def _require_mapping_row(tracker: "_CollectionTracker", row: Any, index: int) -> bool:
    if isinstance(row, dict):
        return True
    tracker.reject("NON_OBJECT_ROW", index=index)
    return False


def _has_valid_position_fx_inputs(
    row: dict[str, Any],
    *,
    valuation: dict[str, Any],
    portfolio_base_currency: str,
) -> bool:
    instrument_currency = normalized_text(row.get("currency"))
    if not instrument_currency or instrument_currency == portfolio_base_currency:
        return True
    return _valid_non_zero_decimal(valuation.get("market_value_local"))


def _held_security_ids(positions_payload: dict[str, Any]) -> set[str]:
    security_ids: set[str] = set()
    rows = positions_payload.get("positions")
    if not isinstance(rows, list):
        return security_ids
    for row in rows:
        if not isinstance(row, dict) or is_cash_asset_class(row.get("asset_class")):
            continue
        security_id = normalized_text(row.get("security_id"))
        if security_id:
            security_ids.add(security_id)
    return security_ids


def _valid_required_decimal(value: Any) -> bool:
    decimal_value = decimal_or_none(value)
    return decimal_value is not None and decimal_value.is_finite()


def _valid_non_zero_decimal(value: Any) -> bool:
    decimal_value = decimal_or_none(value)
    return decimal_value is not None and decimal_value.is_finite() and decimal_value != Decimal("0")


def _valid_positive_decimal(value: Any) -> bool:
    decimal_value = decimal_or_none(value)
    return decimal_value is not None and decimal_value.is_finite() and decimal_value > Decimal("0")


def _duplicate_count(values: Iterable[str]) -> int:
    counts = Counter(values)
    return sum(count - 1 for count in counts.values() if count > 1)


def _duplicates(values: Iterable[str]) -> list[str]:
    return [value for value, count in Counter(values).items() if count > 1]


def _overall_status(
    collections: list[SourceCollectionCompleteness],
) -> SourceCompletenessStatus:
    if any(collection.required and collection.rejected_count for collection in collections):
        return "INCOMPLETE"
    if any(collection.rejected_count or collection.duplicate_count for collection in collections):
        return "DEGRADED"
    return "COMPLETE"


class _CollectionTracker:
    def __init__(self, source_collection: str, *, required: bool) -> None:
        self.source_collection = source_collection
        self.required = required
        self.received_count = 0
        self.accepted_count = 0
        self.rejected_count = 0
        self.duplicate_count = 0
        self.rejection_reasons: dict[str, int] = {}
        self.affected_refs: list[str] = []

    def reject(self, reason: str, *, index: int | None = None, ref: str | None = None) -> None:
        self.rejected_count += 1
        self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1
        affected_ref = ref if ref is not None else f"row:{index}"
        self.add_refs(reason, [affected_ref])

    def add_refs(self, reason: str, refs: Iterable[str]) -> None:
        for ref in refs:
            if len(self.affected_refs) >= _MAX_AFFECTED_REFS:
                return
            self.affected_refs.append(f"{ref}:{reason}")

    def to_summary(self) -> SourceCollectionCompleteness:
        return SourceCollectionCompleteness(
            source_collection=self.source_collection,
            required=self.required,
            received_count=self.received_count,
            accepted_count=self.accepted_count,
            rejected_count=self.rejected_count,
            duplicate_count=self.duplicate_count,
            rejection_reasons=dict(sorted(self.rejection_reasons.items())),
            affected_refs=list(self.affected_refs),
            status=self._status(),
        )

    def _status(self) -> SourceCompletenessStatus:
        if self.required and self.rejected_count:
            return "INCOMPLETE"
        if self.rejected_count or self.duplicate_count:
            return "DEGRADED"
        return "COMPLETE"


__all__ = ["build_lotus_core_source_completeness"]
