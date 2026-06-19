from decimal import Decimal
from typing import Any

from src.core.advisory.artifact_formatting import decimal_to_str, quantized_weight_str
from src.core.advisory.artifact_trade_models import (
    ProposalArtifactExecutionNote,
    ProposalArtifactFx,
    ProposalArtifactTrade,
    ProposalArtifactTradeRationale,
    ProposalArtifactTradesAndFunding,
)
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult

ZERO_AMOUNT = Decimal("0")


def build_trades_and_funding(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactTradesAndFunding:
    fx_rates = _fx_rates_by_pair(request)
    trade_list = _proposal_artifact_trades(result.intents)
    fx_list = _proposal_artifact_fx_list(result.intents, fx_rates=fx_rates)

    return ProposalArtifactTradesAndFunding(
        trade_list=trade_list,
        fx_list=sorted(fx_list, key=lambda item: (item.pair, item.intent_id)),
        ordering_policy="CASH_FLOW->SELL->FX->BUY",
        execution_notes=_execution_notes(has_dependencies=_has_trade_dependencies(result.intents)),
    )


def _fx_rates_by_pair(request: ProposalSimulateRequest) -> dict[str, Decimal]:
    return {row.pair: row.rate for row in request.market_data_snapshot.fx_rates}


def _proposal_artifact_trades(intents: list[Any]) -> list[ProposalArtifactTrade]:
    return [
        _proposal_artifact_trade(intent)
        for intent in intents
        if intent.intent_type == "SECURITY_TRADE"
    ]


def _proposal_artifact_fx_list(
    intents: list[Any], *, fx_rates: dict[str, Decimal]
) -> list[ProposalArtifactFx]:
    return [
        _proposal_artifact_fx(intent, fx_rates=fx_rates)
        for intent in intents
        if intent.intent_type == "FX_SPOT"
    ]


def _has_trade_dependencies(intents: list[Any]) -> bool:
    return any(
        bool(intent.dependencies) for intent in intents if intent.intent_type == "SECURITY_TRADE"
    )


def _proposal_artifact_trade(intent: Any) -> ProposalArtifactTrade:
    rationale = getattr(intent, "rationale", None)
    return ProposalArtifactTrade(
        intent_id=intent.intent_id,
        type="SECURITY_TRADE",
        instrument_id=intent.instrument_id,
        side=intent.side,
        quantity=decimal_to_str(intent.quantity or ZERO_AMOUNT),
        estimated_notional=intent.notional,
        estimated_notional_base=intent.notional_base,
        dependencies=intent.dependencies,
        rationale=ProposalArtifactTradeRationale(
            code=(rationale.code if rationale else "MANUAL_PROPOSAL"),
            message=(
                rationale.message
                if rationale
                else "Manual advisory trade from proposal simulation."
            ),
        ),
    )


def _proposal_artifact_fx(intent: Any, *, fx_rates: dict[str, Decimal]) -> ProposalArtifactFx:
    return ProposalArtifactFx(
        intent_id=intent.intent_id,
        pair=intent.pair,
        buy_amount=decimal_to_str(intent.buy_amount),
        sell_amount_estimated=decimal_to_str(intent.sell_amount_estimated),
        rate=quantized_weight_str(fx_rates[intent.pair]) if intent.pair in fx_rates else None,
    )


def _execution_notes(*, has_dependencies: bool) -> list[ProposalArtifactExecutionNote]:
    if not has_dependencies:
        return []
    return [
        ProposalArtifactExecutionNote(
            code="DEPENDENCY",
            text="One or more BUY intents depend on generated FX intents.",
        )
    ]
