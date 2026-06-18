from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from zulu_contracts import CleanSignalV1, NearMissLabel, TradeOutcomeLabel

from zulu_learning.models import (
    DurableNearMiss,
    DurableTradeOutcome,
    NearMissDetails,
    OutcomeLabelDetails,
)
from zulu_learning.repository import InMemoryLearningRepository


class OutcomeLabeler:
    def __init__(self, repository: InMemoryLearningRepository) -> None:
        self.repository = repository

    def label_trade(
        self,
        *,
        signal: CleanSignalV1,
        details: OutcomeLabelDetails,
        labeled_at: datetime,
    ) -> DurableTradeOutcome:
        label = TradeOutcomeLabel(
            trade_outcome_id=_id("outcome", signal.signal_id, labeled_at.isoformat()),
            tenant_id=signal.tenant_id,
            signal_id=signal.signal_id,
            realized_pnl=details.final_pnl,
            max_adverse_excursion=details.max_adverse_excursion,
            max_favorable_excursion=details.max_favorable_excursion,
            label=_trade_label(details.final_pnl, details.stop_loss_reached),
            labeled_at=labeled_at,
        )
        durable = DurableTradeOutcome(label=label, details=details)
        self.repository.add_trade_outcome(durable)
        return durable


class NearMissLabeler:
    def __init__(self, repository: InMemoryLearningRepository) -> None:
        self.repository = repository

    def label_near_miss(
        self,
        *,
        signal: CleanSignalV1,
        details: NearMissDetails,
        labeled_at: datetime,
    ) -> DurableNearMiss:
        label = NearMissLabel(
            near_miss_id=_id("near_miss", signal.signal_id, labeled_at.isoformat()),
            tenant_id=signal.tenant_id,
            signal_id=signal.signal_id,
            reason=details.rejection_or_skip_reason,
            would_have_triggered=details.entry_trigger_fired,
            labeled_at=labeled_at,
        )
        durable = DurableNearMiss(label=label, details=details)
        self.repository.add_near_miss(durable)
        return durable


def _trade_label(final_pnl: Decimal, stop_loss_reached: bool) -> str:
    if stop_loss_reached:
        return "stopped_out"
    if final_pnl > Decimal("0"):
        return "win"
    if final_pnl < Decimal("0"):
        return "loss"
    return "breakeven"


def _id(prefix: str, *parts: str) -> str:
    digest = sha256(":".join(parts).encode()).hexdigest()
    return f"{prefix}_{digest[:24]}"
